#!/usr/bin/env bash
# Verifies the docs navigation invariants:
#   1. every relative .md link resolves
#   2. every .md is listed in its directory's README
#   3. every docs/ subdirectory is listed in docs/README.md
# Run from the repo root. Exits non-zero on any failure.
set -uo pipefail
fail=0

while IFS= read -r f; do
  d=$(dirname "$f")
  grep -oE '\]\([^)#][^)]*\.md\)' "$f" | sed 's/](//;s/)$//' | while IFS= read -r link; do
    [ -f "$d/$link" ] || echo "DEAD LINK: $f -> $link"
  done
done < <(find ./docs ./README.md -name '*.md') | tee /dev/stderr | grep -q . && fail=1

for readme in docs/README.md docs/*/README.md; do
  dir=$(dirname "$readme")
  for f in "$dir"/*.md; do
    b=$(basename "$f")
    [ "$b" = "README.md" ] && continue
    grep -q "($b)" "$readme" || { echo "UNLISTED: $b missing from $readme"; fail=1; }
  done
done

for sub in docs/*/; do
  name=$(basename "$sub")
  grep -q "$name/README.md" docs/README.md || { echo "UNLISTED DIR: $name missing from docs/README.md"; fail=1; }
  [ -f "$sub/README.md" ] || { echo "NO README: $sub has no README.md"; fail=1; }
done

[ "$fail" -eq 0 ] && echo "docs ok: links resolve, every file is listed, every directory has a README"
exit "$fail"
