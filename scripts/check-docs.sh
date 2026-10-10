#!/usr/bin/env bash
# Verifies the docs navigation invariants:
#   1. every relative .md link resolves
#   2. every .md is listed in its directory's README
#   3. every docs/ subdirectory is listed in docs/README.md
# Only tracked files count: internal docs kept locally but gitignored
# (.gitignore -> "Internal planning") are neither linked to nor listed.
# Run from the repo root. Exits non-zero on any failure.
set -uo pipefail
fail=0
tracked=$(git ls-files --cached --others --exclude-standard)
is_tracked() { grep -qxF "$1" <<<"$tracked"; }

while IFS= read -r f; do
  d=$(dirname "$f")
  grep -oE '\]\([^)#][^)]*\.md\)' "$f" | sed 's/](//;s/)$//' | while IFS= read -r link; do
    target=$(python3 -c 'import os,sys; print(os.path.normpath(os.path.join(sys.argv[1], sys.argv[2])))' "$d" "$link")
    is_tracked "$target" || echo "DEAD LINK: $f -> $link"
  done
done < <(grep -E '^(docs/.*|[^/]*)\.md$' <<<"$tracked") | tee /dev/stderr | grep . >/dev/null && fail=1

for readme in docs/README.md docs/*/README.md; do
  dir=$(dirname "$readme")
  for f in "$dir"/*.md; do
    is_tracked "$f" || continue
    b=$(basename "$f")
    [ "$b" = "README.md" ] && continue
    grep -q "($b)" "$readme" || { echo "UNLISTED: $b missing from $readme"; fail=1; }
  done
done

for sub in docs/*/; do
  name=$(basename "$sub")
  grep -q "^docs/$name/" <<<"$tracked" || continue
  grep -q "$name/README.md" docs/README.md || { echo "UNLISTED DIR: $name missing from docs/README.md"; fail=1; }
  [ -f "$sub/README.md" ] || { echo "NO README: $sub has no README.md"; fail=1; }
done

[ "$fail" -eq 0 ] && echo "docs ok: links resolve, every file is listed, every directory has a README"
exit "$fail"
