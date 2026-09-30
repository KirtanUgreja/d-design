# Checkpoint — 2026-09-30

Resume point. **Nothing here is committed yet**: the working tree holds the v4 docs on top of `8169fd9`.

## Where things stand

| | |
|---|---|
| Decided 2026-09-26 | The product is rebuilt as v4: the model designs each slide in HTML inside theme tokens. Plan: `docs/v4/` |
| Done | `docs/v4/` written (spec, engine, content, design-engine, bench, phases 21–29). `docs/coderules`, `docs/techstack`, `docs/security`, `docs/design`, `docs/findings.md`, `docs/README.md`, `README.md`, `AGENTS.md` updated to v4. `docs/v1`–`v3` deleted |
| Not done | Everything else in phase 21: tag `v3-final`, delete the v3 code, the `api/` skeleton and model seam, the new gate, the bench and baselines |
| Still in the tree, to be deleted by phase 21 | `api/` (v3 pipeline), `web/`, `render/`, `worker/`, `docker-compose.yml`, `samples/` |

## Next

`docs/v4/plan/21-reset.md` → Make. Then phase 22, the make-or-break gate: no later phase starts until the owner rates its wall.

## Owner's tasks in phase 21

- Generate 6 of the bench briefs in Gamma and export them, for the baseline.
- Rate the baselines on the wall (about 30 minutes).
