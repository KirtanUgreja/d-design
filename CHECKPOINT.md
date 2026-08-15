# v3 checkpoint — 2026-08-15

Resume point. Working tree is clean at `b93ab33` on branch `main` (pushed to origin).

## What is done

The **entire v3 roadmap** is built, committed, and the gate is green through every commit:

| Phase | Status |
|---|---|
| 16 accounts | done — Better Auth + Drizzle auth tables, SQLAlchemy + asyncpg, Alembic migrations, two tenant wrappers (`api/db/tenant.py`, `web/src/db/tenant.ts`), RLS, fail-closed session resolution |
| 17 brand-kit-at-scale | done — teams/team_members/brand_kits + team-scoped RLS, isolated upload worker (sharp + DOMPurify + magic bytes), storage.ts → S3 (MinIO), FastAPI brand-kit routes |
| 18 hosting | done — render as a service (`POST /render`, same exporter as CLI), publish flow (render → S3 → api record), footer badge + AI disclosure (never removable), `experiences` + `published_key` |
| 19 billing | done — `quotas` table (atomic `update...returning` counter), free=1 URL w/ badge, paid via `FORCE_PLAN`, kill switch (`KILL_SWITCH=1`), brand kit gated to paid, entitlements route. **Stripe deferred** (user decision) — the `plan` column is the webhook slot |
| 20 pptx | **not started — conditional trigger not met** (recorded in the plan doc) |

Then `b93ab33` — the **first live end-to-end run** of the whole v3 product, which found and fixed six live-only defects:

- **`api/auth/session_data.py` → `resolve_session()`**: naive-vs-aware datetime crash (500) on the auth table's `expires_at`. Normalized to UTC.
- **`api/features/experiences/experiences_data.py` → `save_experience()`**: the insert never set `owner_id` — NOT NULL + RLS with-check violation. Now reads it from the session's `app.user_id`.
- **`api/ai/images.py`**: `openai/dall-e-3` 404s on the key; `1280x720` is rejected by modern image models. Now `openai/gpt-5-image-mini` at `1024x1024`.
- **`api/pipeline/mapping/mapping.py` → `_first_semantic_issue()`**: the distribution gate returned a hard Err with no recovery; the model reliably collapsed onto repeated layouts. Added the same bounded one-repair treatment the schema gets.
- **`api/pipeline/mapping/prompts.py` → the DISTRIBUTE rule**: now demands `max(4, N-1)` distinct layouts for N slides.
- **Auth tables never existed**: web's Drizzle was never run. Added `web/drizzle.config.ts`; the tables live in the `auth` schema (which the api resolver's `auth.session` query expects).

## Verified, not just built

The live run drove the whole product against the real stack:

- **Pipeline live**: brief → interview (human gate, approved) → mapping (with the new repair) → build → 6-slide scientific deck, **2 hand-drawn charts, 1 generated image** (`openai/gpt-5-image-mini`).
- **`samples/remote-work-2026-deck.html`** — the rendered single file (2.5 MB): `connect-src 'none'`, footer badge + `data-ai-disclosure="true"`, charts as inline SVG, image as data URI. **Open it in a browser.**
- **`samples/remote-work-2026-built.json`** — the pipeline payload (deck + images).
- **Publish path live**: real session (auth tables created) → `POST /experiences` → **201**; quota consumed (`used:1, exhausted:true`); second publish → **402** "free tier includes 1 hosted URL". RLS + quota + session resolution all proven together.
- **`samples/aurora-branded-deck.html`** — the phase-18 footer demo deck (editorial-serif, 3 slides).
- **`samples/crm-launch-deck.html`** — the v1 golden-run deck (browser-verified in the v1 checkpoint).

## The gate (must stay green)

```
./scripts/hooks/pre-commit        # api ruff+mypy · web prettier+eslint+tsc · render prettier+tsc+vitest · worker prettier+eslint+tsc+vitest · invariants · docs
./scripts/check-docs.sh           # links resolve, every .md indexed
```

110 api tests (incl. 9 quota + live-DB RLS) + 32 render + 7 web + 9 worker. Schema regenerates with no diff. Migrations at `0008_quotas` (head).

## The stack (docker compose)

```
docker compose up -d        # postgres, minio, render, worker — all healthy
```

- api: `uv run uvicorn app:app --port 8000` (routes: brand-kits, experiences, entitlements)
- render: port 8001 (`node dist/server.cjs`, or the compose service)
- `web/.env.local` has the S3/MinIO + Better Auth dev defaults; `.env` holds the preserved `OPENROUTER_API_KEY`.

## How to run the pipeline

From `api/` (requires the OpenRouter key):

```
uv run python -m cli interview --topic "..." --slides 6 --colors "..." --out /tmp/outline.json   # approve with y
uv run python -m cli mapping --outline /tmp/outline.json --family scientific --out /tmp/deck.json # chart-capable family
uv run python -m cli build --deck /tmp/deck.json --out /tmp/built.json                            # images live
curl -X POST http://localhost:8001/render -H 'content-type: application/json' --data @/tmp/payload.json > out.html
```

`--family scientific|swiss-grid|tech-minimal` supports the `chart` role (french-poster and others do not).

## Natural next steps (not started)

- **The human checks** — signup/login end-to-end in a browser, the security manual checklist (every route with no session / another tenant's session), the pricing/badge human read. The auth tables now exist and the api works, so this is a real possibility with the web app running.
- **Stripe integration** — deferred by decision until a Stripe account exists; the `quotas.plan` column is the webhook slot, `FORCE_PLAN` is the test knob.
- **The web app as a server** — it has no dev/build script; the editor has never run as a Next server in v3. Wiring `next dev` + the Drizzle auth tables (now possible via `drizzle-kit push`) is what the human checks need.
- **PPTX export** — dormant until the market trigger fires (recorded in `docs/v3/plan/20-pptx.md`).
- **Fontsource data-URI embedding** — the exported file uses system font stacks; the plan's follow-up is embedding the family faces as data URIs.
- **Real-browser `connect-src` assertion in CI** — currently a static test.

## Tooling notes

- pnpm 11: build-script allowlist lives in each package's `pnpm-workspace.yaml` (`allowBuilds: { esbuild: true }`), not package.json.
- The render container needed `jsx: 'automatic'` in `render/scripts/build.mjs` — esbuild defaulted to classic JSX where web's tsconfig wasn't discovered, causing "React is not defined" in the container. Verified fixed.
- `drizzle-kit push` in `web/` needs a TTY (it prompts about api-owned tables); the auth tables were created via direct DDL matching `web/src/db/schema.ts`.
