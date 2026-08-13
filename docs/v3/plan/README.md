# v3 — plan

## Status

| Phase | Status |
|---|---|
| [16 — accounts](16-accounts.md) | not started |
| [17 — brand-kit-at-scale](17-brand-kit-at-scale.md) | not started |
| [18 — hosting](18-hosting.md) | not started |
| [19 — billing](19-billing.md) | not started |
| [20 — pptx](20-pptx.md) | not started |

## Dependency graph

```
16 accounts
   │
   ▼
17 brand-kit-at-scale ──▶ 18 hosting ──▶ 19 billing
                                    │
                                    ▼
                                 20 pptx (conditional)
```

## Recommended build order

1. **16 accounts** — auth, sessions, RLS. Everything multi-tenant depends on the boundary.
2. **17 brand-kit-at-scale** — persisted, team-shared kits with upload + extraction. The retention surface.
3. **18 hosting** — the hosted URL for a deck, CDN-served, plus the downloadable file. The business layer.
4. **19 billing** — tiers, quotas, kill switch. Fitted around the editor (v2) as the retention loop.
5. **20 pptx** — native OOXML export, only if the market asks. The last, conditional phase.
