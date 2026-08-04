# Decisions

Every operational choice, what it beat, and what it cost. The rejected option matters as much as the chosen one — a decision without its alternative is just a preference.

## The log

| Decision | Chosen | Over | Because |
|---|---|---|---|
| App hosting | **Vercel** | Fly, self-hosted, Cloudflare | Next.js's own platform; fastest path solo, and the dangerous work moved off it anyway |
| Workers | **AWS ECS Fargate** | Fly, Railway, Lambda, App Runner | Network isolation becomes a subnet and a security group, not a promise. Lambda's 15-minute ceiling doesn't fit transcreation; App Runner hides the networking that is the point |
| Worker count | **Two, split on trust** | One combined worker | The process holding DB credentials must not be the one parsing an attacker's PDF |
| Repos | **Two** — app, and fetch worker | One repo; three repos | Split on the trust boundary, not the job boundary. Only the isolated worker's separation is a security property |
| Schema sharing | **Private npm package** | Submodule, copy + contract test | Version pin makes drift explicit; a submodule sits silently on an old commit |
| Database | **Postgres — Docker → RDS/Aurora** | Supabase, Neon | One VPC with the workers; lowest latency; no cross-cloud egress per job |
| ORM | **Drizzle + drizzle-kit** | Prisma, raw SQL | Already locked in v1 |
| Auth | **Better Auth** | Auth.js, Clerk, Cognito, WorkOS | v1.6, Drizzle adapter, users in *your* Postgres. Ships MFA, passkeys, orgs, verification — all four of which Auth.js lacks and the security doc requires |
| Isolation | **RLS on `current_setting('app.user_id')`** | App-layer only; schema per tenant | `auth.uid()` died with Supabase. Defense-in-depth under the data modules |
| Jobs | **pg-boss** | Inngest, Trigger.dev, Vercel Cron | Jobs enqueue in the same transaction as the data change that caused them. No new datastore |
| Rate limits / quotas | **Postgres atomic counters** | Upstash Redis, platform limits | The quota must be transactional anyway to close the A10 race; one datastore |
| Model access | **OpenRouter behind a seam** | Anthropic direct, Bedrock, Claude Platform on AWS | Model flexibility and cheap experimentation. **Costs a guarantee** — see below |
| Publish target | **Static artifacts to S3** | Vercel routes with `use cache` | Published pages were always "static after render". Removing the origin removes most of the attack surface |
| CDN | **CloudFront** | Vercel edge, Cloudflare | One cloud; explicit cache-key policies, which are now a security control |
| Storage | **S3 + CloudFront** | Supabase Storage, R2 | The workers process every upload and live in AWS |
| Personalized pages | **Static shell + client-side field fetch** | Per-recipient pre-render; Vercel route | One publish path, one renderer. **Costs `connect-src 'none'`** |
| Page runtime | **React SSR + hydrate, Motion** | Vanilla reveal runtime, CSS-only, islands | A second motion implementation would drift from the editor. Weight is the cheaper loss |
| Editor state | **Zustand** | useReducer, Jotai, Immer | One mutable document; undo/redo is the feature that makes AI editing safe to try |
| App chrome UI | **shadcn/ui** | Radix bare, hand-built, Mantine | Own the code, no runtime dep, accessibility behavior from Radix |
| Streaming | **SSE over a Route Handler** | AI SDK, polling, WebSocket | The unit is a validated scene, not a token. No library needed |
| Fonts | **Fontsource, open licence** | Commercial, Adobe Fonts | Redistribution to customers' audiences makes licensing a product constraint |
| Screenshots | **Playwright in the fetch worker** | Browserless, ScreenshotOne | The hostile page renders inside the box built for hostile things |
| Document parsing | **`pdf.js` / `unpdf` in the fetch worker** | Claude native PDF reading | Cheap and local. Highest-CVE dependency class, contained by placement — Claude-native is the documented fallback |
| Email | **Resend** | Postmark, SES, Supabase | Best DX, React Email templates |
| Observability | **Sentry** | Axiom, Better Stack, none | Mature server-side scrubbing, which this product needs more than most |
| Secrets | **Secrets Manager + KMS** | Doppler, env vars, Parameter Store | KMS is what envelope encryption already assumed. Task-role scoping is the real win |
| IaC | **Terraform / OpenTofu** | CDK, SST, console | The fetch worker's isolation must be a reviewable diff, not console state |
| CI/CD | **GitHub Actions + OIDC** | CDK Pipelines, manual | One CI system, no long-lived AWS keys in GitHub |
| Local dev | **Docker Compose + MinIO + LocalStack** | Real AWS dev, Supabase CLI | `storage.ts` and the KMS path get one implementation, not two |
| Tests | **Vitest + Playwright** | node:test, Cypress | Three origins and a sandboxed iframe cannot be tested in jsdom |
| Migrations | **drizzle-kit, one dev DB** | Branch-per-preview | Simplest thing that works solo; revisit if it hurts |
| Model vendor | **None — evaluate per phase** | Standardising on one provider | Any model named today is wrong in two quarters. Build the switching apparatus, not the conviction |
| Evals | **Promptfoo (CI) + self-hosted Langfuse** | Braintrust, LangSmith, hosted anything | Model-neutrality without evals is not a strategy. Self-hosted because a prompt here is embargoed customer messaging |
| Agent framework | **None** | LangGraph, CrewAI, Mastra, Agents SDK | Four deterministic phases with a human gate is not an agent. Your code makes every next-step decision |
| Pipeline language | **TypeScript** | A Python AI service | No ML work; a Pydantic mirror of the Zod schema would be a second source of truth |
| Model client | **Plain `fetch`, OpenAI-compatible** | Vercel AI SDK, Mastra | Start with a function. Take the SDK when it deletes your code rather than adding to it |
| Pipeline tools | **Read-only, tiered** | No tools; tools with side effects | Defense 5 forbids side effects, not tools. Tier 2 stays closed |
| Visual verification | **Render → screenshot → vision critic, one revision** | Zod validation alone; unbounded critic loop | Zod proves valid, not good. Doubles cost to ~$0.40/experience, which is not a cost decision |
| Publish render location | **Job worker** (app fallback) | Vercel route only | Corrects a wrong premise — the job worker ships from the app repo, so it has the renderer and no timeout ceiling |
| v1 infrastructure | **None — Docker Compose only** | Full stack from day one | The long pole is the renderer, and a perfect VPC does not move that risk |
| Our own brand | **Light editorial "gallery wall"** | Wearing `cinematic-dark`; a dark atmospheric site | A site wearing its own art direction proves the product makes one thing. Also the shortest path away from the slop aesthetic ([../design/brand.md](../design/brand.md)) |
| Marketing hero | **A real embedded published artifact + a recorded generation** | Live anonymous generation; a video; a canned prompt box | Published pages are static, so real work costs nothing per visitor. A recorded SSE log is one model call ever and cannot fail on stage |
| Marketing analytics | **Self-hosted, cookieless, marketing site only** | Plausible Cloud, GA4, Fathom | A hosted vendor is a subprocessor decision ([../security/third-parties.md](../security/third-parties.md)). No cookies also means no consent banner |
| Chrome typography | **Commercially licensed, not shared with any AD** | Reusing the output's open faces; Inter/Geist | Our chrome is not redistributed, so the output's licence constraint does not bind it — and a shared face merges the two design systems |

## The two decisions that cost something

Everything else is a preference with a defensible rationale. These two trade away a stated guarantee, and they should be revisited deliberately rather than forgotten.

### 1. OpenRouter weakens schema enforcement

[../security/prompt-injection.md](../security/prompt-injection.md) claims *"a fully compromised model can only emit valid Scene JSON."* Under OpenRouter that is no longer enforced by the decoder — `strict: true` support varies by provider, and some treat a schema as a strong hint.

**What survives:** the Zod parse was always the real gate. Decoder enforcement lowered how *often* the model produced something invalid; it never was the thing that stopped invalid output from being rendered. Output failing Zod is rejected, repaired once, then fails visibly. The claim restates as *"a fully compromised model can only cause a rejected generation"* — same outcome, different route.

**The residual:** repeated repair cycles burn tokens. Denial of wallet, already covered by quotas and the kill switch.

**Revisit when:** Build's repair rate is materially worse than a direct Anthropic call. That number is already in `generations` ([../v1/ai-pipeline.md](../v1/ai-pipeline.md)) — watch it from the first generation. The seam exists so that moving one phase is a config change.

### 2. Client-side personalization ends `connect-src 'none'`

A published page was specified to make **zero** outbound requests, enforced by CSP. Two features broke it: the personalization field fetch and the analytics beacon.

**What survives:** `connect-src` names two exact paths — not `'self'`, not a host, two full URLs. The guarantee degrades from *cannot talk to anything* to *can talk to two endpoints you own, and a browser test proves nothing else*.

**The residual:** a recipient token now appears in a client-side request, which raises the stakes on `Referrer-Policy: no-referrer` and `Cache-Control: private, no-store`.

**Revisit when:** if analytics ever moves to CloudFront access logs and personalization to per-recipient pre-rendering, `connect-src 'none'` comes back. Both are viable; neither is worth doing before there are users.

## What this supersedes

Earlier documents locked decisions this directory reverses. Recorded here rather than silently contradicted.

| Was | Now | Where it was |
|---|---|---|
| Postgres in Docker → **Supabase** | Docker → **RDS/Aurora** | [../v1/spec.md](../v1/spec.md) |
| **Supabase Auth**, RLS via `auth.uid()` | **Better Auth**, RLS via `current_setting('app.user_id')` | [../security/tenancy-and-data.md](../security/tenancy-and-data.md) |
| `storage.ts`: local disk → **Supabase Storage** | local disk → **S3** (MinIO locally) | [../v1/spec.md](../v1/spec.md) |
| **Supabase client** in the dependency baseline | Removed | [../coderules/dependencies.md](../coderules/dependencies.md) |
| `anon` role has zero grants | **No anonymous role exists.** Nothing but the server connects | [../security/tenancy-and-data.md](../security/tenancy-and-data.md) |
| One isolated worker | **Two workers**, split on trust | [../security/infrastructure.md](../security/infrastructure.md) |
| Published pages served from an origin | **Static S3 artifacts**, no origin | [../security/content-and-web.md](../security/content-and-web.md) |
| `connect-src 'none'` | Two exact endpoints | [../security/content-and-web.md](../security/content-and-web.md) |
| Anthropic API called directly | **OpenRouter** behind a seam, no preferred vendor | [../v1/ai-pipeline.md](../v1/ai-pipeline.md) |
| Shape violations are **unrepresentable** — the decoder prevents a hex code | **Zod is the only gate.** The decoder shifts the odds where the route enforces natively | [../v1/scene-schema.md](../v1/scene-schema.md) |
| PDFs go to the model as a document block | Extracted in the **fetch worker** first; model-native reading is the documented fallback | [../v1/ai-pipeline.md](../v1/ai-pipeline.md) |
| Prompt caching is one mechanism with one discount | Activation, discount rate, and minimum prefix all **vary by route** | [../v1/ai-pipeline.md](../v1/ai-pipeline.md) |
| Generation has **no tools** | No tools **with side effects**; read-only tools tiered | [../security/prompt-injection.md](../security/prompt-injection.md) |
| ~$0.20 per experience | ~$0.40 once the visual loop is on | [../v1/ai-pipeline.md](../v1/ai-pipeline.md) |
| Publishing renders on Vercel | Renders in the **job worker** — no timeout ceiling | [backend.md](backend.md) |

The security-relevant rows have been patched at the source. The rest stand as the record of what was believed at the time, which is the convention the version directories already use.

## Still open

Deliberately unresolved, with the condition that would resolve each:

| | Resolve when |
|---|---|
| **Per-phase model selection** | Real briefs and a measured repair rate exist. Guessing now optimizes nothing |
| **Buying commercial type** | v2's three ADs make the difference visible. The highest-leverage money in the product, deferred not refused |
| **Branch-per-preview databases** | Migrations against one shared dev DB start hurting |
| **Cloudflare for SaaS** | Custom domains pass roughly fifty and ACM's SAN limits bite |
| **Pricing and plan limits** | [../v3/spec.md](../v3/spec.md) — quota *enforcement* is built; the numbers are not chosen |
| **MFA rollout** | Better Auth ships it. Accounts hold integration credentials from day one, which argues for sooner than v3 |
| **The product's name** | Before phase 09. `d-design` describes the repository; the editor is where user-facing strings start accumulating and renaming after that is an audit ([../design/brand.md](../design/brand.md)) |
| **The chrome accent hue** | With the first real screen. The constraint is decided — one accent, roughly two uses, never violet or a gradient — and the hue is not |
