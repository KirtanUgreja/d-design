# Phase 27 — app: create flow

> This phase makes the engine a product again: a person opens the app, types a brief, and watches a designed deck arrive, without a terminal.

**Depends on:** 25, 26 · **Blocks:** 28 · **Spec step:** Locked decisions → Stack, Process model · **Size:** L

## Search

**Read first** — [../../design/app.md](../../design/app.md) (all), [../../design/brand.md](../../design/brand.md), [../engine.md](../engine.md) → "Generation jobs and events", [../../techstack/frontend.md](../../techstack/frontend.md)

**Grep for**
- `emit` / the event callback in `api/engine/pipeline.py` — the worker and the CLI share it.
- `store/files.py` — every write must already be atomic before a second process exists.

**Verify externally**
- Next rewrites: is an SSE response streamed or buffered?
- shadcn/ui's current install for Tailwind 4.
- An OpenAPI → TypeScript generator that also gives runtime validation (one parse at entry).

## Make

**Backend**
- `api/worker.py`: claim, heartbeat, abort, resume.
- Thin routes ([../engine.md](../engine.md) → API surface); SSE that tails `events.jsonl` with `Last-Event-ID`.
- OpenAPI types generated into `web/lib/api/schema.d.ts`; the gate fails on a diff.

**Web** — Next.js, Tailwind, shadcn restyled to our brand at install (its `rounded-2xl` + shadow defaults are on the banned list).
- **Home:** the composer and recent decks.
- **Interview + outline gate:** questions with suggested answers and a skip; outline cards with drag, inline edit, regenerate, provenance chips, source popovers, and approve-or-reject on illustrative numbers.
- **Pick a look:** 3 style tiles and an instant shuffle.
- **Generation watch:** ghost slots, screenshots arriving in place, real phase labels only, abort, partial slides kept, "continue".
- **Export reveal:** present (opens the present flavour), download send, PDF.
- The states table from [../../design/app.md](../../design/app.md), in human words.

### Design decisions

- **The API never calls a model or a browser.** It enqueues and reads.
- **The watch shows screenshots**, not live iframes: they are what QA measured.
- **E2E tests replay a recorded event log.** No credits are spent in CI.

## Verify

- [ ] ASGI tests for every route
- [ ] SSE reconnect with `Last-Event-ID` has no gap
- [ ] Killing the worker mid-deck still completes the deck, and no slide is paid for twice
- [ ] A double click on Start enqueues one job
- [ ] Playwright E2E on a replayed event log
- [ ] **Human:** the owner gets a localhost link and a walkthrough, and builds 3 decks start to finish

## Skipped

- Accounts and the brand kit — trigger: phase 29.
- A template gallery — never. "No templates" is the positioning.

## Exit gate

- [ ] First slide within 60 seconds (median) of approval
- [ ] No raw exception text anywhere in the UI
- [ ] The gate, now with the web rows, is green
