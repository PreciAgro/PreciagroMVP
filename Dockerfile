FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=on \
    POETRY_VERSION=1.8.3 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN chmod +x scripts/entrypoint_cie.sh

EXPOSE 8082

ENTRYPOINT ["scripts/entrypoint_cie.sh"]
