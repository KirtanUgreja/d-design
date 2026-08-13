# Week 1 — Foundations, the scene schema, and the renderer

**Dates:** Mon 4 Aug – Sun 10 Aug 2026 · **Status:** Phase 00–05 complete

## What was done this week

The first week built the entire non-AI foundation of the product on an empty repository. The goal was to prove the load-bearing idea before any model work: *a typed scene tree plus a token layer can produce something worth looking at* — and to do it with no AI in the loop at all.

### 1. Research and the design corpus
- Wrote the design docs for three versions of the product, with researched detail for each.
- Built out the engineering docs that everything else follows: code rules, the threat model and security controls, and the tech-stack docs (what runs where, which model, and why each choice was made).
- Researched and recorded the market: why Gamma won (fast, mainstream, generic output) and why Tome died (built for everyone at once, could not convert its most engaged users into revenue). This became the wedge — the product is deliberately narrow, not a general deck tool.
- Made the whole doc corpus navigable in two hops and added project-level conventions (`AGENTS.md`, `CLAUDE.md`) plus a pre-commit enforcement hook.
- Added Python backend rules and aligned every doc to a two-language stack.

### 2. Phase 00 — Foundations
- Set up the repository, the quality gate (typecheck, lint, format), and the codegen chain.
- The gate and the docs invariants pass on an empty tree and start guarding the moment code returns.

### 3. Phase 01 — The scene schema
- Built the single most important contract in the system: the `Scene` tree, an intermediate representation that the AI, the editor, and the renderer all share.
- Pydantic owns the schema; TypeScript types and the Zod validator are generated from it, never hand-edited.
- Defined where cross-language agreement stops — the schema is the boundary.

### 4. Phase 02 — Art-direction design
- Hand-wrote three comps in real HTML/CSS — hero, statement, proof — and extracted the token groups from them.
- Two things the first draft got wrong were corrected before any tokens were written.
- These comps are the reference the renderer is judged against.

### 5. Phase 03 — Art-direction tokens
- Turned the comps into five token groups — **Type, Color, Rhythm, Motion, Texture** — typed against the schema.
- The rule that makes the whole product coherent: **the AI never emits styling.** No hex codes, no pixels, no durations, no font names. It emits content and intent; the token layer resolves intent into values.

### 6. Phase 04 — The renderer
- Built the pure renderer and all 11 scene primitives. One React tree, used everywhere — editor canvas, published page, embed, fullscreen — so what you edit is exactly what ships.
- The renderer core stays pure: no `mode` prop, no `process.env`, no `typeof window`. It must behave identically in every process it runs in.

### 7. Phase 05 — Publish, present, embed
- A generated experience can be published to a live URL, presented fullscreen, and embedded on any page.
- Fixed an RTL-mirror e2e flake by running the tests against a production build instead of `next dev`.

## This week's deliverables
- The full engineering corpus: `docs/coderules/`, `docs/security/`, `docs/techstack/`, `docs/design/`.
- v1 spec, scene schema, art-direction system, and AI-pipeline docs.
- A working repo: the gate, the codegen chain, the schema, the token layer, the renderer with 11 primitives, publish/present/embed.

## Next week's plan
- Add the model seam: one provider abstraction with no preferred vendor.
- Build the Build phase — the call that turns an approved outline into a scene tree.
- Build the Director phase — the call that turns a brief into an editable outline.
- Build the Intake phase — conversation, uploaded document, or URL becomes a `Brief`.
- Put the AI pipeline behind evals: golden briefs, injection payloads, and structural assertions.
