# Performance

## Clarity first, measure before optimizing

Readable code by default. Optimize only what a profiler or a real metric flags. Premature optimization is, solo, wasted time spent making code harder to change in exchange for speed nobody measured a need for.

This is not "ignore performance." It is "spend the performance budget where it is visible to a user," and know where that is in advance.

## The only hot paths

Three, and they are the whole list. Everything else is cold, and cold code should be written for clarity.

### 1. Page load of a published experience

The thing a viewer waits on, and the thing a marketer's audience judges. Non-negotiable, because it is not an optimization — it is the product working.

- Published pages are **static after render**. No DB query, no LLM call per view. Server-render from stored JSON, ship HTML. ([../v3/live-data.md](../v3/live-data.md) bakes live values in at render precisely so the page stays static.)
- **Images and video are the weight**, not the code. Enforce dimension caps, serve compressed, lazy-load below the fold. `ScrollSequence` and 3D carry hard budgets — see [../v3/dimensional.md](../v3/dimensional.md).
- **Fonts** are the other weight. Subset per script, `font-display: swap`, preload the display face.
- The scene tree is small JSON; rendering it is never the bottleneck. The assets around it always are.

### 2. Generation latency

The wait between prompt and page. Perceived speed matters more than wall-clock here.

- **Stream scene by scene.** The user watches the experience assemble and can abort a bad direction early. This is a perceived-performance decision from [../v1/ai-pipeline.md](../v1/ai-pipeline.md), and it beats any raw-speed optimization.
- **Build scenes in parallel** where the director's layout assignment removes cross-scene dependency.
- **Model choice is the real lever:** fast model for director and edit, strong model only for build. Optimizing prompt tokens matters more than optimizing any code around the call.

### 3. The editor canvas

Direct manipulation must feel instant, or the editing model that justifies the whole product falls flat.

- Editing patches **one block** and re-renders the minimum. Never regenerate or re-render the whole tree on a keystroke — the patch shape from [../v1/scene-schema.md](../v1/scene-schema.md) exists for this.
- The reskin transition is the one place to spend real animation effort ([../v2/transformations.md](../v2/transformations.md)); animate only visible scenes, swap off-screen ones instantly.
- Debounce AI-assisted edits; do not fire a model call per keystroke.

## Rules that keep the hot paths fast without micro-optimizing

- **Static and cacheable by default.** A published page that never touches the DB scales to a viral launch for free and cannot exhaust a connection pool.
- **Do expensive work once, at publish, not per view.** Transcreation, live-data fetch, 3D poster generation — all happen at publish or on a schedule, never on the viewer's request.
- **Server components by default; client components only where interaction lives.** The editor is interactive; a published page mostly is not.
- **Measure with a real tool** — the profiler, Lighthouse, a token counter — before changing code for speed. "This feels slow" is a reason to measure, not a reason to optimize.

## What not to optimize

The cold 90%: intake forms, the outline editor, settings, the brand-kit UI, admin. Write these for clarity. A clever optimization in code that runs once per session is pure cost — harder to read, no measurable gain. If a profiler ever flags one, revisit it then, and not before.
