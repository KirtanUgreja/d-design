# Phase 03 — The AD linter

> One validator, two purposes. It refuses art directions that are unreadable, and it refuses art directions that are an injection. Building it as one thing is what stops the security half being deferred as separate work.

**Depends on:** [01](01-ad-format.md), [14](14-texture-without-gradient.md) · **Blocks:** [04](04-three-art-directions.md) · **Spec step:** 3

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

- [ ] A deliberately broken AD — 2:1 contrast, non-monotonic scale, 4-second durations, a 6-character headline budget — fails **every** rule it violates, and the report names each one
- [ ] An AD that passes WCAG 2.2 AA at 4.6:1 and scores `Lc 55` on dark is **rejected**. If it passes, the APCA gate is not wired, and that exact combination is what muddy dark themes look like
- [ ] Both shipped art directions pass every rule. If `cinematic-dark` fails APCA, **fix `cinematic-dark`** — that is the finding, and relaxing the gate to accommodate it is how the gate becomes decorative
- [ ] Derived colours are linted, not just authored ones

**Grammar** ([../../security/testing.md](../../security/testing.md))

- [ ] A colour token of `red; } body { background: url(//evil` is rejected as a hard failure
- [ ] A font family given as a free string is rejected — the field takes an id
- [ ] Each of `url(`, `expression(`, `@import`, `</style`, `javascript:`, and a backslash escape is rejected in every token kind that could carry it
- [ ] An easing curve of `cubic-bezier(0,0,1,1); animation: x` is rejected
- [ ] A value that passes the grammar and is then emitted by `to-css-vars` produces exactly the re-serialized form, never the input string. Assert on the emitted CSS, because that is the thing that ships
- [ ] A DTCG file uploaded with a hostile value is rejected at the Zod parse or by the linter, and the test says which — a control that passes because a different control caught it is a control you have not tested

**Fails closed** ([../../security/testing.md](../../security/testing.md) → "Failing closed")

- [ ] The linter raising an unexpected exception refuses the save. A `catch` returning "no findings" is a vulnerability, not error handling
- [ ] An AD saved by a route that skips the linter is impossible — there is one save path, and it lints

**Human**

- [ ] Read the findings for the deliberately broken AD as a person would. A linter that says `SCALE_RANGE_VIOLATION` teaches nobody anything; the message is part of the feature

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

- [ ] Every rule in the table fails a deliberately broken AD, and the report names each
- [ ] WCAG 2.2 AA and APCA both run, both are hard, and the AD that passes one and fails the other is rejected
- [ ] Every token value is parsed and re-serialized; hostile values are rejected rather than sanitized
- [ ] Font families are ids into the registry, and a free string is refused
- [ ] The linter fails closed on its own exception
- [ ] Both shipped art directions pass, and any change made to make them pass is a change to the art direction
- [ ] The gate is green
