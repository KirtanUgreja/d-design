# Phase 06 — renderer

> This phase makes true that the design family's tokens become actual rendered slides — and that the renderer is pure, so editor and export cannot drift.

**Depends on:** 04 · **Blocks:** 05 · **Spec step:** Locked decisions → renderer, no-styling

## Search

**Read first** — docs/coderules/patterns.md (rule 2, pure renderer; rule 1, no-styling), docs/techstack/frontend.md, docs/coderules/performance.md

**Grep for** — the design registry, the `Deck` schema, the slide-builder output

**Verify externally** — current React version, Motion (`motion/react`), whether the renderer should be React or vanilla for a single-file offline artefact

## Make

The pure renderer: a function from `(deck, designFamily, motion)` to HTML. It renders the slides with the design family's tokens (type, spacing, texture, color, motion) and produces the bytes the exporter inlines.

### Design decisions

- **The renderer is pure and mode-free** — non-negotiable 6. It contains no knowledge of editor, export, or present. Behavior is injected from outside. This is what guarantees "what you edit is what you ship."
- **The renderer consumes the design family, not raw styling.** The model emits *what* is on the slide and *which archetype*; the renderer applies *how it looks* from the family's tokens. No hex, no px, no font name reaches the renderer from the model.
- **The renderer renders image blocks.** An `image` block is a generated data-URI asset framed and styled by the family — its crop, mask, and overlay come from the tokens, not from the model. The renderer never fetches an image; the exporter inlines it (`docs/v1/plan/05-export.md`).
- **The renderer is the single source of visual truth.** A lint rule bans any `mode` prop or mode conditional, and bans Tailwind/utility classes in the renderer — the design family's CSS custom properties are the only styling. This is the no-styling invariant seen from the other side.
- **Motion vocabulary comes from the design family.** The family declares its motion intent (which reveals, what pacing); the renderer applies it via Motion. In the single-file artefact, the motion runtime is tiny and inlined.
- **The navigation shell is part of the renderer output.** The exported file is slide-based: a fullscreen container, a keydown handler (arrows, Space, Home/End, Esc for fullscreen), on-screen prev/next buttons, a slide counter, and swipe on touch. It is the same "present" wrapper the old docs described, but it ships *inside the file* rather than on a hosting page (`docs/v1/spec.md` → Deck navigation).

## Verify

- [ ] The renderer produces HTML for every archetype in the registry
- [ ] The same `(deck, family)` produces the same bytes in editor and export
- [ ] A lint rule bans `mode` props and Tailwind inside the renderer
- [ ] The navigation shell ships in the file: arrows, Space, buttons, counter, swipe
- [ ] **Human:** the rendered slides carry the family's character — type, spacing, texture, color, motion

## Skipped

- A separate editor — v2. v1 renders to HTML only
- Complex charts — v2

## Exit gate

- [ ] Renderer is pure and mode-free
- [ ] It renders every archetype
- [ ] Editor/export byte-identity holds
