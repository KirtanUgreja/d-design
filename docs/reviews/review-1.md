# Review 1 — the deck prompt

> The prompt that generates the 8-slide project review deck, dated 5 August 2026. Paste it into [Claude Design](https://www.anthropic.com/news/claude-design-anthropic-labs) as a single message.

**What this is.** A status review at the end of phase 04: what d-design is, why it exists, what has shipped, and the full timeline through v3. The content is fixed — the prompt exists so the deck can be regenerated identically, or regenerated after the content changes, without re-deriving the art direction and the chart arithmetic every time.

**Three things the prompt does deliberately:**

1. **Front-loads everything.** Editing a slide in Claude Design regenerates it, so every slide is specified before the first render rather than corrected after.
2. **Suppresses the default look.** Gradients, italic emphasis, centred everything, one template applied eight times. Named explicitly, because they are the defaults.
3. **Gives the Gantt as measured proportions, not dates.** Bar geometry is arithmetic, not judgement — see below.

**The acceptance test is the thesis.** This deck argues that separating content from styling is what makes design good. If it comes out looking generated, it refutes its own argument. That single line does more work than any amount of styling instruction, and it is the same bet as rule 7 in [../../AGENTS.md](../../AGENTS.md).

## Assumptions worth checking before you paste

| | |
|---|---|
| Audience | Inferred from the content as a status review. Change the line if it is an investor pitch — it changes the tone throughout |
| Presenter | Left as `[Presenter name]`, an editable placeholder on slide 1 |
| Slide 5 | The header says phases 00–04 (five) while four items are named. The prompt renders the header verbatim and forbids inventing a fifth — do not "fix" this by numbering the items |
| Images | None. The deck is typographic and diagrammatic; no generation, no stock, no icons |

## The chart arithmetic

Slide 7's axis runs 5 August → 25 September 2026: **52 days**, five contiguous bars, no gaps. Day offsets from 5 August as day 1:

| Row | Range | Days | Offsets | Start | Width |
|---|---|---|---|---|---|
| 1 | Aug 5 – Aug 12 | 8 | 1–8 | 0.0% | 15.4% |
| 2 | Aug 13 – Aug 20 | 8 | 9–16 | 15.4% | 15.4% |
| 3 | Aug 21 – Aug 26 | 6 | 17–22 | 30.8% | 11.5% |
| 4 | Aug 27 – Sep 10 | 15 | 23–37 | 42.3% | 28.8% |
| 5 | Sep 11 – Sep 25 | 15 | 38–52 | 71.2% | 28.8% |

The 1 September boundary falls at 51.9%. If the content dates change, recompute these — a Gantt chart that is not to scale is the one failure a viewer notices immediately.

## The prompt

```
Build an 8-slide presentation deck, 16:9, in the canvas. Export target is PDF, so it
must survive export cleanly.

Project: d-design. Audience: people reviewing the project's status and near-term plan.
Goal: they leave believing the core bet is right and the timeline is real.
Tone: confident, plain, technically literate. No hype adjectives.

Everything needed is below. Do not research, do not add facts, figures, logos, or
slides, and do not ask me clarifying questions — the outline is final. Produce all
8 slides in one pass.

RULES
1. Every line under "Copy" is verbatim. Reproduce it word for word. You may break a
   paragraph into lines or pull a sentence out for emphasis; you may not rewrite,
   summarize, or extend it.
2. Lines under "Layout" are instructions to you. Never render them on a slide.
3. Exactly 8 slides, in this order. Nothing invented anywhere.

ART DIRECTION
This deck argues that separating content from styling is what makes design good. If
the deck looks like a generated template, it refutes its own argument. That is the
acceptance test.

- Use my design system if one is set up. Otherwise pick one point of view and hold it
  across all 8: one neutral ground, one accent, two or three grays, and a type scale
  with real jumps between sizes — not three sizes of nearly the same thing.
- Generous negative space. Big type for the one idea on the slide, small type for support.
- Layouts differ slide to slide. Do not apply one template eight times.
- Typographic and diagrammatic only. No photos, no generated images, no stock
  illustration, no decorative icons, no emoji.
- Specifically avoid the default AI-deck look: no purple-to-blue gradients, no gradient
  text, no glassmorphism cards, no drop shadows on type, no italics for emphasis, no
  centering every element, no pill badge on every heading.
- Flat color, real text, standard type. Nothing smaller than ~16px at 1280x720.
  Contrast 4.5:1 minimum. Never carry meaning by color alone.
- Nothing overflows or clips. Copy is fixed, so a crowded slide gets a two-column or
  stacked structure — never a shrunken margin.

---
SLIDE 1 — Title
Copy:
  d-design
  An AI presentation-experience engine — the AI writes content and intent, never style.
  Presenter: [Presenter name]
  Date: August 5, 2026
Layout: quiet, mostly empty. Project name largest; the tagline one step down and doing
the real work. Presenter and date small, on one line, separated from the title by a rule.
Leave "[Presenter name]" as a visible, obviously editable placeholder.

---
SLIDE 2 — Description
Copy:
  d-design generates presentation-style "experiences" from a prompt. A model emits
  structured content plus intent (what to say, how to emphasize it, pacing) into a fixed
  scene schema. A separate art-direction token layer — type, spacing, color, easing,
  duration — resolves that intent into the actual visual output. The AI never touches a
  pixel value directly.
Layout: prose, not bullets. One column at a comfortable measure (~65 characters), left
aligned. Pull the final sentence out at larger size as the slide's kicker.

---
SLIDE 3 — Problem statement
Copy:
  Today you get two bad options for AI-made presentations: hand-build slides yourself
  (slow, no AI leverage), or use an AI slide generator that lets the model pick
  colors/fonts/layout directly — which produces generic, inconsistent, often off-brand
  decks, because the model is doing content and design at once and design is not its job.
Layout: two-column contrast, one column per bad option, with the shared root cause
("the model is doing content and design at once and design is not its job") set beneath,
spanning both. Column headings must reuse the copy's own words — invent no new labels.

---
SLIDE 4 — Probable solution
Copy:
  Split the two jobs structurally. The AI only ever emits content + intent into a schema
  that has no field for a hex code, font, or duration. A separate, versioned
  art-direction layer is the only thing that turns intent into pixels. Result: editing
  content can never break the design system, reskinning the whole product is a token
  swap, and output stays consistent because the model literally cannot produce an
  inconsistent style.
Layout: the one slide that earns a diagram. Show the pipeline — content + intent →
schema (no hex, font, or duration) → art-direction layer → pixels — using only words
from the copy above. Boxes, rules and arrows drawn with type and one accent color; no
icons. Set the three results as a short list beneath the diagram.

---
SLIDE 5 — Completed so far
Copy:
  Completed so far (phases 00–04 of 12, all done)
  Foundations — repo, tooling, CI gate
  Scene schema — the structured tree the AI outputs into (Pydantic-owned, Zod-generated
  on the frontend)
  Art direction — a hand-designed reference comp, then the code token layer that
  encodes it
  Renderer + 11 primitives — the actual rendering engine, judged against the
  hand-designed comp
  This cleared "the one hard gate" of the whole project: the renderer had to look
  genuinely good, on its own judgment, before anything else could proceed. It cleared.
Layout: the four named items as a completed checklist. The final paragraph is not a
fifth item — set it apart below as a callout at heading weight. A quiet progress
indicator for the 12 phases is welcome; label it exactly "phases 00–04 of 12" and do
not number the four items or imply one maps to each phase.

---
SLIDE 6 — Next month's plan
Copy:
  Phase 05 — Publish, present, embed (in progress now). Three wrappers around the same
  renderer, no new drawing:
  Publish a scene tree to a static, shareable URL
  Present it fullscreen with keyboard navigation
  Embed it in someone else's HTML page
  This is the last phase before any AI enters the pipeline — everything up to here is
  proven with hand-written content only.
Layout: the three wrappers as three equal items reading left to right, framed by the
"same renderer, no new drawing" line above and the last sentence below as the punchline.
If it helps, echo slide 4's visual language: one core, three surfaces.

---
SLIDE 7 — Full project timeline
Layout: one Gantt chart, full-bleed, five rows, minimal chrome. Left gutter carries the
date range; each row's text sits with its bar. Bars are contiguous with no gaps.
Differentiate the v2 and v3 rows from the first three by tint or weight within the same
hue — do not introduce new colors.

Axis: August 5, 2026 to September 25, 2026. 52 days total, one continuous scale, weekly
tick labels. The September 1 boundary falls at 51.9%.

The bars must be to scale. Use these measured values exactly:

  Row  Range              Days  Start   Width
  1    Aug 5 – Aug 12     8     0.0%    15.4%
  2    Aug 13 – Aug 20    8     15.4%   15.4%
  3    Aug 21 – Aug 26    6     30.8%   11.5%
  4    Aug 27 – Sep 10    15    42.3%   28.8%
  5    Sep 11 – Sep 25    15    71.2%   28.8%

If you build it on a CSS grid, 52 equal columns = 1 day each; the rows span columns
1–8, 9–16, 17–22, 23–37, 38–52.

Copy (row text, in order, verbatim):
  Aug 5 – Aug 12, 2026: Publishing, presenting, and embedding a scene ships; AI starts
  generating scenes for the first time.
  Aug 13 – Aug 20, 2026: The full human-in-the-loop authoring flow is built: reviewing
  the AI's outline, the first-prompt intake, and editing generated scenes.
  Aug 21 – Aug 26, 2026: Brand kits, uploads, and the remaining visuals land; everything
  is verified end-to-end. v1 ships.
  Aug 27 – Sep 10, 2026: v2 — adds a second art direction (a different visual style on
  the same content), and document/URL import so a brief can be built from an existing
  file or link instead of just a prompt.
  Sep 11 – Sep 25, 2026: v3 — adds derived and personalized experiences, live/real-time
  updates, and multilingual output, running on production infrastructure.
  From here, we continue with ongoing improvements as needed.

The last line is a caption beneath the chart. It is not a sixth bar.

---
SLIDE 8 — Closing
Copy:
  "You would show it to someone." — the project's own definition of done.
  Thank you / questions.
Layout: the quote at the deck's largest size, its attribution clause small beneath it,
"Thank you / questions." smaller still at the bottom. Nothing else on the slide.

---
DONE MEANS
- Exactly 8 slides, in order, every word of Copy present verbatim, nothing added.
- Nothing overflows or clips at 16:9 — check slides 2, 5 and 7 hardest.
- Slide 7's bars measure against the percentage table.
- No two slides share the same layout skeleton.
- Legible from three meters, and it exports to PDF without reflowing.
```

## Follow-ups

Keep these ready rather than improvising — each edit regenerates a whole slide, so a vague correction costs a full re-render.

- `Slide 7: re-measure the bars against the percentage table — [row] is off.`
- `Slide 4: the diagram is doing too much. Cut it to four labeled steps and one arrow style.`
- `Tighten the type scale — the gap between heading and body is too small to read as hierarchy.`

## Connects to

| | |
|---|---|
| [../v1/plan/README.md](../v1/plan/README.md) | The phase status the deck reports on |
| [../v1/plan/05-publish-present-embed.md](../v1/plan/05-publish-present-embed.md) | Slide 6 in full — what phase 05 actually builds |
| [../v1/spec.md](../v1/spec.md) | Slides 3 and 4 in full — the problem and the bet |
| [../design/principles.md](../design/principles.md) | Why our own artifacts are held to the standard slide 8 quotes |
