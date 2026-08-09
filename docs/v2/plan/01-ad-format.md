# Phase 01 — AD format v2

> A format that holds art directions nobody has designed yet. Budgets, versioning, brand mapping, and a primitive token layer stored as DTCG. Both existing art directions migrate into it, and neither is allowed to be the reason the format has a field.

**Depends on:** [00](00-foundations.md) · **Blocks:** [02](02-motion-axis.md), [03](03-ad-linter.md), [04](04-three-art-directions.md) · **Spec step:** 1

> **In progress. The format is defined; nothing has migrated yet.** Started 2026-08-09 and deliberately checkpointed part-way, because the bad state for this phase is a *half-migrated* token layer — every other phase reads it — and stopping at a boundary where nothing has moved is safe in a way stopping half-way through the move is not.
>
> **Done:** `api/schema/art_direction.py` — the v2 record, registered in `EXPORTED`, Zod regenerated, gate green.
>
> **Not started:** the DTCG converter, seeding both art directions, the equality proof, and the `resolveArtDirection` switch. Picking it up is the "Where to resume" section at the bottom, which is written for someone arriving cold.

---

## Search

**Read first**

- [../art-direction-system.md](../art-direction-system.md) → "The format", all of it. It is the specification this phase implements
- [../../v1/art-direction.md](../../v1/art-direction.md) → "The result" — what art direction #2 already cost, and the four gaps it closed. This phase does not re-find them
- [../../coderules/python.md](../../coderules/python.md) — the `ArtDirection` type crosses the boundary now, so Pydantic owns it and Zod is generated

**Grep for**

- `web/src/features/art-direction/art-direction.ts` — the v1 types. `Palette`, `TypeRole`, `Rhythm`, `Texture`, `FontFamilyId`, `VisualBlend`, `VisualStrength` are all already typed to the "no bare string" standard, and all of them move
- `web/src/features/art-direction/to-css-vars.ts` — **the only place a token becomes a string**, and the reason phase 03's grammar validation is a change to one file. Do not write a second emitter
- `web/src/features/art-direction/resolve-art-direction.ts` — the `Record<ArtDirectionId, …>` table that makes a missing art direction a type error. It becomes a database read, and the exhaustiveness has to survive that
- `api/schema/experience.py` — `ArtDirectionId`, the `Literal`. It stops being a `Literal` in this phase and that is the change with the widest blast radius

**Verify externally**

- The DTCG stable version (2025.10) type names for `color`, `dimension`, `duration`, `cubicBezier`, `fontFamily`, `fontWeight`. Get them from the spec, not from memory — the whole value of speaking DTCG is being right about it

---

## Make

```
api/schema/art_direction.py         NEW. The format. Pydantic owns it
api/features/art_direction/
  __init__.py                       load, save, list — the public surface
  art_direction_data.py             SQLAlchemy, art_directions only
  dtcg.py                           DTCG primitive layer <-> token objects
  migrate_v1.py                     one-shot: v1 constants -> v2 rows
web/src/features/art-direction/
  art-direction.ts                  types now generated where they cross
  to-css-vars.ts                    unchanged in shape, fed from the record
  resolve-art-direction.ts          reads the store, not a code table
```

### The record is a DTCG token file plus a semantic wrapper

```
ArtDirection {
  id, version, name, author: 'system' | 'user'
  tokens:  <DTCG primitive layer>            colors, dimensions, durations, ...
  budgets: ContentBudgets                    $extensions
  brandMapping: BrandMapping                 $extensions
  defaultMotion: MotionVocabularyId          $extensions
}
```

**The primitive layer is DTCG; everything the DTCG spec has no concept of lives in `$extensions`, which is the field that exists for exactly this.** Colours, dimensions, durations, cubic-béziers, font families and weights all have standard DTCG types. Budgets, brand mapping, default motion and scene semantics do not, and should not — inventing DTCG types for them would be proposing a standard rather than using one.

This costs nothing now and buys a designer being able to author an art direction in Tokens Studio, and v4's marketplace getting an interchange format for free. **Do not over-invest.** A full Figma round-trip is a v4 concern; choosing a shape that does not have to be migrated is the whole win here.

**An imported token file is external input.** It is the path most likely to be waved through because it arrived from a designer's tool rather than a text field. One Zod parse at the boundary, then phase 03's linter on the parsed result — same as anything typed into a control panel.

### `budgets` — and the honest crack

```
ContentBudgets { eyebrow, headline, body, quote, stat, listItem }   // characters
```

v1 treated character caps as universal constants. They are not: 58 characters is elegant at `editorial-light`'s display size and catastrophic at `bold-brutalist`'s `clamp(4rem, 12vw, 14rem)`.

This is the point where "content is independent of styling" becomes "content is *mostly* independent of styling", and the residue is character budget. **The design response is to surface the coupling, never to hide it** — which is phase 07's overflow banner, and it is why this field exists here rather than being derived at render time.

The v1 caps become `cinematic-dark`'s budgets exactly. Do not take the opportunity to improve them; a migration that also changes behaviour is two changes wearing one commit message.

### `brandMapping` — the AD consumes the brand, not the reverse

```
BrandMapping {
  accentRole: 'accent' | 'bg' | 'ink'
  allowBrandBackground: boolean
  logoTreatment: 'mono' | 'full-color'
  contrastStrategy: 'lighten' | 'darken' | 'auto'
}
```

`'auto'` is not in [../art-direction-system.md](../art-direction-system.md)'s sketch and is added here for a reason found in v1: `resolveBrand` picks its correction direction from the ground's own luminance, which is strictly better than an art direction declaring one and being wrong. Keep the explicit values for an art direction that genuinely wants to override, default to `'auto'`, and let the existing code be the implementation.

A marketer choosing an art direction is choosing that art direction. `cinematic-dark` maps a brand to accents and stays dark; `bold-brutalist` may make the brand colour a full-bleed background, which is what `allowBrandBackground` exists for and the only reason it is a field rather than a constant.

### Derive the palette in CSS, not in JavaScript

```css
--accent:       var(--brand-primary);
--accent-soft:  color-mix(in oklch, var(--accent) 12%, transparent);
--accent-hover: oklch(from var(--accent) calc(l + 0.08) c h);
```

`color-mix()` is Baseline Widely Available and relative colour syntax has shipped everywhere. Two reasons this matters more here than in an ordinary design system: **OKLCH is perceptually uniform**, so nudging `l` actually lightens rather than wrecking a brand's hue the way HSL does — and contrast correction depends on that being well-behaved. And **reskin gets cheaper**: swap `--brand-primary` and every derived token follows, with no JS pass inside the View Transition.

Emit the derivations from `to-css-vars.ts`. It stays the only place a token becomes a string.

### `resolveArtDirection` stops being a code table

In v1 it is `Record<ArtDirectionId, …>`, which makes a missing art direction a compile error. That property cannot survive a database read, and pretending otherwise is worse than losing it deliberately: the function returns a `Result`, an unknown id is `not_found`, and the page that asked renders its designed empty state rather than an unstyled tree.

`ArtDirectionId` stops being a Pydantic `Literal`. What replaces it is not a looser string — it is `{ id, version }` validated against the store, which is a *stronger* check than a Literal was, because it also proves the version exists.

---

## Verify

**The gate** — green, and the schema regenerates with no diff. This phase changes `api/schema/`, so that step is live.

**The format**

- [ ] `cinematic-dark` and `editorial-light` both round-trip: record → `toCssVars` → `fromCssVars` → the same record. The v1 round-trip test extends rather than being replaced
- [ ] Both render byte-identically to their v1 constants. **This is the migration's only real assertion** — a format migration that changes a pixel has changed a design
- [ ] No token is typed as a bare `string`. The v1 type-level test walks the new record and still passes
- [ ] The DTCG primitive layer validates against the published DTCG schema for its declared types
- [ ] `$extensions` holds budgets, brand mapping and default motion, and the DTCG layer holds none of them

**Persistence**

- [ ] Inserting `cinematic-dark` v2 leaves v1 readable and unchanged
- [ ] An experience pinned to `{cinematic-dark, 1}` still resolves after v2 exists
- [ ] An unknown `{id, version}` returns `not_found`, and the page renders its empty state rather than throwing

**Security** ([../../security/testing.md](../../security/testing.md))

- [ ] A user cannot write a row with `owner_id is null` through the tenant wrapper. System art directions are seeded by migration, not by the API
- [ ] An uploaded DTCG file gets one Zod parse at entry and is rejected on shape before anything reads a value from it

**Human**

- [ ] Put v1's `cinematic-dark` and the migrated one side by side on `/dev/primitives` and look. "Byte-identical CSS variables" and "looks the same" are different claims and only one of them is tested above

---

## Skipped

| Not built | Trigger |
|---|---|
| The linter | [03](03-ad-linter.md). This phase defines the types it validates, which is the reason to do them properly here |
| User authoring, the four control axes | Late v2 at the earliest, and only after three hand-authored ADs exist. [../art-direction-system.md](../art-direction-system.md) → "User-authored art directions" holds the design |
| Figma / Tokens Studio round-trip | v4. Speaking DTCG for the primitive layer is the whole of the v2 investment |
| A third `texture` kind | The vocabulary is closed on purpose ([../../v1/art-direction.md](../../v1/art-direction.md) → "The result"). If `bold-brutalist` needs one in phase 04, that is the moment to design the vocabulary properly rather than add a fourth `if` |

---

## What the spec check changed

The Search section says to take the DTCG type names from the spec rather than from memory. Doing that moved the design, and three findings are worth carrying:

| | |
|---|---|
| **`color.$value` is an object** | `{colorSpace, components, alpha?, hex?}` — not a hex string. `hex` is the optional fallback and `components` is authoritative, which happens to be the right way round for us: the linter's APCA and WCAG maths wants channels |
| **`dimension.$value` allows `px` and `rem` and nothing else** | The finding that reshapes the phase — see below |
| **`$extensions` keys are reverse-domain** | One namespace, `com.d-design.v2` |

### Most of this token system cannot be DTCG, and that is the honest answer

The design is deliberately fluid: `clamp(3.5rem, 8vw, 8rem)` for a hero, `62ch` for a measure, `100svh` for a scene frame, `-0.03em` of tracking. **None of those are expressible as a DTCG `dimension`.** A format that claimed otherwise would emit invalid DTCG no tool could read, which is worse than not claiming the standard.

So the split follows where the spec actually draws the line:

- **DTCG layer** — the nine palette colours, the fixed `px` spacing scale, font families and weights, motion durations, cubic-béziers, and unitless numbers (leading, tracking, intensities, `visualStrength`). Real tokens a designer's tool can read.
- **`$extensions`** — every fluid length and clamp triple, the layout→fit table, texture structure, image treatment, budgets, brand mapping, default motion.

That is a smaller DTCG surface than this phase's sketch implies. It is also the one that is true, and the win was never a Figma round-trip — it is choosing a shape that does not have to be migrated later.

`fluid` is stored as the already-typed objects `web` reads rather than re-modelled in Pydantic. Re-declaring `Rhythm`, `Texture` and `ImageTreatment` here would be a second definition of each, and the drift between them would be silent; phase [03](03-ad-linter.md)'s linter is what walks inside them.

---

## Where to resume

Written for someone arriving with no memory of the session that started this.

**1. The converter — `api/features/art_direction/dtcg.py`.** v1's TypeScript constants are the source values. The converter takes a palette/type/rhythm/texture set and emits the DTCG document plus the `$extensions` payload. There is no automated path from the TS constants to Python: they are hand-transcribed once, which is exactly why step 3 exists.

**2. Seed both art directions — a migration, not a script.** `art_directions` already exists (0008) with `(id, version)` as the primary key and `owner_id is null` meaning system. Seeding runs as the migration role, which is the only way a system row can be written at all — the RLS policy makes `owner_id is null` unwritable through `as_user()`, deliberately.

**3. The equality proof, and it is the phase's only real assertion.** *"A format migration that changes a pixel has changed a design."* The pattern this repo already uses for a cross-language invariant is one shared fixture with a test on each side — see `api/tests/test_visual_seed.py` and `renderer.test.ts` agreeing on FNV-1a. Do that here: the stored record and `toCssVars(CINEMATIC_DARK)` must emit an identical CSS-variable map, asserted from both languages against one fixture. Until that exists there are two sources of truth for the same tokens, which is the state this phase must not be left in.

**4. Only then, the switch.** `resolveArtDirection` becomes a store read returning a `Result`, the TypeScript constants are deleted, and `ArtDirectionId` stops being a `Literal`. Note the consequence the phase file does not: **`render` resolves by id today and holds no credential**, so it cannot read the store — its payload has to become validated tokens. That is written up in [15](15-images.md)'s `/measure` and `/screenshot` notes and is the widest-blast-radius part of this phase.

---

## Exit gate

- [ ] Both existing art directions live in the v2 format, in the database, and render identically to v1
- [ ] The primitive layer is DTCG; budgets, brand mapping and default motion are in `$extensions`
- [ ] `to-css-vars.ts` is still the only place a token becomes a string
- [ ] Brand derivation happens in CSS via `color-mix` / relative OKLCH, not in JavaScript
- [ ] `{ id, version }` resolves through the store, and an unknown reference fails closed
- [ ] The gate is green
