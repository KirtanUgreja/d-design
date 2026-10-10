# Performance

## Clarity first, measure before optimizing

Readable code by default. Optimize only what a profiler or a real metric flags. Premature optimization is, solo, wasted time spent making code harder to change in exchange for speed nobody measured a need for.

This is not "ignore performance." It is "spend the performance budget where it is visible to a user," and know where that is in advance.

## The only hot paths

> **Rewritten 2026-09-26 for v4.** The old list named the React renderer and a block-patch editor; neither exists now.

Three, and they are the whole list. Everything else is cold, and cold code should be written for clarity.

### 1. Generation: time and money per deck

The wait between approving an outline and seeing slides, and what each deck costs. Budgets and measurements live in [../v4/bench.md](../v4/bench.md).

- **Slides are composed in parallel**, five in flight behind one semaphore. After the planner assigns intents, slides do not depend on each other.
- **Stream whole slides as they pass QA.** The user watches the deck fill in and can abort early. Perceived speed beats raw speed.
- **Prompt caching is the biggest cost lever.** Stable prefix first (rules, theme, exemplars), so every compose call in a deck reuses one cached prefix ([patterns.md](patterns.md) rule 6).
- **Model choice per stage is a bench result, not a guess** ([../techstack/ai-stack.md](../techstack/ai-stack.md)). A cheaper model for repair is taken only if the bench shows parity.
- **The theme and the deck's generated look cost no model call.** They are code.

### 2. The QA render pool

Every slide is rendered at 1920×1080 in Chromium and measured, and re-measured after each repair and each edit.

- **One browser, launched once, a small pool of pages**, in the worker process. Never a launch per slide.
- **One measurement script, one screenshot per render.** The screenshot is reused as the thumbnail.
- **Bounded:** at most two repair rounds, so at most three renders per slide.
- **An inline text edit re-measures one slide**, not the deck.

### 3. The export file

The artefact a viewer opens, from `file://` with zero network requests.

- **Images and fonts are the weight, not the code.** Images are webp with a dimension cap. Fonts are vendored Latin-subset woff2, embedded as-is, and only the faces the deck uses. Target: under 3 MB for a typical deck.
- `ponytail:` no per-deck font subsetting. Trigger to add fontTools: a non-Latin locale, or fonts exceeding 1 MB of an export.
- **The file is complete without the player.** Text and layout are in the HTML; builds animate *in* from a visible resting state, never *out* of `opacity: 0`.
- **Do expensive work once, at generation.** Opening the file costs nothing.

## Two platform features that do this work for you

The stack moved in a direction that suits this project unusually well. Both of these are opt-in, and both replace code you would otherwise write.

### React Compiler — stop writing memoization

The React Compiler reached 1.0 and is **stable in Next.js 16**, though still opt-in (`reactCompiler: true`) while build-performance data accumulates. It analyses the component tree at build time and inserts the equivalent of `useMemo`, `useCallback`, and `React.memo` automatically.

For the editor's chrome (filmstrip, panels) this is pure subtraction: memoization is boilerplate that clutters components, drifts out of date, and is exactly the kind of code that gets added speculatively by someone optimizing without measuring.

**The rule that comes with it:** the compiler only transforms components that follow the Rules of React. Break them — side effects in render, direct state mutation — and it *silently skips that component* with a warning rather than transforming it wrongly. So the failure mode is not a bug; it is a component that quietly stopped being optimized. That is why the `react-hooks` lint rules are in the gate ([tooling.md](tooling.md)) rather than treated as advisory: they are now load-bearing for performance, not just correctness.

Do not hand-write `useMemo` unless the compiler demonstrably skipped something and a profiler says it matters.

### Caching

`web` holds no data of its own, so there is little to cache there: deck pages are dynamic and read from the API. Slide documents and thumbnails are versioned by slide version, so they can be cached hard by URL. Turbopack is the default builder in Next 16; do not fight it.

## Rules that keep the hot paths fast without micro-optimizing

- **Expensive work runs in the worker, not in a request.** From phase 27, model calls and Chromium live in `api/worker.py`; a route enqueues and returns. If something is being split up to fit inside a request, it is in the wrong process.
- **Never block the API event loop.** One sync call stalls every request ([python.md](python.md)).
- **List endpoints return thumbnails, never image payloads.**
- **Server components by default; client components only where interaction lives.**
- **Measure with a real tool** — the cost ledger, the profiler, Lighthouse — before changing code for speed.

## What not to optimize

The cold 90%: the composer, the outline editor, settings, account screens. Write these for clarity. A clever optimization in code that runs once per session is pure cost — harder to read, no measurable gain. If a profiler ever flags one, revisit it then, and not before.

**Cold for optimization is not cold for design.** [../design/app.md](../design/app.md) borrows this rule to ration *design attention*, and it lands on a different list: the composer and the outline gate are hot there and cold here, because they run once per session — which is exactly what makes them the screens a user forms an opinion on. Assemble them from shadcn/ui and never profile them; still spend real time on what they say and how they feel. Two budgets, two lists, one rule.
