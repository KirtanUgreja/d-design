# d-design docs

> Design corpus for an AI presentation-experience engine. 49 documents plus a 13-file build plan, nothing built yet. Every directory has a README that routes to the exact file you need.

**New here?** Read [v1/scene-schema.md](v1/scene-schema.md) first. Everything else depends on that shape.

**Writing code?** Read [coderules/README.md](coderules/README.md) first. Eleven non-negotiables, and two of them prevent silent cross-tenant bugs.

## How this is organized

Three kinds of directory, and the difference matters when you are looking for something.

**Versioned** — what gets built, and when. A decision recorded in `v1/` stays as the record of what was believed at the time; when `v2/` changes it, `v2/` says so. Do not read a version directory as current truth without checking whether a later one supersedes it.

**Cross-cutting** — true across all versions, kept current rather than versioned. If these disagree with a version directory, these win.

**Dated** — a record of what was said on a day, superseded by nothing and superseding nothing. Never cite one as truth.

| Directory | | What it answers |
|---|---|---|
| [v1/](v1/README.md) | versioned | Generate, edit, publish. One art direction, end to end |
| [v2/](v2/README.md) | versioned | Creative range — same content, radically different experiences |
| [v3/](v3/README.md) | versioned | The wow release: derived, personalized, live, multilingual, dimensional |
| [techstack/](techstack/README.md) | current | Where every piece runs, which model, what the AI may call |
| [security/](security/README.md) | current | Threat model and every control, gated to the version that needs it |
| [coderules/](coderules/README.md) | current | How the code stays consistent when an AI writes most of it |
| [design/](design/README.md) | current | How **our own** app and website look and feel — not what the engine produces |
| [reviews/](reviews/README.md) | dated | What we showed people, and the prompt that produced it |

## Find it fast

Route by the question you arrived with, not by the topic name.

| If you need… | Go to |
|---|---|
| The scene tree — types, blocks, layouts, validation | [v1/scene-schema.md](v1/scene-schema.md) |
| How art direction tokens work | [v1/art-direction.md](v1/art-direction.md), then [v2/art-direction-system.md](v2/art-direction-system.md) for the full format |
| The four AI phases, and what a generation costs | [v1/ai-pipeline.md](v1/ai-pipeline.md) |
| Which model, and how it is chosen | [techstack/ai-stack.md](techstack/ai-stack.md) |
| What tools the AI may call | [techstack/pipeline-tools.md](techstack/pipeline-tools.md) |
| Why the AI never writes styling | [v1/spec.md](v1/spec.md) → "The bet" |
| What we are building, in what order | Each version's `spec.md` → "Build order" |
| The phase-by-phase plan for actually building v1 | [v1/plan/README.md](v1/plan/README.md) |
| Every locked decision, and its rejected alternative | Each version's `spec.md` → "Locked decisions", and [techstack/decisions.md](techstack/decisions.md) |
| Where a piece of infrastructure runs | [techstack/infrastructure.md](techstack/infrastructure.md) |
| Whether something is a security risk | [security/README.md](security/README.md) — it routes by threat |
| A rule about how to write the code | [coderules/README.md](coderules/README.md) |
| How our own site and app should look | [design/principles.md](design/principles.md) — and note it is *not* the art direction |
| An open product-design decision, with a recommended default | [design/questions.md](design/questions.md) |
| Why a competitor died | [v1/market.md](v1/market.md) |
| The legal obligations | [v3/compliance.md](v3/compliance.md) — EU AI Act, in force since 2 Aug 2026 |

## Reading order

If you are coming to this cold and want the argument rather than the reference:

1. [v1/spec.md](v1/spec.md) — the problem, the bet, and the locked decisions
2. [v1/scene-schema.md](v1/scene-schema.md) — the IR everything else is built on
3. [v1/art-direction.md](v1/art-direction.md) — the layer that makes the bet work
4. [v2/spec.md](v2/spec.md) — what proves the abstraction was real
5. [v3/spec.md](v3/spec.md) — what real users will actually see

Then [techstack/README.md](techstack/README.md) for how it runs, and [security/README.md](security/README.md) for what can go wrong.

## Conventions

- **Every directory has a README, and it lists every file in that directory.** If a file exists and its README does not mention it, the README is wrong.
- **Every cross-document claim is a link.** Nothing important is asserted twice in two places; one document owns it and the others point.
- **Superseded decisions are marked, not deleted.** See the *What this supersedes* table in [techstack/decisions.md](techstack/decisions.md).
- **Research is dated.** Sections marked *(researched August 2026)* are point-in-time and will go stale; treat version numbers and CVE floors as needing re-checking rather than trusting.
