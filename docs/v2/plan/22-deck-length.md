# Phase 22 — Deck length

> *"Make me a deck"* has no correct length. *"I have five minutes"* does. The user says how long they are talking and roughly how many slides they want, the Director plans to that number, and the outline gate is where they change their mind before anything expensive is built.

**Depends on:** [10](10-slides-mode.md) · **Blocks:** [19](19-presenter-view.md) *(the timer's target comes from here)* · **Spec step:** presentation delta

The smallest phase in the presentation set and one of the highest-leverage, because it changes what the Director is optimising for.

---

## Search

**Read first**

- [../presentation.md](../presentation.md) → "Deck length is the user's"
- [../../v1/plan/08-intake.md](../../v1/plan/08-intake.md) → the AI-led Q&A that produces the Brief. Two questions are added there, not a new screen
- [../../v1/ai-pipeline.md](../../v1/ai-pipeline.md) → the Director phase and the outline gate. The gate already exists and already edits; this phase gives it a target to edit against
- [../../v1/plan/07-director.md](../../v1/plan/07-director.md) → how the outline is currently produced and what constrains its length today

**Grep for**

- `api/schema/scene.py` → `scenes: Scene[]` with its `3–12` bound. That bound is currently the only thing deciding deck length, and it is a schema limit standing in for a product decision
- `api/schema/brief.py` (or wherever the Brief lives) → the Brief gains `talkLengthMinutes` and `targetSlides`
- `api/features/director/` → where the outline is generated. The target is a prompt input **and** a validation bound
- `web/src/features/editor/` → the outline gate UI. Add and delete already exist or nearly do; this phase makes the count visible against the target

**Verify externally** — nothing. This is a product decision, not a platform question.

---

## Make

```
api/schema/brief.py        talkLengthMinutes, targetSlides
api/features/director/     plans to the target; the outline reports against it
web/src/features/intake/   two questions
web/src/features/editor/   slide count vs target at the outline gate
```

### Two questions at intake

*How long is your talk?* and *roughly how many slides?* Both optional, both with a sensible default derived from the other — a five-minute talk suggests a handful of slides, and a stated slide count implies a length. Neither is a hard constraint on the user; both are hard inputs to the Director.

**Talk length is the more useful of the two** and should be asked first, because it is the number a presenter actually knows. Nobody walks into a room knowing they need eleven slides. They know they have fifteen minutes.

### The Director plans to it

`targetSlides` becomes an input to the outline prompt and a bound the outline is validated against. This is a genuine change in what the Director optimises: today it produces however many beats the narrative wants, within a schema range that was chosen to stop runaway output rather than to fit a room.

The schema's `3–12` stays as the outer safety bound. The target sits inside it, and a target outside the bound is a validation failure at intake with a plain message, not a silent clamp.

### The outline gate reports against the target

The gate already lets the user approve, reorder and delete. It now also shows the count against the target and the implied pace — *"11 slides, ~15 minutes, about 80 seconds each"*. That single line is what makes the number mean something; a raw count does not.

Adding or deleting a slide updates it live. **Do not block the user from exceeding their own target** — it is their talk, and a tool that argues with the person about their own timing is worse than one that stays quiet. Report, do not enforce.

---

## Verify

**The gate** — green.

- [ ] A Brief carries talk length and target slide count, both optional
- [ ] The Director produces an outline at the target ±1 for all five golden briefs
- [ ] A target outside the schema bound fails at intake with a readable message, and is never silently clamped
- [ ] Adding and deleting slides at the outline gate updates the count and pace live
- [ ] Exceeding the target is reported and never blocked
- [ ] The pace line is right: count, minutes, seconds per slide
- [ ] [19](19-presenter-view.md)'s timer reads its target from this field and not from a second source

**Human**

- [ ] Generate the same brief at 5 minutes and at 20 minutes. **The two decks should differ in structure, not merely in count** — if the 20-minute version is the 5-minute version with padding, the Director is treating the target as a stopping condition instead of a plan, and that is the defect this phase exists to prevent

---

## Skipped

| Not built | Trigger |
|---|---|
| Per-slide time allocation | [19](19-presenter-view.md)'s pace-against-target covers the real need. Per-slide budgets are rehearsal-mode work |
| Automatic splitting or merging to hit a number | Same reason auto-splitting is refused in [10](10-slides-mode.md) — a machine-chosen break lands somewhere narratively stupid |
| Trimming an over-length deck automatically | Never. It is their talk. Report the pace and let them cut |
| Speaking-rate personalisation | v3+, and only with rehearsal data. A guessed words-per-minute is worse than an honest average |

---

## Exit gate

- [ ] Intake asks talk length and slide count; both optional, both flow into the Brief
- [ ] The Director plans to the target and hits it ±1 across the golden briefs
- [ ] The outline gate shows count, target and pace, live
- [ ] Over-target is reported, never enforced
- [ ] A 5-minute and a 20-minute deck from one brief differ structurally
- [ ] The gate is green
