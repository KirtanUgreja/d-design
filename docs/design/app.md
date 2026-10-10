# The app

> The product UI. Five surfaces get the craft budget; everything else is furniture ([principles.md](principles.md), principle 3). **Rewritten 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)):
> - The model now composes every slide in HTML.
> - **Every deck gets its own generated look; the user never picks a style** (owner, 2026-10-05).
> - The app is a UI over a Python backend that owns the engine, the data and the export.
>
> The create flow is built in ../v4/plan/27-app-create-flow.md; the editor, present and export in ../v4/plan/28-editor.md.

---

## The flow

```
composer ─► interview + outline gate ─► generation watch ─► editor ─► present / export
 (brief)     (≤5 questions, approve)     (slides stream)     (edit)    (the file itself)
```

Every step before the watch is cheap and reversible. The watch is where the money goes: roughly $1.5–3.5 per 10-slide deck ([../v4/spec.md](../v4/spec.md) → Bets). The gates sit where they do so that a bad direction dies before it costs anything.

---

## The budget, stated as a rule

[../coderules/performance.md](../coderules/performance.md) has a cold-90% rule for code, and [../techstack/frontend.md](../techstack/frontend.md) applies it to the app's cold surfaces: *assemble them, do not craft them.* This document applies the same rule to design attention.

| Hot — craft it | Cold — assemble it |
|---|---|
| The composer — the first prompt | Settings and account (phase 29) |
| The interview + outline gate — hot for trust rather than delight | The brand kit form |
| The cover arriving — the first time the user sees design | The deck list beyond "Recent" |
| The generation watch | The editor's panel *chrome* — its contents are the deck |
| The export reveal and present | Version history as a list |

Five screens. If a week goes into a settings page while the generation watch is a spinner, the budget was spent backwards.

---

## 1. The composer

**A prompt box first, the interview second. Not a chat, and not a form.**

> **2026-10-10 (owner):** the prompt is set at 17px in the interface face. Competitors measured that day: Gamma 12.8px, Pitch 16px, presentations.ai 16px; 16px is the floor that stops iOS zooming on focus. The example chips only fill the box; the recorded runs of the old engine are off the home page. Under the composer, a slowly drifting wall of real slides from the owner's best-rated decks (`web/public/showcase/`), then three proofs drawn as pieces of the product.

```
┌─────────────────────────────────────────┐
│  What are you presenting?               │
│ ┌─────────────────────────────────────┐ │
│ │ Series A pitch for our CI tool…     │ │
│ │ [+ paste notes/data] 10 ▾ Investors▾│ │
│ └──────────────────────────[Start ▸]──┘ │
│  Recent  [▣] [▣] [▣] [▣]                │
└─────────────────────────────────────────┘
```

| | |
|---|---|
| **The prompt** | One sentence is enough. Every placeholder and example is a real founder or sales brief — a pitch, a sales deck, a launch, an investor update, a partnership ([../v4/spec.md](../v4/spec.md) → Locked decisions → First users). Generic examples recruit the wrong cohort (principle 2) |
| **Pasted material** | Notes, numbers, a customer quote, a metrics table. It is text, it needs no fetch, and what it states becomes `YOU`-provenance facts ([../v4/content.md](../v4/content.md) → "Research and the Fact ledger") |
| **Slide count, audience, tone** | Three compact controls on the prompt's edge, each with a default. Never a form above the prompt |
| **Recent decks** | Thumbnails of the real slides. The second session opens their work, not a dashboard |
| **A URL the user types is never fetched** | Research runs through the model gateway's search tool. Importing a URL or a PDF is Skipped until users ask (../v4/plan/24-content-engine.md) — **do not build the affordance now**, because an import button that explains why it is disabled is worse than no button |

No templates and no starting-point gallery. "No templates" is still the positioning; a template picker contradicts the homepage.

---

## 2. The interview and the outline gate

One screen, two halves: the interview on the left, and on the right the storyline it produces, updating as answers arrive.

> **2026-10-10 (owner):** the outline is the person's to change. Any slide's words can be edited in place (they become YOU, and no fact of ours stands behind them), a middle slide can be removed (five stay at least), and **Change the outline** takes an instruction in words: research runs again and the outline is rewritten, keeping what the change does not touch, with more or fewer slides if asked. The deck's name can be renamed at any point. The style card shows the style's name, idea, palette and type; its slide thumbnails are gone, because the code-built layout drew every style as the same old slide.

```
┌──────────────────┬──────────────────────────┐
│ 2 of 4           │ "Flaky CI costs dev teams │
│ What should the  │  a day a week — we fix it"│
│ investors do     │ 1 ▤ Flaky CI costs a day… │
│ afterwards?      │     YOU                   │
│ (Lead the round) │ 2 ▤ 38% of CI failures…   │
│ (Intro partners) │     WEB · 3 sources ⓘ     │
│ [answer…] [Skip] │ drag · edit · [Approve ▸] │
└──────────────────┴──────────────────────────┘
```

**The interview** ([../v4/content.md](../v4/content.md) → "Interview")

- **Adaptive, at most five questions.** One model call writes them all, with their suggested answers; they are shown one at a time with visible progress. A question the brief already answered is never asked.
- **One of them is delivery:** *are you presenting live or sending it?* A deck that is read alone carries more words per slide than one with a presenter in front of it, so the answer sets density.
- **Never brand colours.** The brand kit is asked for after the first deck exists (First run).
- **Every question carries suggested answers** as chips, so answering is a click. Typing is always allowed.
- **Skippable, always.** The interview improves the output; it must never gate it.
- **Refinable in conversation.** After the last question the user can keep talking to the storyline ("make the ask $4M", "drop the competition slide") and the cards update. It is a conversation *about this outline*, not an open chat. A request that is not about the deck gets a one-line redirect, not an answer.

**The outline gate** is the human approval step, and the cheapest place in the product to fix anything.

- **Slide cards, not a bulleted list.** Each card shows its intent and its headline. The headline is an assertion, never a topic label ([../v4/content.md](../v4/content.md) → "Content rules"). The cards should already feel spatial, because the next screen is.
- **Drag to reorder, edit inline, regenerate.** Regenerating the outline is cheap and prominent. That is the whole reason the gate sits before the expensive call.
- **Provenance on every claim:** a `YOU`, `AI` or `WEB` chip. `WEB` opens a popover with the sources: title, date, the quoted line, the link. This is the trust feature, and no competitor has it.
- **Unsourced numbers are flagged** visibly, with three actions: add a source, mark it illustrative, or cut it. A deck made for skeptics cannot carry a number nobody can defend.
- **Approve is the only primary action** on the screen.
- **Time as a range. Never a percentage.**

The interview answers and the approved outline are saved with the deck, so a failed generation never means re-typing.

---

## 3. No look to pick

**Removed 2026-10-05 by the owner.** Asking a user to choose among three looks is a smaller template gallery, the opposite of the product. The deck's look is generated for it — from its own words and tone, with a mark drawn from its title — and the first time the user sees design is **the cover arriving in the watch**. If they want something else, the editor's Design tab has *Try another look*: a new generated look, shown before/after. Never a menu of styles ([../v4/design-engine.md](../v4/design-engine.md) → "Generated, not picked").

---

## 4. The generation watch

One to three minutes, and it is what someone describes to a colleague afterwards. Still the highest-leverage motion design in the product.

> **2026-10-10 (owner: "everything is empty, it feels long"):** the wait shows the work (the labor illusion, Buell and Norton 2011). The outline wait is a list of the outline job's real steps, with what research found ("Found 9 sources: IDC, …") from a `research_done` event. The build shows a live feed of `slide_step` events (designing, redesigning after a look, repairing), a left-to-right sweep on the slides being worked on, and the time so far with an estimate once a slide is done.

**The slides themselves, at size, arriving in place.** The backend emits a slide only once it has been generated, sanitized, rendered and measured ([../v4/engine.md](../v4/engine.md) → "Generation jobs and events"). There is nothing partial to hide behind a progress bar.

| | |
|---|---|
| **The outline is visible ahead, as ghost slots** | Watching known slots fill is dramatically better than watching an unknown list grow |
| **The first slide is the most important frame in the product** | The cover is composed first and arrives first. Budget time for it specifically |
| **A slide with an image arrives with its image** | The image is part of the slide. A failed image never fails the deck: that slide arrives composed without it |
| **Repairs are silent** | A repair round is instrumentation. Showing a user a self-correction is honesty nobody asked for |
| **A slide QA could not fix arrives flagged "needs attention"** | Never silently broken, never hidden. One click opens it in the editor with the defect named in plain words ("the headline runs off the right edge") |
| **No fake steps** | Real phase labels only: "Writing the storyline", "Composing slide 4 of 10". Invented progress ("Crafting magic…") is the most common slop pattern in AI UI |
| **Abort is prominent** | Killing a bad direction early is the reason streaming exists |
| **Failure at slide 6 of 10 keeps the five** | Never discard completed work. Offer to continue from slide 6 |
| **Leaving the page is fine** | A separate worker process runs the generation, not the request. Closing the tab or reloading changes nothing: the watch reconnects and replays what it missed, with no gaps |
| **No sound. Reduced motion respected** | Including here, which is the hardest place to get it right |

---

## 5. The editor

Quiet, because it surrounds the thing that is supposed to be the most beautiful object on the screen (principle 4). The watch lands here: it is the same screen, with the rail full.

```
┌────┬────────────────────────────┬───────────┐
│ 1▣ │                            │Slide Notes│
│ 2▣ │  16:9 canvas, true scale   │ Design    │
│ 3◌ │  click any text to edit    │ Ask for a │
│ 4◌ │                            │ change…   │
│ +  │                            │ [Layout]… │
└────┴────────────────────────────┴───────────┘
  ↶ Undo · saved v12       [Present ▸] [Export ▾]
```

| | |
|---|---|
| **The filmstrip is the navigator** | Screenshots of the real, checked slides. Drag to reorder, add a slide by picking an intent (a big number, a quote, a comparison…), duplicate, delete. Do not build a second navigator |
| **The canvas is the real slide** | The same 1920×1080 slide the export contains, scaled uniformly to fit. It never reflows, so what you see is the export's composition at a different zoom |
| **Click text to edit it in place** | Every piece of copy is editable where it sits: the field nodes are `contenteditable="plaintext-only"` inside a script-less iframe, so a paste can never bring markup or styling with it. On blur the edit is saved and the slide is measured again. If the new text overflows, the canvas says so and offers **Fit to slide** (one AI repair) or undo |
| **Selection is a hairline and a label** | Not a saturated blue box over a designed page. Selection is our chrome's overlay and is never written into the slide's HTML |
| **Slide tab: ask for a change** | A free-text instruction ("make this more visual", "lead with the 38%") plus quick actions: **Regenerate · Different layout · Shorter · Add image · Turn into chart · Split**. Every AI change arrives as a **before/after** that the user accepts or discards; nothing replaces a slide silently |
| **Deck-wide instructions** | "Make the whole deck more formal", "cut it to 8 slides". The same compare-then-accept shape, slide by slide |
| **Notes tab** | Speaker notes for the selected slide, editable. Every slide has them ([../v4/content.md](../v4/content.md) → "Content rules") |
| **Design tab** | The look, visible and changeable as a whole: a **palette variant**, a **type-pairing swap** among the pairings the look allows, **re-roll the look**, and **your brand colours**. Any change re-measures every slide and auto-repairs what broke. A slide that still fails arrives flagged, exactly as in the watch |
| **Version history, labelled** | Every AI operation and every committed text edit is a version with a label ("Rewrote slide 4: make it more visual"). **One snapshot per operation, never per keystroke** (v3 snapshotted every keystroke). Undo and redo are visible and labelled, not just shortcuts; they are what make AI edits safe to *try*, and experimentation is where this product is fun |
| **Autosave** | Quiet, and honest about failures |
| **Present and Export, top right** | Export is the only high-emphasis control. Present opens the "present" export itself (§6) |
| **Mobile is view and present only** | Editing a design surface on a phone is a different product |

---

## 6. Present and export

The export reveal is the moment that gets screenshotted into Slack. It offers two flavours of one deck, and the choice is stated in human words, not format names.

| | |
|---|---|
| **Present** | Opens the **present** export itself, not a preview component. It carries the speaker notes, which the presenter popup shows beside the current and next slide. Copy in the shape of: *"For you: your notes are inside"* |
| **Download to send** | The **send** export: one self-contained `.html` file with **no speaker notes in it**, so emailing the deck never leaks them. Copy in the shape of: *"For them: the slides only"*. Large and prominent, with the deck behind it. It runs offline, anywhere, with zero network requests (../v4/plan/26-player-export.md) |
| **PDF** | A quieter third option, printed from the send export: one slide per page, no notes |
| **Slides are byte-identical in both** | Only the notes differ. What you present is what you send ([../v4/spec.md](../v4/spec.md) → Locked decisions → Presenting) |
| **Flagged slides are named before download** | A slide still marked "needs attention" is listed, with a link back to it. Never a silent broken slide in a file someone is about to send |
| **The file tells you how to present it** | Arrow keys, fullscreen, presenter view. One line on the reveal, not a manual |
| **Exporting is explicit** | A downloaded file never changes under you. A new export is a new file |

**Decks carry no links and no icons in v4.** A URL on a slide is plain text, and the file has nothing clickable that leaves it.

v4 has no hosted URL: sharing means sending the file (../v4/plan/29-accounts-deploy.md → Skipped, with its trigger). The export carries a machine-readable AI marker ([../v4/spec.md](../v4/spec.md) → Locked decisions → Export). How that marker meets a "made with" badge is covered in [website.md](website.md) → "The badge and the AI disclosure are one design problem".

---

## The colour picker that does not exist

Still the most important interaction design problem in the product.

Users will look for a colour picker and a font-size field. **There are none, in v4 as before.** The reason changed, and so did the answer.

**Why they cannot exist.** The model now composes each slide's HTML, and layout is free. Colour, typeface, size and weight are not: a slide may only use the look's tokens ([../v4/spec.md](../v4/spec.md) → Locked decisions → Token rule). A hex from a picker would be a value no look defines, so the control is not hidden; it is unrepresentable. That rule is what keeps a deck of separately composed slides one deck.

**Undesigned, it is a bug report. Designed, it is the pitch: you cannot make this ugly.**

### The rule

Answer **at the moment of reaching**, in the place where the control was expected. Inline, once, positive. Not a docs page, not a tooltip, not an onboarding tour. By the time someone opens documentation to ask why they cannot change a colour, the session is already lost.

The copy should take roughly this shape: *"Colour and type come from the look, so every slide stays one deck. Change the look, or ask this slide for more emphasis."* The exact words need a human voice; the shape is the requirement.

### What replaces it, visibly

There are two levels, and each must look **more** powerful than the control it replaces, because it is:

| Instead of | You get |
|---|---|
| A colour picker | **The look**: the Design tab's palette variants, or a re-roll. The whole palette, coherently, with contrast held |
| A font-size field | **A request to the slide**: "make the number the hero", "a quieter headline". The model recomposes within the look's type scale |
| A font menu | **A type-pairing swap** among the pairings the look allows |
| A brand hex | **The brand kit**, mapped into the look's colour roles, with contrast enforced and the correction shown |
| Nudging a box | **Different layout**: a new composition of the same content, as a before/after |

That division is the lesson to teach: **slide-level changes are requests; look-level changes are the Design tab.**

### The refusal is a designed artifact

Someone will type *"make the headline red"* into the slide's instruction box. The slide cannot hold a colour the look does not define, so the model must **refuse well** and offer the two real routes:
- a palette variant whose accent leans red, if the look has one
- more emphasis on the headline within the current palette

*"Make the headline smaller"* is not a refusal at all. It is a request the model serves inside the type scale. The refusal copy has a named owner; it is not an error string someone writes at 2am.

### Two concessions

- **The look's tokens are visible, read-only**, in the Design tab: the fonts, the colour roles, the type scale. Seeing the system is disarming; editing it value by value is the product's collapse.
- **No HTML or CSS authoring by the user, anywhere.** The model writes the slide and the user directs it. Hand-editing is how the look stops being the single source of visual truth, and it is the fastest route to becoming a worse Webflow. The exported file is generated, not authored.

### Instrument it

Track every time a user hunts for a styling control ([questions.md](questions.md), #273). It is still the best single signal in the product and among the cheapest to instrument.

---

## First run

Research floor: median self-serve time-to-value is ~11 minutes, top performers under 5, and hitting first value inside 14 days is the strongest retention predictor there is.

**Ours: the cover, in its own look, within a minute of approving the outline, and the whole deck in under three minutes** ([../v4/spec.md](../v4/spec.md) → Risks).

| | |
|---|---|
| **Second zero** | The prompt box is focused, with a real founder brief as the placeholder. Once accounts exist (phase 29), their waitlist answer (*what are you presenting, and to whom?*) is already in it |
| **No product tour** | A tour is what you build when the first screen failed |
| **Brand kit comes second, not first** | Wow first. Brand colours are asked for only after the first deck exists, as a Design-tab action framed as *make this yours*. Never in the composer, never in the interview. Six brand fields before anything happens is how the session is lost |
| **Assets are asked for in place** | Only when a slide visibly wants one, never as a setup step. Until upload arrives (phase 29, on its trigger), *Add image* generates one |
| **The aha is their own words in a designed deck they did not lay out** | It lands when the cover arrives. It is not the file. The download comes later and is the *activation* metric, not the aha |
| **Nothing about cost or limits in the first session** | Not until they have succeeded once |
| **A bad first generation gets one obvious control** | *Try a different look*: re-roll from the Design tab, or regenerate the outline. One click |
| **One sample deck in Recent** | Real, openable, breakable. It teaches the editor with nothing at stake |
| **The second session opens their work** | Not a dashboard. A list of one deck is not a dashboard |
| **The first deck is emailed to them** | Phase 29, because it needs an account. It is their proof, and the best re-engagement asset we will ever have |

---

## The states nobody designs

The fail-closed rule governs them all: anything that grants, fails closed ([../coderules/README.md](../coderules/README.md), non-negotiable 10). **A closed failure still needs human copy.** Never show a raw exception. v3 showed users *"model output invalid after 1 repairs…"*, and that is the defect this table exists to prevent.

| State | Requirement |
|---|---|
| Model refused | Plain language, no apology theatre, one actionable next step |
| Generation failed | The brief, the interview and the outline survive. Finished slides are kept. Retrying must not mean re-typing |
| Connection dropped during the watch | Nothing is lost: the worker keeps going, and the watch reconnects and catches up. Say nothing unless it stays down |
| A slide needs attention | QA could not fix it in two rounds. It is shown flagged, with the defect in plain words and two actions: *Fit to slide* or *Different layout* |
| An edit broke the slide | The text is kept and the overflow is shown on the canvas. *Fit to slide* or undo is offered, and the previous version is one click away |
| An AI change failed or was discarded | The slide is untouched. Say what happened in one sentence |
| A look change broke slides | The re-roll completes, broken slides are auto-repaired, and any that still fail arrive flagged. Undo restores the previous look in one step |
| Research found nothing citable | The outline says so on the affected claims, flagged. Never a silent invented number |
| An image failed | The slide arrives composed without it; *Add image* retries |
| Budget cap or kill switch (phase 29) | What ran out, when it resets, what still works. Editing, present and export keep working; only generation stops. Never a raw 429 |
| Rate limited (phase 29) | Same shape as the budget cap. Never silent |
| Session expired mid-edit (phase 29) | Preserve the deck and re-auth in place |
| Offline | The editor holds its state and says so; it must never silently lose an edit. The *exported deck* is offline by design; the editor is not |
| Empty deck list | One sentence and the prompt box. Not an illustration of an empty box |
| Internal errors | Never displayed. Logged ([../security/operations.md](../security/operations.md)) |

---

## Accessibility

AA, non-negotiable for a product whose output other people present to rooms.

- **Keyboard-complete.** Radix supplies most of it ([../techstack/frontend.md](../techstack/frontend.md)), and [../coderules/README.md](../coderules/README.md) says never to simplify it away. The filmstrip reorders by keyboard as well as by drag.
- **Visible focus everywhere.** It is one of the accent colour's two jobs ([brand.md](brand.md)).
- **The editor works at 200% zoom.** Panels collapse, and the canvas keeps the slide's composition: it scales, it never reflows.
- **CSS logical properties in our chrome too.** Free now, and it makes a future RTL UI a `dir` attribute.
- **`prefers-reduced-motion` respected**, including in the generation watch.
- **Open question worth real research:** what a screen reader announces on the canvas. The default position: the slide is a document announced structurally, with selection as an application region ([questions.md](questions.md), #244).

Artefact accessibility is not this document's problem. The engine measures contrast and minimum type size on every slide before a user sees it ([../v4/design-engine.md](../v4/design-engine.md) → "QA metrics"), and duplicating those rules here would create a second source of truth.

---

## Connects to

| | |
|---|---|
| [principles.md](principles.md) | Why these five surfaces and not the other twenty |
| [../v4/ui-research.md](../v4/ui-research.md) | The evidence behind the attention, motivation and trust choices, and the ethics line; phases 30–35 |
| [brand.md](brand.md) | The palette the chrome is built from, and the check against the canvas |
| [website.md](website.md) | What happened before "Start" |
| ../v4/plan/27-app-create-flow.md | Where the composer, the interview + outline gate and the watch are built |
| ../v4/plan/28-editor.md | Where the editor, present and the export dialog are built |
| ../v4/plan/26-player-export.md | The two export flavours and the presenter view |
| [../v4/engine.md](../v4/engine.md) | What the app receives: slide documents, QA screenshots, generation events |
| [../v4/content.md](../v4/content.md) | The interview questions, provenance, and the rules the outline cards are held to |
