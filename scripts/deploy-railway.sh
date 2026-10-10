#!/usr/bin/env bash
# Your own copy of d-design on Railway, from a fresh clone, in one command:
#   ./scripts/deploy-railway.sh
# The first run creates a Railway project with two Postgres databases (app and
# auth, kept apart: docs/coderules rule 8), the api, worker and web services,
# their variables and a public URL, then deploys. Every later run only ships
# the code you have now.
#
# It asks for what it cannot make: your OpenRouter key and who may sign up.
# Set them beforehand to skip the questions (or put them in .env):
#   OPENROUTER_API_KEY=sk-or-... ALLOWED_EMAILS=you@x.com MODEL=deepseek/deepseek-v4.1-flash ./scripts/deploy-railway.sh
#
# Railway's free plan allows 3 services, and the two databases make 5. On the
# free plan, bring your own Postgres (Neon's free tier works): set
# APP_DATABASE_URL and AUTH_DATABASE_URL, two separate databases, and the
# script adds no database of its own.
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }

command -v railway >/dev/null || {
  echo "The Railway CLI is missing. Install it: brew install railway   (or: npm i -g @railway/cli)"
  exit 1
}
railway whoami >/dev/null 2>&1 || railway login

# .env fills in what the shell did not set; the shell wins.
if [ -f .env ]; then
  while IFS='=' read -r key value; do
    case "$key" in OPENROUTER_API_KEY | ALLOWED_EMAILS | MODEL | APP_DATABASE_URL | AUTH_DATABASE_URL)
      [ -n "${!key:-}" ] || export "$key=${value//\"/}" ;;
    esac
  done < <(grep -E '^(OPENROUTER_API_KEY|ALLOWED_EMAILS|MODEL|APP_DATABASE_URL|AUTH_DATABASE_URL)=' .env)
fi

services() {
  railway status --json 2>/dev/null | python3 -c '
import json, sys
for edge in json.load(sys.stdin)["services"]["edges"]:
    print(edge["node"]["name"])'
}

# A Postgres service's own DATABASE_URL, read back once Railway has made it.
# ponytail: a literal copy, so a rotated database password needs this re-run
# by hand. Upgrade path: ${{Service.DATABASE_URL}} references.
database_url() {
  local url=""
  for _ in $(seq 30); do
    url=$(railway variable list --service "$1" --json 2>/dev/null |
      python3 -c 'import json, sys; print(json.load(sys.stdin).get("DATABASE_URL", ""))' || true)
    [ -n "$url" ] && { echo "$url"; return; }
    sleep 2
  done
  echo "Railway did not give $1 a DATABASE_URL within a minute. Run this script again." >&2
  exit 1
}

if ! railway status >/dev/null 2>&1; then
  say "Creating a Railway project"
  railway init --name "${RAILWAY_PROJECT:-d-design}"
fi

# Setup is done once web holds its secret, which is set last; a run that
# stopped halfway (a plan limit, a network error) picks up where it left off.
setup_done() {
  railway variable list --service web --json 2>/dev/null |
    python3 -c 'import json, sys; sys.exit(0 if json.load(sys.stdin).get("BETTER_AUTH_SECRET") else 1)'
}

if ! setup_done; then
  say "First deploy: setting up the project"

  if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    read -rsp "OpenRouter API key (https://openrouter.ai/keys): " OPENROUTER_API_KEY
    echo
  fi
  [ -n "$OPENROUTER_API_KEY" ] || { echo "An OpenRouter key is required."; exit 1; }
  if [ -z "${ALLOWED_EMAILS:-}" ]; then
    default=$(git config user.email || true)
    read -rp "Emails allowed to sign up, comma-separated [$default]: " ALLOWED_EMAILS
    ALLOWED_EMAILS=${ALLOWED_EMAILS:-$default}
  fi
  [ -n "$ALLOWED_EMAILS" ] || { echo "At least one email is required: nobody else can sign up."; exit 1; }

  if [ -n "${APP_DATABASE_URL:-}" ] && [ -n "${AUTH_DATABASE_URL:-}" ]; then
    say "Using your own Postgres databases"
    app_url=$APP_DATABASE_URL
    auth_url=$AUTH_DATABASE_URL
  else
    say "Adding two Postgres databases"
    [ "$(services | grep -c '^Postgres' || true)" -ge 1 ] || railway add --database postgres >/dev/null
    [ "$(services | grep -c '^Postgres' || true)" -ge 2 ] || railway add --database postgres >/dev/null
    # Sorted, the first is "Postgres" and the second "Postgres-xxxx".
    app_db=$(services | grep '^Postgres' | sort | sed -n 1p)
    auth_db=$(services | grep '^Postgres' | sort | sed -n 2p)
    app_url=$(database_url "$app_db")
    auth_url=$(database_url "$auth_db")
  fi

  say "Adding the web, api and worker services"
  for s in web api worker; do services | grep -qx "$s" || railway add --service "$s" >/dev/null; done
  # A second run finds the domain already there; that is not an error.
  railway domain --service web >/dev/null 2>&1 || true

  printf '%s' "$OPENROUTER_API_KEY" |
    railway variable set OPENROUTER_API_KEY --stdin --service worker --skip-deploys >/dev/null
  if [ -n "${MODEL:-}" ]; then
    railway variable set --service worker --skip-deploys "MODEL=$MODEL" >/dev/null
  fi
  secret=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
  # ${{...}} are Railway references, resolved by Railway, not by this shell.
  # web goes last: its secret marks the setup done (setup_done above).
  # shellcheck disable=SC2016
  {
    railway variable set --service worker --skip-deploys \
      "APP_DATABASE_URL=$app_url" RAILWAY_DOCKERFILE_PATH=Dockerfile.worker >/dev/null
    railway variable set --service api --skip-deploys \
      "APP_DATABASE_URL=$app_url" PORT=8000 DAILY_CAP_USD=3 \
      'BETTER_AUTH_URL=https://${{web.RAILWAY_PUBLIC_DOMAIN}}' >/dev/null
    railway variable set --service web --skip-deploys \
      "AUTH_DATABASE_URL=$auth_url" "BETTER_AUTH_SECRET=$secret" "ALLOWED_EMAILS=$ALLOWED_EMAILS" \
      PORT=3000 AUTH_MIGRATE=1 \
      'BETTER_AUTH_URL=https://${{RAILWAY_PUBLIC_DOMAIN}}' \
      'API_ORIGIN=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:8000' >/dev/null
  }
fi

say "Deploying the code"
# Each from its own folder: from the repo root Railway finds no Dockerfile.
railway up ./api --path-as-root --service api --detach
railway up ./api --path-as-root --service worker --detach
railway up ./web --path-as-root --service web --detach

url=$(railway variable list --service web --json |
  python3 -c 'import json, sys; print(json.load(sys.stdin).get("RAILWAY_PUBLIC_DOMAIN", ""))')
say "Building now (about 5 minutes). Then open: https://$url"
echo "Watch a build:   railway logs --service web"
echo "Change model:    railway variable set --service worker MODEL=<openrouter model id>"
