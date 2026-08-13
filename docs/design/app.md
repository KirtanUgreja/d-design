# The app

> The only UI that exists in v1. Three surfaces get the craft budget; everything else is furniture ([principles.md](principles.md), principle 3).

---

## The budget, stated as a rule

[../coderules/performance.md](../coderules/performance.md) has a cold-90% rule for code, and [../techstack/frontend.md](../techstack/frontend.md) applies it to the property panel, outline editor, brand kit and settings: *assemble them, do not craft them.* This document applies the same rule to design attention.

| Hot — craft it | Cold — assemble it |
|---|---|
| Intake / interview, the first prompt | Settings, account |
| The generation watch | Asset list |
| The export reveal | Property panel *chrome* (its contents are generated) |
| — plus the outline gate, which is hot for trust rather than for delight | Brand kit form |

Four screens. If a week goes into a settings page while the generation watch is a spinner, the budget was spent backwards.

---

## 1. Intake

**Prompt box first, then a short structured interview. Not a chat.**

Chat bubbles set expectations this product will not meet — conversational memory, open-ended back-and-forth, off-task requests — and a chat log is not an interview. The interview asks three to five questions with visible progress, and **skipping straight to generate is always available**. The interview improves the output; it must never gate it.

```
┌────────────────────────────────────────┐
│  What are you launching?                │
│  [                                  ▸ ] │
│                                         │
│  ── or start from ──                    │
│  · a product launch  · a pricing change │
│  · a funding announcement               │
└────────────────────────────────────────┘
```

Every example is a real launch brief. Generic examples recruit the wrong cohort ([principles.md](principles.md), principle 2).

**The interview stays visible and editable, permanently.** It is the approved-claims record, and Risk 2 in `v1/spec.md` is that marketers cannot ship copy the AI invented. Which claims came from them and which the model produced is shown — and that provenance display is the trust feature this product has and its competitors do not.

**v1 accepts the interview answers (typed text) and a typed brand kit.** Nothing is fetched: a URL the user types is a string used as a CTA destination, never a request. File import (brand-kit upload) is deferred to v3 — **do not build the upload affordance now**, because an upload button that explains why it is disabled is worse than no button.

No templates and no starting-point gallery. "No templates" is the positioning; a template picker contradicts the homepage.

---

## 2. The outline gate

The human approval step (`v1/plan/02-interview.md`). Nobody else in this category has one, so there is no convention to copy — and it is simultaneously the cost control, the quality control, and the trust device.

- **Slide cards with intent label and headline.** Not a bulleted list. It should already feel spatial, because the next screen is spatial
- **Reorder by drag.** Intent decouples from position, so moving a section does not make the content a lie
- **Edit copy here.** Fixing a headline before the build is far cheaper than after it
- **Regenerate the outline** is cheap and prominent. That is the entire reason the gate exists before the expensive call
- **Approve is the primary action**, and it is the only high-emphasis control on the screen
- **Claim provenance is shown here**, not in the editor. This is the correct gate for Risk 2
- Time as a range. Never a percentage
- **No skip, in v1.** If the gate turns out to be theatre — approval rates near 100% — that is a finding about the interview, not a reason to remove the gate

---

## 3. The generation watch

Forty seconds, and it is what someone describes to a colleague afterwards. The highest-leverage motion design in the product.

**The slides themselves, full size, appearing in place as they arrive.** The SSE stream already delivers whole validated slides ([../techstack/frontend.md](../techstack/frontend.md)) — a slide is generated, Zod-parsed, and emitted as one event, so there is nothing partial to hide behind a progress bar. Anything that failed validation never reaches the client at all.

| | |
|---|---|
| **The outline is visible ahead, ghosted** | Watching known slots fill is dramatically better than watching an unknown list grow |
| **Each slide arrives with the deck's own design-family motion** | Not chrome animation. The reveal you watch is the reveal your audience gets — which is the same what-you-edit-is-what-you-ship guarantee, seen a step earlier |
| **A slide with an image arrives with its image** | The generated image is part of the slide, embedded at export. Watching a hero appear with the slide is the moment that slide lands |
| **The first slide is the most important frame in the product** | Budget time for it specifically |
| **Repairs are silent** | The `repair` event is instrumentation. Showing a user a self-correction is honesty nobody asked for, and it undermines the one moment the product has |
| **Abort is prominent** | Killing a bad direction early is the stated reason streaming exists |
| **Failure at slide 6 of 8 keeps the five** | Never discard completed work. Offer to continue |
| **No fake steps** | "Writing headline…" invented progress is the most common slop pattern in AI UI. Real phase labels only |
| **Leaving the page is fine** | Generation is server-side; it resumes |
| **No sound. Reduced motion respected** | Including here, which is the hardest place to get it right |

---

## 4. The export reveal

The third hot surface, and the one that gets screenshotted into Slack.

The **download** — one self-contained `.html` file — large and prominent, with the deck preview behind it. One click to download, one to present fullscreen with arrow keys, one to copy the file for sending — the thing that keeps the word "presentation" honest. The offline single-file artefact (`v1/spec.md`) is the product; the hosted URL is a v3 layer.

**Exporting is explicit.** A new generation is a new file; nothing changes a downloaded deck after the fact. The review loop (v1) is where a user sends a slide back before download.

**From v3 the hosted deck carries a provenance line** — the "made with" badge and the legally required AI-content disclosure, designed as one mark rather than two ([website.md](website.md), `v3/spec.md`). Worth knowing here because it is the one piece of our design that appears inside someone else's artifact, and it is the only place our chrome and a design family are allowed to meet.

---

## The editor (v2)

Quiet, because it surrounds the thing that is supposed to be the most beautiful object on the screen ([principles.md](principles.md), principle 4). v1 has no editor — the flow is interview → outline gate → generation watch → review → export. The editor below is what v2 builds.

```
┌──────────┬────────────────────────┬──────────────┐
│ outline  │                        │  properties  │
│          │   canvas, true scale   │              │
│ · hook   │                        │  text  [___] │
│ · problem│   ┌──────────────┐     │  emphasis ●○○│
│ · proof  │   │ selected     │     │              │
│ · cta    │   └──────────────┘     │              │
│          │   [ ask for a change ] │              │
└──────────┴────────────────────────┴──────────────┘
```

| | |
|---|---|
| **True scale, always** | What you edit is byte-for-byte what you publish. Any scaling weakens the guarantee the whole product rests on. Fit-width and 100%, nothing else |
| **Selection is a hairline and a label** | Not a saturated blue box over a designed page |
| **The element-scoped prompt lives inline, under the selection, always in the same place** | It is a primary interaction, not a panel tab. It appears only with a selection — an always-present prompt box invites page-level requests the patch shape cannot serve (`docs/v2/plan/12-editor.md`) |
| **Undo is visible and labelled** | Not just a shortcut. It is what makes AI editing safe to *try*, and experimentation is where this product is fun |
| **The outline panel is the slide navigator** | Do not build two |
| **Export is top right and is the only high-emphasis control** | The downloadable single-file HTML is the primary action (`docs/v1/plan/05-export.md`) |
| **Brand kit is one click from the canvas** | It is a v1 primitive, not a setting |
| **Reserve the design-family switcher's space now** | v2 fills it. Retrofitting it into a menu is how it becomes a setting instead of a feature |
| **Mobile is view and present only** | Editing a design surface on a phone is a different product |
| **Selection never enters the renderer core** | Rule 6. The overlay wraps the renderer; a lint rule proves it (`docs/v1/plan/06-renderer.md`) |

The property panel is **generated from the schema** (`docs/v2/plan/12-editor.md`), which is why the next section exists.

---

## The colour picker that does not exist

The most important interaction design problem in the product.

Users will look for a font size and a colour picker. They will not find them, and they **cannot** — the panel is generated from a schema with no presentational fields, so the control is not hidden, it is unrepresentable. That is the product's spine. It is also the moment a first-time user decides whether this is a tool or a toy.

**Undesigned, it is a bug report. Designed, it is the pitch: you cannot make this ugly.**

### The rule

Answer **at the moment of reaching**, in the place where the control was expected. Inline, once, positive. Not a docs page, not a tooltip, not an onboarding tour — by the time someone opens documentation to ask why they cannot change a colour, the session is already lost.

Copy in the shape of: *"Type, colour and spacing come from the design family, so this cannot go off-brand. Change the family, not the pixel."* The exact words need a human voice; the shape is the requirement.

### What replaces it, visibly

Four affordances, and they must look **more** powerful than the thing they replace, because they are:

| Instead of | You get |
|---|---|
| A colour picker | The design family — the whole look, coherently (v2 makes this a switch) |
| A font-size field | **Emphasis** — intent, in the schema, resolved by the tokens |
| A brand hex | The brand kit, mapped into semantic roles with contrast enforced and the correction shown (`v3/plan/17-brand-kit-at-scale.md`) |
| Nudging a gradient | Reroll — a button, not a number field |

**Teach "emphasis" as the replacement vocabulary.** It is the concept that makes the constraint learnable rather than merely enforced.

### The refusal is a designed artifact

Someone will type *"make the headline smaller"* into the element prompt. The Edit call has no field for it, so the model must **refuse well** and offer emphasis instead. That refusal copy is a design deliverable with a named owner, not an error string someone writes at 2am.

### Two concessions

- **Resolved tokens are visible, read-only.** Seeing the system is disarming; editing it is the product's collapse
- **The artefact is the single-file HTML, and it is not hand-editable.** The file is generated, not authored. Hand-editing the HTML is how the design family stops being the single source of visual truth

No CSS or HTML *authoring* in the editor. That is the fastest route to becoming a worse Webflow. The download is the point, not the canvas.

### Instrument it

Track every time a user hunts for a styling control. It is the best single signal in the product and among the cheapest to instrument ([questions.md](questions.md), #273).

---

## First run

Research floor: median self-serve time-to-value is ~11 minutes, top performers under 5, and hitting first value inside 14 days is the strongest retention predictor there is. **Ours should be under 90 seconds**, because we know what they are launching before they arrive.

| | |
|---|---|
| **Second zero** | Their waitlist answer — *what are you launching, and when?* — already in the prompt box, cursor at the end. Not an empty state, not a tour |
| **No product tour** | A tour is what you build when the first screen failed |
| **Brand kit comes second, not first** | Wow first. Six brand fields before anything happens is how the session is lost. Ask immediately *after* the first artifact exists, framed as *make this yours* |
| **Assets are asked for in place** | When a slide visibly wants one. Never as a setup step |
| **The aha is their own words in a designed deck they did not lay out** | Not the file. The download comes later and it is the *activation* metric, not the aha |
| **Nothing about quota or cost in the first session** | Not until they have succeeded once |
| **A bad first generation gets one obvious control** | *Try a different direction.* One click, obviously free |
| **One sample artifact in the account** | Real, openable, breakable. It teaches the editor with nothing at stake |
| **Second session opens their work**, not a dashboard | A list of one artifact is not a dashboard |
| **The first artifact is emailed to them** | Their proof, and the best re-engagement asset we will ever have |

---

## The states nobody designs

Twelve screens everybody sees. Rule 10 in [../../AGENTS.md](../../AGENTS.md) governs them all — anything that grants, fails closed — and **a closed failure still needs human copy**.

| State | Requirement |
|---|---|
| Quota exceeded | What ran out, when it resets, what still works. Never a raw 429 |
| Model refused | Plain language, no apology theatre, one actionable next step |
| Generation failed | Outline and interview survive. Retrying must not mean re-typing |
| Upload rejected | Each of the six controls gets its own sentence (`v3/plan/17-brand-kit-at-scale.md`). "Invalid file" is not one |
| Patch rejected | Previous deck intact, and say which rule (`v2/plan/12-editor.md`) |
| Kill switch active | Honest maintenance state on the generation path only. Editing and publishing keep working |
| Offline | Editor holds state and says so. It must not silently lose a patch. The *deck itself* is offline by design — the editor is not |
| Session expired mid-edit | Preserve the tree, re-auth in place |
| 404 on a removed artifact | A designed page — a customer's audience will hit it |
| Rate limited | Same shape as quota. Never silent |
| Empty artifact list | One sentence and the prompt box. Not an illustration of an empty box |
| Internal errors | Never displayed. Logged ([../security/operations.md](../security/operations.md)) |

---

## Accessibility

AA, non-negotiable for a product whose output is public web pages we are about to lecture other people about.

- Keyboard-complete. Radix supplies most of it ([../techstack/frontend.md](../techstack/frontend.md)) and [../coderules/README.md](../coderules/README.md) says never to simplify it away
- Visible focus everywhere — one of the accent colour's two jobs ([brand.md](brand.md))
- The editor works at 200% zoom: panels collapse, the canvas stays true-scale
- CSS logical properties in our chrome too. Free now, and it makes a future RTL UI a `dir` attribute
- `prefers-reduced-motion` respected, including in the generation watch
- **Open question worth real research:** what a screen reader announces on the canvas. Default position is that the canvas is a document announced structurally, with selection as an application region ([questions.md](questions.md), #244)

Artifact accessibility is not this document's problem — it belongs to the design family registry and the renderer (`docs/v1/plan/06-renderer.md`), and duplicating the rules here would create a second source of truth.

---

## Connects to

| | |
|---|---|
| [principles.md](principles.md) | Why these four surfaces and not the other twenty |
| [brand.md](brand.md) | The palette the chrome is built from, and the check against the canvas |
| [website.md](website.md) | What happened before "Start" |
| `v1/plan/README.md` | The build phases these screens land in |
| [../coderules/patterns.md](../coderules/patterns.md) | Rule 2 — the renderer stays pure and mode-free |
