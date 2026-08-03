#!/usr/bin/env bash
# Claude Code PostToolUse hook. Reads the tool payload on stdin and runs the
# checks that apply to whatever was just written. Silent on success; a non-zero
# exit surfaces the output back to the agent so it fixes the file it just wrote.
#
# Rules in AGENTS.md are advisory — the model has to remember them. This runs
# every time regardless. Add checks here as the code that needs them appears.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 0

path=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null) || exit 0
[ -n "$path" ] || exit 0

case "$path" in
  *.md)
    if ! out=$(./scripts/check-docs.sh 2>&1); then
      printf '%s\n' "$out" >&2
      exit 2
    fi
    ;;
esac

# When code exists, add here — each is one line, each enforces a rule prose cannot:
#   *.ts|*.tsx)  pnpm exec tsc --noEmit && pnpm exec eslint "$path" ;;
exit 0
