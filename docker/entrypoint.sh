#!/bin/sh
set -e

echo "==> Running database migrations..."
uv run alembic upgrade head

echo "==> Starting Viper background worker..."
uv run viper-worker &
WORKER_PID=$!

cleanup() {
    echo "==> Shutting down Viper..."
    kill -TERM "$WORKER_PID" 2>/dev/null || true
    wait "$WORKER_PID" 2>/dev/null || true
}

trap cleanup TERM INT EXIT

echo "==> Starting Viper server on http://0.0.0.0:8000..."
uv run uvicorn viper.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

wait "$SERVER_PID"
