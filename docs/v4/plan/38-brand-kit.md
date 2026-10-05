# Phase 38 — brand kit and logo

> This phase makes true that a user can give us their logo and brand colour once, and every deck after that carries them correctly: the logo placed by code where the composition leaves room for it, legible on every ground, and the deck's generated look built around the brand instead of beside it.

**Depends on:** 29 (accounts: a kit belongs to someone), 36 (generated looks) · **Blocks:** nothing · **Spec step:** Commitments → brand · **Size:** M · **Owner's ask:** 2026-10-05 — "what if user wants to add its logo or something to it?"

## Today

| Have | Missing |
|---|---|
| `brand_hex` in the sampler: a brand colour sets the hue and limits the palettes | No way to enter it in the app |
| A generated mark drawn from the deck's title | No user logo; nothing is uploaded in v4 ([content-and-web.md → Uploads](../../security/content-and-web.md#uploads)) |
| The typed brand kit (text only) | No saved kit, so it is retyped per deck |

## Make

- **The kit** — one per account: logo (light and dark variants, optional), up to two brand colours, an optional brand font *name*, and where the logo goes (cover only · cover and ask · every slide's corner). Saved, reused, editable from the composer.
- **Upload, hostile by default.** Every control in [content-and-web.md → Uploads](../../security/content-and-web.md#uploads) returns before the button does: magic bytes, size and dimension caps before decode, a server-made key, parsing in an isolated worker.
  - **PNG / JPEG / WebP** are re-encoded by Pillow (already in the ledger for exactly this) to a trimmed PNG, capped at 1600 px.
  - **SVG** is sanitised, rasterised in the worker to PNG at two sizes, and the PNG is what ships. No user SVG ever reaches a slide, so no SVG sanitizer has to be perfect.
  - The result embeds as a data URI: the export stays one offline file.
- **`<dd-logo>`** — like `<dd-chart>`: the model places an empty element where the composition has room for it; **code** fills it with the image. The model never sees or writes the image. If the model leaves no room, code puts it in the safe-area corner the composition left emptiest (phase 36 descriptors know where that is).
- **Legible on every ground.** Code measures the logo's luminance against the ground behind it and picks the variant that passes (light, dark, or a one-colour version made by using the logo as a mask filled with an ink token). A logo that fails every variant on a ground is not placed there, and the slide is flagged.
- **The look is built around the brand.** The kit's colours feed `brand_hex` (accent fitted to WCAG 2 + APCA as today; if the brand colour fails as text it becomes a field, never text). No brand colour given → the dominant colour is read from the logo and **proposed**, not applied, until the user accepts it.
- **Brand font by name.** Mapped to the nearest family in our registry by metrics and class, shown as "closest match: X". Uploading a font file is skipped (licensing and hostile-file cost).
- **QA:** a new check that the logo stays inside the safe area, at or above a minimum size, and is not overlapped by text.

### Design decisions

- **The logo is the one thing on the slide not generated.** It is placed, never restyled: no recolour except the one-colour fallback, no crop, no effects.
- **Raster-only output.** Rasterising SVG in the worker removes a whole class of attacks for the cost of a few kilobytes.
- **The generated mark steps back.** With a logo present, the deck's generated mark is not drawn: two emblems compete.

## Verify

- [ ] Hostile-file corpus (polyglots, decompression bombs, SVG with script and external refs, wrong extensions) — every one rejected or neutralised
- [ ] A logo on every bench ground, light and dark: the chosen variant passes contrast, or the slide is flagged
- [ ] Export with a logo makes zero network requests (the offline test)
- [ ] The model's prompt never contains the image or its bytes (a test)
- [ ] **Human:** five real logos across 20 decks — the owner finds none badly placed, too small, or illegible

## Skipped

- Font file upload — trigger: three paying teams ask, with licences
- Multiple kits per account (agencies) — trigger: phase 29's teams ship
- Brand guidelines PDF parsing — trigger: never without an isolated parser and a reason

## Exit gate

- [ ] Hostile corpus 100% handled
- [ ] Logo legible on 100% of the slides it is placed on
- [ ] The owner's logo wall passes
