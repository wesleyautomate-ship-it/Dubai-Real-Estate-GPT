# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for psycopg2 and other native extensions
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY backend ./backend
COPY database ./database
COPY tests ./tests

ENV PYTHONPATH=/app \
    API_HOST=0.0.0.0 \
    API_PORT=8787

EXPOSE 8787

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8787"]
