# Decisions

Every operational choice, what it beat, and what it cost. The rejected option matters as much as the chosen one — a decision without its alternative is just a preference.

## 2026-09-26 — v4

An audit of the v1–v3 build ([../findings.md](../findings.md) → "Measured 2026-09-26") found that every generated deck was a bold heading and one line of text on a flat background. The causes were architectural rather than cosmetic, so seven decisions were reversed on the same day, and a planning review then refined how they are built ([../v4/spec.md](../v4/spec.md)). Each row names what it cost, because a reversal without its cost gets reversed again.

| # | Decision | Chosen | Over | Because | Costs |
|---|---|---|---|---|---|
| 1 | **Who writes the styling** | **The model writes each slide's HTML fragment and scoped CSS.** Colour, `font-family`, `font-size` and `font-weight` may only reference theme tokens, and layout is free | "The AI never writes styling": the model filled a JSON form and one stylesheet rendered it | The form capped output at about five visual variables, and one 265-line stylesheet drew every deck. HTML's freedom is the product's reason to exist, and the token rule keeps a deck cohesive | Model output now carries markup, so the output channel is a security surface. It gets three layers: `nh3` and a `tinycss2` lint → Shadow DOM scoping → a script-less render under a CSP ([../security/content-and-web.md](../security/content-and-web.md)). Editability comes from `data-field` tags rather than from a schema |
| 2 | **Where the deck is assembled** | **The backend.** `web` is UI only: it shows backend HTML in a script-less iframe and presents the export file | A TypeScript renderer in `web`, a `render` service to run it headless, and Pydantic→Zod codegen of the `Deck` | With slides as HTML there is nothing left for a second renderer to do. The `render` service existed only because Python could not SSR React | The export's player is a static JS/CSS asset kept in `api/`, not a React component. Nothing is shared between `web` and the deck except bytes. From phase 27 the backend is two processes (row 8) |
| 3 | **Canvas** | **Fixed 1920×1080, scaled to fit, letterboxed in the slide's own ground colour** | Fluid `100vh` slides with a four-ratio preflight | QA must measure one deterministic size. A fluid frame multiplies every check by four and made v3's type silently wrong in `vw` | Presenters on 4:3 or 21:9 screens see bands. Tracked as a bet in [../v4/spec.md](../v4/spec.md) |
| 4 | **Where facts come from** | **`openrouter:web_search` with `url_citation` annotations, plus pasted material**, recorded in a `Fact` ledger with YOU / WEB / AI provenance | No source of facts, which gave one-bar charts and invented-looking numbers | The first users present to skeptics, and a deck that says nothing is the second failure after one that looks like nothing | Search queries built from customer content reach a search engine through OpenRouter, which is a new data flow ([../security/third-parties.md](../security/third-parties.md)). A search result is untrusted input ([../security/prompt-injection.md](../security/prompt-injection.md)) |
| 5 | **First users** | **Founders and sales**: pitch, sales, launch, investor update, partnership | Every deck type at once | Tome's post-mortem: "AI for everyone at once" was the flaw. It also picks the arcs, the interview and the 12 bench briefs | Lessons, keynotes and reports wait on a trigger |
| 6 | **Auth** | **None until phase 29. Then a managed IdP (WorkOS AuthKit or Clerk), whose JWT FastAPI verifies with PyJWT's `PyJWKClient`.** *Changed 2026-10-08 by the owner for the submission: Better Auth — chosen because it is open source and easy to use — self-hosted in the web app, email and password, its tables in their own `auth` database; FastAPI verifies its JWT through the JWKS exactly as above, and never reads its tables.* A Python-owned `users` row keyed by the provider's `sub` keeps foreign keys real. No table is shared across languages | Better Auth in Node, with `web` stripping the cookie and `api` reading `auth.session` | The split auth was two migration tools on one database, a third-party schema read across a language boundary, and a tenant wrapper that existed only to satisfy a lint | The managed provider is a subprocessor. Revocation becomes a short token lifetime rather than an instant session delete. `EventSource` cannot send a Bearer token, so web reads SSE with a fetch-stream reader from the start. The provider is chosen at phase 29 |
| 7 | **Python, re-examined** | **Python stays** for the backend (the owner's decision, 2026-09-26) | Collapsing to one TypeScript app | The owner prefers Python. **The driver the move cited, DSPy/GEPA, was never used** — zero references in `api/` on 2026-09-26 — so what remains is authoring fluency and the ecosystem | The split survives, but it is narrower: one API contract generated through OpenAPI instead of a generated `Deck` tree, and one tenant wrapper instead of two |

**Refined by the planning review.** These are the build-level decisions that followed from the seven above.

| # | Decision | Chosen | Over | Because | Costs |
|---|---|---|---|---|---|
| 8 | **Where models and Chromium run** | **A separate Python process, `api/worker.py`, from phase 27.** The API never calls a model or a browser and never holds the OpenRouter key. Before phase 27 the CLI calls the engine directly | In-process `asyncio` jobs inside the API | The internet-facing process should hold nothing worth stealing, and a browser rendering model-written HTML should not share a process with request handling. A build also survives an API restart | Two processes to start. Jobs need a hand-off: a job file claimed by atomic rename, a heartbeat, abort and resume |
| 9 | **How a build streams** | **The worker appends events to `events.jsonl`; the API's SSE tails it and honours `Last-Event-ID`** | An in-memory event bus | Reconnects are gapless, and the log replays without a model call. It is also the only channel two processes need | Event models are not route responses, so they are registered in OpenAPI explicitly or web gets no types for them |
| 10 | **Who writes a deck** | **`api/store/files.py` is the only data module**: atomic writes, a per-deck lock, a version check. **API edits get 409 while a build runs** | Each feature owning its own data module over the files | Two processes write the same deck. A single-writer rule is the cheapest thing that makes that safe | The editor must handle 409 as a normal state |
| 11 | **Per-slide CSS scoping** | **Declarative Shadow DOM** (`<template shadowrootmode>`, Baseline 2024). `tinycss2` only lints | Rewriting every selector under `[data-slide]` | The browser does the scoping, so a rewriting bug cannot leak one slide's CSS into another or into the player | The exported file requires a 2024-or-later browser. Fonts and theme tokens are inherited through the shadow boundary; a rule that must reach inside needs `:host` |
| 12 | **What a slide may contain** | **No `<a>` elements; URLs are plain text. No icons. Charts, images and textures are empty `dd-chart`, `dd-image` and `dd-texture` elements our code fills. Model CSS may not animate** (no `animation`, `transition` or at-rules); the player owns motion | An `https:`-only link allowlist; a vendored icon set; texture via `url()` tokens; per-slide `@keyframes` | Removing links removes the `javascript:` class rather than filtering it. Icon rows are the "AI HTML look". No `url()` and no at-rules leaves the CSS lint with almost nothing to get wrong | A URL on a slide is not clickable. Motion variety comes from the theme's motion character alone |
| 13 | **Export flavours** | **"present"** carries speaker notes as an inert `application/json` block for the presenter popup. **"send"** carries none. The PDF uses send | One export file | Notes are written for the presenter, and an emailed deck would leak them | Two assemblies to test for zero requests |
| 14 | **Fonts in the export** | **Vendored Latin-subset woff2 embedded as-is. `fontTools` is deferred** | Subsetting per deck | Subsetting is modification under the OFL, and a modified font may not keep a Reserved Font Name. Embedding unmodified files avoids the question | Larger files. **Trigger:** a non-Latin locale, or fonts over 1 MB of an export |
| 15 | **The theme and the looks** | **Pure code.** The sampler picks axes, code computes tokens and the deck's one generated look | The model writing `theme.css` and a design brief | Deterministic, free, instant, and testable before anything renders | The prose "design brief" for the compose model is assembled from axis descriptions rather than written fresh |
| 16 | **Spend control** | **A per-deck `budget_usd` hard cap that fails closed**, and pinned model ids | A kill switch and quotas at phase 29 only | A repair loop or a retry storm is a denial-of-wallet from our own code, and it exists from phase 22. A pinned id means a provider-side alias change cannot move cost or quality silently | A build can stop short of its slide count, and says so |
| 17 | **AI disclosure on images** | **IPTC XMP `digitalSourceType=trainedAlgorithmicMedia`** in every generated image, alongside the export's marker | The export marker alone | The image is what gets copied out of a deck. EU AI Act Art. 50 has been in force since 2026-08-02 | Pillow must write XMP into webp, verified at phase 25 |

**What stayed** through the re-decide, and why each still holds:
- **The offline single-file artefact** with `connect-src 'none'`. It is the product.
- **OpenRouter behind one seam.** Model choice is a config change, and the bake-off is the apparatus.
- **No agent framework.** The pipeline is still a fixed sequence our code decides.
- **No gradients, neon, blur or glow in the output** ([../design/principles.md](../design/principles.md) §5 governs the artefact).

## The log

Rows marked **Superseded 2026-09-26** name what replaced them. The v3 reasoning stays in the row, because it is how a later reader finds out why a wrong turn looked right.

| Decision | Chosen | Over | Because |
|---|---|---|---|
| **Artefact (2026-08-13)** | **A downloadable single-file `.html` deck that runs offline** — `connect-src 'none'`, fonts embedded | A served/published page (the old artefact) | The product re-decided from the vision up: the file is the artefact. **Still holds in v4**, and v4 makes the "fonts embedded" half true |
| **Slide authoring (2026-09-26)** | **The model writes HTML + scoped CSS within theme tokens** | A JSON form rendered by one stylesheet | See v4 row 1 |
| **Design system (2026-08-13, revised 2026-09-26)** | **A seeded generator makes one look per deck (revised 2026-10-05: no three-look choice), and code computes the theme. No model call** | Three fixed art directions (08-13); a 31-row lookup table picked by `sum(ord(title)) % 31` (v3) | Diversity is architecture, not prompting ([../findings.md](../findings.md) → Model behaviour). v3's "registry" was 13 palettes and font names that never loaded |
| **Canvas (2026-09-26)** | **Fixed 1920×1080, scaled** | Fluid slides | See v4 row 3 |
| **QA (2026-09-26)** | **Render in Playwright → measure DOM + pixels → targeted repair (≤2) → fallback → visible flag** | A vision-model critic, one revision (v2) | AeSlides (arXiv 2604.22840) beat VLM reflection with measurable metrics, and found reflection counterproductive. v3's critic ran only in the CLI, on hand-supplied screenshots |
| **Facts (2026-09-26)** | **`openrouter:web_search` + pasted material → `Fact` ledger** | No facts | See v4 row 4 |
| App hosting | ~~Vercel — `web` only~~ **Superseded 2026-09-26:** decided at phase 29 | Fly, self-hosted, Cloudflare | The product has no users to host for until phase 29, and the `api` image now carries Chromium, which constrains the choice |
| Backend language | **Python** | TypeScript everywhere | Re-examined 2026-09-26 (v4 row 7). It stays by the owner's decision. The DSPy/GEPA driver was never used |
| Backend framework | **FastAPI** | Django + Ninja, Litestar | Pydantic-native, so the models and the API contract are the same objects, and OpenAPI is what `web`'s types are generated from |
| Workers | ~~AWS ECS Fargate~~ **Superseded 2026-09-26:** one worker process, `api/worker.py`, from the same codebase (v4 row 8) | Fly, Railway, Lambda, App Runner | The `render` and `fetch` workers had no job left in v4; the new worker exists to keep the model key and Chromium out of the API. Hosting is a phase-29 decision |
| Runtime count | ~~Five, split on trust and language~~ **Superseded 2026-09-26: three processes** — `web`, `api`, `worker` — from two packages | One combined worker; three runtimes | Each concern has one owner, and the one trust split left is API versus worker. Hostile-byte parsing, the reason for v3's quarantined worker, does not exist in v4 until uploads return |
| Repos | ~~One per runtime~~ **Superseded: one repo, two packages** (`api/`, `web/`) | Two repos; one per runtime | The repository was always one; the per-runtime split was planned and never happened. With OpenAPI codegen there is no package to publish |
| Schema source of truth | **Pydantic** | Zod; a hand-written JSON Schema | The model call happens in Python. In v4 the TypeScript side is generated from **OpenAPI**, not from a `Deck` tree |
| Schema sharing | ~~Generated TS + Zod, private npm package~~ **Superseded 2026-09-26: `openapi-typescript` from FastAPI's OpenAPI, generated in-repo**, with a no-diff gate | Submodule, copy + contract test, TS types only | Slides cross as HTML strings, so `web` validates API payloads rather than a design tree. SSE event models are registered in OpenAPI explicitly |
| Database | **Postgres**, from phase 29 | Supabase, Neon | Unchanged in kind. Before phase 29 decks live in a file store behind one data module |
| ORM | ~~SQLAlchemy + Alembic (`api`) · Drizzle (`web`, auth tables only)~~ **Superseded 2026-09-26: SQLAlchemy + Alembic only**, owned by Python | One ORM; Django ORM; raw SQL | With no auth tables in our database there is no second ORM. Removes v3's most destructive failure mode, Alembic proposing to drop tables it did not own |
| Auth | ~~Better Auth, kept in Node~~ **Superseded 2026-09-26: a managed provider at phase 29**, JWT verified in FastAPI | fastapi-users, Authlib, Better Auth | See v4 row 6. The v3 objection, that hosted IdPs break the FK behind RLS, is answered by keying our tables on the provider's stable subject id |
| Session across languages | ~~`api` reads the `session` table read-only~~ **Superseded: FastAPI verifies a signed JWT against the provider's JWKS**, failing closed | A short-lived JWT minted by `web`; proxy everything through `web` | No third-party table shape in our code. Costs a revocation window equal to the token lifetime |
| Isolation | **RLS on `current_setting('app.user_id')`** — **decided again at phase 29 start** | App-layer only; schema per tenant | **Deferred.** Trigger: a second database client. Until then one Python data module filters by owner, and if RLS arrives there is exactly **one** wrapper, in Python ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)). v3 needed three migrations just to fix recursion in team policies |
| Jobs | ~~PGQueuer~~ **Superseded 2026-09-26: job files claimed by atomic rename**, with a heartbeat, abort and resume, state saved after every slide. On Postgres (phase 29) the claim becomes `SKIP LOCKED` | Procrastinate, Celery, pg-boss | One worker needs no queue product. The protocol is in [../v4/engine.md](../v4/engine.md) → "Generation jobs and events" |
| Rate limits / quotas | **A per-deck `budget_usd` hard cap from phase 22**, failing closed. Per-user caps, atomic counters and the kill switch at phase 29 | Upstash Redis, platform limits | The check must be transactional to close the A10 race. The OpenRouter key's own spend limit is the outer ceiling |
| Model access | **OpenRouter behind a seam** | Anthropic direct, Bedrock, Claude Platform on AWS | Model flexibility, and the bake-off is cheap. **Costs a guarantee**, see below |
| Image generation | **OpenRouter image models, called by our code** (not a model tool) → Pillow → webp data URI | One fixed image vendor; stock-photo APIs | Images are first-class content. v3 embedded one uncompressed 1024² PNG at 2.57 MB of a 2.59 MB file |
| Publish target | ~~Static artifacts to S3~~ **Superseded: no hosted URL in v4.** Trigger: "send a link" requests outnumber "send the file" | Vercel routes with `use cache` | The file is the artefact. v3's publish burned quota on every typo fix |
| CDN | ~~CloudFront~~ **Superseded:** returns only with hosting | Vercel edge, Cloudflare | Nothing to serve |
| Storage | ~~S3 + CloudFront~~ **Superseded: a file store, `api/store/files.py`, single writer**, then Postgres + object storage at phase 29 | Supabase Storage, R2 | Nothing is uploaded in v4, and generated assets live with the deck |
| ~~Personalized pages~~ | **Superseded 2026-08-13** — the offline single-file artefact has no per-recipient variation | | The personalization feature died with the served-page product |
| Page runtime | ~~React renderer + a tiny inlined present/motion runtime~~ **Superseded 2026-09-26: model-written HTML in Declarative Shadow DOM + our static player** (keys, touch, fullscreen, overview, presenter view, all motion) | Vanilla reveal runtime, CSS-only, islands | Motion is still implemented once. The editor shows the same HTML, and present mode shows the file |
| Editor state | **Zustand, if the editor needs a store** (decided in phase 28) | useReducer, Jotai, Immer | The server holds `DeckVersion`s, so undo is a server operation and the client store is thinner than v3's |
| App chrome UI | **shadcn/ui + Tailwind 4** | Radix bare, hand-built, Mantine | Own the code, with Radix's accessibility. v3 imported Tailwind and used none of it, and hand-wrote 578 lines of CSS instead |
| Streaming | ~~SSE over a Route Handler~~ **Superseded 2026-09-26: SSE from FastAPI tailing `events.jsonl`**, read in web by a fetch-stream reader | AI SDK, polling, WebSocket | The job lives in the worker. The unit is still a whole checked slide, not a token |
| Fonts | ~~Fontsource, open licence~~ **Revised 2026-09-26: ~40 OFL families vendored as woff2**, licence verified per family, **embedded as-is** (v4 row 14) | Commercial, Adobe Fonts; system stacks (what v3 actually shipped) | Redistribution to customers' audiences makes licensing a product constraint. Latin-subset files are small enough to embed unmodified |
| Screenshots | ~~Playwright in the fetch worker~~ **Superseded: a Playwright pool in `api/worker.py`**, every request aborted | Browserless, ScreenshotOne | It renders our sanitized, model-written HTML, not attacker-chosen pages. Screenshots of arbitrary URLs are not a v4 feature |
| Document parsing | ~~`pdf.js` / `unpdf` in the fetch worker~~ **Superseded: not built.** Trigger: users ask for URL/PDF import | Claude native PDF reading | It needs an SSRF-safe fetcher and an isolated parser, and neither exists in v4 |
| Email | ~~Resend~~ **Superseded: none until there is product email**; the managed auth provider sends auth email | Postmark, SES | Nothing in v4 sends email |
| Observability | **Sentry, if adopted at phase 29**, with server-side scrubbing configured before the first event | Axiom, Better Stack, none | Unchanged reasoning. Adopting it is a subprocessor decision |
| Secrets | **Local `.env` until phase 29**; the store is chosen with the deploy target | Doppler, env vars, Parameter Store | One secret exists in v4, the OpenRouter key, and from phase 27 only the worker's environment has it |
| IaC | ~~Terraform / OpenTofu~~ **Deferred to phase 29** | CDK, SST, console | Only if the deploy target has infrastructure worth reviewing as a diff |
| CI/CD | **GitHub Actions** mirroring the pre-commit gate. OIDC to a cloud only at phase 29 | CDK Pipelines, manual | v3's workflow never ran on GitHub. v4's first job is to run it |
| Local dev | ~~Docker Compose + MinIO + LocalStack~~ **Superseded 2026-09-26: two dev servers** (`uv run uvicorn`, `pnpm dev`) and a `.env` | Real AWS dev, Supabase CLI | No service in v4 needs a container before phase 29 |
| Tests | **pytest** (`api`, with Playwright for the artefact and QA assertions) · **Vitest + Playwright E2E** (`web`) | One runner; node:test; Cypress | Two languages means two runners. The browser assertions are the ones that matter |
| Migrations | ~~Alembic (`api`) · drizzle-kit (`web` auth tables)~~ **Superseded: Alembic only, from phase 29**, starting from a fresh baseline | Branch-per-preview; one tool for both | One ORM, one tool, one owner |
| Python packaging | **uv** | pip + venv, Poetry, PDM | Unchanged |
| Model vendor | **None — the phase-22 bake-off picks per stage**, and it is re-run when a model family changes | Standardising on one provider | Any model named today is wrong in two quarters |
| Evals | ~~Promptfoo (CI) + self-hosted Langfuse~~ **Superseded 2026-09-26: the v4 bench** ([../v4/bench.md](../v4/bench.md)) — 12 briefs, a wall scored by the owner, content evals, cost and latency per deck | Braintrust, LangSmith, hosted anything | Neither tool was ever wired up: v3's CI ran `pytest -q` only, and its "variety gate" scored a stub model. Promptfoo and Langfuse return only if the bench outgrows plain Python |
| Agent framework | **None** | LangGraph, CrewAI, Pydantic AI, Agents SDK, Microsoft Agent Framework, Mastra | The v4 pipeline is still a fixed sequence with two human gates, outline and look. Web search is a read-only server tool, not agency ([ai-stack.md](ai-stack.md)) |
| Pipeline language | **Python** | TypeScript | Follows the backend |
| Prompt optimization | **DSPy/GEPA, offline only**, if it is ever used | Hand-tuning forever; DSPy at runtime | Unused as of 2026-09-26. The trigger in [ai-stack.md](ai-stack.md) is unchanged |
| Model client | **Plain async `httpx`, OpenAI-compatible**, with JSON mode and text mode | Instructor, the OpenAI SDK, an agent framework | v3's client was synchronous, which ruled out parallel slides |
| Publish render | ~~A thin `render` service (Node)~~ **Superseded 2026-09-26: the backend assembles the export** | Python + Playwright against the editor route; Next.js keeps it | There is no React renderer left to host |
| Pipeline tools | **One read-only server tool, `openrouter:web_search`**. Images, charts, rendering and export are our code's calls | No tools; tools with side effects | The tier rule is unchanged: nothing with side effects ([pipeline-tools.md](pipeline-tools.md)) |
| Visual verification | ~~Render → screenshot → vision critic, one revision~~ **Superseded 2026-09-26:** see QA above | Schema validation alone; unbounded critic loop | The repair loop is still a `for` with a literal limit, and bounded is not autonomy |
| ~~Publish render location: job worker~~ | Superseded — see "Publish render" above | | The premise died with the Python move, and the render service then died with v4 |
| Infrastructure timing | **None before phase 29** | Full stack from day one | v1–v3 stood up accounts, RLS, quotas, teams and publishing before a deck looked designed. A perfect VPC does not move that risk |
| Our own brand | **Light editorial "gallery wall"** | Wearing `cinematic-dark`; a dark atmospheric site | Unchanged ([../design/brand.md](../design/brand.md)) |
| Marketing hero | **A real exported deck + a recorded generation** | Live anonymous generation; a video; a canned prompt box | Unchanged. The SSE log of a real build replays without a model call |
| Marketing analytics | **Self-hosted, cookieless, marketing site only** | Plausible Cloud, GA4, Fathom | Unchanged. The exported deck makes zero requests, so no analytics ever runs in it |
| Chrome typography | **Commercially licensed, never a face from the output registry** | Reusing the output's open faces; Inter/Geist | Unchanged ([../design/brand.md](../design/brand.md)) |

## The decisions that cost something

Everything else is a preference with a defensible rationale. These trade away a stated guarantee, and they should be revisited deliberately rather than forgotten.

### 1. The model writes markup (2026-09-26)

**What it buys:** the design freedom the product was meant to have. v3's decks used less of HTML and CSS than a PowerPoint theme does.

**What it costs:**

| | |
|---|---|
| **A structural control becomes three layered ones** | "The schema has no field for a hex code" was a type-level guarantee. Model markup is held instead by an allowlist sanitizer with no link element, a CSS lint with no `url()` and no at-rules, Shadow DOM scoping, and a browser that runs no slide script and makes no request. Each layer alone stops script execution and exfiltration; none is trusted alone ([../security/content-and-web.md](../security/content-and-web.md)) |
| **Consistency moves from the renderer to the token rule** | A slide can compose freely, and its colour and type still come from the theme. The lint is the enforcement, and a slide that fails it never reaches a user |
| **Editing moves from a schema to tags** | Inline edits find content through `data-field` attributes, and a completeness check catches dropped or invented text ([../v4/design-engine.md](../v4/design-engine.md)) |

**Revisit when:** the sanitizer or lint lets a script or a network request through in a corpus test once. That is evidence a layer is missing, not a pattern to add.

### 2. OpenRouter weakens schema enforcement

[../security/prompt-injection.md](../security/prompt-injection.md) used to claim *"a fully compromised model can only emit valid Deck JSON."* Under OpenRouter the decoder never enforced that — `strict: true` support varies by provider, and some treat a schema as a strong hint.

**What survives:** the parse was always the real gate. For the JSON stages (interview, research, storyline, theme brief) nothing changes: output that fails the Pydantic parse is repaired once per call and then fails visibly. **For slide HTML there is no schema to enforce**, and the gate is the three layers above, so the decoder question does not arise. The claim restates as: *"a fully compromised model can only emit HTML that is sanitized, linted, rendered without scripts and exported under `default-src 'none'`"*.

**The residual:** repair cycles burn tokens. Before phase 29 the ceiling is the OpenRouter key's spend limit, and from phase 29 it is the per-user budget cap and the kill switch.

**Revisit when:** a stage's repair rate is materially worse on a route than on a direct provider call. The cost ledger records repairs per call from the first generation.

### 3. `connect-src 'none'` is back, because the artefact is a file

The old product's client-side personalization and analytics beacon ended `connect-src 'none'` — it was weakened to two exact endpoints. The 2026-08-13 re-decide removed both features and made the offline single-file deck the artefact, so `connect-src 'none'` is back and it is the product.

**What survives, v4:** the exported deck is a single self-contained `.html` file that talks to *nothing*. Fonts are subset and embedded, images are webp data URIs, and the player is the only script, allowed by hash. A browser test asserts zero requests from `file://`.

**The residual:** there is no per-recipient personalization and no analytics beacon. If a hosted URL ever arrives, it must be a decision about this guarantee, not a drift past it.

### 4. The Python backend, re-examined (2026-09-26)

The largest reversal before v4. An earlier lock read *"Everything stays TypeScript"*. It was reversed for direct access to the Python AI/ML ecosystem (DSPy/GEPA above all), authoring fluency, and a backend that is not a frontend framework's server half.

**What 2026-09-26 found:** DSPy and GEPA were never imported. The move's headline driver was never exercised, and its costs were paid in full:
- a Pydantic→Zod codegen of the whole `Deck`
- five runtimes, one of them a language bridge
- two ORMs and two migration tools on one database
- two tenant wrappers
- `api` reading Better Auth's session table

**The decision:** Python stays, by the owner's call. What v4 changes is the shape of the split. The costs above were all consequences of TypeScript *rendering* what Python *decided*. With slides as HTML the backend assembles, the boundary shrinks:

| v3 cost | v4 |
|---|---|
| `Deck` codegen (Pydantic → JSON Schema → TS + Zod, a published package) | OpenAPI → `openapi-typescript`, in-repo, for API payloads only |
| Five runtimes | Three processes from two packages |
| Two ORMs and two migration tools | One of each (phase 29) |
| Two tenant wrappers | None until RLS has a trigger, then one |
| `api` depends on a third-party session table | FastAPI verifies a JWT against JWKS; `users` is our own table |

**What remains procedural:** no agent framework, enforced by a rule and a CI grep rather than by the friction of a second language ([ai-stack.md](ai-stack.md) → "The guardrail that disappeared").

**Revisit when:** the OpenAPI codegen is bypassed once, or when the frontend needs to render something itself.

## What this supersedes

Earlier documents locked decisions this directory reverses. Recorded here rather than silently contradicted.

The `docs/v1`–`docs/v3` paths in the last column are where a decision *was* recorded. Those directories are deleted in v4 and live in git history (commit `8169fd9`); the live source is [../v4/spec.md](../v4/spec.md).

| Was | Now | Where it was |
|---|---|---|
| **"The AI never writes styling"** — the schema has no field for a presentational value (non-negotiable #7) | **The model writes HTML + scoped CSS; colour and type only through theme tokens** (2026-09-26) | [../coderules/README.md](../coderules/README.md), `docs/v1/spec.md` |
| A TypeScript renderer shared by editor, export and a `render` service | **The backend assembles HTML; `web` shows it in a script-less iframe** (2026-09-26) | [frontend.md](frontend.md), [backend.md](backend.md) |
| Fluid slides, guaranteed at 4:3–21:9 by preflight | **Fixed 1920×1080, scaled** (2026-09-26) | `docs/v2/spec.md` |
| Five runtimes, split on trust and language | **Three processes: `web`, `api`, `worker`** (2026-09-26) | [backend.md](backend.md) |
| Better Auth in Node, `api` reads `auth.session` | **Managed auth at phase 29; FastAPI verifies JWTs** (2026-09-26) | [backend.md](backend.md), [../security/tenancy-and-data.md](../security/tenancy-and-data.md) |
| Two tenant wrappers, one per language | **None; RLS deferred, and one Python wrapper if it arrives** (2026-09-26) | [../coderules/patterns.md](../coderules/patterns.md) |
| A vision critic, one revision | **Measured QA in Playwright, targeted repair ≤2** (2026-09-26) | [pipeline-tools.md](pipeline-tools.md) |
| Promptfoo + Langfuse evals | **The v4 bench, with a human-scored wall** (2026-09-26) | [ai-stack.md](ai-stack.md) |
| Postgres in Docker → **Supabase** | Docker → RDS/Aurora (v3) → **decided at phase 29** (v4) | `docs/v1/spec.md` |
| **Supabase Auth**, RLS via `auth.uid()` | Better Auth (v3) → **managed provider** (v4) | [../security/tenancy-and-data.md](../security/tenancy-and-data.md) |
| `storage.ts`: local disk → Supabase Storage → S3 | **`api/store/files.py`** (v4) | `docs/v1/spec.md` |
| `anon` role has zero grants | **No anonymous role exists.** Nothing but the server connects — unchanged | [../security/tenancy-and-data.md](../security/tenancy-and-data.md) |
| One isolated worker → two workers | **None in v4.** Isolation returns with uploads or URL import | [../security/infrastructure.md](../security/infrastructure.md) |
| Published pages served from an origin | **A downloadable single-file HTML deck** (2026-08-13) | [../security/content-and-web.md](../security/content-and-web.md) |
| `connect-src 'none'` → two endpoints | **`connect-src 'none'` is back** — the offline file talks to nothing | [../security/content-and-web.md](../security/content-and-web.md) |
| Three fixed art directions | A 31-family registry (v2/v3) → **a seeded sampler over discrete axes** (v4) | `docs/v1/spec.md` |
| Anthropic API called directly | **OpenRouter** behind a seam, no preferred vendor | `docs/v1/spec.md` |
| Shape violations are **unrepresentable** | The Pydantic parse is the gate for JSON stages; **three layers for slide HTML** (v4) | `docs/v1/plan/01-schema.md` |
| Prompt caching is one mechanism with one discount | Activation, discount and minimum prefix all **vary by route** (dated in [ai-stack.md](ai-stack.md)) | `docs/v1/spec.md` |
| Generation has **no tools** | No tools **with side effects**. v4 has exactly one read-only tool, `openrouter:web_search` | [../security/prompt-injection.md](../security/prompt-injection.md) |
| ~$0.20 per experience | **Cost per deck measured, not assumed**: estimated $1.5–3.5 per 10-slide deck quality-first, measured in phase 22 | `docs/v1/spec.md`, [../v4/spec.md](../v4/spec.md) |
| **TypeScript everywhere** | **Python** backend, **TypeScript UI** — re-examined and kept 2026-09-26 | [ai-stack.md](ai-stack.md) |
| **Zod is the source of truth** for the `Scene` shape | **Pydantic** is; TS types come from OpenAPI (v4) | [../coderules/typescript.md](../coderules/typescript.md) |
| Drizzle is the ORM | **SQLAlchemy + Alembic only** (v4) | [backend.md](backend.md) |
| pg-boss → PGQueuer for jobs | **Job files claimed by the worker** (v4) | [backend.md](backend.md) |
| Plain `fetch` for the model seam | Plain **async `httpx`** | [ai-stack.md](ai-stack.md) |
| The AI SDK's `generateObject` is the escape hatch | **Retired** — the pipeline is Python | [ai-stack.md](ai-stack.md) |
| DSPy *"has no real TypeScript equivalent"* | Moot — DSPy is native to the backend, and **unused** | [ai-stack.md](ai-stack.md) |
| Two repos → one repo per runtime | **One repo, two packages** | [../coderules/structure.md](../coderules/structure.md) |
| Rule 8: *"Drizzle lives in feature data modules"* | **The ORM of that runtime** → now only Python's, plus the file store until phase 29 | [../coderules/README.md](../coderules/README.md) |

The security-relevant rows have been patched at the source. The rest stand as the record of what was believed at the time.

## Still open

Deliberately unresolved, with the condition that would resolve each:

| | Resolve when |
|---|---|
| **Per-stage model selection** | The phase-22 bake-off: wall score first, then $, then seconds. It is re-run whenever a model family changes |
| **The image model** | The phase-25 image bake-off, on the bench briefs |
| **Hosting and deploy target** | Phase 29 start. The constraint: `api` carries Chromium and runs long builds, so it needs a host with long-running processes |
| **The managed auth provider** | **Resolved 2026-10-08:** Better Auth (self-hosted, email and password) for the submission. A managed provider returns to the table when OAuth, MFA or email flows are needed |
| **RLS** | Deferred. Trigger: a second database client ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)) |
| **A queue product** | When file claims, then `SKIP LOCKED`, stop being enough |
| **`fontTools` subsetting** | A non-Latin locale, or fonts over 1 MB of an export |
| **Buying commercial type** | Once the phase-23 wall shows where open faces fall short. Still the highest-leverage money in the product |
| **Pricing and plan limits** | After phase 28, with measured cost per deck in hand |
| **The product's name** | Before phase 27. `d-design` describes the repository, and the app is where user-facing strings start accumulating ([../design/brand.md](../design/brand.md)) |
| **The chrome accent hue** | With the first real screen in phase 27. One accent, roughly two uses, never violet or a gradient |
