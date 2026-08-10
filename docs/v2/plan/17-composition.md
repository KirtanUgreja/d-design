# Phase 17 — Composition

> Framing, texture and imagery fix a scene. This fixes the **sequence** — hierarchy inside a slide, variety between slides, and the editorial furniture that makes a generated deck read as art-directed rather than assembled. It is the phase that answers "the design is fine and the deck is still boring."

**Depends on:** [04](04-three-art-directions.md), [13](13-scene-fit.md), [14](14-texture-without-gradient.md), [15](15-images.md), [18](18-presentation-frame.md) · **Blocks:** [09](09-visual-verification.md), [21](21-art-direction-engine.md) · **Spec step:** delta — see [../spec.md](../spec.md) → "Composition deltas"

> **The presentation pivot made this phase easier and more important, in that order** ([../presentation.md](../presentation.md), 2026-08-10).
>
> **Easier, because composition now has a frame.** Every constraint below — one anchor per scene, asymmetric splits, the ground cycle — assumes something to compose *inside*. On a scrolling page that frame was whatever the reader's window happened to be, so the constraints were hopes. On a slide it is the stage, bounded and known at four aspect ratios, so they are checkable. [18](18-presentation-frame.md) is therefore a dependency, not a neighbour: composing against `8vw` composes against the wrong axis.
>
> **More important, because it now gates [21](21-art-direction-engine.md).** The open question the whole pivot turns on is whether generated decks look alike because of *colour* or because of *layout*. If every slide is still centred text, three generated art directions collide exactly as three hand-authored ones do, and the engine will have been built to answer the wrong question. **Look at the output of this phase before starting 21.** That judgement is this phase's real exit condition and no checklist item can stand in for it.
>
> **One thing got harder.** "Variety between scenes" was previously variety a reader met one at a time while scrolling. In a deck the audience sees slides in quick succession and a presenter clicks through them in a rehearsal — sameness that was diffuse on a page is *concentrated* here, and much more obvious. That is a better test, and it will fail more often.

> **Phase 04 handed this phase two things, one of them measured.**
>
> **`groundCycle` is what makes `bold-brutalist` usable.** That art direction takes a brand kit as its page ground and sets near-black type on it, so it accepts colours lighter than about `#d8d8d8` and refuses everything else — **roughly 2% of the sRGB cube**, which includes most corporate navies and every mid-grey. The refusal is legible and correct, and it is not a product. An inverted palette lets a dark brand take white type, which is the same mechanism the cycle already needs for alternate scenes. This was a stylistic argument before phase 04 and is a measured one now.
>
> **`rule` should probably become furniture and leave the texture union.** Both `editorial-light` (v1) and `bold-brutalist` (phase 04) authored a `rule` layer and removed it after looking at it, independently, for the same reason: a rule tiled across a whole scene is ruled paper, not structure. A visible rule wants placing once, which is what `Furniture` is for. Removing a kind is a renderer change, so it belongs to this phase rather than to the one that found it twice.


---

## What is left after the other four phases

[13](13-scene-fit.md) gives a scene a frame. [14](14-texture-without-gradient.md) gives it a surface. [15](15-images.md) gives it photographs. Each one is necessary and none of them stops the pipeline emitting **eight consecutive centred scenes of a headline and two paragraphs**, which is what a schema-valid, budget-respecting, fully-tokenised experience currently looks like when the model plays it safe.

Principle 5's last banned row names this exactly: *"Five consecutive centred sections at `max-w-3xl` — no rhythm, no hierarchy, no editing."* It was written about our marketing site. It describes our output.

Four specific gaps, and three of them are hardcoded values of the shape v1's art-direction #2 exercise taught us to look for — *a value the system holds globally because it only ever had one instance*:

| Gap | Evidence |
|---|---|
| **No focal hierarchy** | `Scene._structural_rules` caps headlines at one and enforces grid cell counts. Nothing requires a scene to have a single dominant element, so a scene of five `normal` body blocks is valid |
| **Symmetry is hardcoded** | `layouts/split-left.tsx` is `gridTemplateColumns: '1fr 1fr'`. `layouts/grid.tsx` is `repeat(n, 1fr)`. `alignItems: 'center'` is a literal. Every split in the product is 50/50 under every art direction, forever |
| **No sequence rule** | The Director assigns a layout per scene with nothing preventing the same one three times, and nothing varying the ground between them |
| **No furniture** | No scene indices, no running marks, no structural rules. The cheapest signals of intent in editorial design, and the system has none |

None of this is fixed by prompting the model harder. Layout variety asked for in a prompt is layout variety you get sixty percent of the time, and rule 7 means the model cannot be handed the styling anyway. It is fixed by **tokens the art direction owns and constraints the Director must satisfy** — which is the same division of labour as everything else here.

---

## Search

**Read first**

- [../../design/principles.md](../../design/principles.md) → principle 5's last row, and the whole "no rhythm, no hierarchy, no editing" idea
- [../../v1/art-direction.md](../../v1/art-direction.md) → "The result", the table of seven costs. Four were global values that were really one art direction's. This phase finds the next three
- [../../v1/ai-pipeline.md](../../v1/ai-pipeline.md) → the Director phase. Layout assignment already lives there and is not being moved
- [../spec.md](../spec.md) → "Pipeline delta". `maxBlocksPerScene` is already an AD hint the Director reads; the constraints below join it rather than starting a second mechanism

**Grep for**

- `web/src/features/renderer/layouts/split-left.tsx`, `split-right.tsx`, `grid.tsx` — `1fr 1fr`, `repeat(n, 1fr)`, `alignItems: 'center'`, `spaceVar(6)`. Four hardcoded compositional decisions in three files
- `web/src/features/renderer/layouts/centered.tsx`, `stack.tsx` — the same audit
- `web/src/features/director/direct.ts` — where layouts are assigned. The sequence constraints go here, not in the renderer
- `api/schema/scene.py` → `Scene._structural_rules`. The anchor rule joins the headline and grid rules, in the same validator
- `web/src/features/renderer/scene.tsx` — the ground is `COLOR_VAR.bg` on the root and nothing per scene. The ground cycle attaches here
- `web/src/features/intake/`, `web/src/features/director/outline-editor.tsx` — the two surfaces v1 recorded as *"correct but not yet crafted"*. They are picked up in this phase

**Verify externally** — nothing. Every decision here is ours.

---

## Make

```
web/src/features/art-direction/
  art-direction.ts        + Composition tokens, + Furniture tokens
  cinematic-dark.ts · editorial-light.ts · bold-brutalist.ts
web/src/features/renderer/
  layouts/*.tsx           four hardcoded values become four token reads
  scene.tsx               ground cycle, furniture
  furniture.tsx           scene index, running mark, structural rule
web/src/features/director/
  direct.ts               sequence constraints
api/schema/scene.py       the anchor rule
web/src/features/intake/ · director/outline-editor.tsx   the deferred v1 design pass
```

### 1. Every scene has exactly one anchor

```
anchor = headline@hero · stat · chart · image · slot · abstract-visual@bold
```

A scene must contain **at least one**. A scene must not contain **more than two**. Enforced in `Scene._structural_rules`, alongside the rules that already live there.

This is a content rule, not a styling rule, which is why it belongs in the schema and not in the art direction: a scene with no dominant element has nowhere for the eye to land regardless of how it is styled, and a scene with four is a collage. It is also the single highest-leverage change in this phase, because it converts "the model wrote three paragraphs" from a valid output into a repair-loop failure the existing machinery already handles.

The Build phase's repair path handles the rejection the same way it handles any other validation failure. No new mechanism.

### 2. Asymmetry is a token, and there are four of them hiding in the layouts

```ts
interface Composition {
  splitRatio: readonly [number, number];   // 5:7, not 1:1
  splitAlign: 'start' | 'center' | 'end';
  gridRatio: 'equal' | 'lead';             // first cell wider
  regionGap: 1|2|3|4|5|6|7;                // an index into the space scale
  measureShort: Length;                    // a second, narrower measure
}
```

`1fr 1fr` becomes `var(--split-ratio)`. This is the same move as `mix-blend-mode: screen` becoming `visualBlend` in v1 — a hardcoded value the renderer holds becoming a token the art direction owns — and it is a token read, not a branch.

The design content matters as much as the mechanism. A 5:7 split with the text in the narrow column and the image in the wide one is an editorial composition; 50/50 is a slide template. `editorial-light` wants 5:7 with `splitAlign: 'start'` so the text hangs from the top of the column. `cinematic-dark` wants 4:8 centred. `bold-brutalist` wants 3:9 and `end`.

`measureShort` exists because a 62ch measure inside a 5:7 narrow column is a paragraph that wraps every four words. A second measure is what the narrow side of an asymmetric split actually needs, and its absence is why 50/50 felt safe.

### 3. The ground cycles, by lookup

```ts
interface Composition {
  // …
  groundCycle: readonly (keyof Palette | 'accent-block')[];
}
```

Indexed by scene position. `cinematic-dark`: `['bg', 'bg', 'bgElevated', 'bg']` — a barely-perceptible lift every third scene, which is what stops a long dark scroll reading as one undifferentiated field. `editorial-light`: `['bg', 'bg', 'bg', 'bgElevated']`. `bold-brutalist`: `['bg', 'accent-block', 'ink', 'bg']`, where consecutive scenes invert completely.

A lookup indexed by position is not a branch, and the AI never sees it. It is also exactly where `bold-brutalist`'s *"hard-edged colour blocking at the layout level"* — the sentence [04](04-three-art-directions.md) calls the most suspicious in all of v2 — turns out to live. It is a token the existing layouts read, which is what that phase said the honest answer would have to look like.

**Ink follows the ground.** A scene on `ink` ground needs inverted text roles, which is a palette swap on the scene root and not a second set of type tokens. Both grounds get the APCA gate in [03](03-ad-linter.md); an art direction whose inverted scenes fail is an art direction that does not get a ground cycle.

### 4. Furniture

```ts
interface Furniture {
  sceneIndex: 'none' | 'numeric' | 'fraction';   // "03" or "03 / 08"
  indexPosition: 'block-start' | 'block-end';
  rule: 'none' | 'block-start' | 'block-end' | 'both';
  ruleWeight: Length;
  runningLabel: boolean;                          // the experience title, small
}
```

Cheap, entirely token-driven, invisible in a specification and very visible on screen. A scene index in the corner and a hairline rule at the top edge is the difference between a page and a document. It carries no content the AI writes — the index is a position, the running label is the experience's own title — so it adds nothing to the schema and cannot be injected into.

`editorial-light` takes `fraction` + `block-start` rule + running label. `cinematic-dark` takes `numeric` only. `bold-brutalist` takes `numeric` at absurd size and a thick rule.

### 5. Sequence constraints, in the Director

Four rules the Director must satisfy when assigning layouts, checked after assignment and repaired by reassignment rather than by asking the model again:

| | |
|---|---|
| **No three consecutive identical layouts** | Two is a deliberate pairing; three is the model defaulting |
| **The visual ratio floor** | At least ⌈scenes ÷ 3⌉ scenes carry an image, chart, slot or bold abstract visual. An eight-scene experience with no visual is the most common bad output and it is now unrepresentable |
| **Full-bleed is rationed** | At most two per experience, and never adjacent. It is the loudest layout and its power is entirely scarcity |
| **The hook and the CTA are not the same shape** | First and last scene take different layouts. A deck that opens and closes identically reads as a template |

These are constraints on a small assignment problem, not prompt instructions. The Director already reads `maxBlocksPerScene` from the art direction; these are checked in the same place, and each art direction may tighten them.

### 6. Type hierarchy actually being used

An art direction with an 8× type scale, used by a scene that sets everything at `normal`, has a 1× type scale. The rule: **each scene uses at least two distinct type roles, and at least one of them is above `lead`.** It is a companion to the anchor rule, it belongs in the same validator, and it is what makes the eyebrow/hero relationship — the thing carrying most of an art direction's character — actually appear.

### 7. The two deferred v1 surfaces

v1's status line records what was deferred rather than missed: *"the design pass on Intake and the outline gate, which are correct but not yet crafted."* They are picked up here because they are the same kind of work and because they are the first two screens anyone sees. An experience that looks composed, reached through two screens that do not, still reads as unfinished.

They are app chrome, not artifact, so they follow [../../design/brand.md](../../design/brand.md) and are explicitly **not** allowed to converge with `editorial-light` — the same constraint [04](04-three-art-directions.md) puts on the art direction, pointed the other way.

---

## Verify

**The gate** — green.

**Structure**

- [ ] A scene with no anchor is a Pydantic validation error, and the build path repairs it rather than failing the experience
- [ ] A scene with three anchors is a validation error
- [ ] A scene using one type role is a validation error
- [ ] Grep `renderer/layouts/` for `1fr`, `repeat(`, `center` and find only token reads. Four hardcoded values, four tokens
- [ ] No art direction id appears anywhere in `renderer/`. The compositional tokens are the largest batch added since v1 and the easiest place for a branch to slip in

**Sequence**

- [ ] Generate ten experiences. None has three consecutive identical layouts; every one meets the visual ratio floor; none has adjacent full-bleeds; none opens and closes on the same layout
- [ ] The ground cycle produces visible variation across a twelve-scene experience under all three art directions, and inverted scenes pass APCA
- [ ] The constraints are satisfied by reassignment, not by a second model call. A retry loop here is a token furnace with a design justification

**Craft**

- [ ] Furniture renders under all three art directions and carries no AI-written content
- [ ] Asymmetric splits use `measureShort` on the narrow side. A four-word-per-line paragraph means the second measure was added and not used
- [ ] Intake and the outline gate get the design pass, and are distinguishable from `editorial-light` by a stranger

**Human — this is most of the phase**

- [ ] Generate the same brief before and after this phase and put the two full-screen, side by side. If the second is not obviously more composed, the tokens are set too timidly — the most likely failure here is a correct implementation of values that are all too close to the middle
- [ ] Scroll a twelve-scene experience and count how many scenes you can describe afterwards. Sameness is the defect and it is measured by memory, not by a screenshot
- [ ] Show it to someone who did not build it and ask what tool made it

---

## Skipped

| Not built | Trigger |
|---|---|
| A layout engine that composes new layouts | Six layouts × the tokens here is already a large space. A generative layout system is a v3 idea and probably a bad one |
| Per-scene composition overrides in the editor | The AD's tables answer it. An override is an editor-side property on the experience, never a field the AI writes |
| Optical alignment and true grid snapping | Real typographic craft and a genuine rabbit hole. `splitRatio` and `measureShort` are the 80% |
| A "make it more interesting" AI action | It would be the model writing styling with extra steps |
| Cross-scene motion choreography | The motion axis owns timing. Sequencing motion *between* scenes is [11](11-range.md)'s territory if anywhere |
| More than one ground cycle per art direction | A single ordered list is enough until an art direction demonstrably needs two |

---

## Exit gate

- [ ] Anchor rule, two-anchor cap and type-hierarchy rule enforced in the schema, repaired by the existing loop
- [ ] Four hardcoded compositional values in `renderer/layouts/` are tokens, with no branch added
- [ ] Ground cycle, asymmetric splits, second measure and furniture authored for all three art directions
- [ ] Four sequence constraints enforced in the Director, verified over ten generated experiences
- [ ] Inverted-ground scenes pass both contrast gates
- [ ] Intake and the outline gate have had their design pass and do not converge with `editorial-light`
- [ ] Before/after on one brief, full-screen, judged by a person
- [ ] The gate is green
