# Phase 30 — UI prototype and usability baseline

> This phase makes true that the user side is tested on people before it is wired to the engine: the five hot surfaces, clickable, on real decks, in front of five real founders and salespeople, with a measured baseline every later UI phase must beat.

**Depends on:** 23 (tiles), 26 (the export) · **Blocks:** 27, 31, 32, 33 · **Spec step:** First users · **Size:** M · **Model credit:** none

## Search

**Read first** — [../ui-research.md](../ui-research.md) (all), [../../design/app.md](../../design/app.md), [../../design/brand.md](../../design/brand.md), [../../design/principles.md](../../design/principles.md)

**Grep for**
- `bench/runs/*/content/*.json` and `bench/runs/*/engine/*/` — real outlines, slides, screenshots and exports to drive the prototype.
- `api/engine/design/tiles.py` — the style tiles, rendered by our code.

**Verify externally**
- shadcn/ui's current install for Tailwind 4, and how far its defaults must be restyled ([../../design/brand.md](../../design/brand.md) bans `rounded-2xl` and soft shadows).
- A moderated-test script and a recruiting route for five founders or salespeople who present within the next month.

## Make

- **`web/` returns** as the shell phase 27 will wire up: Next.js, Tailwind, shadcn restyled to our brand, our own tokens for the chrome.
- **The five hot surfaces, on fixtures:** composer → interview + outline gate → pick a look → generation watch → editor + reveal. Data is a recorded event log from a real bench run, replayed on a timer at real speed. **No backend, no model, no credit.**
- **The state table** from [../../design/app.md](../../design/app.md) → "The states nobody designs", each state reachable from a debug menu, in final copy.
- **A test harness:** a script for a 30-minute moderated session, a 5-second test of the first screen, a post-task rating, and a notes template.
- **The baseline:** five sessions, recorded with consent.

### Design decisions

- **Prototype the feel before the plumbing.** Phase 27 builds the worker, the routes and SSE; this phase answers whether the screens work for a person, at a fraction of the cost and with no credit.
- **Real decks only.** A prototype on lorem ipsum tests nothing that matters here ([../ui-research.md](../ui-research.md) → competitors: Pitch).
- **The prototype is the start of `web/`, not a throwaway.** Phase 27 replaces the fixtures with the API.

## Verify

- [ ] Every interaction in the prototype answers in under 400 ms (Doherty threshold)
- [ ] Every row of the states table is reachable and has human copy
- [ ] Keyboard-complete; visible focus; works at 200% zoom
- [ ] **Human:** 5 moderated sessions with founders or salespeople, recorded

## Skipped

- The worker, routes, SSE and persistence — phase 27.
- Accounts — phase 29.

## Exit gate

- [ ] 5 of 5 participants reach the reveal without help
- [ ] The 5-second test: at least 4 of 5 say what the product is for
- [ ] A baseline is written down (task times, ratings, every friction observed) in `bench/ui/baseline.md`
- [ ] The ethics line in [../ui-research.md](../ui-research.md) holds on every screen
