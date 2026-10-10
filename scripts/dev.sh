#!/usr/bin/env bash
# The whole app on one machine: the API, the worker and the web, together.
#   ./scripts/dev.sh            then open http://localhost:3000
# Needs ./scripts/setup.sh once, the repo-root .env (.env.example lists it)
# and web/.env.local with AUTH_DATABASE_URL and BETTER_AUTH_SECRET.
# Ctrl+C stops all three.
set -euo pipefail
cd "$(dirname "$0")/.."

export BETTER_AUTH_URL="${BETTER_AUTH_URL:-http://localhost:3000}"
pids=()
trap 'kill "${pids[@]}" 2>/dev/null; wait' EXIT INT TERM

(cd api && uv run alembic upgrade head)
(cd api && exec uv run uvicorn app:serve --factory --port 8000) & pids+=($!)
(cd api && exec uv run python worker.py) & pids+=($!)
(cd web && exec pnpm dev) & pids+=($!)
wait
