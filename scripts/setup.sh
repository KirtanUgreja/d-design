#!/usr/bin/env bash
# One-time setup for a fresh clone.
#
# Stripped to the hooks on 2026-08-10, when the codebase was deleted. It used
# to install both runtimes, start Docker, and run migrations; every one of
# those steps referenced something that no longer exists.
#
# What remains is the part that is not stack-specific and is easy to forget:
# `core.hooksPath` is what makes the versioned hooks in `scripts/hooks` run at
# all. Without it a fresh clone has no gate, and nothing tells you — the first
# sign is a bad commit that landed clean.
#
# Grow this file again as the new stack arrives, one step per thing that a
# second person cloning the repo would otherwise have to be told.

set -euo pipefail
cd "$(dirname "$0")/.."

echo '→ git hooks'
git config core.hooksPath scripts/hooks
chmod +x scripts/hooks/* scripts/checks/*.sh scripts/*.sh

echo
echo 'ready. the gate runs on every commit:'
echo '  ./scripts/hooks/pre-commit   on demand'
echo '  ./scripts/check-docs.sh      links resolve, every file indexed'
