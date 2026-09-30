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
- Up to 3 images per deck.
- A minimal export: arrow keys, fullscreen, scale-to-fit, the CSP.
- **Bake-off:** the 12 frozen outlines on 2 top models, and at reasoning effort "minimal" vs "medium".
- **A/B:** with exemplars vs without.

### Design decisions

- **Design only.** Outlines are frozen, so a bad wall cannot be blamed on content and a good one cannot hide behind it.
- **The baseline is one prompt to the same model.** That is the honest comparison, and it is cheap.
- **If the gate fails twice, pivot to exemplar-fill before phase 23**: the model selects and fills compositions instead of composing freely. It is a smaller claim, and it is decided here rather than discovered in phase 25.

## Verify

- [ ] A hostile-slide suite: script, handlers, `url()`, `@import`, links — none survive, and each payload is first proven to run unsandboxed
- [ ] One failing fixture per QA error code
- [ ] The offline test: zero requests from `file://`
- [ ] Cost and time per deck recorded from the ledger
- [ ] **Human (gate 1):** blind wall ratings of 12 decks against the baselines

## Skipped

- The sampler — trigger: phase 23.
- The content engine — trigger: phase 24.
- Charts, the full player, the app — triggers: phases 25, 26, 27.

## Exit gate

- [ ] At least 8 of 12 decks rated "designed, would present with ≤2 fixes"
- [ ] Preferred over the one-shot baseline in at least 9 of 12 blind pairs
- [ ] At most 1 visible defect per deck
- [ ] Median ≤ $2 and ≤ 4 minutes per deck
- [ ] The design model is chosen and pinned; the exemplar A/B result is recorded
- [ ] Total phase spend ≤ $100
