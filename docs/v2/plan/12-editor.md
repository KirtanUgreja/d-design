# Phase 12 — editor

> This phase makes true that the product has a real editing surface — change copy, reorder slides, re-skin — and that editing is instant, local, and undoable.

**Depends on:** 10 · **Blocks:** 13, 14 · **Spec step:** Locked decisions → editor, re-skin

## Search

**Read first** — docs/techstack/frontend.md (editor, Zustand, undo/redo, Tailwind-on-chrome-only), docs/coderules/patterns.md (rule 2, pure renderer), docs/design/app.md (the editor surfaces)

**Grep for** — the `Deck` schema, the renderer, the v1 lean flow

**Verify externally** — current Zustand, Motion, shadcn/ui; how the editor patches one block and re-renders the minimum

## Make

The editor: a browser surface where a generated deck can be edited — copy changes, slide reorder, block re-skin, undo/redo. It wraps the pure renderer; it never reaches inside it.

### Design decisions

- **The editor wraps the pure renderer.** The renderer core (from v1 phase 06) is untouched — selection, the property panel, and drag handles overlay the rendered output. The `mode`-prop ban and the byte-identity guarantee hold. What you edit is what you export.
- **Editing is local patches, no model call per keystroke.** Copy edits and re-skin are local; a regenerate is an explicit, model-calling action. This keeps editing instant and undoable.
- **Re-skin is the abstraction claim demonstrated.** Switch a deck's design family in seconds — same content, different design system. This is the strongest proof that the design system is a layer, not a theme, and it is the marketing demo.
- **Undo/redo is the feature that makes AI editing safe to try.** Built with the editor, not after.
- **Tailwind stays on chrome only.** The rendered slides are CSS custom properties from the family; a Tailwind class in the renderer is a lint failure.

## Verify

- [ ] Change copy, reorder slides, re-skin, undo/redo
- [ ] Editor and export produce byte-identical output for the same `(deck, family)`
- [ ] The `mode`-prop ban holds in the renderer
- [ ] **Human:** editing a generated deck feels instant and safe (undo works)

## Skipped

- Collaboration / multi-user — v3
- The property panel's full schema-generated surface — v3 (v2 has the essential controls)

## Exit gate

- [ ] Editor works and is instant
- [ ] Re-skin works in seconds
- [ ] Editor/export byte-identity holds
