# Phase 01 — AD format v2

> A format that holds art directions nobody has designed yet. Budgets, versioning, brand mapping, and a primitive token layer stored as DTCG. Both existing art directions migrate into it, and neither is allowed to be the reason the format has a field.

**Depends on:** [00](00-foundations.md) · **Blocks:** [02](02-motion-axis.md), [03](03-ad-linter.md), [04](04-three-art-directions.md) · **Spec step:** 1

> **Done, 2026-08-09.** Both art directions are rows in `art_directions`, seeded by migration 0011, and the TypeScript constants are deleted. `cinematic-dark` and `editorial-light` each emit a **byte-identical** CSS-variable map to the one their v1 constants emitted — the migration's only real assertion, and it holds. What the phase found on the way is in "What actually happened" below the exit gate.

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

- [x] `cinematic-dark` and `editorial-light` both round-trip: record → `toCssVars` → `fromCssVars` → the same record. The v1 round-trip test extends rather than being replaced
- [x] Both render byte-identically to their v1 constants. **This is the migration's only real assertion** — a format migration that changes a pixel has changed a design. Both were identical on the first run
- [x] No token is typed as a bare `string`. The v1 type-level test walks the new record and still passes — with `id` excluded, which is a name and not a token, and the exclusion is written down rather than the check weakened
- [x] The DTCG primitive layer validates against the published DTCG schema for its declared types — one class per `$type`, so a token whose value does not match its type has no representation
- [x] `$extensions` holds budgets, brand mapping and default motion, and the DTCG layer holds none of them — asserted by walking the emitted document, not by reading it

**Persistence**

- [x] Inserting `cinematic-dark` v2 leaves v1 readable and unchanged — `(id, version)` is the key, and `find` puts both halves in the `where`. Looking up by id and taking the newest is v2 rule 15's failure mode arriving as a convenience
- [x] An experience pinned to `{cinematic-dark, 1}` still resolves after v2 exists
- [x] An unknown `{id, version}` returns `not_found`, and the page renders its empty state rather than throwing — 404 from the route, `notFound()` from the pages

**Security** ([../../security/testing.md](../../security/testing.md))

- [x] A user cannot write a row with `owner_id is null` through the tenant wrapper. System art directions are seeded by migration, not by the API — the four `art_directions` tenancy tests from phase 00 cover it, and this phase kept them honest: their fixture used to `delete from art_directions` wholesale, which would now take the seeded rows with it
- [x] An uploaded DTCG file gets one Zod parse at entry and is rejected on shape before anything reads a value from it — `from_document` parses whole or fails whole. There is no upload *route* yet, deliberately: a write path that exists before the feature does is an attack surface with no user

**Human**

- [x] Put v1's `cinematic-dark` and the migrated one side by side on `/dev/primitives` and look. "Byte-identical CSS variables" and "looks the same" are different claims and only one of them is tested above

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

## What was built

```
api/schema/art_direction.py             the format. DTCG tokens + $extensions, both typed
api/features/art_direction/
  __init__.py                           load_art_direction, list_art_directions
  art_direction_data.py                 SQLAlchemy, art_directions only
  dtcg.py                               token constructors, and the interchange document
  seed.py                               both art directions, transcribed from the v1 constants
api/migrations/versions/0011_…          the `fluid` column, and the two system rows
api/routes/art_directions.py            read-only. There is no POST
web/src/features/art-direction/
  from-record.ts                        record -> ArtDirection. The seam that replaced the constants
  art-direction.data.ts                 the store read. server-only, returns a Result
  seeded-records.ts                     the seed fixture off disk, for harnesses and tests
  server.ts                             the server half of the public surface
  (deleted) cinematic-dark.ts, editorial-light.ts, resolve-art-direction.ts
```

---

---

## What phase 04 changed about this format

The plan budgets for a format refactor between art direction #2 and #3 and says to treat needing one as the process working ([README](README.md) → "The one hard gate"). Three things moved, all recorded here because this is the file that owns the format.

**`BrandMapping`'s four fields lost their defaults and are now required.** They were `accent_role='accent'`, `allow_brand_background=False`, `logo_treatment='mono'`, `contrast_strategy='auto'` — fine while nothing read the group, and a problem the moment something did. A Pydantic default generates into `z.enum(…).default(…).optional()`, so `from-record.ts` would have had to write the same default a second time, in another language, on the group that decides whether a customer's brand colour becomes a page's ground. Three constructor calls bought a total wire form.

**`brandMapping` reaches `ArtDirection`.** Phase 01 stored it and nothing read it; `brandCssVars` now looks up `accentRole` to decide which custom properties a brand overlay owns, and `resolveBrand` reads `contrastStrategy`. The deferral recorded here — *"a `contrastStrategy` that does anything"* — is closed, though not the way it was predicted: `bold-brutalist` does not override it. See [04](04-three-art-directions.md).

**Font weights became per-family.** `FONT_REGISTRY`'s `weights` had been `[400, 500, 600]` on every row, which read as a property of the registry and was a property of four families that happened to want the same three. Syne self-hosts one weight here and Space Grotesk three.

Nothing else moved. The DTCG split, the typed fluid layer, the `{id, version}` reference and the `$extensions` boundary all held an art direction they were not extracted from, which is the thing this phase was betting on.

## Exit gate

- [x] Both existing art directions live in the v2 format, in the database, and render identically to v1 — asserted from both languages against `art_direction_css_v1.json`, and looked at on `/dev/primitives`
- [x] The primitive layer is DTCG; budgets, brand mapping and default motion are in `$extensions`
- [x] `to-css-vars.ts` is still the only place a token becomes a string — unchanged by this phase
- [x] Brand derivation happens in CSS via `color-mix` in OKLCH, not in JavaScript — `brandCssVars`, an overlay applied on top of `toCssVars`. The contrast *correction* stays in JS and has to: "move it until it clears 4.5:1" is a measurement, and CSS cannot measure
- [x] `{ id, version }` resolves through the store, and an unknown reference fails closed
- [x] The gate is green

---

## What actually happened

**The equality proof needed a different shape than the phase describes.** It asks for the record and `toCssVars(CINEMATIC_DARK)` to be compared — but step 4 deletes `CINEMATIC_DARK`, so the two halves of that assertion cannot both exist at the end of the phase. Keeping the constants alive purely to be compared against would be two sources of truth maintained by a test.

So the comparison was made *at the moment of deletion* and pinned: `api/schema/fixtures/art_direction_css_v1.json` is the exact CSS-variable map each v1 constant emitted, generated from the files as they were, and `art-direction.test.ts` asserts the migrated records still emit it. Both directions came out identical on the first run, which was the useful outcome — the transcription had nowhere to hide.

**The fluid layer had to be typed in Python after all.** The checkpoint commit that opened this phase left it as `dict[str, object]`, reasoning that re-declaring `Rhythm`, `Texture` and `ImageTreatment` would be a second definition that drifts. That was right while the TypeScript constants were the source of truth and stopped being right at the step that deletes them: there is nothing left to drift *against*, and an opaque dict generates as `z.record(z.unknown())`, which would have made `from-record.ts` a pile of unchecked casts between the database and every published page. Typed, it is a total mapping the compiler checks in both directions.

**The art-direction feature needed two entry points, and the rule says one.** `docs/coderules/structure.md` allows one barrel per feature. The renderer is a client component and imports this feature's types and `toCssVars`; the store read is a data module carrying `import 'server-only'`, whose entire job is to be a build error inside a client bundle. One barrel exporting both makes that error fire on the renderer — the marker working exactly as designed, reporting that the surface is two things. The split is `index.ts` (pure) and `server.ts` (the reads), the lint rule gained a documented exception, and each half is still a single declared surface with nothing reachable around it.

**`render` takes tokens now, and that is a real widening of its input.** It resolved an id against a closed set, which was the safer shape while art directions were code. It holds no credential — deliberately, because that is what makes running a browser next to it safe — so it cannot read the store and an id no longer references anything it can reach. What replaces the closed set is `artDirectionRecordSchema`: the same generated validator `web` parses the same bytes with, every leaf a number or a closed union, with no field a free-form CSS string can arrive in. Phase [03](03-ad-linter.md)'s linter runs on the parsed result, exactly as it will for a designer's uploaded token file.

**One bug, found by the new required field.** `/measure` wrote its `200` header *before* awaiting the work that could fail, so a parse failure made the `catch` write a second set of headers — `ERR_HTTP_HEADERS_SENT`, thrown outside the promise, taking the whole process down. One malformed request was a denial of service on every tenant sharing the service. The ordering was wrong before this phase too; making `artDirection` required is simply what first gave it a reachable trigger. `/screenshot`, four lines below, already had it right.

**Brand derivation moved to CSS, and found a bug on the way.** `resolveBrand` returned the whole `Palette` with one field replaced — a palette derived in JavaScript, and one with a defect hiding in it: `accentSoft` came through as the *art direction's* own, so a brand applied to `cinematic-dark` would have rendered a red accent over an amber wash. It now returns the two values JavaScript actually has to compute, and `brandCssVars` emits the derivation:

```css
--accent:      rgb(26 43 76);                                  /* corrected, measured */
--accent-soft: color-mix(in oklch, var(--accent) 12%, transparent);
```

Two things about that mix are deliberate. **The ratio is the art direction's**, read off the alpha each direction already declared on its own `accentSoft` token — 12% on `cinematic-dark`, 10% on `editorial-light`, and they mean different things ("a glow" against "a wash behind a pull quote"). A constant in the emitter would be this layer overruling the token layer. **And it is an overlay, not a replacement**: `toCssVars` emits exactly what it emitted before, so an experience with no brand renders byte-for-byte what it rendered in v1 and the proof above stays meaningful.

`--accent-hover` is in the phase's sketch and is deliberately not emitted. No block reads it — `cta.tsx` uses `var(--accent)` as a background and the artifact has no hover state to token — and a token nothing reads is dead weight that looks like coverage.

### Deferred, and named rather than quietly dropped

**Applying the brand to a published page.** The overlay exists and every consumer already reads it through `var(--accent-soft)`; what does not exist is a render path that merges it, because v1 never applied a brand kit to output at all — the kit is stored and previewed, and the contrast notice is advisory. Wiring it changes what published pages look like, which is a product decision belonging to the phase that owns the brand's arrival on the page. **Trigger: phase [07](07-reskin.md)**, whose View Transition is the reason the derivation is CSS in the first place.

**A `contrastStrategy` that does anything.** The field is stored and defaults to `'auto'`; `resolveBrand` still picks its direction from the ground's own luminance and never reads the token. That is the correct behaviour today, and the field exists so an art direction can override it — the first one that wants to is phase [04](04-three-art-directions.md)'s `bold-brutalist`.
