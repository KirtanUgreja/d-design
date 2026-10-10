# d-design docs

The product is an AI presentation maker whose edge is design: the model composes each slide in real HTML inside a per-deck design system, every slide is checked in a real browser, content is grounded in cited facts, and the deck exports as one offline `.html` file.

**Start with [code-guide.md](code-guide.md)**: every folder and file, how a deck is made step by step, every term, and the two databases.

## The design of the engine

| | |
|---|---|
| [v4/](v4/README.md) | The spec, the engine, content, the design engine and the bench |

## How the project works

| Directory | What it answers |
|---|---|
| [coderules/](coderules/README.md) | How the code stays consistent when an AI writes most of it. The eleven non-negotiables live here |
| [security/](security/README.md) | Threat model and every control, routed by threat |
| [techstack/](techstack/README.md) | Where every piece runs, which model, what the AI may call, and why each was chosen |
| [design/](design/README.md) | How **our own** app and website look and feel, never what the engine produces |

**Root files**

| | |
|---|---|
| [code-guide.md](code-guide.md) | **The code explained.** Every folder and file, how a deck is made step by step, every term, and the two databases |

## Conventions

- **Every directory has a README, and it lists every file in that directory.** Enforced by `./scripts/check-docs.sh`, which must pass before any commit touching `.md`
- **Every cross-document claim is a link.** One document owns a fact; the others point at it
- **Research is dated.** A platform or market claim without a date is unverifiable a year later
- **Paths in `AGENTS.md` are pointers, not imports.** Never prefix with `@`, which inlines the whole corpus into every session
