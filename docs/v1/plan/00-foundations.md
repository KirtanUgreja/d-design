# Phase 00 — Foundations

> The repo, the gate, and the two rules that must be habits before the first query is written. Nothing in this phase is a feature; everything in it is what stops later phases from needing a rewrite.

**Depends on:** nothing · **Blocks:** everything · **Spec step:** — (precedes step 1)

[../../coderules/tooling.md](../../coderules/tooling.md) puts this at "a few hours, once." Take the day. The custom lint rules here are the only thing standing between a solo AI-assisted build and the duplication numbers in [../../coderules/ai-authorship.md](../../coderules/ai-authorship.md).

---

## Search

**Read first**

- [../../coderules/structure.md](../../coderules/structure.md) — the whole folder layout, both languages, and the server/client boundary
- [../../coderules/tooling.md](../../coderules/tooling.md) — the gate, the lint table, the hook mechanics
- [../../coderules/python.md](../../coderules/python.md) — mypy settings, and **the schema codegen this phase has to stand up**
- [../../coderules/typescript.md](../../coderules/typescript.md) — `tsconfig` flags, and the TS 7 caveat
- [../../coderules/dependencies.md](../../coderules/dependencies.md) — why pnpm and uv, and the ledger format
- [../../techstack/backend.md](../../techstack/backend.md) → "Two ORMs, one database" and "Isolation: RLS on a session variable"
- [../../coderules/patterns.md](../../coderules/patterns.md) → rules 3, 4, 5

**Grep for** — nothing yet. This is the one phase with an empty codebase, which is exactly why the conventions set here have to be right.

**Verify externally before pinning**

| | What to check |
|---|---|
| Next.js | 16.3 is current as of 3 Aug 2026. Confirm the minor, and that `reactCompiler` and `cacheComponents` are still the flag names |
| Python | Current stable, security-supported line. Confirm `type` statement support for the `Result` alias in [../../coderules/python.md](../../coderules/python.md) |
| FastAPI + Pydantic | Pydantic **v2**. Check `model_json_schema()` output for a **nested** tagged union — that is phase 01's shape, and the whole codegen chain runs through it |
| SQLAlchemy | Async. **Confirm `set_config(..., true)` survives the driver you pick**, and that `asyncpg`'s prepared-statement cache can be disabled — it breaks behind a transaction pooler |
| uv | Lockfile committed, `--frozen` in CI, `--exclude-newer` configured. **None of this is on by default** — unlike pnpm, where it is |
| TypeScript | **Stay on 6.** TS 7.0 shipped 8 July 2026 without a public compiler API, and `typescript-eslint` type-aware rules cannot run on it until 7.1 (~Oct 2026). The two-compiler workaround in [../../coderules/typescript.md](../../coderules/typescript.md) is real and is *not worth taking on day one* — a codebase this size typechecks fast on 6. Revisit at 7.1 |
| pnpm | 11+, so `minimumReleaseAge` and install-script blocking are on by default. Verify rather than assume — check that a package published in the last hour refuses to resolve |
| **The generator** | Pick and pin the JSON Schema → TypeScript and JSON Schema → Zod tools **in this phase**, not in phase 01. The codegen chain is a foundation, and discovering it does not handle tagged unions while designing the IR is the worst possible time |

---

## Make

### 1. Two repos, two package managers

v1 stands up two of the five ([../../coderules/structure.md](../../coderules/structure.md)). `render`, `jobs`, and the fetch worker are v2/v3.

```
d-design-api/     uv init          # FastAPI, SQLAlchemy, Pydantic
d-design-web/     pnpm create next-app@latest   # App Router, TypeScript, Tailwind, ESLint, src/
```

`package.json`: leave `pnpm.onlyBuiltDependencies` **absent**. Nothing here needs a native build yet. `sharp` adds itself in phase 10, and the list is more meaningful when every entry arrived for a reason.

`pyproject.toml`: commit `uv.lock`, and configure `--exclude-newer` and frozen installs **now**. On the pnpm side both are defaults; on the uv side neither is, and a supply chain that is hardened on one side only is not hardened ([../../security/platform-and-packages.md](../../security/platform-and-packages.md)).

### 2. Both type checkers, at their strictest

```jsonc
// tsconfig.json
{ "compilerOptions": {
    "strict": true, "noUncheckedIndexedAccess": true, "erasableSyntaxOnly": true } }
```

```toml
# pyproject.toml
[tool.mypy]
strict = true
warn_unreachable = true
disallow_any_explicit = true
```

`erasableSyntaxOnly` is what retires the `enum` lint rule; `disallow_any_explicit` is its Python counterpart. A checker flag beats a lint rule on both sides.

### 3. The gate — and the step that is new

Two hooks, same discipline ([../../coderules/tooling.md](../../coderules/tooling.md)):

```
web (husky + lint-staged)        api (pre-commit)
Prettier → ESLint → tsc          Ruff format → Ruff → mypy → SCHEMA REGEN
```

**The fourth step is the one this whole architecture rests on.** Regenerate `@d-design/schema` from Pydantic and fail on a diff. Without it, "one source of truth" is a claim rather than a fact, and the drift arrives through a hand-edit to generated TypeScript that looks entirely reasonable in review.

**Keep each gate under two seconds.** A gate that is fast is a gate nobody routes around, and every rule below is only as real as the hook that runs it.

### 4. Lint rules — the ones that are the point

Stock TS: `@typescript-eslint/no-explicit-any`, `no-non-null-assertion`, `import/no-cycle`, `react-hooks` including the compiler rules. Stock Python: Ruff's `ANN`, `TID252`, and the `B` set.

Custom, in write-first order:

| Rule | Where | Enforces | Note |
|---|---|---|---|
| `set_config('app.user_id'` appears in **exactly one file** (two from v3) | api | Rule 9 | **Write this one first.** It is the only rule on the list whose violation is a cross-tenant read rather than a design regression — and it is the rule that replaced a structural guarantee the single-language design used to give for free. The count is a literal in the rule, so raising it to two when Better Auth lands is a deliberate edit rather than a silent widening |
| no edit to generated `@d-design/schema` sources | web | The codegen boundary | Second. It is the other guarantee the split turned into a check |
| no `langchain`/`langgraph`/`crewai`/`pydantic_ai`/`autogen` in `pyproject.toml` | api | The agent-framework rule ([../../coderules/dependencies.md](../../coderules/dependencies.md)) | Cheap. A privileged dependency should not arrive by accident |
| no ORM import outside a data module | both | Rule 8 | |
| no `process.env` / `typeof window` / `mode` prop under `renderer/` | web | Rule 6 | Dormant until phase 04, so write it now while it costs nothing to be strict |
| no Tailwind class under `renderer/` | web | The no-styling invariant, seen from the app side ([../../techstack/frontend.md](../../techstack/frontend.md)) | |
| no `dangerouslySetInnerHTML` outside the Slot path | web | [../../security/content-and-web.md](../../security/content-and-web.md) | |
| no `pickle` / `yaml.load` anywhere | api | [../../security/platform-and-packages.md](../../security/platform-and-packages.md) | Two of the 2026 framework CVEs are "load a stored object, get RCE" |
| feature public API boundary | both | Rule 4 | Plugin if one fits, custom if not |

### 5. The post-edit hook

`scripts/hooks/post-edit.sh` already enforces `check-docs.sh` on `.md` edits. Add two branches now: `*.ts` runs `tsc --noEmit` and `eslint` on the written file; `*.py` runs `mypy` and `ruff`. Exit 2 on failure so the agent fixes the file while it still remembers why it wrote the line.

### 6. `docker-compose.yml`

```yaml
postgres    # the real database, same one as production
minio       # S3-compatible object storage
```

**MinIO from day one** is deliberate. `storage.ts` is the only abstraction in the project with a planned second implementation ([../spec.md](../spec.md)), and pointing it at the S3 API locally means it ends up with one implementation after all. MinIO is not a mock; it speaks the same protocol. LocalStack waits for v3 — there are no integration credentials to encrypt yet.

### 7. `api/lib/` — three files, and no more

```
api/lib/result.py     Result[T, E] — the one error type (coderules/python.md)
api/lib/ids.py        uuid4. stdlib, no dependency
api/lib/storage.py    S3 client (boto3) → MinIO locally. One implementation
```

`lib/` is what every feature uses and no feature owns. If something here ends up used by one feature, move it into that feature.

**`web` gets no `lib/result.ts` yet.** It has no data layer and no failure to model — it renders and it calls `api`. Adding the mirror now would be the first speculative duplication in a codebase whose main risk is duplication.

### 8. `api/db/tenant.py` — the dangerous part

```python
# api/db/tenant.py — the only place app.user_id is set in Python
@asynccontextmanager
async def as_user(user_id: str):
    async with session_factory() as s, s.begin():
        await s.execute(text("select set_config('app.user_id', :uid, true)"), {"uid": user_id})
        yield s
```

Three things that are invisible in review and all three are load-bearing ([../../coderules/patterns.md](../../coderules/patterns.md), rule 4): the `true` scopes the setting to the transaction; the pooler must run in **transaction mode**; and a tenant-scoped query outside a transaction is unsafe by construction on a shared pool.

**There is exactly one wrapper in v1, and that is worth noticing while it is true.** The second one arrives with Better Auth in v3, and from that day the control exists twice and must be changed in both places at once. Write the lint rule now — as "`set_config('app.user_id'` appears in exactly *one* file" — so that raising the number to two in v3 is a deliberate edit to a rule rather than a silent widening.

**v1 has one user.** Seed a fixed uuid, read it from env as `LOCAL_USER_ID`, and pass it to `as_user` exactly as v3 will pass a resolved session's user id. The wrapper does not know the difference, which is the entire reason for building it now.

Roles: `api` connects as `app_user`, which has **no `bypassrls`**. A separate migration role owns DDL. There is no anonymous role at all — nothing but the server ever connects ([../../techstack/decisions.md](../../techstack/decisions.md)).

### 9. First migration — two tables and their policies

```
experiences  id, owner_id, title, mode, brand_id, art_direction,
             scenes (jsonb), published_at, created_at, updated_at
brands       id, owner_id, display_font, text_font, primary,
             secondary, neutral, logo_asset_id
```

```sql
create policy own_experiences on experiences
  for all to app_user
  using      (owner_id = current_setting('app.user_id')::uuid)
  with check (owner_id = current_setting('app.user_id')::uuid);
```

The other three tables (`assets`, `briefs`, `generations`) arrive in the phases that need them, each with its own policy and its own isolation test. That keeps the migration story honest — a table exists because something reads it.

The scene tree is one `jsonb` column, never normalized. It is always read and written whole, Pydantic validates it rather than SQL, and normalizing would buy queries nobody runs.

### 10. Next config

```ts
reactCompiler: true      // stable in 16, and hot path #3 is the editor canvas
cacheComponents: true    // author against `use cache` from the start, not later
```

### 11. CI

GitHub Actions, one workflow **per repo**: the gate · tests (pytest / Vitest) · dependency advisory check · `jscpd` on changed files (**warning, never a gate** — it is a signal about the one metric that degrades silently) · `scripts/check-docs.sh`.

`api`'s workflow carries one extra step that the others do not: **regenerate the schema and fail on a diff.** It is the same check as the pre-commit gate, run again where it cannot be skipped with `--no-verify`.

---

## Verify

**The gate**

- [ ] `pnpm lint && pnpm typecheck && pnpm format:check` green on the empty `web` repo
- [ ] `ruff check && mypy` green on the empty `api` repo
- [ ] A commit that fails any step does not land. Test it by breaking one on purpose

**Rule 9, proven rather than assumed** — this is the phase's most important test:

- [ ] `current_setting('app.user_id')` on a connection where it was never set **fails**, and does not match everything. That is [../../coderules/patterns.md](../../coderules/patterns.md) rule 5 applied to isolation
- [ ] A query written outside `as_user` **fails lint**. Write the violation, watch it fail, delete it
- [ ] Two rows owned by two different uuids: `as_user(a)` sees exactly one

**Fail-closed, seeded early** ([../../security/testing.md](../../security/testing.md) → "Failing closed")

- [ ] `Result` is the only error type in `lib/`. No `catch` returning a permissive default exists yet — and now there is a rule and a habit before there is a `catch` to get wrong

**Supply chain** ([../../coderules/dependencies.md](../../coderules/dependencies.md) → "Test")

- [ ] A package published within the last day refuses to resolve — **on both sides**. pnpm gives it to you; uv does not, so this is the one that actually needs testing
- [ ] Both lockfiles committed, installs run frozen
- [ ] CI fails on a known-critical advisory in either tree
- [ ] No agent framework resolves into `pyproject.toml` — assert the grep now, while the answer is trivially yes

---

## Skipped

| Not built | Trigger to build it |
|---|---|
| TypeScript 7 | 7.1 ships the stable compiler API and `typescript-eslint` supports it. Until then it is two compilers on disk for a typecheck that is already fast |
| Biome | The custom rules above can be expressed in it. Speed is not the reason; one binary instead of two is |
| LocalStack | Integration credentials exist (v3) |
| `@d-design/schema` **published** | A second TypeScript consumer exists — `render`, in v2. In v1 a local file link is correct; mark it `ponytail:` with that trigger ([../../coderules/typescript.md](../../coderules/typescript.md)) |
| `render`, `jobs`, the fetch worker | v2 and v3. v1 publishes from a `web` route to local disk |
| Auth, sessions, Better Auth, **the second tenant wrapper** | v3. `as_user` takes a user id from env instead of a resolved session, and that is the only difference — until Better Auth arrives and the wrapper count goes from one to two ([../../techstack/backend.md](../../techstack/backend.md)) |
| Branch-per-preview databases | Migrations against one shared dev DB start hurting |
| Terraform, AWS, CloudFront, ECS | v3. A perfect VPC does not move Risk 1 at all ([../../techstack/infrastructure.md](../../techstack/infrastructure.md)) |

---

## Built — and the five places it deviated

Built 4 Aug 2026. Everything below is a deliberate departure from the plan above, with the trigger that would undo it.

**1. One repo, two project roots.** The plan says two repos. It is `api/` and `web/`, each with its own project root, lockfile and gate, inside this repo. Two hook managers cannot both own `.git/hooks`, so husky-plus-`pre-commit` became one dispatching `scripts/hooks/pre-commit` that runs the same four Python steps and three TypeScript steps against whatever is staged. **Trigger:** `render` or the fetch worker arriving in v2 — at which point each runtime takes the half of that hook that applies to it. Nothing in the layout resists the split; the paths are already `api/…` and `web/…`.

**2. The JSON Schema → Zod generator is ours.** `json-schema-to-zod` was pinned first, exactly as this phase instructs, and it does not resolve `$ref` — every member of the nested tagged union came out as `z.any()` and every character cap was dropped. **A validator that silently accepts anything is worse than no validator**, and finding that here rather than in phase 01 is the entire reason this phase pins generators. `web/scripts/generate-schema.mjs` emits the closed subset of JSON Schema that Pydantic actually produces, and throws on anything it does not recognize rather than degrading. **Trigger to delete it:** a maintained converter that handles `$ref`, `oneOf` + `discriminator`, and Zod 4 output.

**3. `json-schema-to-typescript` went with it.** Types come from `z.infer` on the generated validator, so the schema and its type cannot disagree — the property `z.infer` gave inside one language, recovered across the split. Two dependencies deleted rather than added.

**4. `extra="forbid"` on every schema model** (`api/schema/base.py`). The cross-language fixture test found this immediately: Pydantic ignores an unknown key, the emitter was producing `z.strictObject`, and the two disagreed on the one input worth disagreeing about. Forbidding puts `additionalProperties: false` in the JSON Schema and makes both sides return the same verdict — and it is the right behaviour anyway, since model output is untrusted input and an unknown field is a signal.

**5. Pinned behind the current release, on purpose.** Next.js **16.2.12** and TypeScript **6.0.3**. 16.3.0 was 20 hours old and pnpm's release-age gate refused it, which is the gate working rather than a problem; bump when it clears. TypeScript stays on 6 for the reason in the table above.

Two things the plan expected that turned out not to be needed: `pgcrypto` (`gen_random_uuid()` has been core since Postgres 13, and `migrator` has no privilege to create an extension), and a custom lint rule for `pickle`/`yaml.load` in `api` (Ruff's `S` ruleset covers it; `scripts/checks/invariants.sh` catches the import anywhere).

**Where things ended up**

| | |
|---|---|
| `api/` | `lib/` · `db/` (engine, models, `tenant.py`) · `schema/` · `routes/` · `migrations/` · `tests/` · `scripts/export_schema.py` |
| `web/` | `src/app/` · `src/schema/` (`generated/` off-limits) · `scripts/generate-schema.mjs` · `eslint.config.mjs` |
| repo root | `docker-compose.yml` · `scripts/setup.sh` · `scripts/hooks/{pre-commit,post-edit.sh}` · `scripts/checks/invariants.sh` · `.github/workflows/gate.yml` |

## Exit gate

- [x] Both gates green (2.4s for the whole tree), CI workflow written, post-edit hook fires on a bad `.ts` **and** a bad `.py` write
- [x] **The schema round-trips: Pydantic → JSON Schema → Zod validator + inferred types, regenerating with no diff.** Proved on `schema/probe.py`, a throwaway carrying the one structural property phase 01 depends on — a discriminated union nested inside an object
- [x] `as_user` exists, is the only place `set_config` appears, and `invariants.sh` fails when a second file appears — verified by writing the violation and watching it fail
- [x] Unset-`app.user_id` fails rather than matching all rows. Observed on Postgres 18: the value reverts to `""` and `''::uuid` raises, so it refuses rather than matching
- [x] RLS policies on both tables, isolation test passing — including `with check`, which blocks writing a row owned by someone else
- [x] `docker compose up` gives Postgres and MinIO, offline
- [x] `storage.py` reads and writes an object through the S3 API against MinIO, and a missing key is a `Result` rather than an exception
- [x] `web` builds and `api` starts
- [x] A package published in the last day refuses to resolve **on both sides** — `next@16.3.0` blocked by pnpm, `boto3==1.43.63` blocked by uv, neither lockfile moved
- [x] `AGENTS.md` reviewed against what actually got built

One item is deferred rather than done: **`web` reaching `api` over HTTP**. There is no route in `web` that needs `api` yet, and building a client for a caller that does not exist is the speculative duplication this phase spent its budget avoiding. It lands in phase 06, with the first real call.
