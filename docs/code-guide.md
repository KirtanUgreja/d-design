# Code guide — every part of d-design, in plain words

Written 2026-10-10 for the owner and the project jury. It explains what each folder and file does, how a deck travels through the system, and what every term in the code means. For *why* a decision was made, follow the links into [v4/](v4/README.md).

## 1. The whole system in one picture

```
 Browser
   │  types a brief, answers questions, edits the outline, watches, edits, exports
   ▼
 web/  Next.js 16 app (TypeScript, React 19, Tailwind 4, shadcn/ui)
   │  • sign-in (Better Auth, its own "auth" database)
   │  • every /api/* call is forwarded with a short-lived signed token (JWT)
   ▼
 api/app.py  FastAPI (Python 3.13) — "the API"
   │  • checks the token, checks the deck belongs to you, validates input
   │  • reads decks and puts jobs in a queue — it never calls an AI model
   ▼
 Postgres "app" database on Neon  (decks, jobs, events, files, spend)
   ▲
   │  claims one job at a time
 api/worker.py  — "the worker" (the only process with the AI key)
   │  • runs the engine: research → outline → design → check → review → export
   │  • calls Claude through OpenRouter; renders every slide in Chromium
   ▼
 Events stream back to the browser live (server-sent events)
```

Three services run on **Railway**: `web`, `api` and `worker`. Each is built from its own Dockerfile. The worker is the only one holding `OPENROUTER_API_KEY`.

## 2. How one deck is made, step by step

| Step | What the person sees | What runs | Where in the code |
|---|---|---|---|
| 1. Brief | types what they're presenting on the home page | `POST /api/decks` creates a deck (status `brief`) and queues an `interview` job | `web/components/composer.tsx`, `api/app.py` |
| 2. Interview | 3–6 questions with suggested answers | Claude Haiku writes the questions; answers are folded into the brief | `api/engine/content/interview.py` |
| 3. Screenshots (optional) | uploads up to 6 images | the worker re-encodes each one (never trusts the upload) | `web/components/screens-picker.tsx`, `api/worker.py` → `_screens` |
| 4. Research | "Searching the web for sources" | web search for numbers; each quote is checked against its page | `api/engine/studio/research.py` |
| 5. Outline | the outline page | Claude writes one argument, one claim per slide; code links every number to a fact | `api/engine/studio/outline.py` |
| 6. Outline gate | edit, remove, rewrite, approve numbers | `PATCH /api/decks/{id}/outline`, `POST …/outline/ask` | `web/components/outline-gate.tsx` |
| 7. Look | the style card (name, colours, type) | the deck's visual language and palette are drawn once and kept | `api/looks.py`, `api/engine/design/*` |
| 8. Build | slides arrive one by one, with a live feed | the studio's layers, below | `api/engine/studio/build.py` |
| 9. Edit | change words, ask one slide or the whole deck | edit jobs; QA runs again; every change is a version you can undo | `web/components/live-editor.tsx`, `api/ops.py`, `api/worker.py` |
| 10. Export | Present, Download to send, PDF | one offline `.html` file with zero network requests; PDF printed by Chromium | `api/engine/export/` |

### The build, layer by layer (`api/engine/studio/`)

1. **Art director** (`direct.py`): one call sees the whole outline and plans each slide: its hero, its ground (dark or light), whether it has a picture. Code enforces rhythm, for example never three slides in a row on the same ground.
2. **Designer** (`design.py`): for each slide, Claude Sonnet writes **real HTML and CSS** (and flat SVG), using only the deck's colour and type tokens. Four slides are designed at once.
3. **Measure** (`engine/qa/browser.py`): the slide is rendered in Chromium at 1920×1080 and measured: text off the canvas, overflow, contrast, crowding.
4. **Improver** (`improve.py`): a critic looks at the *screenshot*, scores it and redesigns it. The redesign is kept only if it measures no worse.
5. **Repair**: a slide that still fails gets targeted repairs. The cover gets one more fresh design. Only then does the code-built fallback layout stand in, and the slide is marked.
6. **Deck review** (`review.py`): one call sees all slides on a contact sheet and sends back up to two to redo.
7. **Assemble** (`engine/export/assemble.py`): every slide goes into one HTML file, each in its own Shadow DOM so its CSS can't leak.

## 3. Every folder and file

### Root

| Path | What it is |
|---|---|
| `README.md` | How to run it |
| `AGENTS.md`, `CLAUDE.md` | Instructions for AI coding assistants working in this repo: the rules, commands and where to read first |
| `.env.example` | The environment variables, without secrets. The real `.env` is never committed |
| `db/` | **The two databases as SQL**, generated ([db/README.md](../db/README.md)) |
| `docs/` | Every decision and plan (this file is one) |
| `bench/` | Test briefs, baseline decks and the rubric used to score designs |
| `reports/` | Weekly progress reports |
| `scripts/` | `setup.sh` (installs the git hooks), `dev.sh` (runs everything locally), `check-docs.sh` (docs links), `vendor_fonts.py` (downloads the open fonts), `hooks/` (the commit gate) |
| `.github/workflows/` | The same gate, run on GitHub |

### `api/` — the Python backend

| File | What it does |
|---|---|
| `app.py` | **The API.** Every route: create, read and delete decks, answer questions, edit the outline, build, edit slides, upload a logo or screenshots, rename, export, the event stream, your account. It never calls a model |
| `worker.py` | **The worker.** Takes jobs from the queue and runs them: interview, outline, build, edits, logo and screenshot checks. Holds the AI key |
| `auth.py` | Checks the token the web app sends: signature, issuer, audience, expiry |
| `settings.py` | **The only file that reads environment variables.** The AI models are pinned here: Sonnet 5.5 writes and designs, Haiku 5.5 asks the questions and writes the notes, plus an image model, the daily cap and the per-deck budget |
| `looks.py` | Picks a deck's visual language once and builds its theme |
| `ops.py` | The editor's operations: text edit, reorder, delete slide, recolour, fit, ask a slide, ask the deck, accept a change |
| `cli.py` | Command-line tools: `smoke` (one live call), `openapi` (the API schema for the web), `schema` (the SQL in `db/`), and the bench tools (`freeze`, `baseline`, `build`, `wall`, `bakeoff`, `content`, `injection`, `export`, `fonts`) |
| `alembic.ini`, `migrations/` | Alembic: creates and upgrades the `app` database's tables |
| `Dockerfile`, `Dockerfile.worker` | How Railway builds the API and the worker. The worker's image also contains Chromium |
| `pyproject.toml`, `uv.lock` | Python packages, managed by `uv` |
| `lib/result.py` | `Result`: success or an expected failure, as a value instead of an exception |
| `store/` | **The data module**, the only code that reads or writes data. `sql.py` is Postgres, `files.py` is the same interface on plain files for tests, `models.py` holds the tables, and `tenant.py` is the wrapper that makes sure you only ever reach your own decks |
| `benchtools/` | The bench: baselines, frozen outlines, screenshots, the scoring wall, font measurement |
| `library/languages/` | The 12 visual languages as JSON. **Four are on** (Studio, Frame, Bright, Soft); the others keep old decks' looks |
| `library/fonts/` | Open-licence fonts, stored in the repo so an exported deck never fetches a font |
| `tests/` | About 210 automated tests. A fake model stands in for Claude, so tests cost nothing |

### `api/engine/` — the engine (pure: no web framework, no environment)

| File | What it does |
|---|---|
| `__init__.py` | The engine's public surface. Everything outside imports from here |
| `models.py` | **Every data shape**: Brief, Deck, Fact, Storyline, SlidePlan, Slide, ChartSpec, VisualSpec, Screen. Pydantic checks them; the web's TypeScript types are generated from them |
| `llm/openrouter.py` | **The model seam**, the only code that calls an AI. Plain HTTP to OpenRouter, with retries, a budget check, and a ledger row per call (cost and sizes, never content) |
| `content/interview.py` | Writes the questions and folds the answers into the brief |
| `content/arcs.py` | The story shapes per deck kind (pitch, sales, launch, investor update, partnership, project) and the evidence each needs |
| `content/rules.py` | Word rules: banned filler words, a number must have a source, headline length |
| `content/notes.py` | Speaker notes, 40–120 words per slide |
| `studio/research.py` | Web research. Your own numbers come from your words; web numbers keep their exact quote and link |
| `studio/outline.py` | The storyline: one argument, one claim per slide, the deck's short name, the figures, visuals and screenshot placements; it also takes an outline change in words |
| `studio/direct.py` | The art director |
| `studio/design.py` | The designer, the repair, the one-slide edit ("revise"), and the code-built fallback layout |
| `studio/improve.py` | The improver (the critic that looks at screenshots) |
| `studio/review.py` | The whole-deck review |
| `studio/slide.py` | The rules every slide must meet (the "contract"), the list of AI tells to avoid, the scoring rubric, and the one parser that checks every answer |
| `studio/build.py` | Runs the layers in order, four slides at a time, with the budget, the events and the screenshot placement |
| `studio/preview.py` | The style card's text: style name, idea, fonts and colours |
| `design/languages.py` | Loads the visual languages and chooses one per deck |
| `design/sampler.py` | Draws a deck's look: language, font pairing, grid, ground, density. Seeded by the deck id, so it's repeatable |
| `design/theme.py` | Turns a look into a Theme: the CSS variables (`--c-ink`, `--t-h2`, …) slides may use |
| `design/palettes.py`, `design/color.py` | Colour generation in OKLCH, and contrast maths (WCAG and APCA) |
| `design/dataviz.py` | Checks chart colours for colour-blind separation and contrast |
| `design/patterns.py` | Textures and the deck's mark, generated per deck |
| `design/axes.py` | The lists the sampler picks from (pairings, grids, edges) |
| `components/charts.py` | Charts drawn by our code as SVG, so every value is exact |
| `components/visuals.py` | Product diagrams drawn as SVG: flow, hub, pipeline, stack, phone, browser, chat, waveform |
| `components/images.py` | Pictures: generated in the deck's image style, or your screenshot; re-encoded and cropped |
| `components/logo.py` | Your logo: checked, cleaned, placed on the cover and the close |
| `qa/sanitize.py` | **Security layer 1.** Model-written HTML passes an allowlist: no scripts, links or remote images |
| `qa/lint.py` | **Layer 2.** Model-written CSS: only theme tokens for colour and type; no gradients, blur, animation or remote URLs |
| `qa/browser.py` | **Layer 3.** Renders in Chromium with every network request blocked, measures, screenshots |
| `qa/metrics.py` | The thresholds: what counts as an error (repair it) or a warning |
| `compose/document.py` | Puts slides into one document, each in its own Shadow DOM |
| `compose/edit.py` | Text edits that need no model |
| `export/assemble.py` | The offline HTML file: "present" (with notes and presenter view) and "send" (slides only) |
| `export/pdf.py` | The PDF, printed from the "send" file |

### `web/` — the Next.js frontend (UI only; no deck logic)

| Path | What it does |
|---|---|
| `app/page.tsx` | Home: the composer, your decks, the wall of real slides, the three proofs |
| `app/(auth)/` | Sign in and sign up |
| `app/account/` | Account: details, change password, avatar, the colour game, sign out, delete |
| `app/decks/` | Your decks, each with Delete |
| `app/d/[id]/page.tsx` | One deck through every stage |
| `app/api/[...path]/route.ts` | **The one door to Python**: no session → 401; a session → a fresh 5-minute token added to the call |
| `app/api/auth/[...all]/route.ts` | Better Auth's own routes |
| `proxy.ts` | Sends signed-out visitors to sign-in before private pages |
| `components/composer.tsx` | The prompt box with kind, slide count and tone |
| `components/live-deck.tsx` | The deck page: follows the deck's events and shows the right stage |
| `components/working.tsx` | The waiting screens: real steps, sources found, the live build feed, time so far |
| `components/outline-gate.tsx` | The outline: source marks (YOU, WEB), Edit, Remove, move, Change the outline, approve |
| `components/style-card.tsx`, `brand-colours.tsx`, `logo-picker.tsx`, `screens-picker.tsx` | The outline page's side panel |
| `components/live-editor.tsx` | The editor: words, move, delete, fit, ask a slide, ask the deck, recolour, undo |
| `components/delete-deck.tsx`, `deck-card.tsx`, `your-decks.tsx` | Deck lists and deleting |
| `components/showcase.tsx`, `proofs.tsx` | The home page's wall and proofs |
| `components/colour-game.tsx` | Match the colour |
| `components/ui/` | shadcn/ui building blocks (button, alert-dialog, tabs, and so on) |
| `lib/api/client.ts` | Every call to the API, and the parsing of each answer |
| `lib/api/openapi.json`, `schema.d.ts` | **Generated** from the Python API; the commit gate fails if they drift |
| `lib/auth.ts`, `auth-client.ts`, `auth-allow.ts`, `auth-me.ts` | Better Auth on the server and in the browser, the sign-up allowlist, your profile |
| `public/showcase/` | The 20 slide images on the home page |
| `e2e/auth.spec.ts` | Browser tests of sign-up, sign-in and access rules |

## 4. Glossary

| Term | Meaning |
|---|---|
| **Brief** | What the person typed, plus their answers and pasted material |
| **Deck kind** | pitch, sales, launch, investor update, partnership or project; it sets the story's default order (the **arc**) |
| **Outline / storyline** | The deck's argument: a short name, one governing thought, and a plan per slide |
| **Beat** | A slide's role in the story ("Problem statement", "Demo") |
| **Field** | One piece of a slide's words: `headline`, `kicker` (the small label above), `body`, `point-1`, `figure-1` with `figure-1-label` |
| **Fact** | A number or claim with where it came from: `user` (you), `cited` (a web page, with its quote) or `illustrative` (marked as such) |
| **Provenance — YOU, WEB, AI** | The marks on the outline: your words, a cited source, or written by the AI |
| **Visual language / look** | A whole design system: type kinds, grids, grounds, texture, images, surface. Four are on: Studio, Frame, Bright, Soft |
| **Theme tokens** | The only colours and type a slide may use, as CSS variables: `--c-ground`, `--c-ink`, `--c-accent`, `--t-d1` … `--t-h2`, `--f-display` |
| **Finish: grain, glow** | Film grain and one soft glow drawn by our code, only in looks that allow them. The AI may never write gradients or glow |
| **`dd-chart`, `dd-visual`, `dd-image`** | Empty boxes the AI places in a slide; our code fills them with the chart, the diagram or the picture after sanitizing |
| **Visual kinds** | flow (steps), hub (parts around a centre), pipeline (input, core, output), stack (tech layers), phone, browser, chat, waveform |
| **Origin** | How a kept slide was made: `authored`, `improved`, `repaired`, `fallback` (the code layout) or `edited` |
| **QA, E- and W-codes** | Browser measurements. An **E**rror (e.g. text off the canvas) triggers repair; a **W**arning (e.g. a lot of empty space) is reported |
| **Flagged** | A slide that still has an error after every repair. It's named before you download |
| **Fallback** | The code-built layout used only when every AI design failed |
| **Proposal** | A one-slide change shown before it's applied; **Accept** applies it |
| **Version / history** | A labelled snapshot after each change; undo goes back up to 20 |
| **Job** | A unit of work for the worker: `interview`, `outline`, `build`, `edit`, `style`, `logo`, `screens` |
| **Event** | A numbered message the page receives live (slide ready, stage started, research found N sources) |
| **SSE** | Server-sent events, how the events reach the browser |
| **Ledger** | One row per AI call: model, tokens, cost. Never the prompt or the deck |
| **Daily cap** | The most one person may spend per UTC day (`DAILY_CAP_USD`). Checked before any paid step; if the check itself fails, it refuses |
| **Budget** | The most one deck may spend (`deck_budget_usd`) |
| **Tenant** | "You, and only your decks". Every route goes through `store/tenant.py` |
| **JWT, JWKS** | The signed token the web sends to Python, and the public keys Python uses to check it |
| **Allowlist** | The emails allowed to sign up in this preview (`ALLOWED_EMAILS`) |
| **Blob** | File bytes stored once by their hash |
| **Alembic** | The tool that creates and upgrades the Postgres tables |
| **OpenAPI drift** | The web's generated types must match the Python API; the gate checks it |
| **The gate** | The checks every commit must pass: ruff, mypy --strict, pytest, eslint, tsc, OpenAPI drift, docs links |
| **Bench, wall** | Fixed test briefs, and a page of all their slides that the owner scores by eye |
| **Ponytail** | A comment marking a deliberate shortcut, its limit and the upgrade path |
| **Shadow DOM** | Each slide lives in its own isolated box, so one slide's CSS can't touch another |
| **OKLCH, OKLab** | Colour spaces where lightness is perceptual; palettes are built and compared in them |

## 5. The rules the code keeps

The full list is in [coderules/README.md](coderules/README.md). In short:

- Strict types everywhere.
- Every input is checked once, at the door. AI output counts as input.
- Expected failures are values, not crashes.
- Only theme tokens for colour and type in AI-written slides.
- One data module.
- The engine reads no environment.
- Anything that grants something fails closed: if the spending check can't run, the answer is no.
- Nothing lands unless the gate is green.

## 6. Running it

```
./scripts/setup.sh                       once: installs the git hooks
./scripts/dev.sh                         api + worker + web on http://localhost:3000
cd api && uv run pytest -q               the tests (free: a fake model)
cd api && uv run python -m cli schema    rewrite db/app.sql and db/auth.sql
cd api && uv run python -m cli openapi   rewrite the web's API types (then: cd web && pnpm api:types)
railway up ./api --path-as-root --service api --detach      deploy (also: worker; ./web for web)
```
