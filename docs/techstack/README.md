# Tech Stack

What this is built with, where each piece runs, and why.

The *language* half of the stack was settled in [../v1/spec.md](../v1/spec.md) and [../coderules/](../coderules/README.md). This directory settles the **operational** half — hosting, workers, storage, delivery, auth, jobs — which earlier docs assumed without naming. The security docs already relied on some of it: an "isolated worker with no route to the VPC", a CDN in front of published pages. Those were requirements with no implementation. Now they have one.

## The shape

Three origins, three runtimes, and the split between them is a trust boundary rather than a convenience.

```
                    ┌──────────────────────────────────────┐
  app.<domain>      │  Next.js 16 on Vercel                │  sessions, auth,
  (editor)          │  editor · pipeline · publish render  │  DB access
                    └───────────────┬──────────────────────┘
                                    │ writes artifact
                                    ▼
  pages.<domain>    ┌──────────────────────────────────────┐  no server,
  (published)       │  S3 + CloudFront — static HTML       │  no DB,
  assets.<domain>   │  no origin server to route around    │  nothing to breach
                    └──────────────────────────────────────┘

                    ┌──────────────────┐   ┌──────────────────┐
  AWS / ECS Fargate │  job worker      │   │  fetch worker    │
                    │  pg-boss         │   │  NO db access    │
                    │  DB access       │   │  NO vpc route    │
                    │  no hostile input│   │  hostile input   │
                    └──────────────────┘   └──────────────────┘
                       privileged              quarantined
```

**The two workers are the important idea.** Earlier security docs described one, but the jobs it would run have opposite requirements. Splitting them means the process holding database credentials never parses an attacker's PDF, and the process rendering an attacker's webpage has nothing worth stealing. See [backend.md](backend.md).

**Published pages have no origin server.** Publishing renders the scene tree to HTML and writes it to S3. There is no route to attack, no database to reach, no cache-key disagreement between a CDN and an origin — because there is no origin. This makes [../security/platform-and-packages.md](../security/platform-and-packages.md)'s cache-deception class nearly vanish, and it makes a viral launch page cost pennies.

## The stack

| Layer | Choice | Doc |
|---|---|---|
| **Language** | TypeScript, strict | [../coderules/typescript.md](../coderules/typescript.md) |
| **App framework** | Next.js 16 App Router + React 19.2 | [frontend.md](frontend.md) |
| **Editor state** | Zustand | [frontend.md](frontend.md) |
| **App chrome UI** | shadcn/ui on Radix + Tailwind | [frontend.md](frontend.md) |
| **Motion** | Motion (`motion/react`) | [frontend.md](frontend.md) |
| **Streaming** | SSE over a Route Handler | [frontend.md](frontend.md) |
| **Fonts** | Fontsource, open-license, self-hosted | [frontend.md](frontend.md) |
| **Schema / validation** | Zod 4 — types *and* the model's JSON Schema | [../coderules/typescript.md](../coderules/typescript.md) |
| **Database** | Postgres — Docker local → **RDS/Aurora** | [backend.md](backend.md) |
| **ORM / migrations** | Drizzle + drizzle-kit | [backend.md](backend.md) |
| **Auth** | **Better Auth** on your own Postgres | [backend.md](backend.md) |
| **Isolation** | RLS driven by a session variable | [backend.md](backend.md) |
| **Jobs** | pg-boss on the same Postgres | [backend.md](backend.md) |
| **Model access** | **OpenRouter** behind a thin provider seam — no preferred vendor | [ai-stack.md](ai-stack.md) |
| **Evals** | Promptfoo in CI, self-hosted Langfuse for tracing | [ai-stack.md](ai-stack.md) |
| **Agent framework** | **None.** This is a pipeline, not an agent | [ai-stack.md](ai-stack.md) |
| **Pipeline language** | TypeScript, same as everything else | [ai-stack.md](ai-stack.md) |
| **Pipeline tools** | Read-only only; visual verification loop from v2 | [pipeline-tools.md](pipeline-tools.md) |
| **Email** | Resend | [backend.md](backend.md) |
| **App hosting** | Vercel | [infrastructure.md](infrastructure.md) |
| **Workers** | AWS ECS Fargate, two services | [infrastructure.md](infrastructure.md) |
| **Storage / delivery** | S3 + CloudFront + ACM | [infrastructure.md](infrastructure.md) |
| **Secrets** | AWS Secrets Manager + KMS | [infrastructure.md](infrastructure.md) |
| **IaC** | Terraform / OpenTofu | [infrastructure.md](infrastructure.md) |
| **CI/CD** | GitHub Actions, OIDC to AWS | [infrastructure.md](infrastructure.md) |
| **Local dev** | Docker Compose — Postgres, MinIO, LocalStack | [infrastructure.md](infrastructure.md) |
| **Tests** | Vitest + Playwright | [../coderules/tooling.md](../coderules/tooling.md) |
| **Package manager** | pnpm | [../coderules/dependencies.md](../coderules/dependencies.md) |

## Documents

| | |
|---|---|
| [frontend.md](frontend.md) | The editor, the published artifact, and what JS ships to a viewer |
| [backend.md](backend.md) | App server, the two workers, data, auth, jobs |
| [ai-stack.md](ai-stack.md) | Model neutrality, evals, why there is no agent framework, why not Python |
| [pipeline-tools.md](pipeline-tools.md) | What the model may call, and the loop that lets it look at what it made |
| [infrastructure.md](infrastructure.md) | AWS topology, delivery, secrets, CI/CD, local dev, the repos |
| [decisions.md](decisions.md) | The full log — every choice, its rejected alternative, and what it changed elsewhere |

## Build it in this order

Most of the above is not needed for a long time, and standing it up early is weeks spent on infrastructure before the thing that decides whether this product works — the renderer — exists at all.

| Version | Infrastructure |
|---|---|
| **v1** | **Docker Compose and a dev server. That is all.** Local Postgres, local disk via `storage.ts`, no AWS account, no auth, no workers, no CDN |
| **v2** | Unchanged. Three art directions and reskin are pure application work |
| **v3** | Everything else — AWS, RDS, Better Auth, both workers, S3/CloudFront, Terraform, CI/CD |

v1's verification list includes *"open the published URL in an incognito window"*, which a local dev server satisfies. The real deployment lands with the release that has real users, which is the same boundary every other v3 control sits on ([../security/README.md](../security/README.md)).

**The one thing to get right early is `storage.ts`** — the single abstraction with a planned second implementation. Point it at the S3 API from day one and run MinIO locally, and the local-to-production move is a credential change rather than a rewrite.

## What this changed

Several of these decisions supersede things earlier docs locked. The reversals are recorded in [decisions.md](decisions.md), and the security-relevant ones have been patched at the source rather than left to contradict:

- **Supabase is out.** Postgres moves to RDS/Aurora, auth to Better Auth, storage to S3. `auth.uid()` is replaced by a session variable in every RLS policy
- **`connect-src 'none'` on published pages is gone**, weakened to two named endpoints — the cost of client-side personalization and the analytics beacon
- **One isolated worker became two**, split on trust rather than on job type
- **Published pages are static artifacts**, not server routes
- **Model calls go through OpenRouter**, so the schema constraint is enforced by Zod rather than by the decoder

That last one is the only decision here that trades away a guarantee. It is deliberate, the reasoning is in [backend.md](backend.md), and the metric that tells you whether it was right — the repair rate — already exists in [../v1/ai-pipeline.md](../v1/ai-pipeline.md).
