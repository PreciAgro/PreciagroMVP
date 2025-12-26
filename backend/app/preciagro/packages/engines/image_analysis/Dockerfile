FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=on \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY app/preciagro/packages/engines/image_analysis/requirements.txt /tmp/requirements-image-analysis.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements-image-analysis.txt

COPY app/preciagro ./preciagro
COPY scripts ./scripts

RUN chmod +x scripts/entrypoint_image_analysis.sh

EXPOSE 8084

ENTRYPOINT ["scripts/entrypoint_image_analysis.sh"]
