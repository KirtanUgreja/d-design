# Phase 05 — Budgets in the pipeline

> The art direction is chosen before Build, not after. Generating for a 34-character budget produces genuinely different copy — not the same copy truncated.

**Depends on:** [04](04-three-art-directions.md) · **Blocks:** [07](07-reskin.md) · **Spec step:** pipeline delta

> **Three changes from the presentation pivot** ([../presentation.md](../presentation.md), 2026-08-10). None of them changes this phase's mechanism; all three change what it is budgeting.
>
> **A budget is now bounded by a stage, not by taste.** A character cap was a design judgement about elegance on a page. On a slide there is a hard ceiling — content either fits the frame at 4:3 through 21:9 or it does not — so [18](18-presentation-frame.md)'s preflight is the ground truth a budget should be calibrated against. **The budget's job is to make overflow rare; the preflight's job is to catch it.** If a budget passes copy the preflight then rejects, the budget is wrong and this is where to fix it.
>
> **Speaker notes get a budget too.** [19](19-presenter-view.md) adds AI-drafted notes, and a note nobody can scan in the two seconds before advancing is not a note. It is measured by what fits presenter view without scrolling, and it belongs in `budgets` alongside every other text field rather than in a constant somewhere in `present/`.
>
> **The art direction may be *generated* rather than chosen.** [21](21-art-direction-engine.md) means the AD picked at the outline gate can be one of three made for this deck. That changes nothing here structurally — a generated AD carries `budgets` like any other — but it does mean this phase must not assume the AD id is one of three known values. If anything in the Build path switches on `ArtDirectionId`, it breaks at 21.

---

## Search

**Read first**

- [../spec.md](../spec.md) → "Pipeline delta" — three changes to what the four phases receive, and none to their shape
- [../../v1/ai-pipeline.md](../../v1/ai-pipeline.md) → Phase 3, Build. The request shape this phase adds one field to
- [../../v1/plan/06-model-seam-and-build.md](../../v1/plan/06-model-seam-and-build.md) — how caps reach the prompt today, and the truncation defect that came from getting this wrong once already

**Grep for**

- `api/features/generation/prompts/build.py` — `_limits_section` and `_max_length`, which derive the caps **from Pydantic** rather than restating them. That derivation is the thing to preserve; only its source changes
- `api/schema/scene.py` — the `max_length` on every text field. These are v1's universal caps and they become `cinematic-dark`'s budgets
- `api/features/edit/edit.py` — an edit produces props that must be re-validated against the current budget, which is the third entry point to one mechanism
- `api/ai/complete.py` — `_UNSUPPORTED_STRICT_KEYWORDS`. `maxLength` is stripped from the structured-output schema and enforced by Pydantic afterwards; **per-AD budgets do not change that** and must not reintroduce it

**Verify externally** — nothing. This is prompt and validation plumbing against art directions that already exist.

---

## Make

```
api/features/generation/
  budgets.py               ContentBudgets -> prompt section + validation
  prompts/build.py         reads the AD's budgets, not the schema's caps
  build.py                 takes the ArtDirection reference
api/features/director/
  prompts/director.py      + the AD's maxBlocksPerScene hint
web/src/features/director/
  outline-editor.tsx       + the art-direction picker
```

### The picker moves into the outline gate

Budgets are per art direction, so Build cannot write copy until it knows which art direction it is writing for. The picker therefore sits **in the outline-approval gate**, defaulting to `cinematic-dark`.

That placement is not a UI convenience. It is the point at which the choice becomes cheap: choosing before Build costs nothing, and choosing after Build is a reskin with an overflow report attached. Both paths exist and the gate is the free one.

[../../design/app.md](../../design/app.md) already reserves the picker's toolbar space in the editor. Retrofitting it into a menu is how it becomes a setting instead of the feature it is.

### Where the caps come from now

v1's caps live on the Pydantic model as `max_length` and are read out of it into the prompt — one source, derived twice, which is why the two cannot drift.

That property has to survive the move. The budgets now come from the art direction, so:

- **The prompt section** is generated from `artDirection.budgets`, not from the schema
- **The runtime validation** is a check against the same budgets, applied after the schema parse
- **The schema's `max_length` stays**, as the widest budget any art direction may declare — a floor under the whole system, so a bug in budget resolution cannot produce a 400-character headline

Three enforcement points, one number, and the schema is the backstop rather than the source. That last part is what stops a missing budget failing open.

### Density is a Director hint, not a Build cap

`bold-brutalist` with six blocks in a scene is unreadable at any character budget. Each art direction declares a `maxBlocksPerScene` hint, and it goes to the **Director**, which assigns layouts — not to Build, which fills them.

It is a hint in the prompt and a validation bound on the outline, in that order. Wording it as a hard rule to the model and then not checking it is the failure mode this codebase has already met once.

### Edit re-validates against the current budget

Editing a headline into overflow flags it exactly as reskin does. **One mechanism, three entry points** — generation, edit, reskin — and if the third one needs its own overflow concept, one of the three designs is wrong.

The edit path is the one where this is most tempting to skip, because the user typed the text themselves and it feels rude to flag it. Flag it. The alternative is a page that looks broken on publish and gives no reason.

---

## Verify

**The gate** — green.

**Budgets**

- [ ] The build prompt for `bold-brutalist` states a 34-character headline limit, and the prompt for `editorial-light` states its own. Assert on the rendered prompt, not on the config
- [ ] A golden brief built under `bold-brutalist` produces **materially shorter headlines** than the same brief under `editorial-light`. This is the assertion that proves the feature: same brief, different copy, because the art direction was known before the words were written
- [ ] A scene whose text exceeds the current budget fails validation with a finding naming the field, the length, and the budget
- [ ] The schema's `max_length` still refuses a value wider than any art direction's budget, even if budget resolution returns nothing

**The Director**

- [ ] `maxBlocksPerScene` reaches the Director prompt and bounds the outline it returns
- [ ] An outline exceeding the hint is refused rather than silently accepted

**Edit**

- [ ] An element-scoped edit that overflows the current budget is flagged, and the flag is the same shape reskin produces
- [ ] The edit is still applied. Flagging is not refusing — the user's own words are theirs

**Pipeline regression**

- [ ] The five golden briefs still produce 100% schema-valid scenes after at most one repair, under `cinematic-dark`. The budget change must not reintroduce the truncation defect, and `maxLength` must still be stripped from the structured-output schema
- [ ] The injection corpus still passes all four structural assertions under all three art directions

**Human**

- [ ] Read a `bold-brutalist` build next to a `cinematic-dark` one. If the copy is the same sentence with words removed, the budget reached the validator but not the prompt

---

## Skipped

| Not built | Trigger |
|---|---|
| Regenerating copy on reskin | [07](07-reskin.md), and even there it is offered, never automatic. Rewriting approved marketing copy silently is the one thing this wedge cannot do |
| Per-locale budgets | v3's transcreation, which translates *within* a budget rather than translating and then fixing overflow ([../../v3/localization.md](../../v3/localization.md)) |
| Budgets on the outline's `beat` | The beat is never rendered. Its length is a prompt-engineering concern, not a design one |
| A budget for `Slot` | A Slot has no text field the art direction sets. It is sandboxed content and it takes the sandbox's rules, not the budget's |

---

## Exit gate

- [ ] The art-direction picker is in the outline gate and defaults to `cinematic-dark`
- [ ] Build receives the chosen art direction's budgets, in the prompt and in validation
- [ ] The same brief under two art directions produces genuinely different copy
- [ ] `maxBlocksPerScene` reaches the Director and bounds its outline
- [ ] Edits re-validate against the current budget and flag rather than refuse
- [ ] The golden briefs and the injection corpus still pass, under all three art directions
- [ ] The gate is green
