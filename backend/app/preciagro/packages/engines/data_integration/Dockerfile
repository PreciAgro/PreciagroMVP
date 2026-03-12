# =============================================================================
# PreciAgro Data Integration Engine
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS production

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
RUN groupadd -r preciagro && useradd -r -g preciagro preciagro

COPY --from=builder /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY app/preciagro/ ./preciagro/
RUN chown -R preciagro:preciagro /app

USER preciagro

ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8101

EXPOSE 8101

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8101/health || exit 1

CMD ["python", "-m", "uvicorn", "preciagro.apps.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8101"]
