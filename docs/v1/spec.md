# v1 Spec

## Problem

Presentation tooling splits into two useless halves.

**Template tools** (Gamma, Beautiful.ai, Canva) generate content *into* fixed layouts. They make presentations faster, not better. Every deck shares a skeleton, and the skeleton is visible. Gamma's own reviews name the symptom: generic AI phrasing that needs manual refinement, and design customization "limited compared to PowerPoint or Keynote for pixel-level control."

**Coding agents** (Artifacts, v0, Lovable) generate working HTML with no narrative sense, no visual hierarchy, and no answer to the second prompt. Once 2,000 lines exist, "make that headline smaller" means a regeneration that destroys the parts the user liked.

Nothing turns an idea into an immersive presentation experience that stays editable.

**Read [market.md](market.md) before building.** Gamma reached ~$100M ARR and profitability with ~50 people; Tome raised more, hit ~$4M ARR, and shut its presentation product down in April 2025. Its post-mortem — *"building AI for everyone at once is fundamentally flawed"* — is the single most useful document in this repo's problem space, and it is the reason the wedge below is narrow on purpose.

## The bet

The AI never writes styling. It emits content and intent. An art-direction layer resolves intent into concrete values.

**The rule, stated as a test:** if a value the AI emitted could have been supplied by the art direction instead, it does not belong in AI output. No hex codes, no pixel values, no durations, no font names, no easing curves. Ever.

This is not a style preference. It is the load-bearing constraint — editing, design consistency, the product boundary, and cheap art-direction variety all rest on it. Every design decision below follows from it.

## Locked decisions

| Axis | Decision | Why |
|---|---|---|
| First user | Marketers / product launches | High design standards, real budget, values wow |
| Positioning | Presentation framing, web-experience reality | Bigger market; see Risk 3 |
| Delivery | Live URL, embed, fullscreen + keyboard | Fullscreen is ~50 lines and keeps "presentation" honest |
| Runtime | Typed primitives + sandboxed custom slots | 90% structure, 10% surprise |
| Unit | Scroll sections first | Matches wedge and delivery; slides is a playback mode later |
| Editing | Select → property panel → element-scoped prompt | ~1/5 the cost of a design canvas, covers ~90% of edits |
| Brand | Brand kit is a v1 primitive | Marketers cannot ship off-brand. Table stakes, not a feature |
| Intake | Import / prompt / AI-led Q&A → Brief | Meets users wherever their content already lives |
| Generation | Two-phase: outline approval, then build | Kills bad directions before the expensive call |
| Variety | Art-direction layer above components | Avoids the exact failure we accuse Gamma of |
| Motion | Named vocabulary per art direction | LLMs pick bad easing and timing, reliably |
| Visuals | Uploads + code-generated abstracts + AI imagery | Uploads make output shippable; abstracts make it look designed |
| Charts | Animated `Stat` only | Real charting is a product inside the product |
| Art direction | `cinematic-dark` | Forgiving of sparse content — negative space reads as intentional |
| Pricing | Deferred | Decide when token cost is measurable, not before |

## Architecture

Four pieces. Each is independently understandable and testable.

```
Brief ──▶ Outline ──▶ Scene tree ──▶ SceneRenderer ──▶ URL / embed / fullscreen
         (director)    (build)         (art direction
                                        resolves intent)
```

**Scene tree** — the IR. A typed, validated JSON document. The single contract between the AI, the editor, and the renderer. See [scene-schema.md](scene-schema.md).

**Art direction** — five token groups that turn intent into values. See [art-direction.md](art-direction.md).

**AI pipeline** — four calls, not one. See [ai-pipeline.md](ai-pipeline.md).

**Renderer** — one React tree, used four ways: editor canvas, published page, embed, fullscreen. One implementation means no drift between what you edit and what ships.

### The product boundary

Custom slots let the AI write free HTML/CSS/JS for one signature moment per experience. Each runs in a `srcdoc` iframe with `sandbox="allow-scripts"` and **no** `allow-same-origin`.

That combination means no storage, no cookies, no parent DOM access, no credentialed requests. The not-an-app-generator boundary is enforced by the browser, not by prompt instructions a user can talk their way around.

## Stack

| | |
|---|---|
| **Next.js 16 (App Router) + React 19.2** | Turbopack and the React Compiler are both stable as of 16; Cache Components give explicit control over what's cached on the publish route. React 19.2's View Transitions are the natural mechanism for v2's reskin — worth knowing it's there, not worth using yet |
| **TypeScript** | Strict. See [../coderules/typescript.md](../coderules/typescript.md) |
| **Postgres in Docker → ~~Supabase~~ RDS/Aurora** | Still Postgres either way, so the migration is a connection string. **Superseded:** the operational stack moved to AWS — see [../techstack/decisions.md](../techstack/decisions.md) |
| **Drizzle** | Typed SQL, migrations |
| **Zod** | Schema, validation, and inferred types — one source |
| **Motion** (`motion`, import `motion/react`) | **Not `framer-motion`.** Renamed in 2025 and now maintained independently at motion.dev; the old package still installs but is no longer actively developed |
| **Tailwind** | App chrome only. Never the art direction — that's CSS variables |
| **No preferred model vendor** | Every phase goes through one provider seam. **Superseded:** an earlier draft named a single model for every phase; model choice is now an empirical question answered by repair rate — see [../techstack/ai-stack.md](../techstack/ai-stack.md) and [ai-pipeline.md](ai-pipeline.md) |

**Where this runs in v1: Docker Compose and a dev server. That is all** — no AWS account, no workers, no CDN, no auth ([../techstack/infrastructure.md](../techstack/infrastructure.md)). The operational stack lands with v3, the release that has real users. Building it earlier feels productive and does not move Risk 1 at all.

Two consequences of the Postgres-first choice:

- **No auth in local v1.** Single user. Auth arrives in v3 — the first version an outside person opens. (Provider is now **Better Auth**, not Supabase Auth; see [../techstack/backend.md](../techstack/backend.md).)
- **One thin `storage.ts`** for uploads (local disk → **S3**, with MinIO locally). This is the only abstraction with a planned second implementation. Nothing else gets one — and pointing it at the S3 API from day one means it ends up with one implementation after all.

**The React Compiler being stable matters for the coderules.** `performance.md` says clarity first, measure before optimizing — the compiler handles memoization automatically, so hand-written `useMemo`/`useCallback` is now usually noise rather than optimization.

## Build order

1. Scene schema + Zod types — everything depends on this shape
2. `cinematic-dark` tokens + motion vocabulary
3. `SceneRenderer` + the 11 primitives — **the long pole; this is design work, not typing**
4. Publish route, embed, fullscreen
5. Build phase: Scene JSON generation + validate/repair loop
6. Director phase: Brief → editable outline
7. Intake: AI-led Q&A → Brief
8. Editor: select → property panel → element-scoped prompt
9. Brand kit + uploads
10. AbstractVisual generators → AI imagery → Slot

**Steps 1–4 ship without any AI involved.** Hand-write a scene tree, render it, and look at it. That is the cheapest possible test of the riskiest assumption. Do not build step 5 until step 3 looks genuinely good.

### Two things in step 3 that only pay off two versions later

Both are nearly free while writing the renderer and brutally expensive to retrofit across 19 primitives and 3 art directions. Neither has any v1 benefit, which is exactly why they get named here rather than discovered in v3.

**Author every layout in CSS logical properties.** `margin-inline-start`, not `margin-left`. `padding-block-end`, not `padding-bottom`. `inline-size`/`block-size`, not `width`/`height`. `border-inline-start`, not `border-left`.

v3 ships RTL for Arabic and Hebrew, and if the renderer was authored logically, RTL costs setting `dir` on the root — no mirrored stylesheet, no per-component branching. Authored physically, it means auditing every primitive under every art direction. **This is a v1 decision with a v3 payoff and no v1 upside** ([../v3/localization.md](../v3/localization.md)). `transform` is the one documented exception, and it is where motion lives — noted in [art-direction.md](art-direction.md).

**Keep the renderer pure.** No `mode` prop, no `process.env`, no `typeof window` ([../coderules/patterns.md](../coderules/patterns.md), rule 6). It looks like an ordinary component-hygiene rule in v1, where the renderer runs in one process. It is load-bearing from v3, where the same components run in the app, in the job worker that publishes, and in the visual verification loop — and must behave identically in all three.

Step 5 also brings the pipeline's first tools: `get_brand_kit`, `list_assets`, `get_constraints` — pure reads, no side effects ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)). `list_assets` is how the Build phase selects imagery, which earlier drafts required without ever specifying.

## Persistence

Five tables. No more until something demands one.

```
experiences  id, title, mode, brand_id, art_direction, scenes (jsonb),
             published_at, created_at, updated_at
brands       id, display_font, text_font, primary, secondary, neutral,
             logo_asset_id
assets       id, kind, storage_key, mime, width, height, alt, source,
             created_at
briefs       id, experience_id, payload (jsonb)
generations  id, experience_id, phase, tokens_in, tokens_out,
             repaired (bool), error, created_at
```

The scene tree lives as a single `jsonb` column, not normalized into scene and
block tables. It is always read and written whole, it is validated by Zod rather
than by SQL, and normalizing it would buy queries nobody runs.

`generations` exists only to answer two questions later: what does an experience
actually cost, and which validation rules fail most. Both decide real things —
pricing, and where the schema and prompt disagree.

Two columns to add now rather than backfill: **model id and provider route.** Under a router those are different questions, and the repair rate — the number that decides model selection for every later version ([../techstack/ai-stack.md](../techstack/ai-stack.md)) — is meaningless without both. Record token counts *and* call counts, since not every provider bills per token.

**What never goes in this table: prompts, outputs, or brief content.** A brief here is a customer's unreleased launch messaging under embargo ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)). Phase, counts, a repair flag, an error class, and a duration answer both questions without storing any of it.

## Verification

Six checks. Each maps to a build-order step and fails loudly if that step regresses.

| What | How |
|---|---|
| **Schema** | Round-trip a hand-written `Experience` through Zod, render it, assert no invalid state survives. One `test_scene_schema.ts` with asserts. |
| **No styling in AI output** | Walk every block prop in a generated tree, fail on `/#[0-9a-f]{3,8}\|[\d.]+(px\|rem\|em\|ms\|s)\b/i`. This is the invariant test — see scene-schema. |
| **Renderer** | One page rendering all 11 primitives under `cinematic-dark`. Visual judgment, not snapshots — quality here is human. |
| **Pipeline** | 5 golden briefs → Director + Build → assert 100% Zod-valid after at most one repair. The one automated check that matters. |
| **Edit** | Patch a block, assert the tree stays valid and only the target block changed. |
| **Slot sandbox** | Put `fetch()` and `localStorage` in a slot, confirm both throw. Executed inside a real frame, not jsdom — [../security/testing.md](../security/testing.md) |
| **Logical properties** | Set `dir="rtl"` on the root and confirm the layout mirrors with no stylesheet change. Costs nothing now; it is the only cheap moment to find out the renderer was authored physically |

**End to end:** brief → outline → build → edit a headline → publish → open the URL
in a private window → fullscreen with arrow keys → embed in a blank HTML page.

Also check `prefers-reduced-motion: reduce` collapses all motion, and that every
`Image` has non-empty `alt`. Generated experiences are public web pages.

The golden-brief run is not only a test. **It is the seed of the eval set** that decides model selection from v2 onward ([../techstack/ai-stack.md](../techstack/ai-stack.md)) — structural assertions gate every PR, quality scoring is tracked as a trend and never gates. Growing five briefs into a real dataset is the highest-leverage AI work in the project after the renderer.

## Not in v1

Charts · PDF/PPTX export · speaker notes / presenter view · collaboration · analytics · custom domains · stock images · multiple art directions · freeform canvas · version history · slides mode.

## Risks

**1. Art direction #1 must be genuinely beautiful.** If it isn't, the runtime, the pipeline, and the canvas are all worthless. This is a design problem, solo, and the one place AI assistance helps least. Collect reference work before writing tokens.

**2. AI-invented marketing claims.** Marketers cannot ship copy the AI made up. Intake captures *approved* messaging; the build phase arranges it and must not embellish. Enforced in the build prompt and reviewable at the outline gate.

**3. "Presentation" framing sets expectations v1 won't meet.** PPTX, PDF, speaker notes will all be asked for in week one. Fullscreen + keyboard nav is the minimum that keeps the word honest; messaging carries the rest. Have a real answer ready, not "coming soon."

**4. The art-direction layer is unproven until there are two.** v1 ships one, so the central claim — that variety is cheap — is asserted, not demonstrated. First priority after v1 is art direction #2, and if it requires renderer changes, the abstraction is wrong.
