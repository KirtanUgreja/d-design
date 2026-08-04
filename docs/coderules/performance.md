# Performance

## Clarity first, measure before optimizing

Readable code by default. Optimize only what a profiler or a real metric flags. Premature optimization is, solo, wasted time spent making code harder to change in exchange for speed nobody measured a need for.

This is not "ignore performance." It is "spend the performance budget where it is visible to a user," and know where that is in advance.

## The only hot paths

Three, and they are the whole list. Everything else is cold, and cold code should be written for clarity.

### 1. Page load of a published experience

The thing a viewer waits on, and the thing a marketer's audience judges. Non-negotiable, because it is not an optimization — it is the product working.

- Published pages are **static artifacts, not routes**. The job worker renders HTML once at publish and writes it to S3; CloudFront serves it. No server, no DB query, no LLM call per view ([../techstack/infrastructure.md](../techstack/infrastructure.md)). [../v3/live-data.md](../v3/live-data.md) bakes live values in at render precisely so this stays true.
- **Images and video are the weight**, not the code. Enforce dimension caps, serve compressed, lazy-load below the fold. `ScrollSequence` and 3D carry hard budgets — see [../v3/dimensional.md](../v3/dimensional.md).
- **Fonts** are the other weight. Subset per script, `font-display: swap`, preload the display face.
- **Hydration is the only JavaScript**, and it is a deliberate spend ([../techstack/frontend.md](../techstack/frontend.md)): React and Motion ship so that published motion is the same code as edited motion. Nothing else is allowed to join them — no analytics SDK, no tag manager, no third-party script. The budget is already committed.
- **The page must be complete before hydration.** Text, images, and layout are in the HTML; reveals animate *in* from a visible resting state, never *out* of `opacity: 0`. A page that is blank until JS arrives has traded a real guarantee for an animation.
- The scene tree is small JSON; rendering it is never the bottleneck. The assets around it always are.

### 2. Generation latency

The wait between prompt and page. Perceived speed matters more than wall-clock here.

- **Stream scene by scene.** The user watches the experience assemble and can abort a bad direction early. This is a perceived-performance decision from [../v1/ai-pipeline.md](../v1/ai-pipeline.md), and it beats any raw-speed optimization.
- **Build scenes in parallel** where the director's layout assignment removes cross-scene dependency.
- **Model choice is the real lever:** fast model for director and edit, strong model only for build. Optimizing prompt tokens matters more than optimizing any code around the call — and which model goes where is an eval result, not a guess ([../techstack/ai-stack.md](../techstack/ai-stack.md)).
- **Never block the stream on verification.** The visual critic ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)) runs *behind* the stream: the scene appears as soon as it validates, and a correction surfaces afterwards if needed. Waiting on a render and a vision call before showing anything would spend the perceived-speed win on a quality gain nobody can see happening.

### 3. The editor canvas

Direct manipulation must feel instant, or the editing model that justifies the whole product falls flat.

- Editing patches **one block** and re-renders the minimum. Never regenerate or re-render the whole tree on a keystroke — the patch shape from [../v1/scene-schema.md](../v1/scene-schema.md) exists for this.
- The reskin transition is the one place to spend real animation effort ([../v2/transformations.md](../v2/transformations.md)); animate only visible scenes, swap off-screen ones instantly.
- Debounce AI-assisted edits; do not fire a model call per keystroke.

## Two platform features that do this work for you

The stack moved in a direction that suits this project unusually well. Both of these are opt-in, and both replace code you would otherwise write.

### React Compiler — stop writing memoization

The React Compiler reached 1.0 and is **stable in Next.js 16**, though still opt-in (`reactCompiler: true`) while build-performance data accumulates. It analyses the component tree at build time and inserts the equivalent of `useMemo`, `useCallback`, and `React.memo` automatically.

For the editor canvas — hot path #3, where re-render cost is the whole problem — this is the single highest-leverage setting in the project. It is also pure subtraction: memoization is boilerplate that clutters components, drifts out of date, and is exactly the kind of code that gets added speculatively by someone optimizing without measuring.

**The rule that comes with it:** the compiler only transforms components that follow the Rules of React. Break them — side effects in render, direct state mutation — and it *silently skips that component* with a warning rather than transforming it wrongly. So the failure mode is not a bug; it is a component that quietly stopped being optimized. That is why the `react-hooks` lint rules are in the gate ([tooling.md](tooling.md)) rather than treated as advisory: they are now load-bearing for performance, not just correctness.

Do not hand-write `useMemo` unless the compiler demonstrably skipped something and a profiler says it matters.

### `use cache` — the caching model matches the product

Next.js 16's Cache Components replace route-segment revalidation config with an explicit `"use cache"` directive plus `cacheLife()`. Under `cacheComponents`, the old route-segment config is deprecated, so this is the model to author against from the start rather than migrate to later.

It is a good fit here because the product's caching story is genuinely mixed and was always going to need this granularity: a published experience is static and should be cached hard, its live-data bindings have a real TTL ([../v3/live-data.md](../v3/live-data.md)), and the editor is fully dynamic. One directive at the component that owns each of those beats a per-route setting that has to describe all three.

Turbopack is the default builder in 16 (2–5× faster builds). Nothing to decide — just do not fight it.

## Rules that keep the hot paths fast without micro-optimizing

- **Static and cacheable by default.** A published page that never touches the DB scales to a viral launch for free and cannot exhaust a connection pool.
- **Do expensive work once, at publish, not per view.** Transcreation, live-data fetch, 3D poster generation — all happen at publish or on a schedule, never on the viewer's request.
- **Expensive work runs in the job worker, not in a request.** It has no function-timeout ceiling, so a 12-locale publish is one job rather than a chunking workaround. If something is being split up to fit inside a request, it is in the wrong process.
- **Server components by default; client components only where interaction lives.** The editor is interactive; a published page mostly is not.
- **Measure with a real tool** — the profiler, Lighthouse, a token counter — before changing code for speed. "This feels slow" is a reason to measure, not a reason to optimize.

## What not to optimize

The cold 90%: intake forms, the outline editor, settings, the brand-kit UI, admin. Write these for clarity. A clever optimization in code that runs once per session is pure cost — harder to read, no measurable gain. If a profiler ever flags one, revisit it then, and not before.

**Cold for optimization is not cold for design.** [../design/app.md](../design/app.md) borrows this rule to ration *design attention*, and it lands on a different list: intake and the outline gate are hot there and cold here, because they run once per session — which is exactly what makes them the screens a user forms an opinion on. Assemble them from shadcn/ui and never profile them; still spend real time on what they say and how they feel. Two budgets, two lists, one rule.
