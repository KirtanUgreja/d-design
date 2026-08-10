# d-design

AI presentation engine. The AI emits **content + intent**; a separate art-direction token layer resolves intent into type, spacing, color, easing, duration. **The AI never writes styling.** That one constraint is what makes editing safe, reskin cheap, and the product boundary real.

> **The product is being re-decided from the vision up, as of 2026-08-10.** The `v1/`, `v2/` and `v3/` documentation was deleted — not because it was wrong, but because three releases of layered corrections had made the live decisions hard to find, and the framing underneath them was being changed rather than corrected. Everything is in git history.
>
> **Do not infer product direction from the code.** The code is the record of a plan that is currently under revision. Ask before building anything that assumes a wedge, a surface, or a roadmap.
>
> `docs/versions.md` is the shape the next version directory takes. `docs/findings.md` is the evidence it should not have to rediscover — measurements, model behaviour, the category, dated platform facts.

## What exists in the code, factually

This part is not in question — it runs, and the acceptance run passes.

- **The pipeline works end to end.** A prompt becomes a Brief, an editable outline, streamed scenes, an experience you edit two ways, publish, present fullscreen and embed. Eval corpus green: 5/5 golden briefs, 7/7 injection payloads.
- **Three art directions**, `cinematic-dark`, `editorial-light` and `bold-brutalist`, rendering the same fixture tree with **no branch in the renderer**. Rows in `art_directions`, not TypeScript constants.
- **Eleven primitives, six layouts, six texture kinds, six font families** — see `docs/findings.md` for what that measures out to, which is smaller than it sounds.
- **Two languages.** `api` and `jobs` are Python (FastAPI); `web`, `render` and the fetch worker are TypeScript. **Pydantic owns the `Scene` schema** — the Zod validator and its types are generated from it and never hand-edited. See `docs/techstack/decisions.md` → "The Python backend move".

**~180 source files carry comments pointing at the deleted docs.** They explain why code looks the way it does and now point into git history. Leave them; they get corrected as the code is touched.

## Layout and commands

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
| Our own app and site — **never the engine's output** | `docs/design/README.md` |
| Writing the next version's docs | `docs/versions.md` |
| "Do we already know this?" | `docs/findings.md` |
| **What to build next** | **Not written yet.** The vision is being settled first — ask |

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
