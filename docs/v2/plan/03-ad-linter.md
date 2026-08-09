# Phase 03 — The AD linter

> One validator, two purposes. It refuses art directions that are unreadable, and it refuses art directions that are an injection. Building it as one thing is what stops the security half being deferred as separate work.

**Depends on:** [01](01-ad-format.md), [14](14-texture-without-gradient.md) · **Blocks:** [04](04-three-art-directions.md) · **Spec step:** 3

> **Done, 2026-08-09.** One validator, both halves. It found three real defects in `cinematic-dark` — all of them clearing WCAG 2.2 AA and failing APCA — and the art direction was fixed rather than the gate relaxed. `editorial-light` passed unchanged. What the phase found is under "What actually happened".

> **[14](14-texture-without-gradient.md) lands first and adds four rules to this one.** The no-ramp and no-bloom checks, the OKLCH saturation bound, and the ground-cycle contrast check are all in [../art-direction-system.md](../art-direction-system.md) → "The AD linter". They are the same kind of rule as the rest — a bound with a reason, refused as a hard failure — and building them here rather than as a follow-up is what keeps one validator instead of two.

---

## Search

**Read first**

- [../art-direction-system.md](../art-direction-system.md) → "The AD linter", the whole rules table, and "The linter is also the injection boundary"
- [../../security/content-and-web.md](../../security/content-and-web.md) → "CSS injection via art-direction tokens" — **this is the newest attack surface in the product and the one most likely to be missed**
- [../../coderules/README.md](../../coderules/README.md) → rule 10, anything that grants fails closed. A linter is a thing that grants

**Grep for**

- `web/src/features/art-direction/color.ts` — `contrastRatio`, `relativeLuminance`, `parseHex`, `lighten`, `darken`. WCAG 2 contrast already exists and is already correct; APCA is what is new
- `web/src/features/art-direction/to-css-vars.ts` — the single choke point. The grammar validator runs on the token record *before* this, never on the string it emits
- `api/features/assets/sanitize_svg.py` — the shape to copy. An allowlist over a parser, hard failure on anything outside it, and a cap on how much work a hostile input can cause

**Verify externally**

- The APCA `Lc` thresholds and the current algorithm revision. It is a WCAG 3.0 draft, so pin the revision you implemented in a comment — "APCA" without a revision is not a specification
- That `color-mix()` and relative colour syntax are still where [../spec.md](../spec.md) → "Platform reality" says they are. The linter has to evaluate the *derived* colours, not just the authored ones

---

## Make

```
api/features/art_direction/
  lint.py                  the rules, in one place
  lint_contrast.py         WCAG 2.2 AA and APCA, both
  lint_grammar.py          the injection boundary
  test_lint.py             including the deliberately broken AD
api/schema/art_direction.py   LintFinding, LintReport
```

### It runs in `api`, not in `web`

The linter is the thing standing between a user-authored token value and a published page. It runs where the write happens, on the server, at the point of save — not in the form component that is a convenience for the person typing.

`web` may run the same rules for live feedback. It may not be the only place they run.

### Design rules — hard failures, all of them

| Rule | Bound |
|---|---|
| Text contrast, compliance floor | `ink`/`bg` and `ink-muted`/`bg` ≥ 4.5:1; large display ≥ 3:1 (WCAG 2.2 AA) |
| Text contrast, perceptual gate | body `Lc ≥ 75`; large display `Lc ≥ 60`; incidental `Lc ≥ 45` (APCA) |
| Accent contrast | both of the above, wherever accent carries text |
| Type scale monotonic | `hero > section > lead > normal ≥ muted > eyebrow` |
| Scale range | `hero / normal` between 2.5 and 8 |
| Line height | display ≥ 0.85; body between 1.4 and 1.8 |
| Measure | between 45ch and 80ch |
| Spacing scale | strictly increasing, adjacent ratios between 1.2 and 2.0 |
| Motion duration | between 120ms and 1400ms |
| Reduced motion | present, opacity-only, ≤ 300ms |
| Budgets | headline between 20 and 120 characters |

**An AD that fails cannot be saved.** Not a warning, not a badge — the save is refused with the findings. Same philosophy as scene validation: make bad output unrepresentable rather than asking nicely.

Every bound has a reason. `hero/normal < 2.5` produces a design with no hierarchy; `> 8` produces a headline with orphaned body text. Body line height below 1.4 fails readability; above 1.8 the paragraph stops cohering. These are not taste — they are the range outside which the renderer produces something nobody would defend.

### Why two contrast standards and not one

They answer different questions, and running only one of them fails in a different direction each way.

**WCAG 2.2 AA is the legal floor.** It is what an enterprise accessibility audit runs and what a procurement checklist cites. You cannot ship below it regardless of whether it measures the right thing.

**APCA is the quality gate,** and it is the one that can evaluate the flagship art direction at all. WCAG 2's ratio is polarity-blind — it scores light-on-dark and dark-on-light identically when the eye does not perceive them the same way, which is exactly why dark themes routinely pass 4.5:1 on paper and read muddy. `cinematic-dark` is dark by definition, so the standard everyone reaches for first is the one least able to judge it.

Passing only WCAG 2 yields muddy dark themes that clear the audit. Passing only APCA yields a beautiful page that fails a customer's compliance review. **When they disagree, APCA is almost always the one telling you something true about `cinematic-dark`** — and the response is to fix the art direction, not to relax the gate.

### Grammar rules — the injection boundary

**This is the security half, and it enters with this release because v2 is the first version where a token value is not written by you.**

A token value becomes a CSS custom property, and art directions require `style-src 'unsafe-inline'`. An unvalidated token is therefore a script-adjacent injection point on a page carrying a customer's brand.

**Every value is parsed by type and re-serialized. Nothing is passed through as a string.**

| Token kind | Validation |
|---|---|
| Colours | Parsed into a colour object, re-serialized. Never the original string |
| Numbers | Numeric, range-checked against the bounds above |
| Enums | Matched against known values, rejected otherwise |
| **Font families** | **Selected from a curated registry by id. Never a user-supplied string** |
| Easing curves | `cubic-bezier(a,b,c,d)` with numeric components, or a known keyword |

Rejected outright: `url(`, `expression(`, `@import`, `</style`, `javascript:`, backslash escapes, and any character outside the expected grammar for that token type.

**Rejected, not sanitized.** Sanitizing means guessing what the author meant, and a guess about a value that is about to become CSS on someone else's launch page is not a guess worth making. The v1 codebase already has the shape: `sanitize_svg.py` is an allowlist that drops what it does not recognise, and this is stricter still because a token has exactly one legal form.

Font families deserve the emphasis. A family name is the most natural-looking free-text token in the system and the one most likely to be waved through — which is why they are ids into a registry that maps to a vetted family and file. v1's `FONT_REGISTRY` is already keyed that way, so this is enforcement of an existing shape rather than a new constraint.

### Derived colours are linted too

`--accent-hover: oklch(from var(--accent) calc(l + 0.08) c h)` is a colour that no one authored and that carries text. Compute the derivations and lint them. An art direction whose authored accent passes and whose hover state does not is an art direction that fails.

---

## Verify

**The gate** — green.

**Design rules**

- [x] A deliberately broken AD — 2:1 contrast, a section larger than its hero, a 120ch measure, a 6-character headline budget — fails **every** rule it violates, and the report names each one. One record breaking everything at once, because separately-broken records test the rules and not the *report*, and the report is the feature
- [x] An AD that passes WCAG 2.2 AA and scores in the thirties on dark is **rejected**, with the fixture asserting it clears the legal floor on *both* grounds first — so the test cannot pass for the wrong reason
- [x] Both shipped art directions pass every rule. `cinematic-dark` did not, and `cinematic-dark` was fixed — see below
- [x] Derived colours are linted: `bgElevated` as a second ground, and the CTA's `bg`-on-`accent` pair, which no type role describes because the colours are the other way round

**Grammar** ([../../security/testing.md](../../security/testing.md))

- [x] A colour token of `red; } body { background: url(//evil` is rejected — **at the parse**, because a colour is three floats and there is no field a string can arrive in
- [x] A font family given as a free string is rejected — the field is a `Literal` of vetted names, so an unvetted one has no representation and does not compile on the TypeScript side either
- [x] Each of `url(`, `expression(`, `@import`, `</style`, `javascript:`, a backslash escape, and a bare `{`/`}`/`;` is rejected in the one field with room for a string
- [ ] **Not applicable as written — easing curves are not in this record.** See below
- [x] A value that passes the grammar and is then emitted by `to-css-vars` produces exactly the re-serialized form: every emitted colour matches `rgb(r g b[ / a%])` and nothing else, asserted on the emitted CSS
- [x] A hostile DTCG document is refused by `from_document`, and the test proves the *linter* refused it by asserting the same record parses cleanly first

**Fails closed** ([../../security/testing.md](../../security/testing.md) → "Failing closed")

- [x] The linter raising an unexpected exception refuses the save — the `except Exception` lives inside `lint_art_direction`, where the only thing it can become is a finding
- [x] An AD saved by a route that skips the linter is impossible — there is no save route at all, and the one path an art direction can enter by (`from_document`) lints

**Human**

- [x] The findings read as sentences with the number, the bound and the consequence in them, and a test asserts they do — a message of twelve words or fewer fails it

---

## Skipped

| Not built | Trigger |
|---|---|
| A visual critic | [09](09-visual-verification.md). The linter judges tokens; the critic judges pages. Neither has an opinion on beauty |
| Auto-correcting a failing AD | Never for grammar. For design rules, the four control axes in v3 derive values that pass by construction, which is a better answer than correcting values a user chose |
| Linting user-authored ADs in the browser as they type | Whenever user authoring ships. The rules live in `api` and can be exposed; the point is that the server never trusts the client's verdict |
| A separate security scanner | The whole argument of this phase is that there is one validator. A second one is the first one being skipped |

---

## Exit gate

- [x] Every rule in the table fails a deliberately broken AD, and the report names each
- [x] WCAG 2.2 AA and APCA both run, both are hard, and the AD that passes one and fails the other is rejected
- [x] Every token value is parsed and re-serialized; hostile values are rejected rather than sanitized
- [x] Font families are ids into the registry, and a free string is refused
- [x] The linter fails closed on its own exception
- [x] Both shipped art directions pass, and every change made to make them pass is a change to the art direction
- [x] The gate is green

---

## What actually happened

**The linter found three real defects, all of them in the flagship, and all of them invisible to WCAG.**

| Pair | WCAG 2.2 | APCA | Needed |
|---|---|---|---|
| `muted` body text on `bg` | 7.14:1 ✅ | Lc 48.0 | Lc 75 |
| `eyebrow` on `bg` | 4.94:1 ✅ | Lc 33.9 | Lc 75 |
| CTA label (`bg`) on the `accent` fill | 11.09:1 ✅ | Lc 70.6 | Lc 75 |

`editorial-light` passed every rule unchanged. That contrast is the phase's argument made concrete rather than asserted: WCAG 2's ratio is polarity-blind, so the light direction and the dark one score alike on paper, and only the perceptual gate can tell you which of them is actually muddy.

**The fix was three token changes, and one of them is a finding worth more than the number.** `inkMuted` went from 0.62 to 0.85 alpha, the eyebrow moved from `inkFaint` to `inkMuted`, and the accent lightened from `#f4b740` to `#fcca6d`. The general fact underneath: **on a near-black ground, opacity is not a viable hierarchy mechanism.** The alpha range that clears Lc 75 against `#08090b` is 0.83–1.0 — room for one step below full ink, not three — so a design that wanted `ink`/`inkMuted`/`inkFaint` as three legible tiers could not have them. What carries the hierarchy instead is size, weight, case and tracking, which the type scale was already doing. `inkFaint` stays in the palette at 0.5 and is simply no longer a text colour.

**The phase-01 baseline was not regenerated.** `art_direction_css_v1.json` still holds what the v1 constants emitted; the test now carries an explicit table of the three variables that moved, with their before and after and the reason. A variable that changes *without* being listed still fails — regenerating a baseline is how "no pixel moved" quietly becomes "no pixel moved that anyone checked".

**Most of the grammar half is unreachable, and the tests say so.** Colours are three floats, lengths are a number and a unit enum, easings are four floats, font families are a `Literal`. `red; } body { background: url(//evil` fails the *parse*; there is no field it can arrive in. The grammar module exists anyway, and every test names which layer refused the value — because "a control that passes because a different control caught it is a control you have not tested". The types are the defence; the linter is the assertion that they still are, and the thing that fires the day someone widens a field.

**Font families became a `Literal` rather than a validated string**, which is a strictly stronger control and the one the phase actually asked for. It generates into a Zod enum and a TypeScript union, so `web`'s `FONT_REGISTRY` cannot name a family the schema does not — the two lists are now one list, checked by the compiler rather than by a test that hopes.

**Two bugs found while building it.**

- Migration 0011 seeds from `seed.py`, so a database that ran it yesterday keeps yesterday's values while a fresh one gets today's. Every future change to the seed needs a re-sync revision; 0013 is the first, and it explains why the row is updated in place rather than inserted as a version 2 (nothing has been published, and a published page freezes its own record anyway).
- 0013's first draft passed `model_dump_json` into a `JSONB` bindparam, which encodes the string again and stores a jsonb *scalar string*. The migration reported success and the rows were unreadable. Caught by looking at a row rather than by anything failing — which is what that class of bug does, and the reason `art_direction_data._as_record` parses on the way out instead of trusting the column.

### Where the phase's checklist did not match the code

**"An easing curve of `cubic-bezier(0,0,1,1); animation: x` is rejected."** There is no easing in an art direction. Phase 02 moved motion to its own table, and an easing there is four floats — a string has nowhere to be. The rule the checkbox is reaching for is enforced by the type, and `lint_motion_vocabulary` bounds the numbers around it.

**`Lc 45` for "incidental/disabled" was not used.** The three roles it could have applied to are the *smallest* text in the system, and APCA asks for more contrast as text gets smaller, not less. Applying the loosest threshold to the smallest role would invert the standard being applied, so `eyebrow` is judged as body — which is already generous for 13px — and the tier is left for a genuinely decorative role when one exists.

### Deferred, and named rather than quietly dropped

**Live linting in the browser.** The rules live in `api` and the phase already lists this as later work. Nothing here blocks it, and the important half — that the server never trusts the client's verdict — is true by construction, since there is no client path to a save.

**The ground-cycle rule's inverted-scene half.** `bg` and `bgElevated` are both checked, which is every ground that exists today. Inverted scenes arrive in phase [17](17-composition.md), and the check extends by adding a ground to the list rather than by growing a rule.
