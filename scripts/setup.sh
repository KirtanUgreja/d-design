#!/usr/bin/env bash
# Everything a fresh clone needs. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/.."

echo '→ git hooks'
git config core.hooksPath scripts/hooks
chmod +x scripts/hooks/* scripts/checks/*.sh scripts/*.sh

echo '→ api (uv, frozen)'
# Frozen, always. A build that can resolve differently than the last one is not
# reproducible, and on the uv side --frozen is not the default the way it is
# for pnpm.
(cd api && uv sync --frozen)
[ -f api/.env ] || cp api/.env.example api/.env

echo '→ web (pnpm, frozen)'
(cd web && pnpm install --frozen-lockfile)
[ -f web/.env.local ] || cp web/.env.example web/.env.local

echo '→ playwright (chromium only, explicit — not a lifecycle script)'
(cd web && pnpm exec playwright install chromium)

echo '→ infrastructure'
docker compose up -d

echo '→ migrations'
(cd api && uv run --env-file .env alembic upgrade head)

echo
echo 'ready. `docker compose up -d` for the database and MinIO,'
echo '       `cd api && uv run --env-file .env uvicorn main:app --reload`,'
echo '       `cd web && pnpm dev`.'
