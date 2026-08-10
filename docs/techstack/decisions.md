# Decisions

Every operational choice, what it beat, and what it cost. The rejected option matters as much as the chosen one — a decision without its alternative is just a preference.

## The log

| Decision | Chosen | Over | Because |
|---|---|---|---|
| App hosting | **Vercel — `web` only** | Fly, self-hosted, Cloudflare | Next.js's own platform; fastest path solo, and both the dangerous work and the backend moved off it |
| Backend language | **Python** | TypeScript everywhere | Reverses an earlier lock. AI/ML ecosystem, authoring fluency, and a backend that is not a frontend framework's server half. **Costs a codegen step** — see below |
| Backend framework | **FastAPI** | Django + Ninja, Litestar | Pydantic-native, so the `Scene` schema and the API contract are the same object. Django's ORM would compete with the SQLAlchemy choice; Litestar's ecosystem is smaller |
| Workers | **AWS ECS Fargate** | Fly, Railway, Lambda, App Runner | Network isolation becomes a subnet and a security group, not a promise. Lambda's 15-minute ceiling doesn't fit transcreation; App Runner hides the networking that is the point |
| Runtime count | **Five, split on trust and language** | One combined worker; three runtimes | The process holding DB credentials must not be the one parsing an attacker's PDF. `render` is a *language* boundary, not a trust one — named as such so it is not mistaken for a security control |
| Repos | **One per runtime** | One repo; two repos | The Pydantic→TypeScript schema package becomes a real versioned artifact with an explicit pin, which is what makes the codegen boundary visible |
| Schema source of truth | **Pydantic** | Zod; a hand-written JSON Schema | The model call happens in Python, so the structured-output constraint should not travel. Reverses v1's Zod-first lock |
| Schema sharing | **Generated TS + Zod, private npm package** | Submodule, copy + contract test, TS types only | Version pin makes drift explicit. Generating a Zod validator (not types alone) keeps the editor validating locally and offline |
| Database | **Postgres — Docker → RDS/Aurora** | Supabase, Neon | One VPC with the workers; lowest latency; no cross-cloud egress per job |
| ORM | **SQLAlchemy + Alembic** (`api`) · **Drizzle** (`web`, auth tables only) | One ORM; Django ORM; raw SQL | Better Auth is Node and ships its own Drizzle schema. Two ORMs is the price of keeping it — bounded by a hard table-ownership rule |
| Auth | **Better Auth, kept in Node** | fastapi-users, Authlib, WorkOS/PropelAuth/Kinde | Python has no equivalent. `fastapi-users` leaves MFA, passkeys and orgs to you; hosted IdPs move users out of your Postgres and break the FK the RLS design rests on |
| Session across languages | **`api` reads the `session` table read-only** | A short-lived JWT minted by `web`; proxy everything through `web` | Revocation stays instant (required by the security docs), no shared signing key, and it fails closed with no permissive default |
| Isolation | **RLS on `current_setting('app.user_id')`** | App-layer only; schema per tenant | `auth.uid()` died with Supabase. Defense-in-depth under the data modules — and it matters *more* with two ORMs, since there are two places to forget a `where` |
| Jobs | **PGQueuer** | Procrastinate, Celery, pg-boss | Transactional enqueue is the one property pg-boss was chosen for, and PGQueuer is built around it. Procrastinate has more features this project does not need yet; Celery needs Redis and loses the property |
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
| Local dev | **Docker Compose + MinIO + LocalStack** | Real AWS dev, Supabase CLI | `storage` and the KMS path get one implementation, not two. Compose now brings up five services, which is the first place the runtime count is actually felt |
| Tests | **pytest** (`api`, `jobs`) · **Vitest + Playwright** (`web`, `render`, fetch) | One runner; node:test; Cypress | Two languages means two runners, and that is fine. Three origins and a sandboxed iframe still cannot be tested in jsdom |
| Migrations | **Alembic** (`api`) · **drizzle-kit** (`web` auth tables), one dev DB | Branch-per-preview; one tool for both | Two tools against one database is only safe because the table sets are disjoint. **Alembic's `include_object` must exclude the auth tables** or autogenerate proposes dropping them |
| Python packaging | **uv** | pip + venv, Poetry, PDM | One fast tool for resolve, lock, and run. A committed lockfile and frozen installs are the same discipline `pnpm` already carries ([../coderules/dependencies.md](../coderules/dependencies.md)) |
| Model vendor | **None — evaluate per phase** | Standardising on one provider | Any model named today is wrong in two quarters. Build the switching apparatus, not the conviction |
| Evals | **Promptfoo (CI) + self-hosted Langfuse** | Braintrust, LangSmith, hosted anything | Model-neutrality without evals is not a strategy. Self-hosted because a prompt here is embargoed customer messaging |
| Agent framework | **None** | LangGraph, CrewAI, Pydantic AI, Agents SDK, Microsoft Agent Framework, Mastra | Four deterministic phases with a human gate is not an agent — your code makes every next-step decision. **And** it would be a runtime-privileged dependency in a class under active exploitation ([ai-stack.md](ai-stack.md)) |
| Pipeline language | **Python** | TypeScript | Follows the backend. Reverses the earlier lock; the Pydantic-mirror objection is answered by codegen, not by ignoring it |
| Prompt optimization | **DSPy/GEPA, offline only** | Hand-tuning forever; DSPy at runtime | Now native rather than a second language — which is exactly why "offline, outputs a committed prompt artifact" has to be a written rule instead of a happy accident |
| Model client | **Plain `httpx`, OpenAI-compatible** | Instructor, the OpenAI SDK, an agent framework | Start with a function. Take Instructor when it deletes your code rather than adding to it — and cap its retry, or it multiplies with the seam's repair |
| Publish render | **A thin `render` service (Node)** | Python + Playwright against the editor route; Next.js keeps it | Python cannot SSR React, and the renderer must have exactly one implementation. One endpoint, no secrets, no DB |
| Pipeline tools | **Read-only, tiered** | No tools; tools with side effects | Defense 5 forbids side effects, not tools. Tier 2 stays closed |
| Visual verification | **Render → screenshot → vision critic, one revision** | Schema validation alone; unbounded critic loop; an agent framework | The schema proves valid, not good. Built as a `for` loop with a literal limit in the seam — a bounded loop is not autonomy. Doubles cost to ~$0.40/experience, which is not a cost decision |
| ~~Publish render location: job worker~~ | Superseded — see "Publish render" above | | The premise (the job worker ships from the app repo, so it has the renderer) died with the Python move |
| v1 infrastructure | **None — Docker Compose only** | Full stack from day one | The long pole is the renderer, and a perfect VPC does not move that risk |
| Our own brand | **Light editorial "gallery wall"** | Wearing `cinematic-dark`; a dark atmospheric site | A site wearing its own art direction proves the product makes one thing. Also the shortest path away from the slop aesthetic ([../design/brand.md](../design/brand.md)) |
| Marketing hero | **A real embedded published artifact + a recorded generation** | Live anonymous generation; a video; a canned prompt box | Published pages are static, so real work costs nothing per visitor. A recorded SSE log is one model call ever and cannot fail on stage |
| Marketing analytics | **Self-hosted, cookieless, marketing site only** | Plausible Cloud, GA4, Fathom | A hosted vendor is a subprocessor decision ([../security/third-parties.md](../security/third-parties.md)). No cookies also means no consent banner |
| Chrome typography | **Commercially licensed, not shared with any AD** | Reusing the output's open faces; Inter/Geist | Our chrome is not redistributed, so the output's licence constraint does not bind it — and a shared face merges the two design systems |

## The three decisions that cost something

Everything else is a preference with a defensible rationale. These three trade away a stated guarantee, and they should be revisited deliberately rather than forgotten.

### 1. The Python backend move

The largest reversal in this repository. An earlier lock read *"Everything stays TypeScript — app, both workers, the pipeline"*, with three reasons: the pipeline is not ML work, the `Scene` schema is Zod and a Pydantic mirror would be a second source of truth, and one language is one toolchain.

**What it buys**, and these are the stated drivers rather than a post-hoc rationale: direct access to the Python AI/ML ecosystem (DSPy/GEPA above all), authoring fluency, a backend framework that is not a frontend framework's server half, and room for Python-shaped services later.

**What it costs**, in descending order of how much it will actually hurt:

| | |
|---|---|
| **A codegen step that must never become optional** | Pydantic → JSON Schema → TS types + a generated Zod validator. If regenerating produces a diff, the gate fails. The old objection was correct; the answer is that the second definition is a build artifact, not a maintained file |
| **Two runtimes more than before** | Five. One of them (`render`) is a language boundary rather than a trust boundary, and is labelled as such so it is never mistaken for a security control |
| **Two ORMs and two migration tools against one Postgres** | Survivable only because the table sets are disjoint and enforced. **Alembic's `include_object` excluding the auth tables is the single most destructive thing to get wrong here** |
| **`patterns.md` rule 4 weakens from "one wrapper" to "exactly two"** | Named in [../coderules/patterns.md](../coderules/patterns.md) rather than quietly restated |
| **`api` depends on a third-party session-table shape** | Better Auth's. Pinned, and a major upgrade touches both repos in one session |
| **The friction that kept agent frameworks out is gone** | LangGraph, CrewAI, and Pydantic AI are now one `pip install` away from the process holding database credentials. The rule became explicit because the barrier stopped being free ([ai-stack.md](ai-stack.md)) |

**The residual:** the thing to watch is not any single item above — it is that every one of them is a rule rather than a structure. This move traded several *structural* controls for *procedural* ones, which is the opposite of the direction [../security/adversarial-ai.md](../security/adversarial-ai.md) argues for everywhere else. That is acceptable because these are build-time rules enforced by a gate, not runtime rules enforced by care. It stops being acceptable the moment one of them is only in prose.

**Revisit when:** the codegen step has been bypassed once, or the two RLS wrappers have disagreed once. Either is evidence the split is costing more than the ecosystem is worth.

### 2. OpenRouter weakens schema enforcement

[../security/prompt-injection.md](../security/prompt-injection.md) claims *"a fully compromised model can only emit valid Scene JSON."* Under OpenRouter that is no longer enforced by the decoder — `strict: true` support varies by provider, and some treat a schema as a strong hint.

**What survives:** the schema parse was always the real gate. Decoder enforcement lowered how *often* the model produced something invalid; it never was the thing that stopped invalid output from being rendered. Output failing the parse is rejected, repaired once, then fails visibly. The claim restates as *"a fully compromised model can only cause a rejected generation"* — same outcome, different route.

**The residual:** repeated repair cycles burn tokens. Denial of wallet, already covered by quotas and the kill switch.

**Revisit when:** Build's repair rate is materially worse than a direct Anthropic call. That number is already in `generations` (`v1/ai-pipeline.md`) — watch it from the first generation. The seam exists so that moving one phase is a config change.

### 3. Client-side personalization ends `connect-src 'none'`

A published page was specified to make **zero** outbound requests, enforced by CSP. Two features broke it: the personalization field fetch and the analytics beacon.

**What survives:** `connect-src` names two exact paths — not `'self'`, not a host, two full URLs. The guarantee degrades from *cannot talk to anything* to *can talk to two endpoints you own, and a browser test proves nothing else*.

**The residual:** a recipient token now appears in a client-side request, which raises the stakes on `Referrer-Policy: no-referrer` and `Cache-Control: private, no-store`.

**Revisit when:** if analytics ever moves to CloudFront access logs and personalization to per-recipient pre-rendering, `connect-src 'none'` comes back. Both are viable; neither is worth doing before there are users.

## What this supersedes

Earlier documents locked decisions this directory reverses. Recorded here rather than silently contradicted.

| Was | Now | Where it was |
|---|---|---|
| Postgres in Docker → **Supabase** | Docker → **RDS/Aurora** | `v1/spec.md` |
| **Supabase Auth**, RLS via `auth.uid()` | **Better Auth**, RLS via `current_setting('app.user_id')` | [../security/tenancy-and-data.md](../security/tenancy-and-data.md) |
| `storage.ts`: local disk → **Supabase Storage** | local disk → **S3** (MinIO locally) | `v1/spec.md` |
| **Supabase client** in the dependency baseline | Removed | [../coderules/dependencies.md](../coderules/dependencies.md) |
| `anon` role has zero grants | **No anonymous role exists.** Nothing but the server connects | [../security/tenancy-and-data.md](../security/tenancy-and-data.md) |
| One isolated worker | **Two workers**, split on trust | [../security/infrastructure.md](../security/infrastructure.md) |
| Published pages served from an origin | **Static S3 artifacts**, no origin | [../security/content-and-web.md](../security/content-and-web.md) |
| `connect-src 'none'` | Two exact endpoints | [../security/content-and-web.md](../security/content-and-web.md) |
| Anthropic API called directly | **OpenRouter** behind a seam, no preferred vendor | `v1/ai-pipeline.md` |
| Shape violations are **unrepresentable** — the decoder prevents a hex code | **The schema parse is the only gate.** The decoder shifts the odds where the route enforces natively | `v1/scene-schema.md` |
| PDFs go to the model as a document block | Extracted in the **fetch worker** first; model-native reading is the documented fallback | `v1/ai-pipeline.md` |
| Prompt caching is one mechanism with one discount | Activation, discount rate, and minimum prefix all **vary by route** | `v1/ai-pipeline.md` |
| Generation has **no tools** | No tools **with side effects**; read-only tools tiered | [../security/prompt-injection.md](../security/prompt-injection.md) |
| ~$0.20 per experience | ~$0.40 once the visual loop is on | `v1/ai-pipeline.md` |
| Publishing renders on Vercel | ~~job worker~~ → the **`render` service** | [backend.md](backend.md) |
| **TypeScript everywhere** — app, both workers, the pipeline | **Python** backend (`api`, `jobs`); TypeScript for `web`, `render`, fetch worker | [ai-stack.md](ai-stack.md), `v1/spec.md` |
| **Zod is the source of truth** for the `Scene` shape | **Pydantic** is; Zod and TS types are generated from it | [../coderules/typescript.md](../coderules/typescript.md), `v1/scene-schema.md` |
| Drizzle is the ORM | **SQLAlchemy + Alembic** for app tables; Drizzle keeps **auth tables only** | [backend.md](backend.md) |
| **pg-boss** for jobs | **PGQueuer** | [backend.md](backend.md) |
| Plain `fetch` for the model seam | Plain **`httpx`**; Instructor is the upgrade path, not the Vercel AI SDK | [ai-stack.md](ai-stack.md) |
| The AI SDK's `generateObject` is the escape hatch | **Retired** — deprecated in AI SDK v6 and slated for removal, and the pipeline is Python now | [ai-stack.md](ai-stack.md) |
| DSPy *"has no real TypeScript equivalent"* | **False since `ax-llm/ax`**, and moot — DSPy is native now, and constrained to offline use by an explicit rule | [ai-stack.md](ai-stack.md) |
| Two repos — app, and fetch worker | **One repo per runtime**, five of them | [../coderules/structure.md](../coderules/structure.md) |
| `patterns.md` rule 4: **one** tenant wrapper | **Exactly two**, one per language, both named | [../coderules/patterns.md](../coderules/patterns.md) |
| Rule 8: *"Drizzle lives in feature data modules"* | Generalized to **the ORM of that runtime**, same rule both sides | [../coderules/README.md](../coderules/README.md) |

The security-relevant rows have been patched at the source. The rest stand as the record of what was believed at the time, which is the convention the version directories already use.

## Still open

Deliberately unresolved, with the condition that would resolve each:

| | Resolve when |
|---|---|
| **Per-phase model selection** | Real briefs and a measured repair rate exist. Guessing now optimizes nothing |
| **Buying commercial type** | v2's three ADs make the difference visible. The highest-leverage money in the product, deferred not refused |
| **Branch-per-preview databases** | Migrations against one shared dev DB start hurting |
| **Cloudflare for SaaS** | Custom domains pass roughly fifty and ACM's SAN limits bite |
| **Pricing and plan limits** | `v3/spec.md` — quota *enforcement* is built; the numbers are not chosen |
| **MFA rollout** | Better Auth ships it. Accounts hold integration credentials from day one, which argues for sooner than v3 |
| **The product's name** | Before phase 09. `d-design` describes the repository; the editor is where user-facing strings start accumulating and renaming after that is an audit ([../design/brand.md](../design/brand.md)) |
| **The chrome accent hue** | With the first real screen. The constraint is decided — one accent, roughly two uses, never violet or a gradient — and the hue is not |
