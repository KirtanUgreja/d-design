#!/usr/bin/env bash
# One-time setup for a fresh clone.
#
# The original was stripped to the hooks on 2026-08-10, when the codebase was
# deleted — every step referenced something that no longer existed. It has grown
# back one step per thing a second person cloning this repo would otherwise have
# to be told. Re-running it is safe: every step is idempotent.
#
# What it does NOT do: export your model key. The repo-root `.env` holds
# OPENROUTER_API_KEY (gitignored) and the api reads it from the environment,
# which is why the last thing printed here is how to start the api with it.

set -euo pipefail
cd "$(dirname "$0")/.."

step() { printf '\n→ %s\n' "$1"; }

step 'git hooks'
# `core.hooksPath` is what makes the versioned hooks in `scripts/hooks` run at
# all. Without it a fresh clone has no gate, and nothing tells you — the first
# sign is a bad commit that landed clean.
git config core.hooksPath scripts/hooks
chmod +x scripts/hooks/* scripts/checks/*.sh scripts/*.sh

step 'toolchain'
missing=0
for tool in uv pnpm docker; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '  %-8s %s\n' "$tool" "$("$tool" --version 2>&1 | head -1)"
  else
    printf '  %-8s MISSING\n' "$tool"
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  echo 'install the missing tools above, then re-run this script'
  exit 1
fi

step 'python dependencies (api)'
uv sync --project api --quiet

step 'javascript dependencies (web, render, worker)'
for dir in web render worker; do
  printf '  %s\n' "$dir"
  pnpm --dir "$dir" install --frozen-lockfile --silent
done

step 'playwright browser (the render tests print through a real one)'
pnpm --dir render exec playwright install chromium >/dev/null
echo '  chromium ready'

step 'local infrastructure'
# Postgres, MinIO, and the bucket bootstrap. The app services are NOT started —
# they are what you run by hand while working.
docker compose up -d postgres minio createbucket

step 'database schema'
# The migration role owns DDL; the app connects as a role with no bypassrls and
# `as_user` switches to it per transaction.
(cd api && uv run alembic upgrade head)

step 'auth tables'
# web owns these and Drizzle migrates them. `drizzle-kit push` wants a TTY, so
# it is left to you if they are missing — the compose volume keeps them once
# created.
echo '  if sign-up fails with `relation "user" does not exist`:'
echo '    (cd web && pnpm exec drizzle-kit push)'

step 'model key'
if grep -q '^OPENROUTER_API_KEY=..' .env 2>/dev/null; then
  echo '  .env has OPENROUTER_API_KEY'
else
  echo '  .env has NO OPENROUTER_API_KEY — generation answers 503 until it does'
fi

cat <<'READY'

ready. the gate runs on every commit:
  ./scripts/hooks/pre-commit   on demand
  ./scripts/check-docs.sh      links resolve, every file is indexed

to run the product locally, three terminals:
  cd render && pnpm build && PORT=8001 node dist/server.cjs
  cd api    && set -a && . ../.env && set +a && uv run uvicorn app:app --port 8000
  cd web    && env -u NODE_ENV pnpm dev

  open http://localhost:3000 — sign up, type a topic, generate, approve, save,
  publish. For brand-kit uploads the worker must be running too
  (docker compose up -d worker), and the whole stack can run in containers:
  docker compose up -d

  `NODE_ENV` is `production` in some shells, and `next dev` misbehaves under it
  — every server route 500s. `env -u NODE_ENV pnpm dev` is why that is in the
  line above.
READY
