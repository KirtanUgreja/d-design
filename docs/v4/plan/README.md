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
| [27 — app: create flow](27-app-create-flow.md) | L | not started |
| [28 — editor](28-editor.md) | L | not started |
| [29 — accounts and deploy](29-accounts-deploy.md) | M/L | not started |

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
