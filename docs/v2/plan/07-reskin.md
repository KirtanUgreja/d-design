# Phase 07 — Reskin

> The headline feature. Same experience, different art direction, one click. It is safe because of the snapshot and the overflow report; it is loved because of the transition, which is the next phase.

**Depends on:** [05](05-budgets-in-the-pipeline.md), [06](06-version-history.md) · **Blocks:** [08](08-reskin-transition.md), [09](09-visual-verification.md), [10](10-slides-mode.md) · **Spec step:** 7

---

## Search

**Read first**

- [../transformations.md](../transformations.md) → "Reskin", including "The overflow problem" and "Guarantee"
- [../spec.md](../spec.md) → Locked decisions, the `AD scope: tokens only` row. **That is not a simplification, it is the feature**

**Grep for**

- `api/features/edit/edit.py` — the element-scoped edit. Shorten-with-AI is the same seam call with a different instruction, and writing a second one is the duplication this codebase measures
- `api/features/generation/budgets.py` — from phase 05. The overflow check is that validation run over a whole tree instead of one scene
- `web/src/features/editor/patch.ts` — `applyPatch`, the one validation site. A shortened headline is an ordinary patch and goes through it
- `api/features/history/__init__.py` — snapshot before, from phase 06

**Verify externally** — nothing.

---

## Make

```
api/schema/overflow.py           OverflowReport, OverflowEntry
api/features/reskin/
  __init__.py                    reskin, checkOverflow, shorten
  test_reskin.py
api/routes/reskin.py
web/src/features/reskin/
  reskin.ts                      the client
  overflow-banner.tsx            the banner, the review list, shorten
  ad-picker.tsx                  shared with the outline gate
```

### The mechanics

```
1. snapshot current state              → history, trigger: 'reskin'
2. swap { artDirection, version }
3. re-validate every block against the target AD's budgets
4. produce OverflowReport
5. animate the transition                (phase 08)
6. surface overflow, if any
```

Steps 1 and 3 are what make this safe. Step 5 is what makes it loved. **Do not reorder 1.**

### The overflow report

```
OverflowReport { entries: { sceneId, blockId, field, current, budget }[] }
```

A 58-character headline is elegant in `editorial-light` and catastrophic in `bold-brutalist`, where the budget is 34.

**A character count is not the whole check**, and this is the honest limit of this phase. It catches copy that exceeds a budget — the countable half. The other half is not countable: a headline that fits 34 characters and still collides with a stat block, text that lands on the busy part of an image, a scene that reflows into something nobody would ship. Those are visual, and phase 09 is what sees them. The banner is built here so that phase 09 has somewhere to put its findings, and **the user never needs to know which system found what**.

### Nothing is rewritten automatically

The reskin completes. Overflowing blocks render with a visible flag. The user gets a banner:

> *3 blocks are too long for Bold Brutalist.* → `Review` · `Shorten all with AI`

Each offers a one-click shorten that **shows the proposed text before applying**.

Auto-rewriting would be seamless, and it would silently alter marketing copy someone got legal approval on. For this wedge that is not a bug, it is a lawsuit. **The overflow flag is deliberately visible and deliberately annoying**, and any later change that makes it quieter is a change to the product's position, not to its UI.

Shortening is the edit seam with a budget in the instruction, and its output goes through `applyPatch` like every other patch. One validation site, one undo stack.

### The guarantee, and the thing that could break it

**Any art direction applies to any experience, always.** That holds only because art directions are tokens-only. The instant an art direction can add a layout, reskin becomes "works unless the target lacks the source's layout", and the feature dies as a promise rather than as a bug.

Rule 12 has no compiler behind it. What it gets instead is a grep in `scripts/checks/invariants.sh`: **no file under `renderer/` may reference an art direction id.** That is a weak approximation of a strong rule, and it is worth having precisely because the strong version cannot be automated.

---

## Verify

**The gate** — green.

**Reskin**

- [ ] Reskinning takes a snapshot first, labelled `reskin`, and restoring it returns the tree byte-identically
- [ ] The scene tree is **unchanged** by a reskin. Assert byte-equality on `scenes` — this is the claim, and if a reskin can touch content then content and styling were never separate
- [ ] Every one of 3 art directions × 5 golden experiences reskins without a crash
- [ ] Reskinning to an art direction whose version does not resolve fails closed, before the snapshot

**Overflow**

- [ ] `editorial-light` → `bold-brutalist` on a long-headline experience produces entries naming the scene, block, field, current length and budget
- [ ] `bold-brutalist` → `editorial-light` produces none. Reskinning to a roomier budget cannot overflow
- [ ] An overflowing block still renders, with a flag. Nothing is clipped and nothing is hidden
- [ ] Shorten produces text within budget, shows it before applying, and applies it as an ordinary patch
- [ ] Declining a shorten leaves the block exactly as it was, flag and all

**Tokens-only**

- [ ] `scripts/checks/invariants.sh` fails if any file under `renderer/` names an art direction id
- [ ] The reskin matrix renders with no art-direction-specific code path. Reviewed by reading, because a grep cannot see a branch on a token value

**Security** ([../../security/testing.md](../../security/testing.md))

- [ ] Reskinning another user's experience is refused — through the route, with a valid session belonging to someone else
- [ ] Shorten is a model call on user content, so the injection corpus runs through it: a payload in a headline must not make the shortened text carry an instruction, a URL, or a system-prompt fragment
- [ ] Shorten's output is parsed at the boundary and re-validated against the budget. A model asked to shorten can return something longer

**Human**

- [ ] Reskin something you like. If the result is worse and you cannot say why, that is phase 09's job and worth writing down now as a case for it

---

## Skipped

| Not built | Trigger |
|---|---|
| The transition | [08](08-reskin-transition.md). This phase swaps state; the next makes it a thing people screenshot |
| Visual overflow detection | [09](09-visual-verification.md). The banner is built here with room for its findings |
| Compare view | [11](11-range.md). A bet, and the first thing to cut |
| Reskinning a published page in place | Never automatically. A live launch page changes when its owner publishes, not when they experiment |
| Bulk reskin across experiences | When someone has enough experiences to want it, which is a v3 problem |

---

## Exit gate

- [ ] Reskin snapshots, swaps, re-validates, and reports — in that order
- [ ] The scene tree is byte-identical across a reskin
- [ ] 3 art directions × 5 golden experiences all reskin cleanly
- [ ] Overflow is reported per block, rendered visibly, and never auto-corrected
- [ ] Shorten-with-AI previews before applying and goes through the one patch path
- [ ] The invariants script refuses an art-direction id under `renderer/`
- [ ] Cross-tenant reskin refused; the injection corpus passes through shorten
- [ ] The gate is green
