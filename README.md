# d-design

**An AI presentation maker whose edge is design.** You type a brief, answer a few questions, approve an outline where every number has a source, see the deck's style, and watch the deck arrive slide by slide. You get a deck that looks designed by a person, unlike the last one it made, exported as **one offline `.html` file** (and a PDF).

**Live:** https://web-production-41f09.up.railway.app. Sign-up is limited to the owner's allowlist; ask for access.

## How it makes a deck

| Step | What happens | Where |
|---|---|---|
| Brief → questions | A few targeted questions, including what the product does; skippable | `api/engine/content/interview.py` |
| **1. Research** | Two web searches at once: a **product file** (what it does, for whom, features, pricing, traction, competitors) and the **market evidence** the story needs. Only what a returned page quotes is kept | `api/engine/studio/research.py` |
| **2. Outline** | One argument, a claim and a short explanation per slide, points, a figure, a chart from approved facts or a drawn product visual. Every number traces to you or a source, or is held for your decision | `api/engine/studio/outline.py` |
| **Style** | One of **8 visual languages**, then a generated palette (built around **your brand colour** if you give one) and a type pairing. Three thumbnails of *your* slides show it before you pay for a build | `api/engine/design/`, `api/library/languages/` |
| **3. Art director → designer** | One call plans every slide's composition for the whole deck (hero, field, crop, scale), so no two neighbours look alike. Then a designer writes each slide in real HTML, CSS and flat SVG, inside the deck's tokens. No templates, no reference library | `api/engine/studio/direct.py`, `design.py` |
| **4. Improver** | A creative director **looks at a screenshot of each rendered slide**, critiques it and redesigns it to be bolder. The redesign is kept only if QA measures it no worse | `api/engine/studio/improve.py` |
| **5. Deck review** | The whole deck on one sheet, judged as a piece: rhythm, look-alikes, the tells of AI-made slides. The two weakest slides go back to the improver with a note | `api/engine/studio/review.py` |
| **Check** | Every slide is rendered in Chromium and measured: overflow, collisions, contrast (WCAG + APCA), type size, empty blocks. A defect gets two targeted repairs, then a code-built layout, then a visible flag. Nothing broken ships silently | `api/engine/qa/`, `api/engine/studio/build.py` |
| Edit → export | Edit text, reorder, recolour, fit, undo; present, send (one offline file, zero network requests) or PDF | `api/worker.py`, `api/engine/export/` |

## Architecture

```
browser ──▶ web (Next.js 16, public) ──private network──▶ api (FastAPI) ──▶ Neon Postgres "app"
              │ Better Auth (email + password,                                   ▲
              │ allowlist) ─▶ Neon Postgres "auth"                               │
              │ signs a short EdDSA JWT per request                    worker (model key, Chromium)
```

- **web** is the only public service. It never exposes the JWT to the browser: its `/api` proxy mints one per request.
- **api** verifies the JWT against Better Auth's JWKS. It fails closed: an unreachable JWKS is a 401. Every deck route goes through one tenant wrapper, so another user's deck is a 404. A per-user daily spend cap also fails closed. The api holds **no model key** and runs no browser.
- **worker** has no inbound port. It is the only holder of the OpenRouter key and of Chromium, and claims jobs from Postgres with `SKIP LOCKED`.
- **Data:**
  - In Neon: decks, events, versions, a ledger of every model call's cost per user, and slide files stored by content hash.
  - Better Auth's tables live in their own database, which Python never reads.
- **Hosting:** Railway runs the three services in US East, beside Neon.

## Run it locally

```bash
./scripts/setup.sh          # once: git hooks, Python deps, Chromium
cp .env.example .env        # fill in the keys it lists
./scripts/dev.sh            # api + worker + web → http://localhost:3000
```

`web/.env.local` needs `AUTH_DATABASE_URL` and `BETTER_AUTH_SECRET`. Without accounts, `AUTH_DISABLED=1 uv run uvicorn app:serve --factory` serves one local user.

## Tests and the gate

```bash
cd api && uv run pytest -q          # 180 tests, offline: fake models, real Chromium
cd web && pnpm e2e                  # sign-up, sign-in, the flow, the token proxy
./scripts/hooks/pre-commit          # ruff, mypy --strict, pytest, eslint, tsc, OpenAPI drift, docs
cd api && uv run python -m cli refs --check swiss --looks 30   # a language's references under 30 looks
```

The security tests (`api/tests/test_security.py`) call every route with no session, with a forged token and with another user's session. They also cover the spend cap, including a cap check that itself fails.

## Status: honest

| | |
|---|---|
| Built and tested offline | Everything above |
| Not yet measured | The owner's 12-deck wall for the new design system (design ≥ 4/5, variety ≥ 4/5, "would send it" ≥ 9/12) and the image and compose model bake-offs. These run on test day with fresh model credit. Until then, the design claims are untested |
| Known limits | One worker, so builds queue. Variety across decks is bounded by the size of the reference library. No password reset or OAuth: email and password for an allowlist only |

Plans and decisions: [`docs/v4/plan/master-plan.md`](docs/v4/plan/master-plan.md). Why things are the way they are: [`docs/v4/spec.md`](docs/v4/spec.md). Rules for code: [`AGENTS.md`](AGENTS.md).
