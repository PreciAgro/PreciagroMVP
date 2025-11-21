# Simple Dockerfile for Conversational/NLP Engine
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY preciagro /app/preciagro

EXPOSE 8103

CMD ["uvicorn", "preciagro.packages.engines.conversational_nlp.app:app", "--host", "0.0.0.0", "--port", "8103"]
