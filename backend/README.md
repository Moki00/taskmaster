# Taskmaster Backend

FastAPI backend and multi-agent AI pipeline for Taskmaster. See [`GEMINI.md`](../GEMINI.md) at the repo root for full project context, architecture, and engineering rules.

## Requirements

- Python 3.11+

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env           # fill in required values
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/health`

## Test

```bash
pytest
```

## Structure

See the "Backend folder structure (target)" section of [`GEMINI.md`](../GEMINI.md).
