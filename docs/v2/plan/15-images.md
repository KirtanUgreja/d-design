# Phase 15 — Images that exist

> Every `Image` block in v1 renders a grey rectangle. This phase resolves the asset, art-directs the photograph so it belongs to the art direction instead of fighting it, and wires the generation call that v1 left as a `ponytail:`.

**Depends on:** [00](00-foundations.md), [01](01-ad-format.md), [14](14-texture-without-gradient.md) · **Blocks:** [04](04-three-art-directions.md), [17](17-composition.md) · **Spec step:** delta — see [../spec.md](../spec.md) → "Composition deltas"

---

## The defect, precisely

```ts
// renderer/blocks/image.tsx
<img src={placeholderImageSrc(artDirection)} … />
```

`placeholderImageSrc` returns a data-URI SVG of a single flat rectangle in `bgElevated` with a hairline border. **It is the only thing an `Image` block has ever rendered.** `asset-placeholder.ts` says so in its first line and v1 recorded the gap honestly in two places ([../../v1/plan/11-visuals-and-slot.md](../../v1/plan/11-visuals-and-slot.md) → Skipped, twice: "resolving an `Image` block's `assetId` to a URL" and "the image-generation provider call").

Both were correct deferrals at the time and together they are the largest single reason generated output looks thin. A presentation is images and type. This product currently ships type.

Three things are missing and they are usually confused for one:

| | |
|---|---|
| **Resolution** | An `assetId` becomes a URL a browser can fetch. Uploaded images exist and have never been displayed |
| **Treatment** | A photograph is made to belong to the art direction. Without this, a stock photo under `cinematic-dark` looks pasted onto it |
| **Generation** | Scenes with no asset get one. The cap, the prompt boundary, the storage path and the `Asset` row are all built; the provider call is not |

Resolution and treatment are the ones that change how the product looks. Generation is the one that gets talked about.

---

## Search

**Read first**

- [../../v1/plan/11-visuals-and-slot.md](../../v1/plan/11-visuals-and-slot.md) → "2. Generated imagery" — the three rules, and the exit-gate note on why the provider call was not wired blind
- [../../v1/ai-pipeline.md](../../v1/ai-pipeline.md) → "Imagery". Three rules learned from the wedge rather than from taste
- [../../security/prompt-injection.md](../../security/prompt-injection.md) → Defense 1. The imagery prompt has no access to key messages, and that is what makes "never generate the product" structural
- [../../techstack/infrastructure.md](../../techstack/infrastructure.md) → the quarantine prefix and the upload path. A generated image takes the same one
- [../../security/content-and-web.md](../../security/content-and-web.md) → the published page's CSP. `img-src` is decided here

**Grep for**

- `web/src/features/renderer/blocks/asset-placeholder.ts` — the `ponytail:` this phase closes. Its own note says the block components' props do not need to change, and they do not
- `web/src/features/renderer/blocks/image.tsx` and `video.tsx` — both call it
- `api/features/imagery/imagery.py` — the cap (`MAX_GENERATED_PER_EXPERIENCE = 4`), `build_imagery_prompt`, and the `ponytail:` naming the upgrade path: an image branch **inside** `complete`, so there is still one call site
- `api/features/ai/complete.py` — the seam. `response_format: json_schema` is the one shape it speaks. A second call site is what rule 6 exists to prevent, and this phase is the one that will be tempted
- `api/features/assets/` — `save_asset`, `verify_and_reencode`, `store`. Magic bytes, re-encode, server-generated key. A generated image goes through all of it
- `web/src/features/assets/` — the `source: 'generated' | 'upload'` badge already rendered in the editor

**Verify externally**

- Which image model, and on what terms. As of August 2026 the landscape is unstable in one specific way that matters: **Google's Imagen models are deprecated and shut down on 2026-08-17**, so anything starting there starts on a dead path. Flux 2 Pro is the current value default and takes up to 8 reference images; Gemini 3 Pro Image takes up to 14 and is the strongest at holding a style across a set. Reference-image support is the feature to select on here, not raw fidelity — see "On-art-direction imagery" below

---

## Make

```
api/features/assets/
  routes.py               GET /a/{asset_id} — same-origin, authorized, cacheable
  assets_data.py          + width, height, and the derived sizes recorded at ingest
api/features/imagery/
  imagery.py              the provider call, through `complete`
api/features/ai/
  complete.py             + an image branch. One seam, one call site
web/src/features/renderer/blocks/
  image.tsx               a real <img>, with intrinsic dimensions and a treatment
  asset-placeholder.ts    kept, as the resolve-failure state only
  treatment.tsx           duotone / mono / posterize / overlay / frame / veil
web/src/features/art-direction/
  art-direction.ts        + ImageTreatment
  cinematic-dark.ts · editorial-light.ts   their treatments
api/migrations/versions/  asset dimensions
```

### 1. Resolution: a same-origin path, composed from an id

The renderer is pure and cannot fetch ([../../coderules/patterns.md](../../coderules/patterns.md) rule 6), so the URL has to be **derivable** — which is exactly what v1 recorded as the blocker. Derive it:

```
/a/{assetId}
```

Composing a path from an id is string work, not I/O, and it behaves identically in the browser, the app server and the render service. A signed URL would not: it needs a secret, a clock and a network call, and it would put all three inside the renderer.

That makes assets same-origin for the editor **and** for the published page, which is the decision v1 flagged and left open. Take it: `img-src 'self'` on the published page's CSP, no third-party image host, no CORS, and a cache story that is one `Cache-Control` header.

The route is the security surface, not the renderer:

- **Authorization is on the route and it fails closed.** An asset belonging to an unpublished experience is tenant-scoped through `as_user()`; an asset on a published page is readable because publication made it so. A `catch` returning the bytes is a vulnerability, not error handling (rule 10)
- **No directory traversal, no user-controlled key.** The key is server-generated at ingest and the id is a UUID
- `Content-Type` from the stored, re-encoded type — never from the request, never sniffed
- `Content-Disposition: inline` with `X-Content-Type-Options: nosniff`

**When resolution fails, `placeholderImageSrc` is what renders.** It stops being the only path and becomes the honest one: a missing asset is a flat plate in the art direction's own colours, not a broken-image glyph on a customer's launch page.

### 2. Intrinsic dimensions, or every scene shifts

A `fit: viewport` scene from [13](13-scene-fit.md) with an unsized `<img>` in it lays out at zero height, then reflows when the image decodes — and the taller the frame, the more visible the jump. Record `width` and `height` at ingest (upload **and** generation, same path) and emit them as attributes. The aspect ratio then reserves the box before a byte of image arrives.

Two sizes per asset, produced at ingest by the same re-encode that already runs, and a `srcset`. Not four, not a full pipeline — two, because a hero at 2560px and a grid cell at 480px are the two real cases and the third is speculative.

### 3. Treatment: the part that makes it look art-directed

This is the half that changes the output, and it is the half nobody asks for.

An uploaded photograph has its own colour, contrast and light. Dropped into `cinematic-dark` untreated it reads as a stock image on a dark page. Dropped into `editorial-light` untreated it reads as a stock image on a white page. The art direction has to *consume* the photograph the way it already consumes a brand colour — [../../v1/art-direction.md](../../v1/art-direction.md) → "Brand colors map into semantic roles, they do not replace them" is the exact same principle, applied to pixels.

```ts
interface ImageTreatment {
  tone: 'as-shot' | 'mono' | 'duotone' | 'posterize';
  overlay: TextureKind | 'none';     // from phase 14's vocabulary
  frame: 'none' | 'hairline' | 'block' | 'inset';
  edge: Length;                      // corner radius, 0 for most art directions
  veil: number;                      // 0–1, for text over media
  ratios: readonly Ratio[];          // the crops this AD will accept
}
```

| | `cinematic-dark` | `editorial-light` | `bold-brutalist` |
|---|---|---|---|
| `tone` | `duotone` — ink to accent | `as-shot`, slightly desaturated | `posterize`, 4 levels |
| `overlay` | `grain` | `none` | `halftone` |
| `frame` | `none` | `hairline` | `block` |
| `ratios` | 21:9, 16:9 | 3:2, 4:5 | 1:1, 4:5 |

**Duotone with no gradient and no SVG filter:** greyscale the image, stack a `multiply` layer in the shadow token and a `screen` layer in the highlight token. Two flat colours, two blend modes, three lines of CSS. It is the classic implementation and it happens to be exactly what [14](14-texture-without-gradient.md) permits.

**And this is where the reskin claim gets its best demonstration.** One uploaded photograph, three art directions, three genuinely different images — because the treatment is a token and the pixels never changed. Nothing is regenerated, nothing is re-uploaded, the transition is a CSS change. That is a better argument for the whole thesis than any type specimen, and it should be the screenshot in [08](08-reskin-transition.md).

The `ratios` list is the one that will be argued about. An art direction that accepts any aspect ratio has no compositional opinion; cropping to the AD's own set is what makes a page of images look like a spread rather than a folder. Crop by `object-fit: cover` against a token `aspect-ratio` — never by re-encoding, so switching art directions re-crops instead of re-processing.

### 4. Generation, through the one seam

`complete` gains an **image branch** — the upgrade path `imagery.py` already names. Not a second client, not a second call site, not a provider SDK imported in a feature module. The seam is the most security-critical file in the codebase and the reason it is one file is that it is one file.

Everything around it exists and is tested: the per-experience cap that fails closed by signature, the prompt builder with no access to key messages, magic-byte verification, re-encode, the `Asset` row with `source='generated'`, and the editor badge.

Three things this phase adds to it:

**On-art-direction imagery.** The prompt already carries scene intent, beat and tone. Add the art direction's **character** — not its tokens. "Cool, near-black, single hard light source, no lens flare" is character; `#08090B` is a token, and putting token values in an image prompt is the same category error as letting the AI write styling. Where the provider takes reference images, the reference is a rendered plate of the AD's own palette and texture, which is a much stronger consistency mechanism than adjectives and is the reason reference-image support is the selection criterion.

**Regeneration is not a reskin step.** Reskinning does not regenerate imagery — the treatment re-tints it. This keeps reskin free, keeps it fast enough to sit inside a View Transition, and is the correct answer anyway.

**Cost stays visible.** `MAX_GENERATED_PER_EXPERIENCE = 4` is per experience and fails closed. Generated imagery is the first place this product's cost model stops being a rounding error, and the cap is the control. Record actual spend per experience alongside the token cost the pipeline already tracks.

### 5. The three v1 rules do not move

**Never generate the product.** Atmosphere, texture, abstract environment. A generated product shot is a legal and credibility problem and the prompt builder's lack of access to key messages is what makes the rule structural rather than aspirational.

**Prefer `AbstractVisual` first.** Six generators after [14](14-texture-without-gradient.md), all free, all on-brand, all deterministic. Generation is the exception for scenes that need photographic depth code cannot supply — and it is now genuinely worth reaching for, because before this phase there was nothing to reach for.

**Mark it.** `source: 'generated'`, visible in the editor. A marketer must know what is real before they publish, and [../../v3/compliance.md](../../v3/compliance.md) turns that from taste into obligation.

---

## Verify

**The gate** — green.

**Resolution**

- [ ] An uploaded image renders. This has never been true and it is the phase's first checkbox
- [ ] `/a/{id}` for an asset in another tenant's experience returns 404, through `as_user()`, and no code path returns bytes from a `catch`
- [ ] `/a/{id}` for an asset on a published page is readable without a session, and only because publication made it so
- [ ] `Content-Type` comes from the stored re-encoded type; `nosniff` is set
- [ ] The published page's CSP is `img-src 'self'` and a third-party image URL is blocked. Test it with a real remote URL
- [ ] A missing or unauthorized asset renders the art direction's flat plate, never a broken-image glyph
- [ ] `srcset` serves the small variant to a grid cell and the large one to a hero

**No layout shift**

- [ ] Every `<img>` carries intrinsic `width` and `height`. Assert in the renderer test, not by eye
- [ ] CLS is zero on a `fit: viewport` scene containing a hero image, measured in the render service

**Treatment**

- [ ] The same photograph under all three art directions produces three visibly different images, with no re-encode and no second asset row
- [ ] Duotone uses blend modes and flat token colours. Invariants check 8 still passes — a duotone implemented with a gradient is the exact regression this ordering exists to catch
- [ ] Text over an image is legible under every treatment, at the AD's `veil`. This is an APCA check against the image's own mean luminance, not a guess
- [ ] Crops come from the AD's `ratios` and change on reskin
- [ ] An image next to an `AbstractVisual` in the same scene does not fight it. The `/dev/visuals` review page from v1 extends to cover this pairing

**Generation**

- [ ] Exactly one call site. Grep for the provider's name and find it only in `complete.py`
- [ ] The cap fails closed when a count cannot be produced
- [ ] The prompt contains no key messages, no proof points, and no token values. Assert at the function boundary, the way `generate_slot` is asserted
- [ ] A generated image goes through magic-byte verification and re-encode, lands with `source='generated'`, and is badged in the editor
- [ ] Injection corpus: a payload instructing the model to depict the product, or to render text into the image, produces neither
- [ ] Cost per experience is recorded

**Human**

- [ ] Generate one experience with imagery and one without, and look at them next to each other. If the difference is not obvious, the treatment is doing nothing and the tokens are wrong
- [ ] One photograph, three art directions, full screen. This is the reskin demo and it either lands or it does not

---

## Skipped

| Not built | Trigger |
|---|---|
| Regenerating imagery on reskin | The treatment re-tints it. Revisit only if a specific AD pair looks wrong in a way tokens cannot fix |
| A background-removal or subject-isolation pass | A real scene needs a cut-out. `LogoWall` in [12](12-primitives.md) is the first candidate |
| More than two rendition sizes | A third real breakpoint |
| Video generation | Not in v2, unchanged from v1 |
| Frame extraction from uploaded video | [12](12-primitives.md) → `ScrollSequence`, and it brings a decoder into the fetch worker with it |
| A user-facing image editor — crop, reframe, adjust | The AD's `ratios` do the cropping. A manual crop is an editor surface and a second source of truth |
| Serving from a CDN edge | v3, with AWS. `Cache-Control` on a same-origin route is the v2 answer |

---

## Exit gate

- [x] Uploaded images render, on a same-origin authorized route that fails closed
- [x] Zero layout shift on a viewport-fit scene — by the art direction's `ratios` token rather than by intrinsic dimensions; see the deviation below
- [x] Both shipped art directions declare an `ImageTreatment`, and one photograph reads two ways with no re-encode and no second asset row. The third way waits on `bold-brutalist` in [04](04-three-art-directions.md)
- [x] Duotone, overlay, frame and veil are all token-driven and gradient-free
- [ ] **Generation is not built.** Deferred deliberately, below
- [x] `asset-placeholder.ts`'s `ponytail:` is deleted; the file survives as the resolve-failure state, which is what the note predicted
- [x] The gate is green
- [ ] Two rendition sizes and a `srcset` — deferred with generation

## What is deferred, and why

**Image generation.** Everything around it exists and is tested — the cap that fails closed, the prompt builder with no access to key messages, magic-byte verification, re-encode, the `Asset` row, the editor badge. What is missing is a provider decision that cannot be made from inside the repo: this phase's own Search section records that Google's Imagen shut down on 2026-08-17, so the obvious default is a dead path, and the selection criterion is reference-image support rather than fidelity. Wiring a provider blind is what v1 declined to do for the same reason, and it was right.

The two things that make the product look different — **resolution and treatment** — are built. The phase said as much before it started: *"Resolution and treatment are the ones that change how the product looks. Generation is the one that gets talked about."*

**Two renditions and `srcset`** go with it: both are ingest-pipeline work, and a second rendition of an image nobody can generate yet is speculative.

## What the build found

**The duotone destroyed the photograph, and only looking at it showed that.** The first implementation stacked a `multiply` plate in the ground colour *and* a `screen` plate in the accent on top of an opaque image. Every midtone was crushed and the result was a flat olive rectangle with no photograph left in it. That is not how a duotone is built: the canonical construction paints the *wrapper* in the highlight colour and multiplies the greyscaled image onto it, then lifts the blacks with a single `screen` plate. Two colours, two blend modes, and the pixels do the shaping instead of being covered up.

**The veil was being applied to every image.** It exists for copy sitting on media, and `cinematic-dark` sets it to 0.45 — which, on a plate with no text on it, is a 45% fog. It is now scoped to `bleed`, the treatment where content actually sits over the image.

**`invariants.sh` never checked new files.** `git ls-files` lists only *tracked* paths, so `treatment.tsx` — which contains a shadow — passed check 9 by not existing yet. New code is precisely where a violation arrives. `mine()` now passes `--others --exclude-standard`. This is the second fail-open found in that file in two phases, and both were found the same way: by breaking a check on purpose and watching nothing happen.

**Rule 19's own exemption could not be expressed as a grep.** A hard offset shadow with zero blur is allowed, and check 9 flagged it. Matching the permitted CSS shape was tried and is wrong — `0 0 20px red` contains the same `0 0` as the legal form, so the filter waved a bloom through. The exemption is now a named helper, `hardShadow()`, and the check asks "does this line call it" instead of judging a value's position in a space-separated list.

### Deviations

| | |
|---|---|
| The box is reserved by the AD's `ratios`, not by intrinsic `width`/`height` | The scene tree carries an `assetId` and no dimensions, so intrinsic sizing needs either a fetch in the renderer (rule 6) or dimensions in the schema. The art direction already has to declare `ratios` to crop, and one token reserving the box *and* cropping is fewer moving parts than two mechanisms |
| `/a/{id}` is a `web` route proxying to `api`, not an `api` route the page points at | Same-origin is the whole point. Pointing an `<img>` at the api origin works and would force the published page's CSP to name a second host, which is the one thing that stops `img-src 'self'` from being available |
| `ImageTreatment.overlay` is a `TextureLayer`, not a `TextureKind` | A kind alone cannot say how strong, how big, or in what colour. It is emitted into the same `--texture-N-*` namespace one past the ground layers, so `TextureLayerView` reads it with no second path |
