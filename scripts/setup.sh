#!/usr/bin/env bash
# One-time setup for a fresh clone. Re-running it is safe.
#
# It does not export your model key: the repo-root `.env` holds
# OPENROUTER_API_KEY (gitignored) and `api/settings.py` reads it.

set -euo pipefail
cd "$(dirname "$0")/.."

step() { printf '\n→ %s\n' "$1"; }

step 'git hooks'
# core.hooksPath is what makes the versioned hooks run at all. Without it a
# fresh clone has no gate, and nothing tells you.
git config core.hooksPath scripts/hooks
chmod +x scripts/hooks/* scripts/*.sh

step 'toolchain'
if command -v uv >/dev/null 2>&1; then
  printf '  uv  %s\n' "$(uv --version)"
else
  echo '  uv  MISSING — install it, then re-run this script'
  exit 1
fi

step 'python dependencies (api)'
uv sync --project api --quiet

step 'web dependencies'
if command -v pnpm >/dev/null 2>&1; then
  (cd web && pnpm install --frozen-lockfile --silent)
  echo '  web ready'
else
  echo '  pnpm MISSING (corepack enable, or npm i -g pnpm) — the web app will not start until it is installed'
fi

step 'chromium (the bench wall, and QA)'
(cd api && uv run playwright install chromium >/dev/null)
echo '  chromium ready'

step 'model key'
if grep -q '^OPENROUTER_API_KEY=..' .env 2>/dev/null; then
  echo '  .env has OPENROUTER_API_KEY'
else
  echo '  .env has NO OPENROUTER_API_KEY — live calls will fail until it does'
fi

cat <<'READY'

ready. the gate runs on every commit:
  ./scripts/hooks/pre-commit   on demand
  ./scripts/check-docs.sh      links resolve, every file is indexed

the engine is driven from the CLI until the app exists (phase 27):
  cd api
  uv run python -m cli smoke                 one live call; prints its cost
  uv run python -m cli baseline --set smoke  one-shot baseline decks
  uv run python -m cli wall --run NAME       the wall page a human scores
READY
