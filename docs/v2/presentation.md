# Presentation

The unit is a slide. Someone stands up and shows it to a room. Everything in this document follows from that one sentence.

## Why this document exists

**Decided 2026-08-10.** Until this date the product was drifting into a scrolling web page that could be presented. That drift was never argued for — it accumulated. v1 locked *"scroll sections first; slides is a playback mode later"* and *"presentation framing, web-experience reality"*, and every phase after it inherited the assumption without re-testing it.

The re-test failed. The original intent was a presentation, the competitive position is stronger as a presentation, and the architecture is *better* as a presentation. Three findings, in order of how much they should have changed the plan earlier:

**1. The market's loudest complaint is caused by exactly this drift.** Gamma's most-cited defect across reviews is that its PowerPoint export breaks — text shifts, spacing changes, fonts substitute. The stated cause is structural: *its layouts are optimised for vertical cards and do not convert cleanly into fixed 16:9 slides*. That is not an export bug. It is a page-shaped product being asked to become a deck. It also cannot work offline at all, which is a real reason people still open PowerPoint in a venue with bad wifi. **Both defects are inherited by anything built page-first.**

**2. A slide is a solvable frame; a page is not.** Composition — the thing [plan/17-composition.md](plan/17-composition.md) exists to fix — needs to know what it is composing inside. A page's frame is whatever the reader's window happens to be, so "one anchor per scene" and "asymmetric split" are hopes. A slide's frame is bounded, so they are constraints a linter can check. **The art-direction layer gets stronger here, not weaker.**

**3. The live room is where the design work is worth anything.** A page is judged alone on a laptop. A slide is judged by forty people at once, on someone else's projector, while its author is talking. That is the harder case and the one nobody has made beautiful.

## What does not change

Stated first, because it is most of the system.

| | |
|---|---|
| The scene tree | Unchanged. Same 11 primitives, same layouts, same regions, same `jsonb` column ([../v1/scene-schema.md](../v1/scene-schema.md)) |
| Rule 7 | Unchanged and now load-bearing in a second way. The AI writes content and intent; a deck's design is still resolved from tokens |
| The token layer | Unchanged in shape. Five groups, tokens only, no layout ownership ([art-direction-system.md](art-direction-system.md)) |
| The renderer's purity | Unchanged, and about to be tested properly. Rule 6 forbids a `mode` prop, and presentation mode does not get one |
| `mode: 'scroll' \| 'slides'` | Already in the schema since v1. What changes is which value is the product |

**No migration, no content rewrite, no second authoring pass.** A tree that reads as eight scenes reads as eight slides. This pivot is a change of default, frame and surrounding features — not a change of data.

## The frame

**A slide is fluid. It fills the whole screen, edge to edge, with no black bars — and it is guaranteed to work between 4:3 and 21:9.**

That is a deliberate rejection of the industry default. PowerPoint, Keynote, Google Slides and Figma Slides all use a **fixed canvas**: a 1920×1080 stage scaled as one piece, letterboxed on anything that is not 16:9. It is predictable and it is why their exports work. It also means black bars on a laptop, black bars on a hall screen, and a design that can never use the room it is actually in.

Filling the screen is the better artefact and the harder engineering. The engineering is the price of the differentiator, so it gets designed rather than hoped for.

### The failure this creates, stated concretely

Fluid type is authored today as `clamp(3.5rem, 8vw, 8rem)` and fluid padding as `clamp(6rem, 14vw, 12rem)`. Both grow with **width**. A presentation screen varies in width *and* height, and the two vary in opposite directions:

| Screen | Where it comes from | `8vw` hero | `14vw` padding ×2 | Height available | Result |
|---|---|---|---|---|---|
| 4:3 · 1440×1080 | old conference projectors | 115px | 403px | 1080px | fits, under-filled |
| 16:10 · 1680×1050 | most laptops | 134px | 470px | 1050px | fits |
| 16:9 · 1920×1080 | projectors, TVs | 154px | 538px | 1080px | tight |
| 21:9 · 1920×823 | hall LED walls, ultrawides | 154px | 538px | 823px | **overflows** |

The wide-and-short case is the dangerous one: width-driven units grow at exactly the moment vertical room disappears. A two-line headline at 21:9 does not fit, and the author cannot know that from their laptop. **That is the failure mode where the product embarrasses someone in public, which is the one thing a presentation tool may never do.**

### The fix is a unit change, not a branch

Fluid values stop being driven by viewport width and start being driven by the **smaller axis of the stage**.

```
scenePaddingY   clamp(6rem, 14vw, 12rem)     →  clamp(6rem, 14cqmin, 12rem)
hero size       clamp(3.5rem, 8vw, 8rem)     →  clamp(3.5rem, 8cqmin, 8rem)
```

At 21:9 that turns a 538px padding block into 115px and a 154px hero into 66px — the slide breathes instead of bursting. At 4:3 the numbers are unchanged, because there width *is* the smaller axis.

**Container units rather than `vmin`, and the reason is rule 6.** The renderer runs in four surfaces: the editor canvas, the published deck, the `render` service, and the presenter's next-slide preview. In three of those the stage is *not* the viewport, so a viewport unit is silently wrong in them. A slide stage declaring `container-type: size` makes every fluid token resolve against the frame it is actually inside, everywhere, with no process check and no `mode` prop.

This is a **token change plus one CSS property** — `Unit` gains `cqmin`/`cqw`/`cqh`/`cqmax`, the stage declares containment, and every art direction re-authors its `preferred` values. It adds no branch to any component, which is the test [../v1/art-direction.md](../v1/art-direction.md) established and the one that still applies.

### The guarantee, and who checks it

> **Every slide in a published deck is checked at 4:3, 16:10, 16:9 and 21:9 before anyone presents it. A slide that overflows at any of the four is flagged, never silently clipped.**

The check reuses `OverflowReport` from [plan/13-scene-fit.md](plan/13-scene-fit.md) and the `render` service from [plan/00-foundations.md](plan/00-foundations.md), run four times with a different viewport. **No new overflow concept, no second report type** — same rule the reskin and scene-fit designs already agreed on. If four aspect ratios appear to need their own mechanism, one of the three designs is wrong.

Full detail: [plan/18-presentation-frame.md](plan/18-presentation-frame.md).

## Playback

One scene is one slide. No auto-splitting — a machine-chosen break lands somewhere narratively stupid and the user pays for it in the room.

| | Scroll (handout) | **Presentation (default)** |
|---|---|---|
| Advance | scroll | arrow keys, click, clicker, phone |
| Motion trigger | 25% in viewport | on advance |
| Durations | full | ~30% shorter — an advance is a beat, not a journey |
| Parallax | on | off entirely |
| Scene padding | the art direction's | collapsed to the stage |
| Frame | `fit` table, floored at `100svh` | every slide is the stage, unconditionally |
| Overflow | grows and is reported | **is a defect** and is reported |

The first three come from `slidesVariant` on the motion vocabulary, authored in phase 02. **Playback is a lookup, not a code path.** The moment a component asks `if (mode === 'slides')` to choose a duration, that field has been bypassed.

The one genuine difference is that overflow changes meaning. In a scrolling handout a tall scene grows, which is ugly but survivable. On a slide there is nowhere to grow, so overflow is a bug to fix before presenting — same measurement, different consequence.

## The live room

Four things, all chosen because the room demands them and none of them optional now that the room is the design target.

**Speaker notes, drafted by the AI.** `Scene.notes` has existed since v1 and has never been written to. The AI already knows what a slide is trying to do, so drafting *what to say out loud* is nearly free and is something PowerPoint has never done. It is content, not styling, so rule 7 is untouched — but [../v1/spec.md](../v1/spec.md) Risk 2 applies twice over, because a presenter reads notes aloud in a real meeting. Notes are grounded in the Brief, budgeted, and reviewable at the outline gate like everything else the AI asserts.

**Presenter view.** Notes, a timer, and the next slide on the laptop; the slide alone on the projector. Built as a second window synced over `BroadcastChannel`, with the Window Management API as progressive enhancement that places it on the right screen automatically. The enhancement is Chromium-only; the base mechanism works everywhere, so nobody is stranded.

**Offline.** A one-file download — a self-contained HTML document with fonts, images and textures inlined. Double-click, present, no wifi, no login, no install. This is the direct answer to Gamma's flat inability to work offline, and it is a genuinely small piece of work because the renderer is already pure and the published page already makes zero requests.

**A clicker and a timer.** Presenter remotes send arrow keys, so the clicker is nearly free. The timer is real work and belongs in presenter view.

Phone remote is wanted and is built last, because it is the only one of the five that needs a live server channel — and it is therefore **the one feature that cannot work in the offline case**. That contradiction is stated in the product, not discovered on stage.

Detail: [plan/19-presenter-view.md](plan/19-presenter-view.md), [plan/20-offline-and-export.md](plan/20-offline-and-export.md), [plan/23-phone-remote.md](plan/23-phone-remote.md).

## Getting it out of the product

**PDF now. PowerPoint later, on evidence.**

PDF is exact and nearly free once a stage exists — it is the stage printed at a chosen ratio, and 16:9 is already one of the four ratios the preflight guarantees. It answers *"send me the deck"*, *"legal needs a copy"* and *"the venue laptop has no internet"* without any of them becoming a design compromise.

Editable `.pptx` is deliberately **not** built yet, and the reason is the research, not laziness. Every AI slide tool that ships lossy export is judged on the export: web fonts substitute, textures flatten, motion vanishes. Shipping a `.pptx` that looks worse than the thing it came from damages the product more than not shipping one. The honest answer for now is a link that presents, a PDF that prints, and a file that works offline — and if paying users still ask for editable PowerPoint, it is a v3 phase with native OOXML generation rather than a converter.

## The handout

Scroll mode survives as a secondary view, not as a product. A shared link opens as a deck; a reader who wants to skim it as a document can. It already works, so it costs nothing to keep — but it is not designed for, not sold, and never the default.

## Deck length is the user's

Intake asks how long the talk is and roughly how many slides. The Director plans to that number, and the outline gate lets the user add and delete slides before a single one is built. This is a small change with a large effect: *"make me a deck"* has no correct length, and **"I have five minutes"** does. Detail: [plan/22-deck-length.md](plan/22-deck-length.md).

## The art direction stops coming off a shelf

The repetition problem is the reason this document was written at all, and the frame change does not solve it. Three hand-authored art directions on a fixed set of six layouts produce decks that rhyme, and at scale they collide — publicly, on customers' branded material, which is worse for a pitch deck than for a slide deck because two competitors pitching the same investor is a real Tuesday.

So the engine moves forward out of v3:

> **Input a brand, a site, or a reference. Get three complete art directions generated for this deck. Pick one. Nothing comes off a shelf.**

`cinematic-dark`, `editorial-light` and `bold-brutalist` stop being the user's choices and become the engine's exemplars — the three points that prove the format has range, which is exactly what they were built for. The constraint from [art-direction-engine.md](art-direction-engine.md) carries unchanged: **abstract qualities only, never fonts, exact colours or layouts.** A tool that clones a reference is a plagiarism machine with your name on it.

This is also the release where a token value becomes untrusted input, so the linter stops being a quality tool and becomes the injection boundary ([../security/content-and-web.md](../security/content-and-web.md)). Detail: [plan/21-art-direction-engine.md](plan/21-art-direction-engine.md).

## Risks this pivot creates

**1. Fluid is a promise the preflight has to keep.** The whole differentiator against a fixed canvas is *no black bars*, and it is worth nothing if a slide can break at a ratio the author never opened. If the four-ratio check turns out to be too weak in practice, the correct retreat is a fixed 16:9 canvas — and it is a retreat, so it should be taken deliberately rather than by accumulation, which is how the page framing arrived in the first place.

**2. The wedge moved and the research did not.** [../v1/market.md](../v1/market.md) is grounded in marketers doing product launches. The user is now a founder or salesperson pitching live. Gamma and Tome remain the right lessons, but the comparison set is no longer Framer and Vev — it is Pitch, Canva, Beautiful.ai and PowerPoint itself, and that research has not been done.

**3. Five live-room features is a lot of surface for a release that also generates art directions.** Presenter view, offline, timer, phone remote and export are each small; together they are a product's worth of edges, and every one of them fails in public. The build order puts them after the frame for that reason, and phone remote last because it is the only one that cannot work offline.

**4. The variety promise was counted on 2026-08-10 and the plan did not keep it.** *"Better composition may matter more than a generated palette"* was the original wording of this risk, and the measurement turned it from a suspicion into a finding: **6 font families, 6 layouts, 6 texture kinds**, and half of every art direction identical across all three. The engine was aimed at colour — the axis a viewer attributes to the brand anyway — while typography and layout, which carry the identity, were the smallest axes in the system. Compounding it, LLMs mode-collapse on exactly this task, so asking a model for three distant art directions returns three variations of one idea. The measurement, the evidence and the four fixes are in [variety.md](variety.md); [plan/24-font-registry.md](plan/24-font-registry.md) is the largest of them and [plan/21-art-direction-engine.md](plan/21-art-direction-engine.md)'s sampler is the one that matters most.

**5. Component and UI libraries are refused, and the refusal will be re-proposed.** It was proposed on the day of the pivot as a way to buy creative range, and it is the disease presented as the cure — every SaaS site looks alike *because* of shared component libraries, and a library component carries styling the art direction cannot reach, which ends reskin. Written down with reasons and with two real carve-outs in [variety.md](variety.md) → "What is *not* the fix", so the next person to propose it argues with a document rather than a memory.
