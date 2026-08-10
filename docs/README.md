# d-design docs

> The corpus was cleared on 2026-08-10. What remains is everything true regardless of what the product turns out to be. **The product itself is being re-decided from the vision up, and no version directory exists yet.**

## What happened, and why nothing here describes the product

Four directories were deleted: `v1/`, `v2/`, `v3/` and `reviews/`. They were not wrong so much as *layered* — three releases of decisions, each correcting the one before, with the corrections marked in strikethrough until finding the live decision meant reading the history of a dead one.

The judgement behind it: a product whose *"who is this for, and what is the artefact"* has changed is not a document that needs correcting. Improving it incrementally converges on a better version of the wrong thing.

**Everything deleted is in git history** — its last state is the commit immediately before this one, which includes the presentation pivot and the variety measurement made just before the clear. Nothing was lost; it was moved out of the way.

## What survives, and why

**Current** — kept because it is about how code is written, what can attack it, what runs where, and how our own surfaces look. None of that is a product decision.

| Directory | What it answers |
|---|---|
| [coderules/](coderules/README.md) | How the code stays consistent when an AI writes most of it. The eleven non-negotiables live here |
| [security/](security/README.md) | Threat model and every control, routed by threat |
| [techstack/](techstack/README.md) | Where every piece runs, which model, what the AI may call, and why each was chosen |
| [design/](design/README.md) | How **our own** app and website look and feel — never what the engine produces |

**Root files** — about the corpus, not about a version of the product.

| | |
|---|---|
| [versions.md](versions.md) | **How a version is documented.** The required files, what each owns, the phase anatomy, the conventions, and when to start fresh instead of extending. Read this before writing the next version directory |
| [findings.md](findings.md) | **Evidence, not direction.** Measured facts about this codebase, LLM behaviour, the category, platform status with dates, and the process lessons. Nothing here says what to build |

## What comes next

A new version directory, written after the vision is settled rather than before. [versions.md](versions.md) specifies its shape; [findings.md](findings.md) is the evidence it should not have to rediscover.

**Two constraints on whatever gets decided**, and both are facts rather than opinions:

- **The code exists.** A Python API, a TypeScript renderer, a Pydantic-owned schema, a working pipeline, three art directions and a passing acceptance run. Docs describing a product that ignores all of it are a rewrite rather than a plan — which may be the right call, but it should be a decision rather than something discovered in week three.
- **~180 source files carry comments pointing at the deleted docs.** They explain *why* code looks the way it does, and they now point into git history. Leave them: rewriting 180 files of comments before the product is decided is churn. They get corrected as the code is touched.

## Conventions

- **Every directory has a README, and it lists every file in that directory.** Enforced by `./scripts/check-docs.sh`, which must pass before any commit touching `.md`
- **Every cross-document claim is a link.** One document owns a fact; the others point at it
- **Research is dated.** A platform or market claim without a date is unverifiable a year later
- **Paths in `AGENTS.md` are pointers, not imports.** Never prefix with `@` — that inlines the whole corpus into every session
