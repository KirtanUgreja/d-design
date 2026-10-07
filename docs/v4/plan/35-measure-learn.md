# Phase 35 — measure, learn, and the ethics gate

> This phase makes true that the user side improves on evidence: a small, privacy-safe set of events tells us where people stall, five users a month tell us why, and every UI change passes the ethics line before it ships.

**Depends on:** 29 (accounts), 31–34 · **Blocks:** — · **Spec step:** Risks; [../../design/questions.md](../../design/questions.md) #273 · **Size:** S/M

## Search

**Read first** — [../ui-research.md](../ui-research.md) → the ethics line, ten rules; [../../security/operations.md](../../security/operations.md) → logging; [../../design/app.md](../../design/app.md) → "Instrument it"

**Grep for**
- Every place the web app could log deck content — it must not ([../../security/operations.md](../../security/operations.md)).

**Verify externally**
- The Digital Fairness Act's text when it is tabled (expected Q4 2026), and a check of our screens against it.
- A privacy-respecting product analytics option that can run without third-party cookies.

## Make

- **Ten funnel events, ids and timings only — never content:** brief started, interview skipped or finished, outline approved, look picked (and shuffles), first slide shown, deck done, AI change accepted / discarded / undone, export, present, rehearse.
- **The styling-hunt signal:** each time a user reaches for a colour or font control that does not exist ([../../design/app.md](../../design/app.md) → "Instrument it").
- **A monthly five-user test** on the current build, using phase 30's harness; findings filed against phases.
- **The ethics gate:** a checklist from [../ui-research.md](../ui-research.md) → "The ethics line", run on every UI change in review, and a quarterly audit of all screens.
- **A UI scorecard** in `bench/ui/results.md`: time to first look, drop-off per step, accept and undo rates, rehearsal use, the styling-hunt rate.

### Design decisions

- **No content in analytics, ever.** Ids, timings and counts only; the same rule as the engine's ledger.
- **Retention is earned by the deck, not engineered.** No streaks, no re-engagement nags; the only email is the user's own deck (phase 29).

## Verify

- [ ] A test asserts no event payload contains deck text, a brief or a fact
- [ ] The ethics checklist is part of the review template and the gate's docs check
- [ ] **Human:** the first monthly test is run and filed

## Skipped

- A/B testing infrastructure — trigger: enough weekly users for a test to finish in under a month.
- Heatmaps and session replay — never; they record content.

## Exit gate

- [ ] The scorecard exists with one month of data
- [ ] Zero ethics-checklist failures in the audit

## Sprint status (2026-10-08) → [master-plan.md](master-plan.md)

**After submission.** It needs accounts (29) and weekly users. The no-content rule already holds in the engine's ledger.
