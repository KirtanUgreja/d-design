# Backend

One Python codebase, two processes. **Rewritten 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)). The module layout is in [../v4/engine.md](../v4/engine.md) → "Layout"; this document is why the backend is shaped that way.

## What the backend owns

Everything the product is: the engine, the data and the export. `web` owns only what the user touches ([frontend.md](frontend.md)).

| | Runs | Has | Never has |
|---|---|---|---|
| **api** — `api/app.py`, FastAPI | Routes, one Pydantic parse at entry, SSE, small edits to a deck | The deck store | **The OpenRouter key, a browser, a model call** |
| **worker** — `api/worker.py` | The engine: interview, research, storyline, compose, QA, repair, images, export, PDF | The OpenRouter key, Chromium, the deck store | **An inbound port** |
| **engine** — `api/engine/` | A pure library both entry points import | Nothing of its own | FastAPI imports |

**Before phase 27 neither process exists.** The CLI imports the engine and calls it directly, which is how phases 22–26 are built and benchmarked. The split arrives with the app, because that is when there is an internet-facing process to keep clean.

v3 had five runtimes. Three of them existed to move a `Deck` tree between a Python pipeline and a TypeScript renderer, and one to parse uploads. With slides as HTML the backend assembles, and with no uploads, none of those has a job ([decisions.md](decisions.md) → "2026-09-26 — v4").

## The worker

### Why a second process

**The process that faces the internet should hold nothing worth stealing, and should not run a browser.** The API parses requests from strangers. The worker holds the one secret in the system and renders model-written HTML in Chromium. Keeping those apart is the same trust split v3 drew around its fetch worker, pointed at what v4 actually has.

Two more things fall out of it for free: a build survives an API restart, and a slow build cannot starve request handling.

### Jobs

The API and the worker share no memory, so a job is a file.

| Step | How |
|---|---|
| **Enqueue** | The API writes a job file for the deck and returns |
| **Claim** | The worker claims a job by **atomic rename**. Two workers cannot both win a rename |
| **Heartbeat** | The claim carries a timestamp the worker refreshes. A stale heartbeat means the worker died, and the job is claimable again |
| **Progress** | State is saved **after every slide**, so a resumed job skips what is done |
| **Abort** | The API writes an abort marker; the worker checks it between calls and stops, keeping finished slides |
| **Failure** | One slide failing never discards the others. v3's builder threw away every finished slide on any error |

`ponytail:` job files on one machine. The ceiling is one host; at phase 29 the claim becomes a Postgres `SELECT … FOR UPDATE SKIP LOCKED`, with the same protocol above it.

### Events

The worker **appends events to `events.jsonl`** in the deck's directory. The API's SSE endpoint tails that file.

- Every event has a monotonically increasing id. A reconnecting client sends **`Last-Event-ID`** and the API replays from there, so a reload loses nothing.
- The unit is a whole checked slide, never a token. Anything that failed QA arrives as `slide_flagged`, not as a broken slide.
- `error` events carry human copy and a code. **An exception string never reaches a client.**
- The log replays without a model call, which makes it the fixture for the generation-watch UI and the recording for the marketing site.

The event list is in [../v4/engine.md](../v4/engine.md) → "Generation jobs and events".

### The browser in the backend

Playwright (Python) runs in the worker: one Chromium, a small page pool.

| Control | Why |
|---|---|
| **Every request is aborted except `data:`** | The slide's fonts and images are data URIs. Nothing a model wrote can fetch anything |
| **The slide's own scripts never run** | The sanitizer removes them, and the measure script is injected by us. Phase 22 verifies which Playwright setting enforces this |
| **A fresh context per deck, disposed after** | No state carries between decks |
| **Hard timeouts, and the page is killed on breach** | A pathological layout is the cheapest denial of service available |
| **Fixed 1920×1080 viewport** | QA measures one deterministic size |

The same render produces three things: the QA measurements, the screenshot that becomes the thumbnail, and (through print CSS) the PDF.

**This is not v3's fetch worker.** That one rendered pages an attacker chose. This one renders our own sanitized markup with the network cut. The residual and the container hardening are in [../security/infrastructure.md](../security/infrastructure.md).

### Budget

Every deck has a **`budget_usd` hard cap**. Before each model call the worker checks the cost ledger against it; at the cap the build stops, keeps what is done, and emits a plain-language event. **It fails closed**: a ledger that cannot be read refuses the call ([../coderules/patterns.md](../coderules/patterns.md) rule 5).

This exists from phase 22, not phase 29, because the first denial-of-wallet is our own repair loop.

## Data

**Until phase 29: a file store.** One directory per deck holding the deck JSON, its assets, the event log and the job file.

**`api/store/files.py` is the only data module.** Both processes go through it and nothing else touches the files.

| Rule | Why |
|---|---|
| **Atomic writes** (write a temp file, then rename) | A crash never leaves half a deck |
| **A per-deck lock** | Two writers cannot interleave |
| **A version check on every write** | A stale editor tab cannot overwrite a newer deck |
| **API edits get 409 while a build runs** | During generation the worker is the single writer. The editor treats 409 as a normal state, not an error |

`ponytail:` files and locks on one host. The upgrade path is phase 29.

**From phase 29: Postgres, SQLAlchemy and Alembic, owned by Python alone**, from a fresh baseline. One ORM and one migration tool: v3's two-ORM arrangement, and with it the risk of Alembic proposing to drop tables it did not own, is gone because no auth table lives in our database.

Generated assets move to object storage with the same module in front of them.

## The API contract

FastAPI's OpenAPI document is the contract. `openapi-typescript` turns it into `web/lib/api/schema.d.ts`, and the gate fails if regenerating produces a diff.

- **One Pydantic parse per route, at entry.** Past that the value is typed and trusted.
- **Expected failures are typed results** mapped to a status and human copy. Only bugs raise.
- **SSE event models are registered in OpenAPI explicitly.** They are not route responses, so FastAPI would otherwise leave them out and web would have no types for the stream.
- Routes are listed in [../v4/engine.md](../v4/engine.md) → "Generation jobs and events".

## Auth (phase 29)

Phases 21–28 have no accounts. At phase 29:

- **Better Auth** (owner, 2026-10-08), self-hosted in the web app: email and password, sessions, and its **JWT plugin**, whose JWKS FastAPI trusts. Its tables are in the `auth` schema, never read by Python. (Planned before: a managed IdP, WorkOS AuthKit or Clerk — reconsidered for OAuth or MFA.)
- **FastAPI verifies the JWT** with PyJWT's `PyJWKClient` against the provider's JWKS: signature, issuer, audience and expiry. **Any failure is `401`.** There is no permissive default.
- **A Python-owned `users` row keyed by the provider's `sub`.** Decks reference `users.id`, so foreign keys and cascade deletes are real. This answers v3's objection that a hosted IdP breaks the foreign key.
- **No table is shared across languages.** v3's `web` stripped a cookie signature and `api` read Better Auth's `session` table directly; both are gone.
- **Web sends `Authorization: Bearer`**, which is why it reads SSE with a fetch-stream reader: `EventSource` cannot set a header.

**The cost:** revocation is no longer an instant session delete. It is bounded by the token lifetime, so keep that short. The provider is a subprocessor ([../security/third-parties.md](../security/third-parties.md)).

**Isolation.** One Python data module filters every query by owner. **RLS is deferred**; the trigger is a second database client, because RLS earns its cost when there is more than one place to forget a `where` ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)).

**Authorization is checked at the data layer, never in middleware alone** ([../security/platform-and-packages.md](../security/platform-and-packages.md), CVE-2025-29927). With `web` holding no data, there is nothing for a Next.js middleware bypass to reach.

## Model access: OpenRouter behind a seam

`api/engine/llm/openrouter.py` is the only module that talks to a model, and only the worker runs it. Plain async `httpx`; a JSON call and a text call; one repair per call; pinned model ids; every call writes a cost-ledger entry. The specification is [../v4/engine.md](../v4/engine.md) → "The model seam", and the model questions are [ai-stack.md](ai-stack.md).

**It costs a guarantee.** OpenRouter's `strict: true` enforcement varies by provider, so the decoder does not guarantee a schema. What holds instead:

> For the JSON stages, the Pydantic parse is the gate: a failure is repaired once and then fails visibly. For slide HTML there is no schema; the gate is the sanitizer, the lint, and a render that runs no script and makes no request.

The residual is wasted tokens, which the per-deck budget bounds.

## What never reaches a log

Restating [../security/tenancy-and-data.md](../security/tenancy-and-data.md), because this is the layer where it gets violated:

**No prompts. No outputs. No brief, interview or deck content.** The cost ledger and the logs hold ids, sizes, timings, model ids and dollars. `events.jsonl` holds slide ids and thumbnails' paths, not copy.

If an error tracker is adopted at phase 29, configure server-side scrubbing before the first event is sent — [../security/operations.md](../security/operations.md).
