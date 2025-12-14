#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -n "${DATABASE_URL:-}" ]; then
  echo "[CIE] running migrations..."
  alembic upgrade head
else
  echo "[CIE] DATABASE_URL not set, skipping migrations"
fi

echo "[CIE] starting uvicorn..."
exec uvicorn preciagro.packages.engines.crop_intelligence.app.main:app --host 0.0.0.0 --port "${PORT:-8082}"
