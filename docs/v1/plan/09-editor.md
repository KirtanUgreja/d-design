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

### Design the absence, because the absence is the product

The panel being structurally incapable of a colour picker is the good news for the architecture and an open interaction-design problem for the user, who **will** look for one. It is not hidden, it is unrepresentable — and that distinction is invisible to a person who just wants the headline smaller. This is the moment a first-time user decides whether the product is a tool or a toy, and it is the single most likely first-session churn cause in v1 ([../../design/app.md](../../design/app.md)).

Undesigned, it is a bug report. Designed, it is the pitch: *you cannot make this ugly.*

Four things this phase has to build, none of them large:

| | |
|---|---|
| **An answer at the point of reaching** | Inline, once, positive, in the place the control was expected. Not a docs page and not an onboarding tour — by the time someone opens documentation to ask why they cannot change a colour, the session is already lost |
| **The refusal is a designed artifact with an owner** | Someone types *"make the headline smaller"* into the element prompt. The Edit call has no field for it, so the model refuses — and that copy has to be written deliberately, offering **emphasis** instead. It is not an error string written at 2am, and it is the most-read sentence the product will ship |
| **Resolved tokens visible, read-only** | Seeing the system is disarming. Editing it is the product's collapse |
| **Instrument the reach** | Count every hunt for a styling control. Cheapest high-signal metric in the product, and it is the number that decides whether the answer above is working |

The replacement affordances must look **more** powerful than what they replace, because they are: the art direction instead of a colour picker, emphasis instead of a font size, the brand kit instead of a hex field ([10](10-brand-and-uploads.md)), reroll instead of nudging a gradient.

**Reserve the art-direction switcher's toolbar space now.** v2 fills it ([../../v2/spec.md](../../v2/spec.md)). Retrofitting it into an overflow menu is how the headline feature of the next release arrives looking like a setting.

**No CSS or HTML export**, in any version. It is the fastest available route to becoming a worse Webflow.

### The canvas is true scale, always

Fit-width and 100%, nothing else. What you edit is byte-for-byte what you publish, and any scaling weakens the guarantee the whole product rests on. Two consequences for this phase: selection is **a hairline and a label**, not a saturated box over a designed page, and the element-scoped prompt lives **inline under the selection, always in the same place** — it appears only with a selection, because an always-present prompt box invites page-level requests the patch shape cannot serve.

Mobile is view-and-present only. Editing a design surface on a phone is a different product.

### Undo/redo earns the store

A stack of past trees with structural sharing. It is the feature that makes AI-assisted editing safe to *try* — a user who can undo instantly will experiment, and experimentation is where this product is fun. **Build it with the editor, not after**, because retrofitting undo into a store that mutates in place is a rewrite.

### Selection lives outside the renderer

The canvas overlays selection, handles, and the panel *around* the rendered output. Nothing about selection enters `SceneRenderer`. The lint rule from phase 00 enforces it and the guarantee it protects is the product's spine: what you edit is byte-for-byte what you publish.

**Built 2026-08-09, with one addition to the renderer worth defending.** The overlay has to find a block's box in the DOM, and the only alternatives were reaching into `renderer/blocks/` — which this phase's Search section names as proof the design is wrong — or measuring nothing. So `Reveal` now stamps `data-block-id` on the wrapper it already renders. That is **identity, not a mode**: emitted unconditionally, byte-identical in all three processes, carried by the published page too, and readable without branching on anything. The scene has carried `id="scene-…"` since phase 04 for exactly the same reason. A `mode` prop would have been the other thing, and it is still banned.

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
- [ ] **"Make the headline smaller" produces a written refusal that offers emphasis** — not a silent no-op, not a stack trace, not a generic "I can't help with that"
- [ ] The styling-control reach is counted. Confirm the event fires by looking for a colour picker yourself

**Purity**

- [ ] `SceneRenderer` still takes no `mode` prop, and the editor's selection overlay is entirely outside it. Lint proves it; read the diff anyway

**Performance** — hot path 3

- [ ] A keystroke in the panel re-renders one block, not the tree. Check with the profiler, not by feel
- [ ] AI edits are debounced

**Security**

- [ ] Edit output is schema-parsed like every other model response
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
| A `motion` control | `motion` lives on `Block`, not on `props`, and `BlockPatch` carries `props` only — offering it would mean widening the one shape both producers share, which is not a decision to make from inside a panel. [../scene-schema.md](../scene-schema.md) does list it as editable, so this is owed. Trigger: add `motion?` to `BlockPatch`, regenerate, handle it beside `props` in `applyPatch` |
| Delete and reorder, for blocks and scenes | Also in the scene-schema table, and also not a `BlockPatch`. They are tree operations, so they want their own store actions and their own undo entries — a bigger design than this phase's patch path, and nothing in the exit gate turns on them |
| Loading a real experience into the editor | `/edit/[id]` reads the phase 01 `full` fixture. `api` has no scenes-by-experience read: publish stores a whole `Experience`, and Build streams scenes to the client without persisting them. Trigger: that GET exists |
| The art-direction switcher's toolbar space | The doc says reserve it now. It is not reserved — there is no toolbar yet, and reserving space in a chrome that does not exist is not reservation. Trigger: the editor grows a toolbar, which is before v2 fills it |

---

## Exit gate

- [x] One patch shape, two producers, one validation site — `web/src/features/editor/patch.ts` is the only place a patch is applied, and both producers construct the same `BlockPatch`. The AI's half arrives as `EditResult.props` and is handed to the identical function, which is why there is one undo stack rather than two
- [x] Only-the-target-block-changed test passing, and asserted by **identity** rather than deep-compare — a deep compare passes even when an untouched block was rebuilt identically, and a rebuilt block is the re-render hot path 3 forbids
- [x] Undo/redo across both edit kinds, plus a refused patch not consuming an undo step and a new edit forking the redo branch
- [x] The property panel is generated and provably cannot offer a presentational control — `controls.ts` walks the generated Zod union and contains no list of block types; `editor.test.ts` walks every derived control against `PRESENTATIONAL`
- [x] A user hunting for a colour picker gets an answer where they looked — `StylingAnswer`, inline in the panel, naming emphasis, the brand kit and reroll. The reach is counted
- [x] The renderer is still pure — `SceneRenderer` takes the same three props; selection is measured from outside via `data-block-id`, which is identity rather than a mode (see below)
- [ ] **Editing feels instant** — not measured. The structural-sharing property it depends on is tested, and the React Compiler is on, but "check with the profiler, not by feel" has not been done

**Verified live 2026-08-09** at `/edit/<uuid>`: select a headline, edit `text` in the panel and watch the renderer update with the selection box tracking the reflow, then type "make the headline smaller and dark blue" into the element prompt and get back a written refusal offering the emphasis field and the brand kit, with the tree untouched.
