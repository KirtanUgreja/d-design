# v2 — plan

## Status

| Phase | Status |
|---|---|
| [09 — design-engine](09-design-engine.md) | not started |
| [10 — layout-generation](10-layout-generation.md) | not started |
| [11 — charts](11-charts.md) | not started |
| [12 — editor](12-editor.md) | not started |
| [13 — vision-critic](13-vision-critic.md) | not started |
| [14 — pdf-export](14-pdf-export.md) | not started |
| [15 — variety-gate](15-variety-gate.md) | not started |

## Dependency graph

```
09 design-engine
   │
   ▼
10 layout-generation ──▶ 11 charts ──▶ 13 vision-critic
   │                        │
   ▼                        ▼
12 editor ──────────────▶ 14 pdf-export
   │
   ▼
15 variety-gate
```

## Recommended build order

1. **09 design-engine** — grow the registry to 30+, still data. Everything downstream depends on the space.
2. **10 layout-generation** — per-slide layout generation within the family grammar. The core v2 bet.
3. **11 charts** — first-class chart blocks. Content variety, schema-owned.
4. **12 editor** — the editor and re-skin. The retention loop, built after the engine is solid.
5. **13 vision-critic** — the bounded critic, after a real editor exists to re-render.
6. **14 pdf-export** — faithful print render of the HTML.
7. **15 variety-gate** — the fingerprint gate in CI, the standing version of v1's acceptance measurement.
