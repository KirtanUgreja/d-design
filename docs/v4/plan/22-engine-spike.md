# Phase 22 — engine spike

> This phase makes true the claim v1–v3 never reached: a model composing HTML inside a token system, checked in a browser, produces decks that look designed. **It is the make-or-break gate. Nothing after it starts until it passes.**

**Depends on:** 21 · **Blocks:** 23, 24, 25, 26 · **Spec step:** Bets 1 and 9, Locked decisions → Slide authoring, Token rule, QA · **Size:** L

## Search

**Read first** — [../design-engine.md](../design-engine.md) (all), [../engine.md](../engine.md) → "Security of AI-written HTML", [../../design/principles.md](../../design/principles.md) §5, [../../findings.md](../../findings.md) → Model behaviour

**Grep for**
- `git show cbfebfa^:web/src/features/art-direction/color.ts` — the APCA maths to port.
- `git show cbfebfa^:api/features/slot/generate.py` — the `_WILL_NOT_WORK` list for the lint.
- `render/tests/offline.test.ts` at `v3-final` — the zero-request test to port.

**Verify externally**
- Playwright (Python): does Declarative Shadow DOM parse through `set_content`, or only `goto`?
- Does `page.evaluate` run under a page CSP of `script-src 'none'`?
- The nh3 `attribute_filter` API.
- Design references for the exemplars: Swiss-style posters, editorial spreads, agency and launch decks. Not template marketplaces.

## Make

- **3 hand-specified themes** and **8 vendored OFL families** (licence checked per family).
- **12 exemplars**: 6 archetypes × 2, each passing lint and QA under all 3 themes.
- `compose/author.py`: a cached deck-level prefix (rules, tokens, exemplar pack) and a per-slide suffix (fields, intent, archetype, the previous slide's structure).
- `qa/sanitize.py` (nh3) and `qa/lint.py` (tinycss2).
- `compose/document.py`: one shadow root per slide.
- QA errors E1–E10, with **one** repair round.
- A minimal export: arrow keys, fullscreen, scale-to-fit, the CSP.
- **Bake-off:** the 3 smoke outlines on cheap paid models first (owner's decision, 2026-09-30: cheap models, no free ones, quality judged on the wall). A dearer model is tried only if the wall says the cheap ones are not good enough. One full 12-deck run at the end.
- **A/B:** with exemplars vs without.

### Design decisions

- **Design only.** Outlines are frozen, so a bad wall cannot be blamed on content and a good one cannot hide behind it.
- **The baseline is one prompt to the same model.** That is the honest comparison, and it is cheap.
- **If the gate fails twice, pivot to exemplar-fill before phase 23**: the model selects and fills compositions instead of composing freely. It is a smaller claim, and it is decided here rather than discovered in phase 25.

## Verify

- [x] A hostile-slide suite: script, handlers, `url()`, `@import`, links — none survive, and each payload is first proven to run unsandboxed (`tests/test_hostile.py`, 2026-10-01). It found a `</style>` breakout and unquoted `url()` passing the lint; both fixed
- [x] One failing fixture per QA error code, E1–E9 (`tests/test_qa_codes.py`). E10 moves to phase 25 with images
- [x] The offline test: zero requests from `file://` (`tests/test_offline.py`), itself proven to catch a leak
- [x] Cost and time per deck recorded from the ledger (`bench/results.md`)
- [ ] **Human (gate 1):** blind wall ratings of 12 decks against the baselines

## Skipped

- The sampler — trigger: phase 23.
- The content engine — trigger: phase 24.
- Charts, the full player, the app — triggers: phases 25, 26, 27.
- Images — trigger: phase 25, which owns `dd-image` and the image-model bake-off. None of the frozen outlines asks for an image, so a phase-22 pipeline would have had nothing to draw (owner's decision, 2026-10-01).

## Exit gate

> **Closed 2026-10-01 on design, by the owner's decision after two failed attempts.** The preference and usable lines failed (8 then 6 of 12; 10 then 7 of 12). The owner re-read gate 1 as a design gate, which the engine wins: Designed 4.25 and 4.42 against the one-shot's 3.83 and 3.75, and 6 wins, 4 ties, 2 losses on Designed alone in attempt 2. It loses on Says something, which the frozen outline caps. This re-reading was made **after** seeing the results, and is recorded as such. The exemplar-fill pivot is not taken; the content gap goes to phase 24 and is re-tested against the one-shot at gate 2. Evidence: `bench/results.md`.


- [ ] At least 8 of 12 decks rated "designed, would present with ≤2 fixes" — 10 of 12 on attempt 1, 7 of 12 on attempt 2
- [ ] Preferred over the one-shot baseline in at least 9 of 12 blind pairs — 8 of 12 on attempt 1, 6 of 12 on attempt 2
- [x] At most 1 visible defect per deck — 0
- [x] Median ≤ $2 and ≤ 4 minutes per deck — $0.055, about 1 minute
- [x] The design model is chosen and pinned; the exemplar A/B result is recorded
- [ ] Total phase spend ≤ $10 (owner's budget, 2026-09-30; was $100)
