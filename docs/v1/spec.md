# v1 — spec

## Theme

**One paragraph. What this release proves that the last one did not.**

The previous release proved a schema-valid, art-directed scene tree could render to HTML. It could not prove the thing that matters: that a deck can be *generated* rather than *assembled from repeated frames*, and that the result reads as designed rather than templated.

v1 proves the core claim with a real, downloadable artefact: **a user gives a topic, a slide count, and (optionally) a brand kit; an AI-led interview iterates until the user is satisfied; a mapping pass turns the agreed outline into a per-slide spec; a build pass generates each slide individually in HTML; the result exports as one self-contained `.html` file that runs offline in any modern browser with zero network requests.**

The old "three art directions" were still *skeletons* — a fixed frame that the model filled in. v1 abandons the skeleton entirely. The design system itself is **generated per deck** from a large discrete combinatorial space, and each slide is generated individually, so two decks cannot converge on the same frame and no single deck repeats one.

## The flow

```
user input (topic, slide count, brand kit, extra info)
  → AI-led brainstorm/interview (iterates with the user until they are satisfied)
  → mapping pass (outline → per-slide spec: content, layout, animation, charts)
  → slide builder (per-slide: generate one beautiful HTML slide at a time)
  → single-file HTML export (fonts, styles, motion embedded; runs offline)
```

Each of the four phases is a **separate AI call** with a **separate, versioned prompt**, run by a **plain, deterministic orchestrator** — not an agent framework. The "different skills and plugins" you described live in the *prompt/design-tool layer* (per-slide design rules, a layout catalogue, a chart library), not in a runtime graph.

## Commitments vs bets

### Commitments — true regardless of user feedback

| Commitment | Why it holds |
|---|---|
| **The artefact is a single self-contained `.html` file.** Fonts, styles, motion, and scripts embedded; runs from `file://` or any static host with **zero network requests** | This is the whole product. It is what makes it offline, portable, and un-attackable by a CDN |
| **There is no fixed skeleton, no "art direction" as a theme, no template the model fills in.** The design system is generated per deck | The thing the user deleted the old codebase for. It does not come back under a new name |
| **Per-deck design systems are sampled from a large discrete combinatorial space, not invented free-form by one prompt** | Your own findings.md measured that asking one model for three distinct artefacts returns three variations of one. Diversity is an architecture problem, not a prompting problem |
| **Within a deck, layouts vary across slides while type/color stay constant** | This is how a human designer works — a deck reads as ONE designed thing, not a collage. Cohesion plus variety |
| **The user approves an outline before slides are generated** | The old human gate, kept. It is simultaneously the cost control, the quality control, and the trust device |
| **The pre-commit gate stays green — typecheck, lint, format, and generated code regenerates with no diff** | Non-negotiable 11. The docs gate too |

### Bets — each names its falsifier

| Bet | What would disprove it |
|---|---|
| **Per-slide generation produces decks that read as authored rather than assembled.** The variance comes from the design system + slide-level layout, not from a repeated frame | A blind comparison where testers cannot tell our decks from Gamma's at > chance level |
| **A large combinatorial design space (10–15 families in v1) is enough to make two decks visibly different.** The fingerprint of two random decks differs beyond a threshold | Two sampled decks share a fingerprint above threshold on the acceptance run |
| **The offline single-file format is a feature, not a limitation.** Marketers actually want a file they can run offline / send / embed, versus a hosted URL | Early users cite "I want a link to share" as a blocker more often than they cite the file as a win |
| **The AI-led interview is a differentiator** versus a single prompt box | Users skip the interview and type one prompt, then edit manually |
| **The design space can be verified by a fingerprint before rendering** — the variety claim is measurable, not vibes | The fingerprint metric cannot distinguish a varied deck from a collapsed one |

## Locked decisions

| Axis | Decision | Why |
|---|---|---|
| **Artefact** | One self-contained `.html` file, offline, zero network | The product. Portability + un-attackable + the "wow" of a file that just works |
| **Design system** | Generated per deck from a discrete registry; never a fixed skeleton | The deleted disease. Diversity is structural |
| **Design-space size (v1)** | ~10–15 families | Big enough to never see the same deck twice; small enough to keep quality high |
| **Within-deck variety** | Layouts vary per slide; type/color/tone constant | Human-designer behavior. Cohesion + variety |
| **Pipeline** | Four plain sequential AI calls, deterministic orchestrator, **no agent framework** | Agent frameworks are a runtime-privileged dependency under active exploitation, and this pipeline is not an agent — your code makes every next-step decision |
| **Skills/plugins** | Live in the prompt + design-tool layer (per-slide rules, layout catalogue, chart library), not in a runtime agent graph | The variety and beauty come from the design system, not from orchestration |
| **Schema** | A `Deck` schema (Pydantic-owned, TS + Zod generated) | One source of truth, both languages |
| **No-styling invariant** | AI output carries no presentational values (hex/px/font/duration); the schema has no field for them | The old rule survives — it is what makes the design system the single source of visual truth |
| **Human gate** | Outline approval before slide generation | Cost control + quality control + trust |
| **Export** | HTML (v1) + PDF (v2) | HTML is the product; PDF is the distribution add-on |
| **Images** | **First-class content.** The slide builder decides per-slide whether an image earns its place — background, hero, illustration, chart companion — and generates it via **OpenRouter image models**. Images are embedded as data URIs in the single-file HTML | "Does this slide want an image?" is a design decision the build makes per slide, and it is how a deck stops being text-on-background. Generated images are new works (no stock-licensing cost), and embedding keeps the zero-network guarantee |
| **Deck navigation** | **Slide-based**: arrow keys, Space, on-screen prev/next buttons, fullscreen, a slide counter. **No scroll.** Autoplay banned | A deck is presented, not read. Scroll is Gamma's vertical-card pattern — the page-shaped disease this product exists to cure. The file degrades to swipe + buttons on touch |
| **Publishing** | The `.html` file is the artefact; a hosted URL is v3 | The file is the product now; the URL is the business later |
| **Renderer** | A pure, mode-free renderer that produces the exact same bytes in editor and export | What you edit is what you ship |

## What changes from the last version

| Old | New | Why |
|---|---|---|
| Three fixed art directions (`cinematic-dark`, `editorial-light`, `bold-brutalist`) | A per-deck generated design system from a discrete registry | The fixed skeleton was the disease |
| Schema-valid `Scene` tree of "scenes" | A `Deck` of slides, each with its own layout archetype | The unit of generation is the slide, not the scene |
| A four-phase pipeline (Intake → Director → Build → Edit) | A four-phase pipeline (Interview → Mapping → Build → Review), **per-slide build** | The mapping pass makes per-slide generation possible |
| Published static HTML to S3 + CloudFront, originless | A **downloadable self-contained `.html` file** | Offline is the product; the file replaces the URL as the primary artefact |
| `connect-src 'none'` → two named endpoints (personalization, analytics) | `connect-src 'none'` — a self-contained offline file talks to **nothing** | Offline kills the personalization and analytics endpoints |
| ~$0.20 per experience, ~$0.40 with visual loop | Cost per deck is higher (per-slide generation); measured in v1, budgeted in v2 | Per-slide generation is more calls; that is the price of the variety |
| Editor with property panel, undo/redo, brand kit upload | v1 is a **lean flow**: interview → mapping → build → review → export. Editor is v2+ | The lean flow is the wedge; the editor is the retention loop |
| Uploads (v1) deferred | Brand kit in v1 is **typed text** (colors, fonts, vibe), not file upload | File upload is a whole security surface; text brand kit proves the flow |

## Risks

1. **Per-slide generation produces incoherent decks.** Each slide is beautiful but the deck does not read as one authored thing. → The design system is constant within a deck; the mapping pass owns the through-line. Retired if the blind test passes.
2. **The combinatorial space collapses.** Sampled families end up looking like variations of one another. → The acceptance run measures fingerprints, and the fingerprint is asserted in CI. Retired if two sampled decks differ above threshold.
3. **The offline single-file format is a feature nobody asked for.** → The blind test and early-user interviews. If "I want a link" dominates, the URL becomes the v2 artefact and offline becomes a mode.
4. **The AI-led interview is annoying.** Users want a prompt box, not a conversation. → The interview is short, skippable, and shows its value (the outline). Retired if skip rate is high.
5. **Brand kit via typed text is too weak.** Marketers expect to drop in their logo and colors. → v2 adds brand-kit upload and color extraction; v1's typed text is the honest minimum.
6. **Generated images raise cost and add a failure mode.** Image models are the most expensive call per deck, and a bad image (wrong subject, on-brand miss, or a grey rectangle from a transient failure) is a visible defect. → The slide builder prompts images within the design family's visual rules; images are embedded, capped in dimension, and the visual review (phase 07) catches the failures. Cost per deck is measured and budgeted in v2. Retired if the review's image-failure rate is high.
