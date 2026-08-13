# Phase 02 — interview

> This phase makes true that the user's intent is captured by an AI-led conversation, not a single prompt box, and that the result is an approved outline the mapping pass can trust.

**Depends on:** 01 · **Blocks:** 03 · **Spec step:** The flow

## Search

**Read first** — docs/design/app.md (intake is an interview, not a chat), docs/design/principles.md (appeal has to be aimed), docs/security/prompt-injection.md (user input reaches an LLM)

**Grep for** — the old intake/prompt code in git history (`git log` on the cleared tree), the `Brief` shape

**Verify externally** — current model that handles multi-turn instruction-following well; the OpenRouter seam

## Make

The interview pass: a plain, deterministic orchestrator drives an AI-led multi-turn conversation that elicits the topic, the slide count, the brand kit, the audience, and the goal — and produces an **outline** the user approves.

### Design decisions

- **The interview is an AI-led Q&A, not a chat.** It asks the questions that matter (topic, audience, goal, slide count, brand kit, must-haves) and iterates until the user is satisfied. It is short and skippable — the value it produces is the approved outline.
- **The brand kit in v1 is typed text** — colors, fonts, vibe — not file upload. File upload is a whole security surface (upload handling, magic bytes, SVG, decompression bombs) that v2 takes on. Typed text proves the flow.
- **The outline is the first schema-validated shape.** It is the approved-claims record — the claims the deck will make — and the trust device. Risk 2 in `v1/spec.md` is about invented claims, and the outline is where that is prevented.
- **Prompt injection is live from the first model call.** The interview input is untrusted; the outline is schema-validated at the boundary. See [security/prompt-injection.md](../../security/prompt-injection.md).

## Verify

- [ ] The interview produces a schema-valid outline
- [ ] The user can approve or reject the outline; rejection loops back
- [ ] The outline records claim provenance (which claims came from the user, which from the model)
- [ ] **Human:** an interview with a sample brief produces a tight outline a marketer would approve

## Skipped

- File upload (brand kit) — v2
- URL fetching — v3
- Templates — deliberately never. The whole point is no fixed frames

## Exit gate

- [ ] Interview produces an approved outline
- [ ] Outline is schema-validated at the boundary
- [ ] Claim provenance is recorded
