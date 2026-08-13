# Phase 00 — foundations

> This phase makes true that there is a skeleton at all: a repo, a gate, and the *shape* of the design space, before any model call or any rendering.

**Depends on:** — · **Blocks:** all · **Spec step:** Locked decisions → design system, pipeline

## Search

**Read first** — docs/coderules/README.md (the eleven), docs/versions.md (the shape), AGENTS.md (the pointers)

**Grep for** — nothing yet; this is the first phase on an empty tree. The gate (`scripts/check-docs.sh`, `scripts/hooks/pre-commit`, `scripts/hooks/commit-msg`) already works.

**Verify externally** — Node and Python toolchain versions in use; `pnpm` and `uv` availability; the `OPENROUTER_API_KEY` in `.env` is present.

## Make

The repository skeleton, the design-space skeleton, and the two gates that must stay green forever.

### Design decisions

- **Repo layout** — a single repo with `web/` (Next.js app), `schema/` (Pydantic source of truth), `render/` (the pure renderer), and `scripts/`. One repo keeps the codegen boundary visible and the gate single. This reverses the old "one repo per runtime" — the runtime count is smaller now, and a single gate is worth more than the isolation.
- **The design-space skeleton** — a `design-system` registry as *data*, not code. A `DesignFamily` is a tuple of discrete axes: type pairing, layout archetypes, spacing rhythm, texture, color system, motion vocabulary. v1 seeds ~10–15 families. A family is a *combination*, not a theme — two decks can draw the same family and still differ because layouts and content differ.
- **The gate** — the existing pre-commit hook, plus the docs gate. Typecheck, lint, format, and `schema` regenerates with no diff. This is non-negotiable 11.
- **No agent framework.** The pipeline is four plain sequential AI calls driven by a deterministic orchestrator. The "skills/plugins" live in the prompt layer, not in a runtime graph. This is the [agent-framework rule](../../techstack/ai-stack.md).

## Verify

- [ ] `./scripts/check-docs.sh` passes
- [ ] `pnpm install` and `uv sync --frozen` succeed
- [ ] The pre-commit hook runs typecheck, lint, format
- [ ] A trivial model call through the seam returns a schema-valid result
- [ ] **Human:** the design-space skeleton has at least 10 clearly distinct families, judged by eye

## Skipped

- Editor — not built. v1 is the lean flow: interview → mapping → build → review → export
- File uploads — not built. Brand kit is typed text in v1
- Auth, accounts, billing — v3

## Exit gate

- [ ] Repo skeleton in place, both package managers work
- [ ] Gate is green and runs on commit
- [ ] Design-space skeleton exists as data with ~10–15 families
- [ ] The model seam returns one schema-valid call
