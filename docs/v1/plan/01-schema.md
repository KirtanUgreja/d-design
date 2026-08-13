# Phase 01 — schema

> This phase makes true that "a deck" and "a design family" have precise, validated shapes that both languages share.

**Depends on:** 00 · **Blocks:** 02, 03, 04, 06 · **Spec step:** Locked decisions → schema, no-styling

## Search

**Read first** — docs/coderules/python.md (Pydantic source of truth), docs/coderules/typescript.md (generated consumption), docs/coderules/patterns.md (rule 1, no-styling)

**Grep for** — the existing `schema/` directory (empty), any existing Pydantic models, the codegen script

**Verify externally** — current Pydantic v2, Zod v4; the JSON Schema → TS generator in use

## Make

The `Deck` schema (Pydantic, the source of truth), the generated TS types + Zod validator, and the design-system registry as validated data.

### Design decisions

- **The `Deck` schema owns the shape of a deck**: slides, each with a layout archetype, content blocks, motion intent, and (in later versions) charts. It carries **no presentational values** — no hex, no px, no font name, no duration. That is non-negotiable 7 and rule 1.
- **Images are a first-class block type.** An `image` block expresses *what* the image should be (subject, role: background / hero / illustration / chart companion), not *how it looks* — the design family's tokens style it, and the slide builder generates the image via OpenRouter image models. The schema has no field for a URL or a file path; a generated image is embedded as a data URI at export (`docs/v1/plan/05-export.md`), so the zero-network guarantee holds.
- **The design-system registry is data, validated by Pydantic.** A `DesignFamily` is a tuple of discrete axes (type pairing, layout archetypes, spacing rhythm, texture, color system, motion vocabulary). The registry is the single source of visual truth.
- **The no-styling invariant holds structurally** — a model that tries to emit `color: '#fff'` produces invalid JSON. A runtime backstop (the `PRESENTATIONAL` regex walk) is the second line.
- **The `Deck` schema is the boundary between the pipeline and the renderer.** It is what the mapping pass produces and the slide builder consumes.

## Verify

- [ ] `Deck` schema validates a golden deck JSON
- [ ] Generated TS types + Zod validator match the Pydantic source (regeneration is a no-diff)
- [ ] A model cannot emit a presentational value — it produces invalid JSON
- [ ] **Human:** the design registry reads as 10–15 genuinely distinct families, not 10–15 variations of one

## Skipped

- Charts — deferred to v2. The schema has a `chart` block shape but no renderer
- Video, 3D, dimensional blocks — v3

## Exit gate

- [ ] `Deck` schema and generated TS/Zod committed
- [ ] Design registry validated and committed
- [ ] No-styling backstop test passes
- [ ] Regeneration produces no diff
