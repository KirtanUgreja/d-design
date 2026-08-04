# Phase 09 — Editor

> Select → property panel → element-scoped prompt. Roughly a fifth the cost of a design canvas and it covers about 90% of edits — because every edit is the same patch against one block, whether a human or a model produced it.

**Depends on:** [06](06-model-seam-and-build.md), [04](04-renderer.md) · **Blocks:** the end-to-end run · **Spec step:** 8

---

## Search

**Read first**

- [../scene-schema.md](../scene-schema.md) → "Editing" and "What the property panel exposes" — the panel's contents are a table, not a design exercise
- [../ai-pipeline.md](../ai-pipeline.md) → "Phase 4 — Edit"
- [../../techstack/frontend.md](../../techstack/frontend.md) → "The editor" — Zustand, and why undo/redo is the feature that makes AI editing safe to try
- [../../coderules/patterns.md](../../coderules/patterns.md) → rule 2. The editor overlays selection *around* the rendered output, never by passing `mode="editor"` into the core
- [../../coderules/performance.md](../../coderules/performance.md) → hot path 3

**Grep for**

- `src/schema/patch.ts` — `BlockPatch` exists from phase 01. Property-panel edits and AI edits produce the **identical** shape, so there is one code path and one place validation lives
- `src/features/renderer/index.ts` — the editor imports the index and nothing deeper. If a selection overlay needs to reach into `renderer/blocks/`, the design is wrong
- `src/lib/ai/complete.ts` — Edit is `phase: 'edit'`. No second call path
- Before writing a debounce: check `lib/`. If it is not there, three lines and own it — never a dependency for a debounce

**Verify externally**

- Zustand's current API for a store with structural sharing on an undo stack. This is the only place in v1 where state management is load-bearing rather than incidental

---

## Make

```
src/features/editor/
  index.ts
  store.ts               Zustand: tree, selection, patch, undo, redo, status
  canvas.tsx             selection overlay wrapping SceneRenderer
  property-panel.tsx     generated from the schema, not hand-written per block
  ai-edit.ts             element-scoped prompt → the same patch shape
  editor.test.ts
```

### One patch shape, two producers

```ts
{ sceneId, blockId, props: Partial<BlockProps> }
```

The property panel produces it. The element-scoped prompt produces it. **A full regeneration is never triggered by an edit.** The tree is re-validated after every patch, in one place.

That single shape is what makes "make this headline punchier" structurally incapable of restyling the page or rewriting a neighbour. The Edit call sees one block and returns patched props; there is no field in its output where anything else fits.

### The panel is generated, not written

[../scene-schema.md](../scene-schema.md) has a table of what each block exposes. That table is the schema, so **derive the panel from the schema** rather than hand-writing eleven panels. Eleven hand-written panels is eleven places for a new prop to be forgotten, and it is precisely the duplication shape [../../coderules/ai-authorship.md](../../coderules/ai-authorship.md) measures.

The consequence is the good one: because no prop is presentational, **the panel is structurally incapable of offering a font size or a colour picker.** The thing users most expect and most reliably use to wreck a design cannot be built, and not because someone decided not to build it.

`AbstractVisual`'s **reroll seed is a button, not a number field.** It is the affordance users will reach for constantly.

`Slot` exposes `description` only. The code is not hand-editable in v1, and an AI edit operates on the description.

### Undo/redo earns the store

A stack of past trees with structural sharing. It is the feature that makes AI-assisted editing safe to *try* — a user who can undo instantly will experiment, and experimentation is where this product is fun. **Build it with the editor, not after**, because retrofitting undo into a store that mutates in place is a rewrite.

### Selection lives outside the renderer

The canvas overlays selection, handles, and the panel *around* the rendered output. Nothing about selection enters `SceneRenderer`. The lint rule from phase 00 enforces it and the guarantee it protects is the product's spine: what you edit is byte-for-byte what you publish.

### The Edit call

**In:** one block, its scene context, and a user instruction. **Out:** `Partial<BlockProps>`. One tier-0 tool: `read_block(id)`, so an edit is a diff rather than a rewrite.

**Debounce AI edits.** Never fire a model call per keystroke.

Re-validate the tree after every patch, **against the current art direction's budgets** — which is the same mechanism v2's reskin will use ([../../v2/transformations.md](../../v2/transformations.md)). Building it that way costs nothing now.

**Caching is probably a loss here.** Edit prefixes are small and the calls are frequent; a prefix under the route's minimum plus a write premium makes cached edits *more* expensive. Measure before enabling.

### Two open questions, resolved

**Scene reordering across intents** — resolved in [01](01-scene-schema.md): `intent` decouples from position. Dragging `proof` above `problem` does not make the field a lie. The only positional rule is that the `hook` is first, and the editor refuses that drag rather than rewriting intents.

**Where `AbstractVisual` seeds come from** — derive from the scene id, not from a random per generation. A regenerated scene that looks different for no reason is a bug the user cannot explain, and reroll stays an explicit user action.

---

## Verify

**The gate** — green.

**The patch** ([../spec.md](../spec.md) → Verification, row 5)

- [ ] Patch a block: the tree stays valid, and **only the target block changed.** Deep-compare every other block
- [ ] A patch producing an invalid tree is rejected and the previous tree survives intact
- [ ] A property-panel edit and an AI edit of the same field produce byte-identical patches
- [ ] A patch that would break a structural rule — a second `Headline` in a scene, a region that does not exist on the layout — is refused

**Undo/redo**

- [ ] Undo restores the exact previous tree, deep-equal
- [ ] Redo after undo restores the exact next tree
- [ ] Undo across an AI edit works the same as across a panel edit — one stack, not two

**The panel**

- [ ] The generated control set for every block type contains **no** colour, size, font, duration, or easing control. Assert it programmatically by walking the generated controls; this is the no-styling invariant seen from the UI side
- [ ] Adding a prop to a block schema makes the control appear without touching panel code
- [ ] Reroll seed is a button

**Purity**

- [ ] `SceneRenderer` still takes no `mode` prop, and the editor's selection overlay is entirely outside it. Lint proves it; read the diff anyway

**Performance** — hot path 3

- [ ] A keystroke in the panel re-renders one block, not the tree. Check with the profiler, not by feel
- [ ] AI edits are debounced

**Security**

- [ ] Edit output is Zod-parsed like every other model response
- [ ] An edit instruction attempting to change a neighbouring block, restyle the page, or set a `href` outside the Brief's URL set is structurally unable to — the patch shape has no field for it, and the post-build checks still run on the patched tree

---

## Skipped

| Not built | Trigger |
|---|---|
| Freeform canvas / drag-anywhere | Not in v1. It is roughly 5× the cost of the panel for the last 10% of edits |
| Version history | Not in v1. Undo/redo is per-session; persisted history is a v3 concern |
| Collaboration | Not in v1, and it changes the store's shape fundamentally — worth knowing before Zustand is chosen, and it does not change the choice for a single user |
| Regenerating a whole scene from the editor | Clearly needed eventually. The open question is whether it re-reads neighbours for consistency; resolve it when a real user asks, not before |
| Hand-editing `Slot` code | v1 exposes `description` only. Hand-editing sandboxed code is a feature for a different product |

---

## Exit gate

- [ ] One patch shape, two producers, one validation site
- [ ] Only-the-target-block-changed test passing
- [ ] Undo/redo across both edit kinds
- [ ] The property panel is generated and provably cannot offer a presentational control
- [ ] The renderer is still pure
- [ ] Editing feels instant
