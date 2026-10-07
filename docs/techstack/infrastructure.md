# Infrastructure

Where everything runs. **Rewritten 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)): local-first, and nothing is stood up before phase 29.

The short version of the lesson: v1–v3 built six containers, a VPC design, RLS, quotas and publishing around decks that did not look designed. v4 builds no infrastructure until a wall of 12 decks does.

## The repo

One repository, two packages.

```
d-design/
  api/      Python — engine · store · routes · worker · CLI · bench
  web/      TypeScript — the app (from phase 27)
  docs/  scripts/
```

`render/` and v3's `worker/` are deleted in phase 21. The earlier plan of one repo per runtime never happened, and with OpenAPI codegen in-repo there is no schema package to publish.

## Local development

| Phases | What runs |
|---|---|
| **22–26** | Nothing long-running. `uv run python -m cli …` calls the engine directly and writes a deck to disk |
| **27–28** | Three processes: `uv run uvicorn app:app`, `uv run python -m worker`, `pnpm dev`. `scripts/setup.sh` prints the three commands |
| **29** | Adds Postgres |

**No Docker Compose, no MinIO, no LocalStack.** Compose returns at phase 29 only if Postgres locally is easier that way. v3's compose file brought up six services for a product with no users.

**Requirements on a developer machine:** uv, pnpm, and Playwright's Chromium (`uv run playwright install chromium`; Firefox and WebKit too for the hostile-slide suite).

**Secrets:** one, `OPENROUTER_API_KEY`, in a gitignored `.env`. From phase 27 only the worker reads it. Set a spend limit on the key itself; it is the outer ceiling under every per-deck budget.

**Decks on disk** live under a gitignored data directory, one folder per deck ([backend.md](backend.md) → "Data").

## CI

GitHub Actions, mirroring the pre-commit gate exactly.

| | |
|---|---|
| **api** | ruff · `mypy --strict` · pytest, including the offline-export, lint, sanitizer and QA-fixture tests. Chromium installed in the job |
| **web** (from phase 27) | tsc · eslint · prettier · Vitest · OpenAPI types regenerate with no diff |
| **Both** | Dependency advisory check · `./scripts/check-docs.sh` |
| **Never in CI** | Anything that calls a model. The bench costs money and its judge is a human |

v3's workflow was written and never ran on GitHub. Phase 21's exit includes one green run.

Workflow hygiene does not wait for a cloud: actions pinned to a commit SHA, `permissions:` declared, no `pull_request_target` with a PR-head checkout ([../security/build-pipeline.md](../security/build-pipeline.md)).

## What phase 29 decides

> **Decided 2026-10-08 for the submission (the owner needs a live link):**
> - **Railway** runs three services from this repo: `web` (public), `api` (private network only, no model key), `worker` (private, no inbound port, the OpenRouter key and Chromium).
> - **Neon** holds two databases, `app` and `auth`, and the blobs, stored by content hash.
> - **Secrets** are Railway's per-service variables; the model key is set on the worker alone.
> - The answers below were the open questions; the property under the table still decides every one.

Deliberately open until then, each with its constraint:

| Question | Constraint |
|---|---|
| **Where `api` and `worker` run** | The worker carries Chromium and runs builds of several minutes. That rules out short-lived function platforms for it. The worker needs no inbound port |
| **Where `web` runs** | Anywhere Next.js runs. It holds no secret beyond the auth provider's public config |
| **Postgres** | Any managed Postgres. One region, chosen as a compliance input |
| **Object storage** | For generated assets, behind the same data module |
| **The auth provider** | Better Auth, self-hosted in the web app (owner, 2026-10-08; [backend.md](backend.md) → "Auth (phase 29)") |
| **Secrets** | The host's secret store. The OpenRouter key goes to the worker only |
| **IaC** | Only if the target has network rules worth reviewing as a diff |
| **Hosted share links** | Not built. Trigger: "send a link" requests outnumber "send the file" |

**The one property to carry into any deployment:** the worker is not reachable from the internet, and the API cannot read the model key. On a laptop that is a convention; deployed it must be a network rule and a secret scope, and phase 29's first check is that both hold.

## What the v3 design had, and when it returns

Recorded so nobody rebuilds it by reflex. The reasoning in each was sound for the product it served.

| v3 piece | Returns when |
|---|---|
| A quarantined fetch worker on its own subnet | URL import or file upload is built. It needs an SSRF-safe fetcher and an isolated parser ([../security/infrastructure.md](../security/infrastructure.md)) |
| S3 + CloudFront for published decks, custom domains, ACM | Hosted share links are built |
| Secrets Manager + KMS envelope encryption | Integration credentials exist |
| Terraform, OIDC to AWS | The deploy target is AWS |
| PGQueuer / a queue | File claims and then `SKIP LOCKED` stop being enough |

The full v3 topology is in git history at commit `8169fd9`.
