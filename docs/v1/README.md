# v1 — generate, edit, publish

> One art direction, end to end. Proves the runtime, the editing model, and that the output can be beautiful.

**Start here:** [scene-schema.md](scene-schema.md). Everything in this repo depends on that shape.

v1 is deliberately small: a single user, a local Postgres, no accounts, no deployment. Its whole purpose is to answer one question — *can a typed scene tree plus a token layer produce something genuinely beautiful?* If the answer is no, nothing later matters.

## Files

| Doc | What's in it |
|---|---|
| [spec.md](spec.md) | The problem, the bet, 15 locked decisions, architecture, stack, persistence, build order, verification, risks |
| [plan/](plan/README.md) | **The implementation plan.** Twelve phases from an empty repo to a published experience, each with what to read, what to build, and what to verify. Build status lives in its README |
| [scene-schema.md](scene-schema.md) | **The IR.** Every type, all 11 blocks, 6 layouts and their regions, all validation rules, the editing patch shape |
| [art-direction.md](art-direction.md) | The token layer: 5 groups, `cinematic-dark`'s concrete values, motion implementation, accessibility |
| [ai-pipeline.md](ai-pipeline.md) | The four phases with concrete API shapes, validation and repair, caching, and what an experience costs |
| [market.md](market.md) | Why Gamma won and Tome died, and what that says about the wedge |

## Find it fast

| If you need… | Go to |
|---|---|
| A block's props, or which layouts exist | [scene-schema.md](scene-schema.md) → "Block types", "Layouts and regions" |
| Why character caps are enforced in Pydantic and not in the JSON Schema | [scene-schema.md](scene-schema.md) → "Validation rules" |
| Concrete token values for `cinematic-dark` | [art-direction.md](art-direction.md) → "Color", "Type", "Rhythm", "Motion" |
| How reduced motion is handled | [art-direction.md](art-direction.md) → "Motion" (WCAG 2.3.3: media query *and* an in-page toggle) |
| The request shape for a Build call | [ai-pipeline.md](ai-pipeline.md) → "Phase 3 — Build" |
| Why `CTA.href` can only come from the Brief | [ai-pipeline.md](ai-pipeline.md) → "Phase 3 — Build", and [../security/prompt-injection.md](../security/prompt-injection.md) |
| What a full experience costs to generate | [ai-pipeline.md](ai-pipeline.md) → "What an experience actually costs" (~$0.20, ~$0.40 with visual verification) |
| Why AI-generated product imagery is refused | [ai-pipeline.md](ai-pipeline.md) → "Imagery" |
| The database tables | [spec.md](spec.md) → "Persistence" |
| What is explicitly *not* in v1 | [spec.md](spec.md) → "Not in v1" |
| What to build first, and what blocks what | [plan/README.md](plan/README.md) → "Dependency graph" |
| How far through the build you are | [plan/README.md](plan/README.md) → "Status" |
| What the AI is allowed to call | [ai-pipeline.md](ai-pipeline.md) → "What the Build phase may call" |
| Why the decoder no longer guarantees the schema | [scene-schema.md](scene-schema.md) → "Why the length caps matter more than they look" |
| What v1 has to run on | [spec.md](spec.md) → "Stack" — Docker Compose and a dev server, no AWS |
| The two things authored in v1 purely for v3 | [spec.md](spec.md) → "Two things in step 3 that only pay off two versions later" |
| What the app's four screens should *feel* like | [../design/app.md](../design/app.md) — the product's own design, which is not the art direction |

## Superseded by later decisions

v1 stands as the record of what was believed at the time. These parts have since moved:

| v1 said | Now | Where |
|---|---|---|
| Postgres in Docker → Supabase | Docker → RDS/Aurora | [../techstack/decisions.md](../techstack/decisions.md) |
| `storage.ts`: local disk → Supabase Storage | local disk → S3, MinIO locally | [../techstack/infrastructure.md](../techstack/infrastructure.md) |
| Auth arrives with Supabase | Better Auth, in v3 | [../techstack/backend.md](../techstack/backend.md) |
| A single named model for every phase | One seam, **no preferred vendor**; per-phase choice decided by repair rate | [../techstack/ai-stack.md](../techstack/ai-stack.md) |
| Shape violations are *unrepresentable* — the decoder prevents them | **The schema parse is the only gate.** Enforcement varies by provider; the decoder shifts the odds | [scene-schema.md](scene-schema.md), [ai-pipeline.md](ai-pipeline.md) |
| PDFs go to the model as a document block | Extracted in the **fetch worker** first; model-native reading is the documented fallback | [../techstack/infrastructure.md](../techstack/infrastructure.md) |
| Prompt caching is one mechanism with one discount | Activation, discount, and minimum prefix all vary by route | [ai-pipeline.md](ai-pipeline.md) |
| Generation has no tools | No tools *with side effects*; read-only tools are tiered, and v1 ships three | [../techstack/pipeline-tools.md](../techstack/pipeline-tools.md) |
| ~$0.20 per experience | ~$0.40 once v2's visual verification loop is on | [ai-pipeline.md](ai-pipeline.md) |

**Two things were added to v1 that v1 does not benefit from**, because both are cheap now and brutal to retrofit: CSS logical properties throughout the renderer (v3 RTL), and a pure renderer with no environment branching (v3 runs it in three processes). Both are in [spec.md](spec.md) → Build order.

The stack table in [spec.md](spec.md) has been patched where a stale line would actively mislead someone building from it. Everything else stands.

## Connects to

| | |
|---|---|
| [../v2/README.md](../v2/README.md) | What v2 changes, and why the abstraction was unproven with one AD |
| [../techstack/README.md](../techstack/README.md) | Where all of this actually runs |
| [../security/prompt-injection.md](../security/prompt-injection.md) | The threat that arrives with the first generated experience |
| [../coderules/patterns.md](../coderules/patterns.md) | The no-styling invariant and the pure renderer, as enforced rules |
| [../design/README.md](../design/README.md) | How **our own** app looks — the second design system, and the one that must never merge with `cinematic-dark` |
