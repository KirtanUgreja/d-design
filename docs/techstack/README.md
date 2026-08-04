# Tech Stack

> What this is built with, where each piece runs, and why. Including which model — and the answer is deliberately "no preferred vendor".

**Start here:** [The shape](#the-shape) below — three origins, three runtimes, and the trust boundary between them.

**Looking for one decision and its rejected alternative?** [decisions.md](decisions.md) is the full log.

What this is built with, where each piece runs, and why.

The *language* half of the stack was settled in [../v1/spec.md](../v1/spec.md) and [../coderules/](../coderules/README.md), and has since been **reversed** — the backend is Python and this directory now owns that decision ([decisions.md](decisions.md) → "The Python backend move"). This directory also settles the **operational** half — hosting, workers, storage, delivery, auth, jobs — which earlier docs assumed without naming. The security docs already relied on some of it: an "isolated worker with no route to the VPC", a CDN in front of published pages. Those were requirements with no implementation. Now they have one.

## The shape

Three origins, five runtimes, two languages. Most of the splits are trust boundaries; one is a language boundary, and it is labelled so it is never mistaken for a security control.

```
                    ┌──────────────────────────────────────┐
  app.<domain>      │  web — Next.js 16 on Vercel      TS  │  sessions, Better Auth,
  (editor)          │  editor · renderer · marketing       │  AUTH TABLES ONLY
                    └───────────────┬──────────────────────┘
                                    │ session cookie
                                    ▼
                    ┌──────────────────────────────────────┐
                    │  api — FastAPI                   PY  │  the four phases,
                    │  pipeline · seam · quotas · data     │  all app tables
                    └───┬───────────────┬──────────────┬───┘
                        │               │              │
        ┌───────────────▼──┐  ┌─────────▼────────┐  ┌──▼───────────────┐
        │  jobs        PY  │  │  render      TS  │  │  fetch worker TS │
        │  PGQueuer        │  │  scene → HTML    │  │  NO db access    │
        │  DB access       │  │  Playwright      │  │  NO vpc route    │
        │  no hostile input│  │  NO db, NO keys  │  │  hostile input   │
        └───────────────┬──┘  └─────────┬────────┘  └──────────────────┘
           privileged   │               │              quarantined
                        │  writes artifact
                        ▼               ▼
  pages.<domain>    ┌──────────────────────────────────────┐  no server,
  (published)       │  S3 + CloudFront — static HTML       │  no DB,
  assets.<domain>   │  no origin server to route around    │  nothing to breach
                    └──────────────────────────────────────┘
```

**Two ideas carry this diagram.**

**The trust splits.** `fetch worker` and `jobs` have opposite requirements — one parses attackers' bytes and holds nothing worth stealing, the other holds database credentials and never sees hostile input. `render` sits between them: it has the renderer but neither database access nor a model key, so its worst case is a wrong page. See [backend.md](backend.md).

**The language split, which is a cost rather than a control.** `render` exists because Python cannot server-side-render React and the renderer must have exactly one implementation ([../coderules/patterns.md](../coderules/patterns.md) rule 2). **Python decides; TypeScript renders.** That line explains most of the architecture, including why `web` reaches no application table and why `api` reads exactly one table it does not own.

**Published pages have no origin server.** Publishing renders the scene tree to HTML and writes it to S3. There is no route to attack, no database to reach, no cache-key disagreement between a CDN and an origin — because there is no origin. This makes [../security/platform-and-packages.md](../security/platform-and-packages.md)'s cache-deception class nearly vanish, and it makes a viral launch page cost pennies.

## The stack

| Layer | Choice | Doc |
|---|---|---|
| **Backend language** | **Python**, typed — `api` and `jobs` | [ai-stack.md](ai-stack.md) |
| **Backend framework** | **FastAPI** | [backend.md](backend.md) |
| **Frontend language** | TypeScript, strict — `web`, `render`, fetch worker | [../coderules/typescript.md](../coderules/typescript.md) |
| **App framework** | Next.js 16 App Router + React 19.2 | [frontend.md](frontend.md) |
| **Editor state** | Zustand | [frontend.md](frontend.md) |
| **App chrome UI** | shadcn/ui on Radix + Tailwind | [frontend.md](frontend.md) |
| **Motion** | Motion (`motion/react`) | [frontend.md](frontend.md) |
| **Streaming** | SSE over a Route Handler | [frontend.md](frontend.md) |
| **Fonts** | Fontsource, open-license, self-hosted | [frontend.md](frontend.md) |
| **Schema / validation** | **Pydantic** — the source of truth. Zod 4 + TS types generated from it | [ai-stack.md](ai-stack.md) |
| **Database** | Postgres — Docker local → **RDS/Aurora** | [backend.md](backend.md) |
| **ORM / migrations** | **SQLAlchemy + Alembic** (app tables) · Drizzle (auth tables only) | [backend.md](backend.md) |
| **Auth** | **Better Auth**, kept in Node, on your own Postgres | [backend.md](backend.md) |
| **Session across languages** | `api` reads the `session` table read-only | [backend.md](backend.md) |
| **Isolation** | RLS driven by a session variable — **two wrappers, one per language** | [backend.md](backend.md) |
| **Jobs** | **PGQueuer** on the same Postgres | [backend.md](backend.md) |
| **Model access** | **OpenRouter** behind a thin provider seam — no preferred vendor | [ai-stack.md](ai-stack.md) |
| **Evals** | Promptfoo in CI, self-hosted Langfuse for tracing | [ai-stack.md](ai-stack.md) |
| **Agent framework** | **None.** Not an agent — and it would be privileged, in a class under active exploitation | [ai-stack.md](ai-stack.md) |
| **Model client** | Plain `httpx`. Instructor if the seam grows | [ai-stack.md](ai-stack.md) |
| **Pipeline tools** | Read-only only; visual verification loop from v2 | [pipeline-tools.md](pipeline-tools.md) |
| **Email** | Resend | [backend.md](backend.md) |
| **App hosting** | Vercel | [infrastructure.md](infrastructure.md) |
| **Workers** | AWS ECS Fargate, four services | [infrastructure.md](infrastructure.md) |
| **Storage / delivery** | S3 + CloudFront + ACM | [infrastructure.md](infrastructure.md) |
| **Secrets** | AWS Secrets Manager + KMS | [infrastructure.md](infrastructure.md) |
| **IaC** | Terraform / OpenTofu | [infrastructure.md](infrastructure.md) |
| **CI/CD** | GitHub Actions, OIDC to AWS | [infrastructure.md](infrastructure.md) |
| **Local dev** | Docker Compose — Postgres, MinIO, LocalStack | [infrastructure.md](infrastructure.md) |
| **Tests** | pytest (Python) · Vitest + Playwright (TypeScript) | [../coderules/tooling.md](../coderules/tooling.md) |
| **Package managers** | **uv** (Python) · pnpm (TypeScript) | [../coderules/dependencies.md](../coderules/dependencies.md) |

## Documents

| | |
|---|---|
| [frontend.md](frontend.md) | The editor, the published artifact, and what JS ships to a viewer |
| [backend.md](backend.md) | App server, the two workers, data, auth, jobs |
| [ai-stack.md](ai-stack.md) | Model neutrality, evals, why there is no agent framework, and what the Python backend costs |
| [pipeline-tools.md](pipeline-tools.md) | What the model may call, and the loop that lets it look at what it made |
| [infrastructure.md](infrastructure.md) | AWS topology, delivery, secrets, CI/CD, local dev, the repos |
| [decisions.md](decisions.md) | The full log — every choice, its rejected alternative, and what it changed elsewhere |

## Find it fast

| If you need… | Go to |
|---|---|
| What JavaScript ships to a viewer | [frontend.md](frontend.md) → "The published artifact" |
| Why the published page can no longer claim zero network requests | [frontend.md](frontend.md) → "What talks to the network" |
| Editor state, undo/redo | [frontend.md](frontend.md) → "The editor" |
| How generation streams to the UI | [frontend.md](frontend.md) → "Streaming" |
| Font licensing, and per-script coverage | [frontend.md](frontend.md) → "Fonts" |
| What each runtime may touch, and why there are five | [backend.md](backend.md) → "The five runtimes" |
| Which ORM owns which tables — **read before any migration** | [backend.md](backend.md) → "Two ORMs, one database" |
| The RLS session-variable pattern, and why there are now two wrappers | [backend.md](backend.md) → "Isolation" |
| Auth — why Better Auth stayed in Node | [backend.md](backend.md) → "Auth: Better Auth, in Node" |
| How the Python API learns who the user is | [backend.md](backend.md) → "Session resolution" |
| Where publishing renders | [backend.md](backend.md) → "Publishing — where the render happens" |
| Jobs, and transactional enqueue | [backend.md](backend.md) → "Jobs: PGQueuer" |
| Which model to use | [ai-stack.md](ai-stack.md) → "The stance: no favourite model", "What actually constrains the choice" |
| The eval harness | [ai-stack.md](ai-stack.md) → "Evals — the missing apparatus" |
| Why there is no agent framework, and the CVE evidence | [ai-stack.md](ai-stack.md) → "Agent framework: none" |
| Which languages run where, and what the split costs | [ai-stack.md](ai-stack.md) → "Language" |
| How the `Scene` schema crosses the language boundary | [ai-stack.md](ai-stack.md) → "The `Scene` schema, which is the whole cost of this move" |
| Why DSPy is allowed but only offline | [ai-stack.md](ai-stack.md) → "DSPy — now native, and still offline" |
| What the model is allowed to call | [pipeline-tools.md](pipeline-tools.md) → "The three tiers", "The catalog, by phase" |
| The render-and-look loop | [pipeline-tools.md](pipeline-tools.md) → "The visual verification loop" |
| AWS topology, subnets, isolation | [infrastructure.md](infrastructure.md) → "AWS topology" |
| How published pages are delivered | [infrastructure.md](infrastructure.md) → "Delivery" |
| Secrets and KMS | [infrastructure.md](infrastructure.md) → "Secrets" |
| Local development setup | [infrastructure.md](infrastructure.md) → "Local development" |
| What v1 actually needs to run | [infrastructure.md](infrastructure.md) → "What v1 actually stands up" (Docker Compose, no AWS) |
| Why a choice was made, or what it replaced | [decisions.md](decisions.md) → "The log", "What this supersedes" |
| What is still undecided | [decisions.md](decisions.md) → "Still open" |

## Build it in this order

Most of the above is not needed for a long time, and standing it up early is weeks spent on infrastructure before the thing that decides whether this product works — the renderer — exists at all.

| Version | Infrastructure |
|---|---|
| **v1** | **Docker Compose and two dev servers.** Local Postgres, `web` on Next.js, `api` on uvicorn, local disk via `storage`, no AWS account, no auth, no `jobs`, no `render`, no CDN |
| **v2** | Adds `render`, because the visual verification loop needs the renderer and Playwright together |
| **v3** | Everything else — AWS, RDS, Better Auth, `jobs`, the fetch worker, S3/CloudFront, Terraform, CI/CD |

**v1 is where the language split first costs something real**, and it is worth knowing before you feel it: two dev servers, two package managers, and a codegen step between them. In v1 the renderer runs in the browser only, so `render` is not needed — publishing is a `web` route writing to local disk. That is the fallback the [backend.md](backend.md) design keeps.

v1's verification list includes *"open the published URL in an incognito window"*, which a local dev server satisfies. The real deployment lands with the release that has real users, which is the same boundary every other v3 control sits on ([../security/README.md](../security/README.md)).

**The one thing to get right early is `storage.ts`** — the single abstraction with a planned second implementation. Point it at the S3 API from day one and run MinIO locally, and the local-to-production move is a credential change rather than a rewrite.

## What this changed

Several of these decisions supersede things earlier docs locked. The reversals are recorded in [decisions.md](decisions.md), and the security-relevant ones have been patched at the source rather than left to contradict:

- **The backend is Python.** `api` and `jobs` are FastAPI and PGQueuer; `web`, `render`, and the fetch worker stay TypeScript. Pydantic owns the `Scene` schema and TypeScript is generated from it
- **Supabase is out.** Postgres moves to RDS/Aurora, auth to Better Auth, storage to S3. `auth.uid()` is replaced by a session variable in every RLS policy
- **`connect-src 'none'` on published pages is gone**, weakened to two named endpoints — the cost of client-side personalization and the analytics beacon
- **One isolated worker became two, and then five runtimes**, split on trust — except `render`, which is split on language
- **Published pages are static artifacts**, not server routes
- **Model calls go through OpenRouter**, so the schema constraint is enforced by the schema parse rather than by the decoder

Two of those trade away a guarantee — the Python move and OpenRouter. It is deliberate, the reasoning is in [backend.md](backend.md), and the metric that tells you whether it was right — the repair rate — already exists in [../v1/ai-pipeline.md](../v1/ai-pipeline.md).

## Connects to

| | |
|---|---|
| [../coderules/README.md](../coderules/README.md) | The rules these choices imply, including the two new non-negotiables |
| [../security/README.md](../security/README.md) | Every control assumes this topology — especially the two-worker split |
| [../security/third-parties.md](../security/third-parties.md) | The data-flow consequence of routing model calls through OpenRouter |
| [../v1/spec.md](../v1/spec.md) | The language half of the stack, settled earlier |
