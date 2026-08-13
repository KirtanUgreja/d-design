# Phase 17 — brand-kit-at-scale

> This phase makes true that a marketer's brand lives in the product — persisted, team-shared, file-uploaded, and mapped to any design family with contrast enforced.

**Depends on:** 16 · **Blocks:** 18 · **Spec step:** Locked decisions → brand kit

## Search

**Read first** — docs/v1/plan/02-interview.md (typed-text brand kit in v1), docs/design/app.md (the brand kit surfaces), docs/security/content-and-web.md (upload handling: magic bytes, SVG, decompression bombs)

**Grep for** — the brand-kit shape in the schema, the interview prompt, the design registry

**Verify externally** — current image extraction and color-mapping tools (open-license); the upload sanitization baseline

## Make

The brand kit becomes a real product surface: persisted, team-shared, and fed by **file upload** (logo, colors, fonts) with extraction, mapped to the design family's semantic roles with contrast enforced.

### Design decisions

- **Upload is a security surface, and it is now justified.** Magic bytes, SVG handling (served only through `<img>`), decompression bombs — the old upload rules arrive with the feature that needs them. Brand-kit upload sits in the isolated worker (the old fetch-worker placement).
- **Extraction is separate from mapping.** The brand kit extracts *facts* (a logo, a color, a font). Mapping turns those into the design family's *semantic roles* (accent, background, display face) — with contrast enforced, because a marketer's logo color is never guaranteed to work as text.
- **The kit is team-shared.** A team's brand is one artifact; the kit is a tenant-scoped row. RLS from phase 16 applies.
- **The kit maps to any design family.** The same brand in a bold family and an editorial family — the mapping is per-family, which is the abstraction claim applied to brand.

## Verify

- [ ] File-upload brand kit: logo, colors, fonts
- [ ] Extraction is separate from mapping; contrast enforced
- [ ] Team-shared, RLS-scoped
- [ ] The same brand maps to two different families and stays on-brand in both
- [ ] **Human:** a brand kit applied to two families reads as the same brand, twice

## Skipped

- Font *upload* (licensing) — deferred. The kit maps to registry families; custom font upload is a licensing decision, not a technical one

## Exit gate

- [ ] Upload, extraction, mapping, contrast enforcement
- [ ] Team-shared and RLS-scoped
- [ ] Same brand, multiple families, on-brand in all
