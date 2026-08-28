"""Application settings, loaded from environment / .env. See ../.env.example for every variable.

This is the ONLY place environment configuration is read. Agents, channels, and integrations
must receive values from `settings`, never call os.environ directly.
"""
from __future__ import annotations

import sys
from typing import Literal

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Runtime ──────────────────────────────────────────────────────────
    ENV: Literal["local", "dev", "staging", "production"] = "local"
    LOG_LEVEL: str = "INFO"

    # ── Gemini / Agent Platform ─────────────────────────────────────────
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash"
    USE_ENTERPRISE: bool = True
    USE_VERTEXAI: bool = True

    # ── Google Cloud (required) ─────────────────────────────────────────
    GCP_PROJECT_ID: str = "hackathon8-20"
    GCP_REGION: str = "us-central1"
    FIRESTORE_COLLECTION_PREFIX: str = "taskmaster"

    # ── Vertical config (required) ──────────────────────────────────────
    ACTIVE_VERTICAL: str

    # ── Gmail channel ────────────────────────────────────────────────────
    GMAIL_CLIENT_ID: str | None = None
    GMAIL_CLIENT_SECRET: str | None = None
    GMAIL_REFRESH_TOKEN: str | None = None
    GMAIL_SENDER_EMAIL: str | None = None

    # ── Twilio channel (SMS + voice) ────────────────────────────────────
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_FROM_NUMBER: str | None = None

    # ── Scheduler ────────────────────────────────────────────────────────
    CALENDAR_ID: str | None = None

    # ── Safety switch ────────────────────────────────────────────────────
    AUTO_SEND_REPLIES: bool = False


def _load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        missing = sorted({str(err["loc"][0]) for err in exc.errors() if err["type"] == "missing"})
        if missing:
            sys.stderr.write(
                "Taskmaster failed to start: missing required environment variable(s): "
                f"{', '.join(missing)}.\n"
                "Copy backend/.env.example to backend/.env and fill these in.\n"
            )
        else:
            sys.stderr.write(f"Taskmaster failed to start: invalid configuration.\n{exc}\n")
        raise SystemExit(1) from exc


settings = _load_settings()