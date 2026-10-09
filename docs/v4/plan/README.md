# v4 — plan

Phase numbers continue from v3 ([../../versions.md](../../versions.md): a phase number is a filename, not a position). Branches are `phase-21-reset` … `phase-29-accounts-deploy`.

## Now: the sprint to submission

**[master-plan.md](master-plan.md)** — build everything on 2026-10-09 (no credit), test on 2026-10-10 (the owner tops up), submit by 2026-10-10. It orders the work, sets the cut lines and the budget, and says which phase owns each item.

**[demo-script.md](demo-script.md)** — the 3-minute stage demo for 2026-10-10: showcase decks, the click path, and what to do if the live build is slow.

## Status

| Phase | Size | Status |
|---|---|---|
| [21 — reset](21-reset.md) | M | built 2026-09-30 — open human check (baseline ratings) moves after submission |
| [22 — engine spike](22-engine-spike.md) | L | **closed 2026-10-01 on design** |
| [23 — design system](23-design-system.md) | M | built 2026-10-01; superseded in part by 36 and 39 (languages constrain the look) |
| [24 — content engine](24-content-engine.md) | M | **closed 2026-10-01**; re-run 2026-10-08 on storyline.v4 / research.v2 ($1.10, 11 of 12 outlines with a chart) |
| [25 — composition and QA](25-composition-qa.md) | L | free half built; images moved to 39; **gate 2 = the test-day wall (2026-10-10)** |
| [26 — player and export](26-player-export.md) | M | built 2026-10-05; the stage and email tests move after submission |
| [27 — app: create flow](27-app-create-flow.md) | L | built offline 2026-10-07 (API, worker, live web flow); **test day:** the owner's 3 live decks |
| [28 — editor](28-editor.md) | L | free half built 2026-10-07; **build day (P1):** AI edits as proposals, notes, duplicate |
| [29 — accounts and deploy](29-accounts-deploy.md) | M/L | **build day (P0, owner 2026-10-08):** Better Auth (email and password), hosted Postgres behind the one tenant wrapper, JWT verified in FastAPI, user management, a per-user cap; packaging P1 |
| [30 — UI prototype](30-ui-prototype.md) | M | built 2026-10-05; the 5 sessions move after submission |
| [31 — first run](31-first-run.md) | M | partly in place from 30; **build day (P1):** the brief survives sign-up |
| [32 — watch and reveal](32-watch-reveal.md) | M | mostly built; **build day (P1):** real states, flagged slides named before download |
| [33 — trust and control](33-trust-control.md) | M | mostly built; proposals arrive with 28 |
| [34 — presenter confidence](34-presenter-confidence.md) | S/M | presenter view built (26); rehearse mode after submission |
| [35 — measure, learn, ethics](35-measure-learn.md) | S/M | after submission |
| [36 — independent design](36-independent-design.md) | L | built 2026-10-07/08; **owner's wall: one house style** — references return in 39; archive, palettes, variable fonts kept |
| [37 — beautiful data](37-beautiful-data.md) | M | built; charts in 33 of 36 decks; **build day (P0):** the "pair" form for two values |
| [38 — brand kit and logo](38-brand-kit.md) | M | engine built; **build day (P1):** per-deck upload without accounts |
| [39 — design reset](39-design-reset.md) | L | **the build day's core (P0):** 8 visual languages, 64 references adapted not filled, imagery, the style preview, `compose.v11` |

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

## Build order

The original order (21 → 29) is done through 28. **From 2026-10-08 the order is [master-plan.md](master-plan.md)'s:** 39 (languages, references, retrieval, `compose.v11`, images, preview) with parallel agents on the references, **29's accounts and database in parallel** (agents on the SQL store and the web auth), then 37's pair form, model plumbing, the security tests, and P1 (28, 31, 38, 29's packaging, 32) → test day.

**Every phase exit includes a wall** the owner scores ([../bench.md](../bench.md)). Status lives here and in each phase's exit gate, nowhere else.
