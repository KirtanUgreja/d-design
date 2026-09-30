# Patterns

The domain-specific rules. These matter more here than in a generic app, because each one protects something the product cannot work without.

The first three protect the *product*: the deck's visual coherence, the edit/export guarantee, and where data is read. The next three protect it from *failing quietly*: a cross-tenant read, a permissive default, and a second way to call a model. Every one of the second group describes a bug that looks like reasonable code in review.

> **Rules 1, 2, 3, 4 and 6 were rewritten on 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)). Each says what it replaced.

## 1. The token rule

**Model-written CSS may reference the theme for colour and type, and nothing else. Layout is free.**

*Replaces "the no-styling invariant" (2026-09-26). That rule gave the model a JSON form with no field for a visual value, and one stylesheet drew every slide. It capped decks at about five visual variables ([../findings.md](../findings.md)).*

| The model may write | The model may not write |
|---|---|
| Any layout: grid, flex, positions, sizes, spacing, transforms | A raw colour (hex, `rgb()`, `oklch()`, a named colour) |
| `color: var(--c-ink)`, `background: var(--c-ground)` | A `font-family` that is not a theme token |
| `font: var(--t-display-xl)`, a `font-weight` the theme embeds | A raw `font-size` |
| Texture through a theme token (`mask-image: var(--tex-halftone)`) | Gradients, blur, glow, soft shadows, `url()`, `@import`, `@font-face` |

**Enforcement is a parse at entry, not a schema.** Slide HTML goes through `nh3` (an allowlist: no scripts, handlers, forms, iframes, `<a>` links or inline `style`) and its CSS through a `tinycss2` lint. The lint only lints. It does not rewrite selectors: **each slide's CSS is scoped by its own Declarative Shadow DOM root**. The full lists are in [../v4/design-engine.md](../v4/design-engine.md) → "Slide lint" and [../v4/engine.md](../v4/engine.md) → "Security of AI-written HTML".

**The rule for when the lint fires:** the violation goes back to the model as the repair prompt. If the same legitimate need keeps firing it, add a token to the theme. Never add an exception to the lint.

**The theme is the single source of visual truth, and it is pure code.** The sampler picks the axes and code computes the tokens and the three looks; no model call writes a theme. That is what keeps separately composed slides one deck, and what makes a theme swap possible.

A `style` attribute, a per-slide colour override, or a "just this once" raw hex is the single change that would unravel it.

## 2. The engine is pure, and the app never renders a slide

**`api/engine/` is plain functions of their arguments. It imports no web framework and reads no environment.**

*Replaces "the renderer core is pure and mode-free" (2026-09-26). There is no TypeScript renderer any more.*

- **Behaviour is injected**: the model client, the event sink, storage and the browser pool are arguments. `settings.py` is the only module that reads the environment.
- **One path to a deck.** The CLI, the worker and the bench call the same engine functions through `engine/__init__.py`.
- **One assembly.** The editor's slide documents, present mode and the download all come out of the same export code. Present mode shows the export file itself, so what you present is byte-for-byte what you send.
- **`web` never builds slide HTML.** It shows backend-produced documents in sandboxed iframes without `allow-scripts`, and QA screenshots as thumbnails. Edits are read back as `textContent` of `data-field` nodes and sent to the API.

**Process rule, from phase 27:** model calls and Chromium run only in `api/worker.py`. The API process never calls a model or a browser. Before phase 27 the CLI calls the engine directly.

The practical form of the ban: nothing under `engine/` may import `fastapi`/`starlette`, read `os.environ`, or branch on who is calling. An import-linter contract enforces the first ([tooling.md](tooling.md)). An engine that behaves differently under the bench than in the product is a bench that measures something else.

## 3. Storage is touched in one module

**Until phase 29, `api/store/files.py` is the only data module. Nothing else opens a deck file.**

*Replaces the two-ORM rule (2026-09-26): SQLAlchemy in `api`, Drizzle in `web`, two migration tools on one database. `web` now has no database at all.*

**The single-writer rule.** A file store has no transactions, so exactly one writer owns a deck at a time:
- During a generation job, the worker is the only writer. It persists after every slide.
- An API edit to a deck that is generating gets a **409**, never a merge.
- Outside a job, the API process writes.

**From phase 29** the store becomes Postgres, and the rule takes its old shape: SQLAlchemy is imported only in Python `*_data.py` modules, never in a route or the engine. Each table's access has one home, because that is where the ownership filter lives ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)).

No generic repository layer over either. `files.py` is a handful of functions; SQLAlchemy is already the abstraction over SQL.

## 4. Every tenant-scoped query runs inside the tenant wrapper

**Exactly one wrapper, in Python. It arrives with Postgres in phase 29. A second is a bug.**

*Replaces "exactly two wrappers, one per language" (2026-09-26). `web` no longer has a database, and the TypeScript copy guarded nothing: it was never called.*

```python
# api/db/tenant.py — the only place app.user_id is set
@asynccontextmanager
async def as_user(user_id: str):
    async with session_factory() as s, s.begin():
        await s.execute(text("select set_config('app.user_id', :uid, true)"), {"uid": user_id})
        yield s
```

Three things make this the most dangerous code in the backend, and all three are invisible in review:

- **The `true` in `set_config` scopes the value to the transaction.** Without it the setting persists on the connection, and a pooled connection serves the next request as the previous user. One boolean between correct and a cross-tenant read.
- **The pooler must run in transaction mode.** Session mode binds a connection for a whole client session, which silently breaks the scoping above.
- **A tenant-scoped query outside a transaction is unsafe by construction** on a shared pool.

So the rule is not "remember to set the variable." It is: **one function can talk to the database as a user, and everything goes through it.** A lint bans `set_config('app.user_id'` outside that file.

Until phase 29 there are no tenants, and the file store has no user scoping. That is a known ceiling of a local, single-user product, not a control.

Test the unset case explicitly: `current_setting('app.user_id')` on a connection where it was never set must fail, not match everything. That is rule 5 applied to isolation.

## 5. Anything that grants, fails closed

The OWASP A10 rule from [../security/infrastructure.md](../security/infrastructure.md), stated as a coding pattern because that is where it is violated.

> **Availability degrades open. Authorization degrades closed.**

```python
# wrong — reads as defensive programming, is a vulnerability
try: return await check_budget(user)
except Exception: return Allowed()

# right
try: return await check_budget(user)
except Exception: return Refused("budget check unavailable")
```

The test is one question: **could this failure grant something?** An image that fails to generate leaves a slide without an image, and nobody has been given anything. A budget check that times out and returns "allowed" has.

The same rule covers the sanitizer and the lint: **a slide that could not be parsed is rejected, never passed through.**

This is why expected failures are `Result` and not exceptions ([python.md](python.md)). A `Result` forces the caller to choose a branch. The dangerous shape is always a `catch`/`except` returning a default, because a default is a decision nobody reviewed.

Prove it by injection: make each check raise and assert refusal.

## 6. One seam for model calls

**Every call to a model goes through `api/engine/llm/openrouter.py`.** Not one per stage, not one per feature. `web` never holds a model credential, and from phase 27 neither does the API process: only the worker runs the seam.

*Replaces `api/ai/complete.py` (2026-09-26), whose bugs are listed in [../v4/engine.md](../v4/engine.md) → "The model seam".*

The seam owns these, so no call site reimplements them:

| | Rule |
|---|---|
| **Async** | One shared `httpx.AsyncClient`, timeouts per stage, bounded backoff. The old seam was sync, which ruled out parallel slides |
| **JSON mode** | Strict `json_schema`, then one Pydantic parse |
| **Text mode** | For slide HTML: tagged `<slide>…</slide><style>…</style>`, parsed by us. HTML never travels inside JSON |
| **Repair** | **One per call**, carrying the model's real previous answer and the error. Never a counter shared across a request |
| **`finish_reason`** | `length` or a refusal is a typed failure, never parsed |
| **Cost ledger** | Every call appends stage, model, prompt version, tokens (in, cached, out), USD, ms, repair |
| **Web search** | `openrouter:web_search` is the only tool. Results are data and become `Fact`s |
| **Prompt caching** | Stable prefix first, `cache_control` breakpoints, a sticky session per deck |
| **Logging** | Ids, sizes, timings, cost. Never prompts or content |

**The model gets no tool with side effects.** Image generation, rendering and export are our code's calls.

### Bounded loops stay bounded

The QA loop is render → measure → repair, **at most two rounds**, then a fallback composition, then a visible flag ([../v4/design-engine.md](../v4/design-engine.md)). It is a `for` loop with a literal limit in the engine.

**It is not an agent and must not be built with an agent framework** ([../techstack/ai-stack.md](../techstack/ai-stack.md)). The test is one question: *can the model change how many times this runs?* If no, it is a loop. If yes, reread the framework decision.

## 7. Formatting is locale-aware from day one

Numbers, currency, and dates go through the platform's locale formatting (`Intl` in `web`; one formatting helper in the engine for chart labels and stats), never string concatenation. This is also an XSS boundary: a formatted value is a text node, never interpolated into markup.

## 8. Comments explain why, not what

Comments capture the non-obvious decision, the tradeoff, the thing the code cannot say about itself. They never restate the code.

Deliberate shortcuts get a `ponytail:` comment naming the ceiling and the upgrade path:

```python
# ponytail: file store, one writer per deck. Ceiling: one machine, one user.
# Upgrade: Postgres + the tenant wrapper in phase 29.
```

That is debt made greppable. A corner cut without the comment is the actual debt.
