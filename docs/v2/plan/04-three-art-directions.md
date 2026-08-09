# Phase 04 — Three art directions

> `editorial-light` moves into the format. `bold-brutalist` breaks it. This is the phase the whole build order is arranged around, and needing a format refactor here is the process working rather than failing.

**Depends on:** [01](01-ad-format.md), [02](02-motion-axis.md), [03](03-ad-linter.md) · **Blocks:** [05](05-budgets-in-the-pipeline.md), [06](06-version-history.md), [12](12-primitives.md) · **Spec step:** 4, 5

---

## Search

**Read first**

- [../art-direction-system.md](../art-direction-system.md) → "The three hand-authored art directions" — the sketched values for both
- [../../v1/art-direction.md](../../v1/art-direction.md) → "The result" — what `editorial-light` already is, and the seven things it cost. **This phase does not re-derive them**
- [../../design/brand.md](../../design/brand.md) → "The collision this decision walks into" — three constraints on `editorial-light` that are not this phase's to relitigate
- [../../design/principles.md](../../design/principles.md) → principle 5, the banned list. `bold-brutalist` is the art direction most likely to reach for a gradient of two violets and call it a statement

**Grep for**

- `web/src/features/art-direction/editorial-light.ts` — it exists, it is authored, and its comment block records why each number is what it is. Migrating it means moving values, not re-choosing them
- `web/src/features/renderer/blocks/` — every primitive. `bold-brutalist` is the stress test, and the ones that break will be `Stat`, `Quote`, `List` and `AbstractVisual`, in that order
- `web/src/features/renderer/tokens.ts` — `VISUAL_BLEND`, `visualOpacity`, `COLOR_VAR`. Three values that used to be hardcoded and became tokens when art direction #2 arrived. If `bold-brutalist` finds a fourth, it belongs here in exactly the same way

**Verify externally**

- Two open-licence display faces on Fontsource that are not Fraunces, not Newsreader, and not whatever our own chrome uses. `bold-brutalist` needs a face with real weight at 12vw, which is a narrower set than it sounds

---

## Make

```
api/features/art_direction/
  seeds/cinematic_dark.tokens.json
  seeds/editorial_light.tokens.json      migrated from the v1 constants
  seeds/bold_brutalist.tokens.json       new
api/migrations/versions/                 seed all three at version 1
web/src/app/globals.css                  + bold-brutalist's two families
docs/coderules/dependencies.md           + the ledger lines
```

### A doc conflict to resolve before authoring `editorial-light`

[../art-direction-system.md](../art-direction-system.md) sketches `editorial-light`'s ground as `#FBFAF8`, **warm off-white**. [../../design/brand.md](../../design/brand.md) requires the opposite: our own chrome is warm paper, so `editorial-light` must be *cool or bright white*, "not both warm".

v1 resolved this toward `brand.md` and shipped a cool `#fbfcfd`. **Keep that resolution and treat the sketch as superseded**, because the constraint has a reason that outlives a colour preference: if our wall and art direction #2 converge, the site stops looking like a neutral wall and starts looking like it is wearing one of the three things we sell.

The other two constraints from `brand.md` are already satisfied by the v1 authoring and should be re-checked rather than re-decided: a display face different from both `cinematic-dark`'s and our chrome's, and an accent much louder than our chrome's two-appearances-per-screen rule.

**The check is concrete, and it is a human one:** put `editorial-light` on the editor canvas with the app chrome around it, and a stranger must be able to tell which pixels are the product and which are the artifact. If they cannot, **the art direction moves**, not the chrome — changing a hand-authored AD costs a day, changing an identity that has leaked into every route and string costs an audit.

### `bold-brutalist` — the one that breaks things

```
--bg           brand.primary at full strength   (allowBrandBackground: true)
--ink          computed black or white, whichever passes both contrast gates
type.hero      clamp(4rem, 12vw, 14rem), tracking -0.05em, weight 800
rhythm         dense — roughly half cinematic-dark's scene padding
budgets.headline  34
texture        none, but hard-edged colour blocking at the layout level
defaultMotion  mechanical-snap … which does not exist yet
```

Three things in that sketch are traps, and naming them now is cheaper than finding them at render time.

**`--bg` from the brand colour means the ink is computed, not authored.** `allowBrandBackground` exists because of this art direction, and the linter's contrast rules now run against a background that is not known until a brand kit is attached. That is a real change to when linting happens: an art direction is lintable on its own, and an art direction *plus a brand* is a second thing that must also be lintable. Build the second check; it is the one that catches a customer's magenta making every headline illegible.

**`defaultMotion: mechanical-snap` is a forward reference.** That vocabulary is phase 11. Point `bold-brutalist` at `cinematic-slow` for now with a `ponytail:` naming the swap, or the seed is a broken foreign key wearing a design decision.

**"Hard-edged colour blocking at the layout level" is the sentence to be most suspicious of in all of v2.** Layout belongs to the scene, not to the art direction — rule 12, and the thing reskin's whole promise rests on. Whatever this turns into, it is a *token* the existing layouts read: a block-level surface colour, a rule weight, an edge treatment. If it cannot be expressed that way, the honest outcome is that `bold-brutalist` does not get it, and that outcome is recorded rather than worked around.

### Expect the format to be wrong, and budget for it

Two points define a line, and you will mistake AD-specific tokens for universal ones. **The third art direction is what tells you the format is right**, which is why the spec's Risk 1 says to budget for a format refactor between AD #2 and AD #3 and to treat needing one as the process working.

The v1 exercise found four values held globally because "global" and "cinematic-dark's" were indistinguishable. Expect `bold-brutalist` to find more. Each one follows the same path: **a hardcoded value in the renderer becomes a token in the format**, which is a token read and not a branch.

---

## Verify

**The gate** — green, and the linter passes all three art directions.

**The hard gate for this phase**

- [ ] `bold-brutalist` renders all 11 primitives with **no branch added to the renderer**. No `mode`, no `if (artDirection.id === …)`, no second layout path. A hardcoded value becoming a token is expected and fine; a conditional is the abstraction failing ([../../v1/art-direction.md](../../v1/art-direction.md) → "The result")
- [ ] Every token added in this phase is read by the renderer the same way `--bg` is — through `to-css-vars` and a `var()`, with no art direction named anywhere in `renderer/`

**The art directions**

- [ ] All three pass the linter on every rule, including APCA, and any change made to pass it is a change to the art direction
- [ ] `bold-brutalist` + a hostile brand kit — a mid-grey, a neon, a pastel — still passes both contrast gates, or is refused with a message a marketer can act on
- [ ] All three render the `hostile` fixture without overflowing the viewport. That fixture exists for exactly this
- [ ] `editorial-light`'s migrated record renders byte-identically to its v1 constants

**Security**

- [ ] The three seeds are inserted by migration with `owner_id is null`, and no API path can create a system art direction
- [ ] Both new font families are ids in the registry, imported in `globals.css`, and have ledger lines. A registry row without an import renders as a system fallback and looks like a font-loading bug

**Human — this is most of the phase**

- [ ] Look at all three, full-screen, on the `full` fixture. If two of them feel like the same design at different brightnesses, one of them is not pulling its weight
- [ ] `editorial-light` on the editor canvas with the app chrome around it. A stranger must be able to tell product from artifact
- [ ] `bold-brutalist` must look **deliberate**, not loud. The failure mode is a design that reads as a mistake, and no automated check can tell you which one you have

---

## Skipped

| Not built | Trigger |
|---|---|
| A fourth art direction | v3's user authoring and AI derivation. Three is what proves the format; four is what proves you enjoyed authoring them |
| `mechanical-snap` | [11](11-range.md). `bold-brutalist` points at `cinematic-slow` until then, with a `ponytail:` |
| The four user control axes | Late v2 at the earliest ([../art-direction-system.md](../art-direction-system.md) → "User-authored art directions"). They are the same four v3's AI fills in, which is why they are designed before they are built |
| A texture kind that suits a light or a flat ground | Deliberately refused here. `editorial-light` and `bold-brutalist` both take `texture: []` and get their structure from hairlines and colour blocks. A fourth kind is a renderer change of the branching sort |

---

## Exit gate

- [ ] Three art directions in the store, all passing the linter, all at version 1
- [ ] `bold-brutalist` renders every primitive with no renderer branch
- [ ] Every value the phase moved out of the renderer is a token the renderer reads generically
- [ ] `bold-brutalist` under a hostile brand kit either passes both contrast gates or is refused legibly
- [ ] `editorial-light` is distinguishable from our own chrome by a stranger
- [ ] Any format refactor this phase forced is recorded in [01](01-ad-format.md)'s file and reflected in the seeds
- [ ] The gate is green
