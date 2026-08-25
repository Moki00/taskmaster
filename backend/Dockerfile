FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir -e .

COPY app ./app

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
