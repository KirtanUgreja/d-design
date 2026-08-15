#!/usr/bin/env bash
# The project-specific invariants a linter cannot express.
#
# Each one maps to a decision that quietly unravels the product if it drifts,
# and each is a grep because a grep is a rule that cannot be forgotten under
# deadline pressure. docs/coderules/tooling.md -> the lint table.
#
# Four of these exist because the Python move replaced a structural guarantee
# with a procedural one. There used to be one language, so there was one tenant
# wrapper, one schema, and no way to install LangGraph without also installing
# Python. None of that is true now.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

fail=0
note() { printf '  ✗ %s\n' "$1" >&2; fail=1; }

# Only our own code. `git ls-files` is exact where an --exclude-dir list is a
# guess that grows a hole the first time a vendored directory is renamed.
#
# `--others --exclude-standard` is load-bearing: plain `git ls-files` lists only
# *tracked* files, so a brand-new file was invisible to every check in here
# until someone staged it. New code is precisely where a violation arrives, and
# the check that would have caught it ran on everything except the file that
# had it. Found in v2 phase 15, when a new `treatment.tsx` containing a shadow
# passed check 9 by not existing yet. `--exclude-standard` keeps `.gitignore`
# honoured, so `node_modules` and `.next` stay out.
mine() { git ls-files --cached --others --exclude-standard -- "$@"; }

# No source tree, no invariants to check. The codebase was deleted on
# 2026-08-10 and several checks below assert that something *exists* — a
# tenant wrapper, an Alembic `include_object` — so with no code they fail
# rather than pass, which is a false alarm on an empty repo rather than a
# real finding. The moment `api/` or `web/` returns, so does every check.
#
# This guard is deliberately narrow: it triggers only when BOTH roots are
# absent. A half-deleted tree is a real problem and still fails loudly.
if [ ! -d api ] && [ ! -d web ]; then
  printf '  - no api/ or web/ tree; invariants skipped (see AGENTS.md)\n'
  exit 0
fi
# Success means "found something", decided by whether there was output — not by
# the pipeline's exit code.
#
# The exit-code version of this failed open, which in a file of security checks
# is the bug rather than a bug. `git ls-files` lists a file that has been
# deleted but not yet staged; grep exits 2 on the missing path; xargs turns any
# child failure into 123; `scan` reported "no match" and the check passed. So
# every invariant here — including the tenant wrapper — was silently disabled
# for anyone mid-refactor with an unstaged deletion. Found in v2 phase 14, by
# deleting `gradient-mesh.tsx` and watching two brand-new checks go quiet.
#
# Filtering to files that still exist fixes the cause; returning on output
# fixes the class, because xargs batching means the exit code was never a
# reliable answer to "did anything match" in the first place.
scan() { # scan <grep-args...> -- <pathspec...>
  local args=() ; while [ "$1" != "--" ]; do args+=("$1"); shift; done; shift
  local files out
  files=$(mine "$@") || return 1
  [ -n "$files" ] || return 1
  out=$(printf '%s\n' "$files" \
        | while IFS= read -r f; do [ -e "$f" ] && printf '%s\0' "$f"; done \
        | xargs -0 grep "${args[@]}" 2>/dev/null)
  [ -n "$out" ] || return 1
  printf '%s\n' "$out"
}

# `scan`, minus lines that are comments. Requires -n so there is a `file:line:`
# prefix to anchor against.
#
# This exists because three checks in this file have now fired on the comment
# explaining the rule they enforce — check 6 solved it once by matching an
# assignment instead of a word, and checks 7 and 9 walked straight back into
# it. A rule worth enforcing is a rule worth writing down next to the code, and
# a checker that punishes you for writing it down is one people delete.
#
# Test files are dropped for the other half of the same problem: a test that
# asserts a construct never ships has to name the construct.
#
# Both filters are applied to `scan`'s *output* rather than to its pathspec.
# `:(exclude)*.test.*` alongside a directory pathspec returns an empty file
# list in this repo — every check using it passed unconditionally, which is the
# same fail-open shape as the bug above and was found the same way, by breaking
# a check and watching nothing happen.
code_scan() { # code_scan <grep-args...> -- <pathspec...>
  local out
  out=$(scan "$@") || return 1
  out=$(printf '%s\n' "$out" \
        | grep -vE '^[^:]+:[0-9]+:[[:space:]]*(//|\*|/\*)' \
        | grep -vE '^[^:]*\.(test|spec)\.[a-z]+:')
  [ -n "$out" ] || return 1
  printf '%s\n' "$out"
}

# --- 1. The tenant wrapper ------------------------------------------------
# THE HIGHEST-VALUE RULE IN THIS FILE. It is the only one whose violation is a
# cross-tenant read rather than a design regression.
#
# The count is a literal, not a computed thing, so raising it is a deliberate
# edit someone reviews. It is 2 since v3 phase 16: Better Auth brought the
# TypeScript wrapper (web/db/tenant.ts). A third is a bug.
EXPECTED_TENANT_WRAPPERS=2
EXPECTED_TENANT_FILES="api/db/tenant.py web/src/db/tenant.ts"

# The bracket keeps this script from matching itself.
found=$(scan -lE "set_config\('app[.]user_id'" -- \
          'api/**/*.py' 'web/**/*.ts' 'web/**/*.tsx' | sort)
count=$(printf '%s' "$found" | grep -c . )

if [ "$count" -ne "$EXPECTED_TENANT_WRAPPERS" ]; then
  note "app.user_id is set in $count file(s), expected $EXPECTED_TENANT_WRAPPERS:"
  printf '      %s\n' $found >&2
  note "every tenant-scoped query goes through a wrapper (patterns.md rule 4)."
elif [ "$(printf '%s' "$found" | tr '\n' ' ' | sed 's/ $//')" != "$EXPECTED_TENANT_FILES" ]; then
  note "app.user_id is set in '$found', expected '$EXPECTED_TENANT_FILES'"
fi

# --- 2. No agent framework ------------------------------------------------
# It would land in the process holding database credentials, model
# credentials, and decrypted integration tokens — the opposite end of the
# placement rule from where risky dependencies belong. The class is also under
# active exploitation. The decision is falsifiable and the conditions are
# written down in docs/techstack/ai-stack.md; what this stops is it dying
# quietly, in a dependency line nobody read.
frameworks='langchain|langgraph|crewai|pydantic[-_]ai|autogen|agno|llama[-_]index|smolagents'
if grep -qiE "^\s*[\"']?($frameworks)" api/pyproject.toml 2>/dev/null; then
  note "an agent framework appears in api/pyproject.toml. It needs a ledger line naming"
  note "what it does that your own code cannot — the tool loop here is a for with a limit."
fi

# --- 3. Table ownership, seen through the ORMs -----------------------------
# Two migration tools against one database survive only because their table
# sets are disjoint. A SQLAlchemy import in web, or a Drizzle import in api, is
# not a style problem.
if scan -qE "^[[:space:]]*(import|from)[[:space:]]+sqlalchemy" -- 'web/src/**'; then
  note "SQLAlchemy imported in web/. api owns the application tables; web owns auth."
fi
if scan -q "drizzle-orm" -- 'api/**/*.py'; then
  note "Drizzle referenced in api/. Drizzle touches auth tables only, from web."
fi

# The ORM belongs in a data module, not a route or a component. `db/` is the
# shared home for the engine, the models and the wrapper; features get
# `*_data.py`.
orm_strays=$(scan -lE "^[[:space:]]*(import|from)[[:space:]]+sqlalchemy" -- 'api/**/*.py' \
  | grep -vE '^api/(db/|migrations/|tests/)' \
  | grep -vE '_data\.py$' \
  | grep -vE '/test_[^/]+\.py$')
if [ -n "$orm_strays" ]; then
  note "SQLAlchemy imported outside db/ and outside a *_data.py module:"
  printf '      %s\n' $orm_strays >&2
fi

# --- 4. Alembic cannot touch the auth tables -------------------------------
# Without the filter, an autogenerate run sees seven tables it does not know
# about and writes a migration to delete them. The single most destructive
# failure mode in this architecture.
# Checking that the word appears is not enough — it appears in a file where the
# filter has been unwired too. Assert the definition, the wiring, and the table
# list separately.
env_py=api/migrations/env.py
for required in 'def include_object(' 'include_object=include_object' 'AUTH_TABLES' '"session"'; do
  if ! grep -qF "$required" "$env_py" 2>/dev/null; then
    note "$env_py is missing '$required' — Alembic could propose dropping the auth tables."
  fi
done

# --- 5. Dangerous deserialization ------------------------------------------
# Ruff's S301/S506 cover the common spellings inside api; this catches the
# import itself, anywhere. Two of the 2026 framework CVEs are "load a stored
# object, get RCE".
if scan -qE "^[[:space:]]*import[[:space:]]+pickle|^[[:space:]]*from[[:space:]]+pickle[[:space:]]|yaml[.]load[[:space:]]*\(" -- 'api/**/*.py'; then
  note "pickle or yaml.load in api/. Neither has a safe use here."
fi

# --- 6. The Slot sandbox ----------------------------------------------------
# `allow-same-origin` alongside `allow-scripts` gives the frame the parent's
# origin, and every guarantee the Slot rests on evaporates at once: storage,
# cookies, parent access and credentialed requests all come back. It is one
# word, in one attribute, and nothing else in the codebase would notice.
#
# docs/v1/plan/11-visuals-and-slot.md asks for this as a codebase-wide grep
# rather than a component test, and the reason is that the component's own
# tests would still pass — the sandbox would simply be weaker.
#
# Matches an *assignment* (`sandbox="…"`, `const SANDBOX = '…'`), not the bare
# word. The first version of this check matched the word and immediately fired
# on slot.tsx's own comment explaining why it must never be added — a check
# that flags the documentation of a rule is a check people learn to ignore.
if scan -qiE "sandbox[[:space:]]*=[[:space:]]*[\"'][^\"']*allow-same-origin" -- 'web/**/*.ts' 'web/**/*.tsx' 'web/**/*.html'; then
  note "allow-same-origin appears in a sandbox attribute. With allow-scripts that is a same-origin iframe running generated code."
fi

# --- 7. A scene owns its frame ---------------------------------------------
# NOTE ON THE PATHSPEC, because it is a trap this file is already carrying
# elsewhere: `dir/**/*.tsx` matches only files at least one directory deep.
# `renderer/scene.tsx` and `renderer/tokens.ts` are invisible to it, and the
# first version of the snap check below passed while the violation sat in
# `scene.tsx`. A bare directory prefix matches everything under it, so that is
# what both checks here use. The `**` spellings in checks 1-6 have the same
# hole — `api/**/*.py` does not see `api/main.py`.

# v2 rule 20. Whether a scene fills the viewport is the art direction's lookup
# from the layout the AI wrote — never a field the AI sets, and never a
# constant in the renderer. This is the check that approximates it, because the
# rule has no type to enforce it.
#
# The defect it exists for was real and shipped: `layouts/full-bleed.tsx`
# hardcoded `minBlockSize: '100vh'`, which made one layout own the screen while
# the other five were content-height, and did it in the unit that overflows by
# the height of a mobile URL bar. Nothing caught it — the renderer tests assert
# structure, and the structure was correct.
#
# Token *reads* are the point and must not fire, so this matches a quoted CSS
# literal rather than the bare unit — a `var(--scene-min-block-…)` reference is
# never one. Matching the word instead fired immediately on the comment in
# full-bleed.tsx explaining why the constant was removed, which is the same
# trap check 6 above already fell into once and the reason both are written
# against the *value* and not the name. docs/v2/plan/13-scene-fit.md.
if code_scan -nE "[\"'\`][[:space:]]*[0-9.]+(vh|dvh|lvh)[[:space:]]*[\"'\`]" -- \
     'web/src/features/renderer/'; then
  note "a literal viewport height in renderer/. A scene's frame is the art direction's fit token, not a constant here (rule 20)."
fi

# The two halves of scroll snapping, and the rule-6 split between them.
# `scroll-snap-align` is a property of a scene and belongs to the renderer
# core; `scroll-snap-type` is a property of a playback surface and belongs to
# the wrapper. The core does not know it is inside one, and the moment it does,
# it has an opinion about where it is running.
# Anchored to the colon so it matches a *declaration* and not prose. scene.tsx
# names the property in the comment explaining why it is not there, which is
# the third time this file has had to learn that lesson.
if scan -nE "(scrollSnapType|scroll-snap-type)[[:space:]]*:" -- \
     'web/src/features/renderer/'; then
  note "scroll-snap-type in renderer/. That is the scroll container's property, and the container lives in present/ (rule 6)."
fi

# --- 8. No gradient, anywhere in the artifact -------------------------------
# v2 rule 18, and the reason it is a grep rather than guidance: the rule
# already existed. docs/design/principles.md principle 5 bans gradients
# outright, and it was filed under docs/design/ where everyone read it as being
# about our own chrome — so the artifact carried a coloured bloom behind every
# hero for the whole of v1 while the principle sat there indicting it.
#
# A component test would not have caught it. Every renderer test passed the
# entire time, because they assert structure and the structure was correct.
#
# Colour changes by dot, line, dither or hard edge. The vocabulary that
# replaces the ramps is web/src/features/renderer/texture/patterns.ts.
if code_scan -nE "(linear|radial|conic)-gradient\(|repeating-(linear|radial|conic)-gradient\(" -- \
     'web/src/features/renderer/' 'web/src/features/art-direction/'; then
  note "a gradient function in the artifact layer. Colour changes by dot, line, dither or hard edge (rule 18)."
fi

# --- 9. No neon, no bloom, no glow ------------------------------------------
# v2 rule 19. Written as a *property* ban rather than as taste guidance,
# because the version that bans "too much glow" requires someone to judge how
# much, and a check that needs a judgement is a check that gets argued with.
#
# A hard offset shadow with zero blur is a print device and is allowed — which
# is why the banned thing is the blur, not the shadow. Matching `blur(` covers
# `filter` and `backdrop-filter` in one; the shadow properties are matched by
# name because any chromatic shadow at any radius is the effect.
#
# Saturation is bounded by *value* rather than by grep, in the linter — phase
# 03. A saturated colour is not neon; a saturated colour that appears to emit
# light is, and that is a value judgement a grep cannot make.
# A hard offset shadow with zero blur is a print device and rule 19 allows it
# explicitly — so the exemption has to be expressible, or the check bans what
# the rule permits and gets switched off the first time someone needs a plate.
#
# The exemption is a **named helper**, `hardShadow()` in tokens.ts, and not a
# syntax this check tries to recognise. Matching the allowed CSS shape was
# tried first and is wrong: `0 0 20px red` — offsets zero, blur 20 — contains
# the same `0 0` as the permitted form, so the filter passed a bloom. Position
# in a space-separated list is not something grep should be asked to judge.
# Routing the one legal case through a helper turns "is this shadow a bloom?"
# into "does this line call the helper", which grep can answer exactly.
if code_scan -nE "blur\(|boxShadow|textShadow|dropShadow|box-shadow|text-shadow" -- \
     'web/src/features/renderer/' | grep -vE 'Shadow: hardShadow\('; then
  note "a blur or a soft shadow in renderer/. Neon is a lighting effect: the banned property is the blur (rule 19)."
  note "a hard offset shadow is allowed, through tokens.ts's hardShadow() and only through it."
fi

# --- 10. The variety gate (v2, phase 15) ------------------------------------
# The "53% identical" measurement made into a standing check. The golden
# briefs run through the pipeline with a deterministic seam and the gate
# asserts the design-space claims that must never silently creep back:
# cross-deck fingerprints differ, within-deck layouts and chart types are
# distributed, and no presentational value passes the backstop.
#
# It runs whenever api/ exists (the guard at the top already ensured one of
# api/ or web/ is present) and it is fast — no network, no model calls.
if [ -d api ]; then
  if ! out=$(env -C api uv run python -c "
from pipeline.acceptance.gate import run_variety_gate
import sys
passed, report = run_variety_gate()
print(report)
sys.exit(0 if passed else 1)
" 2>&1); then
    note "the variety gate is red — the design space has collapsed:"
    printf '      %s\n' "$out" >&2
    note "two decks converged on a fingerprint, or a deck collapsed to one frame (15-variety-gate.md)."
  fi
fi

[ "$fail" -eq 0 ] || printf '\ninvariants failed — see docs/coderules/tooling.md\n' >&2
exit "$fail"
