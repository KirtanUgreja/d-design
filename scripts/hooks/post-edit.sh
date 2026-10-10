#!/usr/bin/env bash
# Claude Code PostToolUse hook. Reads the tool payload on stdin and runs the
# cheap check for the file that was just written. Silent on success; a non-zero
# exit hands the output back to the agent while it still remembers the line.
#
# Deliberately light. Until phase 21 this ran full mypy, tsc and an invariants
# script after every write, which made every edit slow and every half-finished
# change look like a failure. Types and tests belong to the pre-commit gate.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 0

path=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null) || exit 0
[ -n "$path" ] || exit 0
rel=${path#"$PWD/"}

reject() { printf '%s\n' "$1" >&2; exit 2; }

case "$rel" in
  web/lib/api/schema.d.ts)
    reject "$rel is generated from the API's OpenAPI document. Change the Pydantic model and regenerate."
    ;;
  docs/*.md|README.md)
    out=$(./scripts/check-docs.sh 2>&1) || reject "$out"
    ;;
  api/*.py)
    out=$(env -C api uv run ruff check "${rel#api/}" 2>&1) || reject "$out"
    ;;
  web/*.ts|web/*.tsx)
    out=$(env -C web pnpm exec eslint "${rel#web/}" --max-warnings 0 2>&1) || reject "$out"
    ;;
esac
exit 0
