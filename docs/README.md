# d-design docs

> **The live plan is [v4/](v4/README.md), decided 2026-09-26.** The product is an AI presentation maker whose edge is design: the model composes each slide in real HTML inside a per-deck design system, every slide is checked in a real browser, content is grounded in cited facts, and the deck exports as one offline `.html` file.

## What happened

| Date | |
|---|---|
| 2026-08-10 | The first corpus and codebase were cleared |
| 2026-08-13 | The product was re-decided as an offline single-file HTML deck; `v1/`–`v3/` were written and built |
| 2026-09-26 | An audit found every generated deck was a heading and one line of text on a flat ground ([findings.md](findings.md) → "Measured 2026-09-26"). `v1/`–`v3/` were deleted and replaced by [v4/](v4/README.md) |

**Everything deleted is in git history.** The last state of `v1/`–`v3/` and of the code they describe is commit `8169fd9`.

**What changed, in one line:** the model may now write slide HTML and CSS, inside theme tokens. "The AI never writes styling" is reversed ([v4/spec.md](v4/spec.md) → Locked decisions).

## The live plan

| | |
|---|---|
| [v4/](v4/README.md) | What gets built and why: the spec, the engine, content, the design engine, the bench, and phases 21–29 |

## What survives a vision change

**Current, not versioned** — about how code is written, what can attack it, what runs where, and how our own surfaces look. Updated to v4 on 2026-09-30.

| Directory | What it answers |
|---|---|
| [coderules/](coderules/README.md) | How the code stays consistent when an AI writes most of it. The eleven non-negotiables live here |
| [security/](security/README.md) | Threat model and every control, routed by threat |
| [techstack/](techstack/README.md) | Where every piece runs, which model, what the AI may call, and why each was chosen |
| [design/](design/README.md) | How **our own** app and website look and feel — never what the engine produces |

**Root files**

| | |
|---|---|
| [versions.md](versions.md) | **How a version is documented.** The required files, the phase anatomy, and when to start fresh |
| [findings.md](findings.md) | **Evidence, not direction.** Measurements of this codebase, model behaviour, the category, platform facts with dates, and process lessons |

## What comes next

[v4/plan/README.md](v4/plan/README.md) holds the status. Phase 21 (reset) is in progress: the docs are written; the code reset, the gate and the bench are not started.

**The one constraint on the build:** the v3 code still in the tree is a different product. Phase 21 deletes it. Port a piece only where a phase names it.

## Conventions

- **Every directory has a README, and it lists every file in that directory.** Enforced by `./scripts/check-docs.sh`, which must pass before any commit touching `.md`
- **Every cross-document claim is a link.** One document owns a fact; the others point at it
- **Research is dated.** A platform or market claim without a date is unverifiable a year later
- **Paths in `AGENTS.md` are pointers, not imports.** Never prefix with `@` — that inlines the whole corpus into every session
