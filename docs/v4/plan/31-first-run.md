# Phase 31 — first run and the composer

> This phase makes true that a first-time visitor sees the product really work before any sign-up, and then sees their own words in a designed look within a minute of a one-step sign-up, without retyping anything.

**Depends on:** 30, 27, 29 (for the one-step sign-up) · **Blocks:** 35 · **Spec step:** First users; Risks → time to value · **Size:** M

## Search

**Read first** — [../ui-research.md](../ui-research.md) → first impressions, endowed progress, goal-gradient; [../../design/app.md](../../design/app.md) → §1 the composer, "First run"; [../../design/website.md](../../design/website.md); [../../design/principles.md](../../design/principles.md) § 7, the demo must cost nothing

**Grep for**
- `bench/ui/baseline.md` — what phase 30's participants stumbled on first.

**Verify externally**
- How Gamma and two other AI presentation makers handle the first minute today (sign-up wall, quiz, demo), as a fresh teardown.

## Make

- **See it work before signing up, for $0** (principle 7): a recorded replay of a real generation — the same event stream, replayed client-side — and real exported decks to open and present. No anonymous live generation: that is a bill and an abuse surface.
- **The brief survives sign-up.** A visitor can type their brief first; sign-up is one step (passwordless or OAuth, phase 29) and the interview starts from what they typed. Nothing is retyped.
- **The first screen is the proof:** one focused prompt box, a real founder brief as the placeholder, three example briefs as one-click chips (pitch, sales, investor update), and a real deck visible behind the box.
- **Real head starts only:** pasted notes and the brief pre-fill interview answers; a waitlist answer pre-fills the prompt (phase 29). Never a fake "step 2 of 10".
- **The path is short and named:** *Brief → Outline → Look → Deck*, the current step marked, visible from the first screen.
- **One sample deck in Recent**, real and breakable, so the editor can be learned with nothing at stake.
- **Teach while waiting:** during the generation watch, one or two quiet lines about the editor (*"Click any text to change it"*), never a tour.
- **The brand kit comes after the first deck**, framed as *make this yours*.

### Design decisions

- **The interview is about this deck, not about the user.** No segmentation quiz before value ([../ui-research.md](../ui-research.md) → competitors: Gamma).
- **Head starts must be true.** Endowed progress is used only where progress is real (the ethics line).

## Verify

- [ ] Time from approving the outline to the cover, measured in the browser, median ≤ 60 s
- [ ] The replay and the example decks work with no account and make zero model calls
- [ ] A brief typed before sign-up arrives intact after it
- [ ] **Human:** 5 first-time users, unmoderated: what they understood in 5 seconds, and where they hesitated

## Skipped

- URL and PDF import — trigger in [24-content-engine.md](24-content-engine.md).
- Templates or a starting gallery — never.

## Exit gate

- [ ] Median time from approval to the cover ≤ 60 s
- [ ] At least 4 of 5 first-time users reach the watch without help
- [ ] Beats phase 30's baseline on time-to-first-look and on the 5-second test
