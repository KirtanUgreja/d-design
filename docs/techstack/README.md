# Tech Stack

> What this is built with, where each piece runs, and why. **Re-decided 2026-09-26 with v4** ([../v4/spec.md](../v4/spec.md)). There are two packages and three processes, each concern has one owner, and the model gateway is still vendor-neutral.

**Start here:** [The shape](#the-shape).

**Looking for one decision and its rejected alternative?** [decisions.md](decisions.md) is the full log. The 2026-09-26 reversals are at the top.

## The shape

Two packages, three processes, two languages, and one rule. **The backend owns everything the product is. The frontend owns only what the user touches.**

```
                ┌────────────────────────────────────────────────────┐
  browser  ───▶ │  web — Next.js 16 + React 19                   TS  │  UI only:
                │  composer · interview · outline · looks ·          │  no DB, no model key,
                │  generation watch · editor · present               │  renders no slide itself
                └─────────────────────────┬──────────────────────────┘
                                          │  /api/* (rewrite in dev) · SSE over fetch
                                          ▼
                ┌────────────────────────────────────────────────────┐
                │  api — FastAPI, Python 3.13                    PY  │  internet-facing
                │  routes · one Pydantic parse at entry ·            │  NO model key,
                │  SSE tails events.jsonl                            │  NO browser
                └─────────────────────────┬──────────────────────────┘
                                          │  file store (single writer) · job files
                                          ▼
                ┌────────────────────────────────────────────────────┐
                │  worker — api/worker.py, same codebase         PY  │  no inbound port
                │  engine/  interview · research · storyline ·       │  holds the
                │           compose · QA · export                    │  OpenRouter key
                │  Chromium — every request aborted · Pillow         │
                └─────────────────────────┬──────────────────────────┘
                                          │
                     OpenRouter — text, image, web_search (ZDR routes only)

  artefact: one offline .html per deck. The player, embedded fonts, webp images,
            CSP default-src 'none', connect-src 'none'
```

**Before phase 27 there is no API and no worker process**: the CLI calls the engine directly. The split arrives with the app, because that is when something internet-facing exists to split from.

**Four ideas carry this diagram.**

**Each concern has one owner.** v3 split the product across five runtimes:
- `web` rendered the deck, and Python decided it.
- A `render` service bridged the two languages.
- A `fetch` worker parsed uploads.
- Auth lived half in each language.

v4 gives the engine, the data and the export to the backend alone. The frontend renders nothing of the deck itself:
- It shows backend-produced HTML in a script-less iframe.
- It presents the export file byte for byte.
- It uses QA screenshots as thumbnails ([frontend.md](frontend.md)).

**The model composes, and the backend checks.** The model writes each slide's HTML and CSS within theme tokens. Every slide is rendered in a real browser, measured and repaired before anyone sees it ([../v4/design-engine.md](../v4/design-engine.md)). That needs a browser in the backend, and it lives in the worker process ([backend.md](backend.md) → "The worker").

**The process that faces the internet holds nothing worth stealing.** The API never calls a model or a browser and never holds the OpenRouter key. The worker does all three and accepts no inbound connection. v3 had the same idea in its fetch worker; v4 applies it to the one secret and the one browser it actually has.

**The artefact is still the file.** One self-contained `.html` per deck, with `connect-src 'none'` and fonts and images embedded. It comes in two flavours, **present** (with speaker notes) and **send** (without), so emailing a deck never leaks the notes ([frontend.md](frontend.md) → "The exported deck"). That has been the decision since 2026-08-13, and v4 is what makes it true: v3's exporter shipped system font stacks and no `@font-face` at all (../findings.md).

## The stack

| Layer | Choice | Doc |
|---|---|---|
| **Backend language** | **Python 3.13**, `mypy --strict` | [ai-stack.md](ai-stack.md) → "Language" |
| **Backend framework** | **FastAPI** | [backend.md](backend.md) |
| **Schema / validation** | **Pydantic**, the one source. TypeScript types for web are generated from FastAPI's OpenAPI | [backend.md](backend.md) → "The API contract" |
| **Model access** | **OpenRouter** via plain async `httpx`, from the worker only. JSON mode for structured stages, **text mode** for slide HTML. One **pinned** model id per stage, chosen by the phase-22 bake-off | [ai-stack.md](ai-stack.md) |
| **Facts** | `openrouter:web_search`, with `url_citation` annotations becoming `Fact`s | [ai-stack.md](ai-stack.md) → "Web search" |
| **QA · thumbnails · PDF** | **Playwright (Python)** in the worker: one browser, a page pool, every request aborted except `data:` | [backend.md](backend.md) → "The worker" |
| **AI-written HTML safety** | **`nh3`** (HTML allowlist, no `<a>`) · **`tinycss2`** (CSS lint only) · **Declarative Shadow DOM** for per-slide scoping · a script-less iframe · the export CSP | [../security/content-and-web.md](../security/content-and-web.md) → "AI-written HTML and CSS" |
| **Design system** | **Pure code.** A seeded generator makes one look per deck, mostly from continuous parameters. No model call | [../v4/design-engine.md](../v4/design-engine.md) |
| **Fonts** | ~40 OFL families vendored as Latin-subset woff2, licence checked per family, **embedded as-is**. `fontTools` is deferred | [frontend.md](frontend.md) → "Fonts" |
| **Images** | OpenRouter image models → **Pillow** (webp only) → data URIs carrying the IPTC `trainedAlgorithmicMedia` tag. Our code's call, not a model tool | [pipeline-tools.md](pipeline-tools.md) |
| **Streaming** | The worker appends to `events.jsonl`; the API's SSE tails it and honours `Last-Event-ID`. Web reads it with a fetch-stream reader | [backend.md](backend.md) → "The worker" |
| **Storage** | A file store, `api/store/files.py`, the only data module: atomic writes, a per-deck lock, a version check → Postgres + SQLAlchemy + Alembic at phase 29, owned by Python alone |
| **Spend** | A per-deck `budget_usd` hard cap that fails closed, read from the cost ledger | [backend.md](backend.md) → "Budget" | [backend.md](backend.md) → "Data" |
| **Auth** | Phase 29: **Better Auth** in the web app (owner, 2026-10-08; email and password), its JWT verified in FastAPI by PyJWT's `PyJWKClient` | [backend.md](backend.md) → "Auth (phase 29)" |
| **App framework** | Next.js 16 App Router + React 19 | [frontend.md](frontend.md) |
| **App chrome UI** | shadcn/ui + Tailwind 4 on our brand tokens | [frontend.md](frontend.md) |
| **API types in web** | `openapi-typescript`: generated, never hand-edited, no-diff gate. SSE event models are registered in OpenAPI explicitly | [frontend.md](frontend.md) → "The app: UI only" |
| **Agent framework** | **None.** The pipeline is a plain orchestrator and the model has no tool with side effects | [ai-stack.md](ai-stack.md) → "Agent framework: none" |
| **Evals** | The v4 bench: 12 briefs, a wall of rendered decks, human scores, and content evals | [ai-stack.md](ai-stack.md) → "Evals", [../v4/bench.md](../v4/bench.md) |
| **Tests** | pytest, with Playwright for the artefact assertions · Vitest + Playwright E2E for web | [../coderules/tooling.md](../coderules/tooling.md) |
| **Package managers** | **uv** (Python) · pnpm (TypeScript) | [../coderules/dependencies.md](../coderules/dependencies.md) |
| **Hosting** | Local-first. The deploy target is decided at phase 29 | [infrastructure.md](infrastructure.md) |

**Removed by v4** (phase 21 does the deleting; the last state of each is at commit `8169fd9`):
- the `render` service and the v3 upload `worker` (unrelated to v4's `api/worker.py`)
- MinIO and `docker-compose.yml`
- Better Auth + Drizzle, and the RLS migrations
- the quotas, kill-switch, teams and `briefs` tables
- the Pydantic→Zod `Deck` codegen and the TypeScript renderer

## Documents

| | |
|---|---|
| [frontend.md](frontend.md) | The app as UI only, the exported deck and its player, fonts, and what talks to the network |
| [backend.md](backend.md) | What `api` owns, generation jobs, the browser in the backend, data, the API contract, auth at phase 29 |
| [ai-stack.md](ai-stack.md) | Model neutrality, the stages and their models, text mode, web search, prompt caching, evals, and why there is no agent framework |
| [pipeline-tools.md](pipeline-tools.md) | What the model may call (one read-only tool), what our code calls on its behalf, and the measured QA loop |
| [infrastructure.md](infrastructure.md) | Local-first development, the repo, CI, secrets, and what phase 29 decides |
| [decisions.md](decisions.md) | The full log: every choice, its rejected alternative, and what it changed elsewhere |

## Find it fast

| If you need… | Go to |
|---|---|
| Why the model may now write CSS | [decisions.md](decisions.md) → "2026-09-26 — v4" |
| Which model runs which stage | [ai-stack.md](ai-stack.md) → "Stages and models (v4)" |
| Why slide HTML is not returned as JSON | [ai-stack.md](ai-stack.md) → "Text mode for slide HTML" |
| How web search works and what it costs | [ai-stack.md](ai-stack.md) → "Web search" |
| Prompt caching, and why the prompt order matters | [ai-stack.md](ai-stack.md) → "Prompt caching" |
| How a build streams, survives a reload, and aborts | [backend.md](backend.md) → "The worker"; [../v4/engine.md](../v4/engine.md) → "Generation jobs and events" |
| Why models and Chromium run in a separate process | [backend.md](backend.md) → "The worker" |
| Who may write a deck, and what a 409 means | [backend.md](backend.md) → "Data" |
| Where decks are stored before accounts exist | [backend.md](backend.md) → "Data" |
| How web gets its types | [backend.md](backend.md) → "The API contract" |
| Auth, when it arrives | [backend.md](backend.md) → "Auth (phase 29)" |
| How the app shows a slide without running its markup | [frontend.md](frontend.md) → "The app: UI only" |
| What JavaScript ships in a deck | [frontend.md](frontend.md) → "The exported deck" |
| Why the exported deck makes zero network requests | [frontend.md](frontend.md) → "What talks to the network" |
| Font licensing, and why fonts are not subset | [frontend.md](frontend.md) → "Fonts" |
| What the model is allowed to call | [pipeline-tools.md](pipeline-tools.md) → "The one tool" |
| The render → measure → repair loop | [pipeline-tools.md](pipeline-tools.md) → "The QA loop" |
| Why there is no agent framework, and the CVE evidence | [ai-stack.md](ai-stack.md) → "Agent framework: none" |
| What only phase 29 decides (hosting, auth vendor, queue) | [infrastructure.md](infrastructure.md) → "What phase 29 decides" |
| Why a choice was made, or what it replaced | [decisions.md](decisions.md) → "The log", "What this supersedes" |
| What is still undecided | [decisions.md](decisions.md) → "Still open" |

## Build it in this order

The v4 order is the whole lesson of v1–v3: those releases built accounts, RLS, quotas, teams and publishing around decks that did not look designed. v4 puts infrastructure last, behind a human gate.

| Phase | Stack it needs |
|---|---|
| **21 reset** | uv + pnpm, the gate, the bench. Deletes `render/`, `worker/`, compose and the v3 tables |
| **22 engine spike** | The engine alone, from the CLI: OpenRouter, Playwright, `nh3`, `tinycss2`. **Nothing after it starts until the owner scores the wall ≥4/5** |
| **23 design system** | The font registry, palettes, the sampler. Pure code |
| **24 content engine** | `openrouter:web_search`, the `Fact` ledger |
| **25 composition + QA** | Image models, Pillow, the full measured loop |
| **26 player + export** | The player, the two export flavours, PDF |
| **27 app** | `web` arrives, and the backend splits into `api` and `worker`: Next.js, shadcn/Tailwind, `openapi-typescript`, SSE |
| **28 editor** | Nothing new |
| **29 accounts + deploy** | Postgres + SQLAlchemy + Alembic, the managed IdP + PyJWT, budget caps per user, the kill switch, the deploy target |

**The two things to get right early:**
- **The browser aborts every request from day one.** It renders model-written HTML in the process holding the model key.
- **`api/store/files.py` is the only module that writes a deck.** That makes phase 29's move to Postgres a change to one module rather than a hunt.

## What this changed

The 2026-09-26 reversals, each recorded with its reason in [decisions.md](decisions.md):

- **The model writes slide HTML and CSS within theme tokens.** "AI never writes styling" is retired, and a token rule plus a lint replace it
- **`web` is UI only.** The TypeScript renderer, the `render` service and the `Deck` codegen are gone, and the backend assembles every deck
- **Models and Chromium run in a worker process** (from phase 27). The internet-facing API holds no model key
- **A fixed 1920×1080 canvas, scaled to fit**, replaces fluid `100vh` pages
- **Facts come from web research with citations** and from what the user pastes
- **Founders and sales first**: pitch, sales, launch, investor update, partnership
- **Auth waits until phase 29 and moves to a managed provider.** FastAPI verifies JWTs, and a Python-owned `users` row keyed by the provider's `sub` keeps foreign keys real
- **Python stays by the owner's decision.** DSPy/GEPA, the reason the move cited, was never used

## Connects to

| | |
|---|---|
| [../v4/spec.md](../v4/spec.md) | The decisions this directory implements |
| [../v4/engine.md](../v4/engine.md) | The engine's layout, data model, events and model seam |
| [../coderules/README.md](../coderules/README.md) | The rules these choices imply |
| [../security/README.md](../security/README.md) | Every control assumes this topology, especially the three layers around AI-written HTML |
| [../security/third-parties.md](../security/third-parties.md) | Where data goes when OpenRouter, its providers and its search engines see a prompt |
