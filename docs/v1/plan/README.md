# v1 — plan

## Status

| Phase | Status |
|---|---|
| [00 — foundations](00-foundations.md) | done |
| [01 — schema](01-schema.md) | done |
| [02 — interview](02-interview.md) | done |
| [03 — mapping](03-mapping.md) | done |
| [04 — slide-builder](04-slide-builder.md) | done |
| [05 — export](05-export.md) | done |
| [06 — renderer](06-renderer.md) | done |
| [07 — visual-review](07-visual-review.md) | done |
| [08 — acceptance](08-acceptance.md) | in progress |

## Dependency graph

```
00 foundations
   │
   ▼
01 schema ──────────────┐
   │                    │
   ▼                    ▼
02 interview        03 mapping ──▶ 04 slide-builder ──▶ 06 renderer ──▶ 05 export
   │                    │                                     │
   └────────────────────┴─────────────────────────────────────┘
                                                                │
                                                                ▼
                                                            07 visual-review
                                                                │
                                                                ▼
                                                            08 acceptance
```

## Recommended build order

1. **00 foundations** — repo skeleton, the gate, the design-space skeleton. Everything depends on this.
2. **01 schema** — the `Deck` schema and design-system registry. Defines what "a deck" and "a design family" are.
3. **02 interview** — the AI-led interview that produces the outline. Needs the schema (the outline is the first schema-validated shape).
4. **03 mapping** — outline → per-slide spec. Needs the schema and the outline.
5. **04 slide-builder** — per-slide HTML generation. Needs the mapping and the design registry.
6. **06 renderer** — the pure renderer and design tokens. Can be developed in parallel with 04, but the builder feeds it.
7. **05 export** — single-file HTML export and offline check. Needs the renderer and the built slides.
8. **07 visual-review** — the human visual review loop. Needs a built deck.
9. **08 acceptance** — the acceptance run and variety measurement. Needs everything.

Phases 04 and 06 are the heart. Everything else is scaffolding around the per-slide generation that must actually be beautiful and varied.
