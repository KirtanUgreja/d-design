# d-design docs

> The corpus was cleared on 2026-08-10 and **re-decided on 2026-08-13**. The product is now an **AI-designed HTML presentation** that exports as a **single self-contained `.html` file running offline** — built by a per-slide generative pipeline, not a fixed template. The new vision lives in [v1/](v1/README.md), [v2/](v2/README.md) and [v3/](v3/README.md).

## What happened, and why nothing here describes the product

Four directories were deleted: `v1/`, `v2/`, `v3/` and `reviews/`. They were not wrong so much as *layered* — three releases of decisions, each correcting the one before, with the corrections marked in strikethrough until finding the live decision meant reading the history of a dead one.

The judgement behind it: a product whose *"who is this for, and what is the artefact"* has changed is not a document that needs correcting. Improving it incrementally converges on a better version of the wrong thing.

**Everything deleted is in git history** — its last state is the commit immediately before this one, which includes the presentation pivot and the variety measurement made just before the clear. Nothing was lost; it was moved out of the way.

**The new vision (2026-08-13) re-decided the product.** The old system was a schema-valid `Scene` tree rendered through three fixed "art directions" — which was still a skeleton the model filled in. The new product is different: the design system is **generated per deck** from a combinatorial registry, each slide is **generated individually**, and the artefact is a **downloadable single-file HTML** that runs offline. The old three-art-direction approach is gone — it is precisely what the user deleted it for.

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

The vision is settled (2026-08-13). [v1/](v1/README.md) is the build; [versions.md](versions.md) specifies its shape; [findings.md](findings.md) is the evidence it should not have to rediscover.

**The one constraint on the build**, and it is a fact rather than an opinion:

- **The old code is a different product.** It was a schema-valid `Scene` tree rendered through three fixed art directions — precisely the "same skeleton, different skin" problem this product exists to solve. Nothing from the old codebase is a starting point. Recover a specific piece from git only if it is deliberately chosen, never because it happens to be there.

## Conventions

- **Every directory has a README, and it lists every file in that directory.** Enforced by `./scripts/check-docs.sh`, which must pass before any commit touching `.md`
- **Every cross-document claim is a link.** One document owns a fact; the others point at it
- **Research is dated.** A platform or market claim without a date is unverifiable a year later
- **Paths in `AGENTS.md` are pointers, not imports.** Never prefix with `@` — that inlines the whole corpus into every session
