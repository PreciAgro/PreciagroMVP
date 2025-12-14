# =============================================================================
# PreciAgro Geo Context Engine
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libgeos-dev libproj-dev gdal-bin \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS production

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl libgeos-c1v5 libproj22 gdal-bin \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd -r preciagro && useradd -r -g preciagro preciagro

COPY --from=builder /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY preciagro/ ./preciagro/
RUN chown -R preciagro:preciagro /app

USER preciagro

ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8102

EXPOSE 8102

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8102/api/v1/health || exit 1

CMD ["python", "-m", "uvicorn", "preciagro.packages.engines.geo_context.api.main:app", "--host", "0.0.0.0", "--port", "8102"]
