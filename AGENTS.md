# d-design

AI presentation-experience engine. The AI emits **content + intent**; a separate art-direction token layer resolves intent into type, spacing, color, easing, duration. **The AI never writes styling.** That one constraint is what makes editing safe, reskin cheap, and the product boundary real.

**Status: phases 00–05 done — a hand-written scene tree can be published, viewed, presented fullscreen, and embedded with no AI anywhere in the loop. Phase 06 (model seam + Build phase) next — the first phase with a model call in it.** `docs/` is the spec; `docs/v1/plan/README.md` is the build status. Start at `docs/README.md`.

**Two languages.** `api` and `jobs` are Python (FastAPI); `web`, `render`, and the fetch worker are TypeScript. **Pydantic owns the `Scene` schema** — the Zod validator and its types are generated from it and are never hand-edited. See `docs/techstack/decisions.md` → "The Python backend move".

## Layout and commands

One repo, two project roots. `render`, `jobs` and the fetch worker are v2/v3 and get their own directories when they arrive.

```
api/    Python. lib/ db/ schema/ routes/ features/ migrations/ tests/   → uv
web/    TypeScript. src/app/ src/features/ src/schema/                  → pnpm
scripts/  setup.sh · hooks/{pre-commit,post-edit.sh} · checks/invariants.sh
```

```
./scripts/setup.sh                          # hooks, both installs, docker, migrations
docker compose up -d                        # Postgres + MinIO
cd api && uv run --env-file .env uvicorn main:app --reload
cd api && uv run pytest -q                  # needs docker compose up
cd web && pnpm dev
cd web && pnpm schema:generate              # after ANY change to api/schema/
./scripts/hooks/pre-commit                  # the gate, on demand
```

`api/` is the Python project root, not a package — modules are `lib.result`, `db.tenant`, `schema.scene`, and scripts run as `uv run python -m scripts.<name>`.

## Read before you write

Paths are **pointers, not imports** — read the file when the task touches it. Do not prefix with `@`; that inlines the whole corpus into every session.

| Task touches | Read first |
|---|---|
| Any code at all | `docs/coderules/README.md` |
| Where a file or feature goes | `docs/coderules/structure.md` |
| Backend code, Pydantic, the schema codegen | `docs/coderules/python.md` |
| Renderer/editor code, generated types, error handling | `docs/coderules/typescript.md` |
| Adding a package — **including any agent framework** | `docs/coderules/dependencies.md` |
| Renderer, data access, model calls | `docs/coderules/patterns.md` |
| DB, auth, tenants, RLS | `docs/coderules/patterns.md` + `docs/security/tenancy-and-data.md` |
| User input, uploads, URLs, tokens, CSP | `docs/security/README.md` (routes by threat) |
| Prompts, models, evals, AI tools | `docs/techstack/ai-stack.md`, `docs/techstack/pipeline-tools.md` |
| Where something runs or deploys | `docs/techstack/infrastructure.md` |
| "Why was this chosen?" | `docs/techstack/decisions.md` |
| The scene tree | `docs/v1/scene-schema.md` |
| What to build next | `docs/v1/spec.md` → Build order |

## Non-negotiable

1. Strict types both sides. TS: no `any`, no `!`. Python: `mypy --strict`, no bare `Any`, no unexplained `# type: ignore`.
2. One schema parse per external input, at entry — Pydantic in `api`, Zod in `web`. Model output, tool-call arguments, and anything crossing a process boundary are all external input.
3. Expected failures return `Result`; only bugs throw/raise.
4. Import across features only through their public surface (`index.ts` / `__init__.py`).
5. No new dependency without a ledger line in `docs/coderules/dependencies.md`. Anything parsing untrusted bytes goes in the fetch worker. **An agent framework needs a ledger line too — "everyone uses it" is not one.**
6. `renderer/` core is pure — no `mode` prop, no `process.env`, no `typeof window`. It runs in three processes and must behave identically in all of them.
7. AI output carries no presentational values (hex/px/font/duration). The schema has no field for them.
8. The ORM only in a feature data module — SQLAlchemy in `*_data.py`, Drizzle in `*.data.ts` with `import 'server-only'`. Drizzle touches **auth tables only**.
9. Every tenant-scoped query goes through the tenant wrapper. There are **exactly two** — `as_user()` and `asUser()` — and a third is a bug.
10. Anything that grants, fails closed. A `catch`/`except` returning a permissive default is a vulnerability, not error handling.
11. The gate is green — typecheck, lint, format, **and the schema regenerates with no diff** — or the commit does not land. `scripts/checks/invariants.sh` enforces 1, 8, 9 and the no-agent-framework rule by grep; run it before you assume you are clean.

## How to work

**Before writing a helper, grep for it.** The measured failure mode of AI-written code is duplication, not incorrectness — a second copy of something that already exists. Rules 6, 8, 9 and the model seam each exist because there must be exactly one of that thing.

**Ponytail mode:** the laziest solution that works. Platform over dependency, one line over fifty, deletion over addition. Mark a deliberate shortcut with a `ponytail:` comment naming the ceiling and the upgrade path.

**Never:** loosen rule 7 with a `styleOverride` field · add `allow-same-origin` to the Slot sandbox · give the AI a tool with side effects · authorize in middleware alone · log prompts, scene content, or recipient fields · **hand-edit generated TypeScript in `@d-design/schema`** · **install an agent framework** (LangGraph, CrewAI, Pydantic AI, …) — the pipeline is four sequential calls, and the framework would be privileged; see `docs/techstack/ai-stack.md`.

**Docs:** editing any `.md` means `./scripts/check-docs.sh` must still pass — every link resolves, every file is listed in its directory README.
