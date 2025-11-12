#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

APP_MODULE="preciagro.packages.engines.image_analysis.app.main:app"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8084}"

echo "[ImageAnalysis] starting uvicorn on ${HOST}:${PORT}..."
exec uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}"
