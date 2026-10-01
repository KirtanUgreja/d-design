# v4 — the engine

> How a brief becomes an offline deck: the pipeline, where every module lives, the data model, what streams to the browser, the model seam, and how model-written HTML is made safe. [spec.md](spec.md) owns the decisions and their reasons; this file is the shape they take. Content rules live in [content.md](content.md), and the design system, slide contract, lint and QA live in [design-engine.md](design-engine.md).

---

## The pipeline

```
Brief ─► interview: one call, ≤5 questions with suggested answers, skippable ─► content/interview.py
      ─► research: openrouter:web_search → Fact ledger ─────────────────────► content/research.py
      ─► storyline: arc by deck type, assertion headlines, provenance ──────► content/storyline.py
         ⏸ the user edits and approves the outline
      ─► looks: sampler → 3 themes (pure code) → style tiles rendered
         from exemplars with the deck's real title. No model call ──────────► design/*
         ⏸ the user picks a look, or shuffles (instant)
      ─► planner: an intent and an archetype per slide, rhythm rules ───────► compose/planner.py
      ─► in parallel: speaker notes (one call) and, per slide, 5 at a time:
           compose (model → html + css) → sanitize → lint
           → fill components (dd-chart · dd-image · dd-texture)
           → render at 1920×1080 in Chromium → measure
           → targeted repair (≤2) → exemplar-fill fallback → flag ──────────► compose/*, components/*, qa/*
      ─► deck check: structural variety across slides ──────────────────────► qa/fingerprint.py
      ─► editor: inline edits · AI edits · recolour / restyle · versions
      ─► assemble: player + one shadow root per slide + fonts + webp images
         + CSP + AI markers → deck.html in "present" or "send" flavour;
         deck.pdf through a Playwright print of "send" ────────────────────► export/*
```

**Stages, and who does the work.** Model roles are "writing", "design" and "image". Concrete, **pinned** model ids come from the phase-22 bake-off and are recorded in [../techstack/ai-stack.md](../techstack/ai-stack.md). Default is quality first.

| Stage | Call shape | Model role | Calls per 10-slide deck |
|---|---|---|---|
| Interview | JSON: ≤5 questions, 3 suggested answers each | writing (a cheap model is fine) | 1 |
| Research | Text with the `openrouter:web_search` tool, then JSON `Fact[]` | writing | 1–2 (≤30 results) |
| Storyline | JSON `Storyline` | writing | 1 (+1 repair) |
| Looks | **Code only** | — | 0 |
| Notes | JSON, after approval, in parallel with compose | writing | 1 |
| Compose | **Text**: fenced `html` and `css` blocks | design | 10 (slide 1 warms the cache, then fan out) |
| Repair | Text, same shape, carrying the measured defect list | design (a cheaper model if phase 22 shows parity) | ≈0.2–0.3 per slide |
| Images | An image model, 0–4 per deck, plus a cheap "does this image contain text?" check with one regeneration | image | 0–4 |
| Revise (editor) | Text, same shape as compose | design | per request |

---

## Layout

Two runtimes in one repo. **Python owns the engine, the data and the export; TypeScript owns the UI.** They meet at one HTTP API described by OpenAPI.

```
api/                                  Python 3.13 · uv · ruff · mypy --strict · pytest
  app.py                              FastAPI; mounts feature routers. Never calls a model or a browser
  worker.py                           (phase 27) claims jobs, runs the engine, owns Chromium and the key
  settings.py                         the only module that reads the environment (key, pinned models, budgets)
  cli.py                              outline | theme | build | qa | export | bench | wall — drives the engine directly
  engine/                             PURE: imports no FastAPI and reads no env; behaviour is injected
    __init__.py                       the public API — every caller goes through here
    models.py                         the Pydantic models below
    pipeline.py                       the orchestrator: plain async functions + an event callback + the budget cap
    llm/openrouter.py · images.py     the model seam (below)
    content/                          interview · research · storyline · notes · rules · arcs · prompts/*.md
    design/                           axes · sampler · theme · color (OKLCH, WCAG 2 + APCA) · brand · texture · tiles
    compose/                          planner · author · repair · fallback · revise · document (one shadow root per slide)
    components/                       charts (spec → SVG) · images (prompt, treatment, webp, XMP) · texture
    qa/                               browser (Playwright, all network aborted) · measure.js · metrics
                                      contrast · fingerprint · lint (tinycss2) · sanitize (nh3)
    export/                           assemble · pdf · player/player.js · player/player.css  (static; ours)
  store/files.py                      THE data module: data/decks/<id>/{deck.json, events.jsonl, ledger.jsonl, slides/, assets/}
  features/
    decks/routes.py                   thin: read, edit (409 while a job runs), downloads
    generation/routes.py              thin: enqueue, abort, SSE that tails events.jsonl
  library/
    fonts/<family>/                   *.woff2 (Latin subset) · OFL.txt · meta.json (metrics, weights, class)
    exemplars/<id>.{html,json}        the taste asset (design-engine.md → Exemplars)
  tests/

bench/                                briefs/*.json (with frozen outlines) · rubric.md · baselines/ · injection/ · runs/ (ignored)

web/                                  Next.js · React 19 · Tailwind 4 · shadcn/ui · UI ONLY — no DB, no renderer
  app/
    layout.tsx · globals.css          our brand tokens (../design/brand.md)
    page.tsx                          home: the composer + recent decks
    new/[id]/page.tsx                 interview + outline gate
    new/[id]/look/page.tsx            pick a look
    deck/[id]/page.tsx                generation watch → editor (one screen)
    deck/[id]/present/page.tsx        present: the "present" export, full screen
  features/                           composer · interview · outline · looks · watch · editor · present · export
                                      (each with an index.ts public surface)
  components/ui/                      shadcn primitives, restyled to our brand at install
  lib/api/                            schema.d.ts (GENERATED from OpenAPI) · client.ts · events.ts (fetch-stream SSE)
  next.config.ts                      rewrites /api/* → FastAPI
```

**Rules that follow from the layout:**
- **Callers reach the engine only through `engine/__init__.py`**, and features reach each other only through their public surface.
- **`store/files.py` is the only module that reads or writes deck data.** Writes are atomic (write, then rename) under a per-deck lock with a version check. While a job runs, the worker is the only writer and API edits get a 409. Phase 29 re-implements this one interface on Postgres and object storage.
- **Prompts are versioned files**, `prompts/<stage>.v<N>.md`. Every ledger entry records the prompt version, so a bench result can be tied to the prompt that produced it.
- **The CLI, the worker and the bench call the same engine functions.** There is no second path to a deck.
- **The web app never builds slide HTML.** It shows documents the backend assembled: slide documents in iframes, the export in present mode, and QA screenshots as thumbnails.

---

## Data model

Pydantic, in `api/engine/models.py`. These are field lists, not code. The TypeScript view is generated from OpenAPI into `web/lib/api/schema.d.ts`, and the gate fails if it has a diff.

| Model | Fields |
|---|---|
| `Brief` | `id` · `prompt` · `pasted[{title, text}]` · `deck_type` (pitch · sales · launch · investor_update · partnership · auto) · `answers[{qid, question, text}]` · `audience` · `ask` · `minutes` · `slide_count` (3–25) · `delivery` (live · send) · `tone` · `research: bool` · `brand?{name, colors ≤3}` · `locale` |
| `Fact` | `id` · `text` · `value?` · `unit?` · `source` (user · cited · illustrative) · `citation?{url, title, publisher, date, snippet}` · `status` (proposed · approved · rejected) |
| `SlidePlan` | `id` · `beat` (its place in the arc) · `intent` · `archetype` · `exemplar_ids[]` · `fields[{name, text, budget_words, fact_ids}]` (the headline is a field) · `chart?{type, title, unit, series[{name, points[{label, value}]}], highlight?, fact_ids ≥1}` · `image?{prompt, why, aspect, role}` · `notes` · `provenance{field → YOU/AI/WEB}` |
| `Storyline` | `governing_thought` · `deck_type` · `audience` · `ask` · `key_points[3–5]` · `slides: SlidePlan[]` |
| `Theme` | `id` · `seed` · `axes{pairing, palette_strategy, grid, motif, image_treatment, density, scale, edge, motion}` · `colors{role → oklch + hex}` · `fonts{display, text, label?}` · `scale{step → px}` · `grid{cols, margin, gutter}` · `radius` · `shadow_hard` · `contrast[{fg, bg, wcag, apca}]` |
| `Slide` | `id` · `plan_id` · `version` · `html` (sanitized) · `css` (linted) · `fields{name → text}` · `assets{ref → asset_id}` · `origin` (authored · repaired · fallback · edited) · `attempts` · `qa{status, errors[Defect], warnings[Defect], metrics, fingerprint, screenshot}` · `cost_usd` |
| `Defect` | `code` (E1–E10, W1–W6) · `field?` · `selector` · `measured` · `threshold` |
| `Deck` | `id` · `schema_version` · `owner_id?` · `title` · `status` · `brief` · `facts[]` · `storyline` · `theme` · `slides[]` · `assets{id → {mime, w, h, path, sha256, prompt, model, treatment, ai_generated}}` · `budget_usd` (a hard cap that fails closed) · `version` · timestamps |
| `Job` | `id` · `deck_id` · `kind` · `state` · `heartbeat_at` · `attempt` · `error_code?` |
| `Event` | `seq` · `at` · `type` (a discriminated union, below) · `data` |
| `LedgerEntry` | `at` · `deck_id` · `job_id` · `stage` · `slide_id?` · `model` · `provider` · `prompt_version` · input / cached / output / reasoning tokens · `cost_usd` (from the response's `usage`) · `latency_ms` · `attempt` · `ok` · `error_kind?` |

---

## Generation jobs and events

**API surface.** Routes are thin, and each does one Pydantic parse at entry.

| Route | Does |
|---|---|
| `POST /decks` · `GET /decks` · `GET /decks/{id}` | Create from a `Brief`, list (thumbnails only, never image payloads), read |
| `POST /decks/{id}/interview` | Get the questions, accept answers or a skip |
| `POST /decks/{id}/outline` · `PATCH …/outline` · `POST …/outline/approve` | Generate, edit (reorder, text, add/remove, confirm or remove flagged numbers), approve |
| `POST /decks/{id}/looks` · `POST …/looks/{n}/choose` | Sample 3 looks and their tiles (or shuffle), choose one |
| `POST /decks/{id}/build` · `GET …/events` (SSE) · `POST …/build/abort` | Enqueue the build, stream it, stop it |
| `GET …/slides/{sid}/document` · `GET …/thumb.webp` | One slide as a full HTML document for the editor iframe; its QA screenshot |
| `PATCH …/slides/{sid}/fields` · `POST …/slides/{sid}/revise` | An inline text edit (an edit job re-renders and re-runs QA); an AI edit with an instruction (returns a candidate to accept or discard) |
| `POST /decks/{id}/slides` · `DELETE …/slides/{sid}` · `POST /decks/{id}/reorder` | Add (with an intent), delete, reorder |
| `POST /decks/{id}/theme` | Recolour or swap the pairing (deterministic + QA re-run), or restyle (regenerate with the content locked) |
| `GET /decks/{id}/export.html?flavour=present|send` · `GET …/export.pdf` | The artefact |
| `POST /decks/{id}/undo` · `POST …/redo` | Move between per-operation snapshots |

**Events** (appended to `events.jsonl`, each with a `seq`):
- `stage {name, state}`
- `outline_ready`
- `looks_ready`
- `slide_ready {slide_id, position, thumb_url, status}`
- `slide_flagged {slide_id, defects}`
- `cost {total_usd}`
- `done`
- `error {code, message}`, where `message` is human copy and never an exception string

The event models are registered in OpenAPI explicitly, because FastAPI leaves out models that no route returns.

**Jobs.** Before phase 27 the CLI runs the pipeline in its own process. From phase 27:
- **`worker.py` claims a job** (an atomic rename in the file store), heartbeats, and appends events. A stale heartbeat lets the job be claimed again.
- **State is persisted after every slide**, so a worker killed mid-deck resumes without paying for any slide twice.
- **Abort** marks the job; the worker stops after the current slide and keeps what is done.
- **One slide failing never discards the others.** That was v3's `slide_builder.py:116`.
- **SSE tails `events.jsonl`** and honours `Last-Event-ID`, so a reconnect has no gap. The browser reads it with a ~30-line `fetch` stream reader, because `EventSource` cannot send the Bearer token phase 29 needs.

`ponytail:` one worker process on one machine. The ceiling is one host; the upgrade path is Postgres `SKIP LOCKED` claims in phase 29.

---

## The model seam

`api/engine/llm/openrouter.py` and `images.py`. They are the only modules that talk to a model. Ported from v3's `api/ai/complete.py` (keep `_strict_schema` and the injectable transport) with that file's bugs fixed:

| Behaviour | Rule |
|---|---|
| Transport | `httpx.AsyncClient`, timeouts per stage, bounded backoff on 429/5xx. The v3 seam was synchronous, which ruled out parallel slides |
| `complete_json(schema, …)` | A strict `json_schema` response format, then one Pydantic parse. On failure, **one repair per call**, carrying the real previous answer and the validation error. v3 counted repairs per seam instance (one per deck), sent back `""`, and crashed on an unbound `raw` (`complete.py:200-217`) |
| `complete_text(parse, …)` | For slide HTML. The model answers in fenced `html` and `css` blocks and we parse them. HTML escaped inside JSON strings wastes tokens and breaks, and format constraints reduce diversity ([../findings.md](../findings.md) → Model behaviour) |
| `finish_reason` | `length` or a refusal is a typed failure, never parsed |
| Reasoning | `reasoning.effort` is set per stage with a generous `max_tokens`, because reasoning tokens are billed out of `max_tokens` ([../techstack/ai-stack.md](../techstack/ai-stack.md)) |
| Web search | `openrouter:web_search` in `tools`, with the engine pinned (exa or parallel, never `native`, so results do not change with the model). Citations come back as `url_citation` annotations (`url`, `title`, `content`) and become `Fact`s in `research.py` |
| Prompt caching | The stable prefix goes first: rules, then theme tokens, then the exemplar pack. `cache_control` breakpoints and a sticky `session_id` per deck. Slide 1 warms the cache, then the rest fan out. Check the minimum cacheable prefix per model at phase 21 |
| Images | `images.py` requests 1536×1024 or 1024×1536 and returns bytes, never a data URI |
| Cost | Every call appends a `LedgerEntry` with `cost_usd` read from the response's `usage`. The pipeline checks `deck.budget_usd` before each call and **refuses when the check itself fails** |
| Logging | Ids, sizes, timings and cost only. **Never prompts, deck content or answers** ([../security/operations.md](../security/operations.md)) |
| Tools with side effects | None. Image generation, rendering and export are our code's calls, never the model's |

---

## Security of AI-written HTML

The model now writes markup, so the output channel carries the risk. Three independent layers; any one of them stops script execution and data exfiltration on its own.

**Layer 1: parse and sanitize** (`qa/sanitize.py`, nh3)

| Allowed | Everything else is removed |
|---|---|
| **Tags:** `div section header footer h1–h3 p span strong em small sup sub br hr ul ol li blockquote figure figcaption`, plus our components `dd-image`, `dd-chart`, `dd-texture` | `script`, `style` attributes, `svg`, `a`, `img`, `form`, `input`, `iframe`, `object`, `embed`, and anything unlisted |
| **Attributes:** `class` (matching `[a-z][a-z0-9-]{0,39}`), `data-field` (must be one of this slide's field names), `data-deco`, `data-layer`, `data-bleed`, `data-build`, `aria-hidden`, and enum attributes on the `dd-*` elements | `style`, `id`, every `on*`, `href`, `src` |
| **Limits:** ≤150 elements, nesting depth ≤12, ≤16 KB of HTML and ≤16 KB of CSS per slide | Over-limit slides fail and are repaired |

**There are no links in slides.** URLs appear as plain text. v3 rendered an unvalidated CTA href while inline script was allowed, which was a `javascript:` XSS; removing `<a>` removes the class.

**Layer 2: lint the CSS** (`qa/lint.py`, tinycss2)
- **Scoping is the browser's job.** Each slide lives in its own Declarative Shadow DOM root, so its CSS cannot reach the player or another slide. We lint; we never rewrite selectors.
- No `url()`, no at-rules of any kind, no `:host` / `:root` / `html` / `body` selectors, no backslash escapes.
- No `<` anywhere: `</style>` inside slide CSS ends the element and turns the rest into live HTML — a full-slide link survives the CSP. The document also writes `</` in slide CSS as `<\/`, so a frame that skipped the lint stays inside its `<style>`.
- tinycss2 reads an unquoted `url(...)` as its own token, not a function. The lint checks both.
- The token rule and the rest of the bans are in [design-engine.md](design-engine.md) → "Slide lint".

**Layer 3: the browser**

| Where | Control |
|---|---|
| QA render (Playwright) | Every request is routed to abort except `data:`. The page's CSP is `script-src 'none'`; our measure script is injected over CDP. Check at phase 22 that `evaluate` still works under that CSP, and that Declarative Shadow DOM parses through `set_content` |
| Editor | A `srcdoc` iframe with `sandbox="allow-same-origin"` and **no** `allow-scripts`. The parent sets `contenteditable="plaintext-only"` on `data-field` nodes |
| Present mode in the app | The export runs our player script, so its iframe is `sandbox="allow-scripts"` and **no** `allow-same-origin`: the deck cannot reach the app's origin |
| Export | A CSP meta of `default-src 'none'; script-src 'sha256-<player>'; style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'` |

**Tests that hold the layers** (Chromium, Firefox and WebKit):
- A hostile-slide suite and the injection corpus in `bench/injection/`, recovered from `git show cbfebfa^:api/evals/injection/`.
- A **control on the control**: each hostile payload is first proven to run when unsandboxed, so a passing test means the control worked, not that the payload was broken.
- A `file://` test asserting zero network requests, including with the presenter popup open.

**Untrusted inputs to the model:** pasted material and web-search results are wrapped as quoted data in every prompt. They can steer the copy (a claim the user sees and approves) but not the output channel, which layers 1–3 hold ([../security/prompt-injection.md](../security/prompt-injection.md)).

**Speaker notes are private.** They ship only in the "present" flavour, as an inert `application/json` block the presenter popup reads. The "send" flavour and the PDF contain none.

**AI disclosure.** Every export carries machine-readable markers and a visible disclosure line in the player chrome (not on the slides). Generated images carry the IPTC XMP tag `digitalSourceType=trainedAlgorithmicMedia`. EU AI Act Art. 50 has been in force since 2026-08-02; check the Code of Practice's required mechanism at phase 26.
