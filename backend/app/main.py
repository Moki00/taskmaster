"""FastAPI app entrypoint. No agent or channel routes here yet — /health only."""
from __future__ import annotations

import logging
import time
import uuid
from importlib.metadata import PackageNotFoundError, version

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings

try:
    APP_VERSION = version("taskmaster-backend")
except PackageNotFoundError:
    APP_VERSION = "0.0.0-dev"


def _configure_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_logging()
log = structlog.get_logger("taskmaster")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Binds a request id to every log line emitted while handling a request, and logs start/end + latency."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        log.info("request_started", method=request.method, path=request.url.path)
        try:
            response: Response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            log.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                elapsed_ms=elapsed_ms,
            )
            raise

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        log.info(
            "request_finished",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )
        return response


app = FastAPI(title="Taskmaster API", version=APP_VERSION)
app.add_middleware(RequestIDMiddleware)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": APP_VERSION,
        "env": settings.ENV,
        "active_vertical": settings.ACTIVE_VERTICAL,
    }
