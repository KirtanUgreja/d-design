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
mine() { git ls-files -- "$@"; }
scan() { # scan <grep-args...> -- <pathspec...>
  local args=() ; while [ "$1" != "--" ]; do args+=("$1"); shift; done; shift
  local files ; files=$(mine "$@") || return 1
  [ -n "$files" ] || return 1
  printf '%s\n' "$files" | tr '\n' '\0' | xargs -0 grep "${args[@]}" 2>/dev/null
}

# --- 1. The tenant wrapper ------------------------------------------------
# THE HIGHEST-VALUE RULE IN THIS FILE. It is the only one whose violation is a
# cross-tenant read rather than a design regression.
#
# The count is a literal, not a computed thing, so raising it is a deliberate
# edit someone reviews. It goes to 2 in v3 when Better Auth brings the
# TypeScript wrapper (web/db/tenant.ts). A third is a bug.
EXPECTED_TENANT_WRAPPERS=1
EXPECTED_TENANT_FILES="api/db/tenant.py"

# The bracket keeps this script from matching itself.
found=$(scan -lE "set_config\('app[.]user_id'" -- \
          'api/**/*.py' 'web/**/*.ts' 'web/**/*.tsx' | sort)
count=$(printf '%s' "$found" | grep -c . )

if [ "$count" -ne "$EXPECTED_TENANT_WRAPPERS" ]; then
  note "app.user_id is set in $count file(s), expected $EXPECTED_TENANT_WRAPPERS:"
  printf '      %s\n' $found >&2
  note "every tenant-scoped query goes through a wrapper (patterns.md rule 4)."
elif [ "$found" != "$EXPECTED_TENANT_FILES" ]; then
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

[ "$fail" -eq 0 ] || printf '\ninvariants failed — see docs/coderules/tooling.md\n' >&2
exit "$fail"
