# v4 — plan

Phase numbers continue from v3 ([../../versions.md](../../versions.md): a phase number is a filename, not a position). Branches are `phase-21-reset` … `phase-29-accounts-deploy`.

## Status

| Phase | Size | Status |
|---|---|---|
| [21 — reset](21-reset.md) | M | built 2026-09-30 — open: the owner's ratings. Gamma baselines dropped for now (2026-10-01) |
| [22 — engine spike](22-engine-spike.md) | L | **closed 2026-10-01 on design** — owner re-read gate 1 after two failures: the engine wins Designed, loses Says something; content gap → 24, re-tested at gate 2 |
| [23 — design system](23-design-system.md) | M | built 2026-10-01 — automated checks pass but one: 9 of 10 pairings across 12 decks. Open: the owner's tile wall and deck wall |
| [24 — content engine](24-content-engine.md) | M | **closed 2026-10-01** — automated exit lines pass; the two human checks skipped by the owner |
| [25 — composition and QA](25-composition-qa.md) | L | in progress — the free half built 2026-10-05; images, the end-to-end run and gate 2 need a credit top-up |
| [26 — player and export](26-player-export.md) | M | built 2026-10-05 — automated checks green on Chromium and WebKit; Firefox in CI. Open: the owner's stage test (external display + clicker) and the email-attachment test |
| [27 — app: create flow](27-app-create-flow.md) | L | **backend built 2026-10-07**: `store/files.py` (atomic, versioned, per-deck lock, rename-claimed jobs), `worker.py` (heartbeat, resume without paying twice, abort), `app.py` (thin routes, SSE with `Last-Event-ID`); 7 offline tests. Left: OpenAPI → TS types, the web wired to it, E2E on a replayed log, the owner's 3 live decks |
| [28 — editor](28-editor.md) | L | not started |
| [29 — accounts and deploy](29-accounts-deploy.md) | M/L | not started |
| [30 — UI prototype](30-ui-prototype.md) | M | built 2026-10-05 — automated checks pass; open: the owner's 5 moderated sessions (`bench/ui/session-script.md`) |
| [31 — first run](31-first-run.md) | M | not started |
| [32 — watch and reveal](32-watch-reveal.md) | M | not started |
| [33 — trust and control](33-trust-control.md) | M | not started |
| [34 — presenter confidence](34-presenter-confidence.md) | S/M | not started |
| [35 — measure, learn, ethics](35-measure-learn.md) | S/M | not started |
| [36 — independent design](36-independent-design.md) | L | **in progress 2026-10-07** — built: descriptors, archive, targets, `compose.v9` (no exemplars, verbalized sampling, colour pairs, 32k cap: one real deck, 0 fallbacks, $0.13), novelty gate, procedural fallback (3,270/3,270 pass QA). Continuous palette, motif grammar, sameness bench (`cli sameness`; the code-built layout alone repeats 65% at 275 slides). Variable fonts (11 display families). Left (needs credit and the owner): the owner's look at the 2026-10-07 Harbor build, and the 30-deck paid sameness run. Planned 2026-10-05 (owner) — **before 25's gate 2**: every slide's composition generated toward unexplored design space and checked against an archive of all slides; no exemplars, archetypes or menus in the compose path |
| [37 — beautiful data](37-beautiful-data.md) | M | **code built 2026-10-07**: 9 forms chosen from the data, validated series colours (1,000 seeds), emphasis, computed callouts, data as text; storyline.v4 and research.v2 ask for charts and series. Left (needs credit and the owner): re-freeze outlines, the bench, the data wall. Planned 2026-10-05 (owner) — charts chosen by the data's job (hero figure, emphasis, stacked, dumbbell, waffle…), drawn in the deck's look, colour-validated, and present whenever approved facts carry a series |
| [38 — brand kit and logo](38-brand-kit.md) | M | **engine built 2026-10-07**: hostile-by-default ingest (raster re-encode, SVG drawn to pixels with the network cut), code placement in an empty safe corner, legible variant, E12/W9, brand-colour proposal. Left: the saved kit and upload UI (after phase 29's accounts), the logo wall. Planned 2026-10-05 (owner) — saved kit; logo uploaded hostile-by-default, rasterised, placed by code in `<dd-logo>`, legible on every ground; the look built around the brand colour |

## Dependency graph

```
21 reset
   │
   ▼
22 engine spike ══ HUMAN GATE 1: "looks designed", beats the one-shot baseline
   │
   ├──▶ 23 design system ──┐
   ├──▶ 24 content engine ─┼──▶ 25 composition + QA ══ HUMAN GATE 2: "would send to an investor or customer"
   │                       │            │
   └──▶ 26 player + export ◀────────────┘
                 │
                 ▼
        27 app: create flow ──▶ 28 editor ──▶ 29 accounts + deploy
```

### The user side (phases 30–35, planned 2026-10-05)

Phases 27–29 build what the app *does*; phases 30–35 make it *feel* right, each tested on real users against a baseline. The evidence and the ethics line are in [../ui-research.md](../ui-research.md).

```
26 player ──┬──▶ 30 UI prototype (no credit) ──┬──▶ 27 create flow ──▶ 31 first run ──┐
23 tiles ───┘                                  │          │       ──▶ 32 watch+reveal ─┤
                                               │          ▼                            ├──▶ 35 measure,
                                               └────▶ 28 editor ──▶ 33 trust+control ──┤    learn, ethics
                                                          │       ──▶ 34 presenter ────┘
                                                          ▼
                                                   29 accounts + deploy (31's sign-up, 35's data)
```

## Recommended build order

1. **21 reset** — delete what v4 replaces, set the rules and the gate, build the bench and rate the baselines. Nothing is built on the old tree.
2. **22 engine spike** — the make-or-break phase. Frozen outlines, so the wall measures design alone. **Nothing after it starts until gate 1 passes.**
3. **23 design system** — before content, because design is the claim at risk and frozen outlines make it independent of content.
4. **24 content engine** — outlines that say something true. Independent of 23 and can run beside it.
5. **25 composition and QA** — needs both 23 and 24. Ends at gate 2.
6. **26 player and export** — independent after 22, but placed here so it presents real decks.
7. **27 app: create flow** — the first time the product is a web app again.
8. **28 editor**.
9. **29 accounts and deploy** — last, deliberately. v1–v3 built this first.

**Every phase exit includes a wall** the owner scores ([../bench.md](../bench.md)). Status lives here and in each phase's exit gate, nowhere else.
