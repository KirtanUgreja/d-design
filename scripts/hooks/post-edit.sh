#!/usr/bin/env bash
# Claude Code PostToolUse hook. Reads the tool payload on stdin and runs the
# checks that apply to whatever was just written. Silent on success; a non-zero
# exit surfaces the output back to the agent so it fixes the file it just wrote.
#
# Rules in AGENTS.md are advisory — the model has to remember them, and
# remembering degrades across long sessions and context compaction. This runs
# every time regardless. The pre-commit gate still runs all of it; this just
# moves the feedback to the moment the agent can still remember why it wrote
# the line.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 0

path=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null) || exit 0
[ -n "$path" ] || exit 0

# Repo-relative, so the case below can match on directory.
rel=${path#"$PWD/"}

reject() { printf '%s\n' "$1" >&2; exit 2; }

case "$rel" in
  # Generated. The gate would catch a hand-edit at commit time; catching it
  # here catches it while the reason it looked necessary is still in context.
  web/src/schema/generated/*)
    reject "$rel is generated from api/schema/*.py. Change the Pydantic model and run \`pnpm schema:generate\` — a hand-edit here fails the gate (coderules/python.md)."
    ;;

  *.md)
    out=$(./scripts/check-docs.sh 2>&1) || reject "$out"
    ;;

  api/*.py)
    out=$(env -C api uv run ruff check "${rel#api/}" 2>&1) || reject "$out"
    out=$(env -C api uv run mypy 2>&1) || reject "$out"
    ;;

  web/*.ts|web/*.tsx|web/*.mjs)
    out=$(env -C web pnpm exec eslint "${rel#web/}" --max-warnings 0 2>&1) || reject "$out"
    out=$(env -C web pnpm exec tsc --noEmit 2>&1) || reject "$out"
    ;;
esac

# The invariants are cheap and their violations are the silent ones.
case "$rel" in
  api/*|web/*)
    out=$(./scripts/checks/invariants.sh 2>&1) || reject "$out"
    ;;
esac

exit 0
