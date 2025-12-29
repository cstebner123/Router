#!/usr/bin/env bash
set -euo pipefail

# Find repo root (works even if you run script from another directory)
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "[dev] repo root: $REPO_ROOT"

# Load env (supports .env in repo root OR one level above, per your setup)
if [ -f "$REPO_ROOT/.env" ]; then
  echo "[dev] loading .env from repo root"
  export $(grep -v '^#' "$REPO_ROOT/.env" | xargs)
elif [ -f "$REPO_ROOT/../.env" ]; then
  echo "[dev] loading .env from parent of repo root"
  export $(grep -v '^#' "$REPO_ROOT/../.env" | xargs)
else
  echo "[dev] WARNING: no .env found at $REPO_ROOT/.env or $REPO_ROOT/../.env"
fi

# Show key config (safe)
echo "[dev] DATABASE_URL=${DATABASE_URL:-<not set>}"

# Run FastAPI in dev mode
exec uvicorn router.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
