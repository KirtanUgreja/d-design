# v1 — the self-contained HTML deck

> The minimal product that proves the core claim: an AI-designed deck that **does not look template-made**, shipped as a **single self-contained `.html` file that runs offline**.

## What this release is

A marketer or founder types what they want (slide count, a brand kit, extra info), an AI-led interview iterates with them until they are satisfied, a mapping pass converts it into a per-slide spec, and a build pass generates each slide as a distinct HTML slide. The output is one `.html` file — fonts, styles, and motion embedded — that runs in any modern browser with **zero network requests**.

This is not Gamma's page-shaped product and not a template tool. It is a **generative design engine** that samples a per-deck design system from a large combinatorial space, then generates each slide individually so the deck reads as authored rather than assembled from repeated frames.

## Files

| File | What's in it |
|---|---|
| [README.md](README.md) | This map |
| [spec.md](spec.md) | The decisions and bets for v1 — theme, commitments, risks |
| [plan/README.md](plan/README.md) | The phases, dependency graph, and build order for v1 |
| [plan/00-foundations.md](plan/00-foundations.md) | Phase 00 — repo skeleton, the gate, the design-space skeleton |
| [plan/01-schema.md](plan/01-schema.md) | Phase 01 — the `Deck` schema and the design-system registry |
| [plan/02-interview.md](plan/02-interview.md) | Phase 02 — the AI-led brainstorm/intake interview |
| [plan/03-mapping.md](plan/03-mapping.md) | Phase 03 — the per-slide mapping pass |
| [plan/04-slide-builder.md](plan/04-slide-builder.md) | Phase 04 — the per-slide HTML generation |
| [plan/05-export.md](plan/05-export.md) | Phase 05 — single-file HTML export and offline check |
| [plan/06-renderer.md](plan/06-renderer.md) | Phase 06 — the pure renderer and the design tokens |
| [plan/07-visual-review.md](plan/07-visual-review.md) | Phase 07 — the human visual review loop |
| [plan/08-acceptance.md](plan/08-acceptance.md) | Phase 08 — the acceptance run and variety measurement |

## Find it fast

| If you need… | Go to |
|---|---|
| What v1 actually is, in one paragraph | [spec.md](spec.md) → Theme |
| The core bet and how it could fail | [spec.md](spec.md) → Commitments vs bets |
| What design variety mechanism we use | [spec.md](spec.md) → Locked decisions |
| The exact user flow | [spec.md](spec.md) → The flow |
| What we deliberately are not building | [spec.md](spec.md) → What changes from the last version |
| The build order | [plan/README.md](plan/README.md) → Recommended build order |
| Where the design-space skeleton lives | [plan/00-foundations.md](plan/00-foundations.md) |
| How images are generated (OpenRouter image models, embedded) | [spec.md](spec.md) → Images, [plan/04-slide-builder.md](plan/04-slide-builder.md) |
| How the offline single-file guarantee is checked | [plan/05-export.md](plan/05-export.md) |
| How we measure that decks look different | [plan/08-acceptance.md](plan/08-acceptance.md) |
