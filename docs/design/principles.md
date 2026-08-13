# Principles

> Eleven rules for our own surfaces. Each one names the decision it forces and the failure it prevents, because a principle that forces no decision is decoration.

---

## 1. The site is the proof, not the pitch

The product claims AI-generated experiences can be genuinely beautiful. **Our own surfaces are the first sample of that claim anyone sees.** A visitor who lands on a stock SaaS page has already been shown the counter-argument before reading the headline.

This is not vanity. It is the same reason `docs/v1/spec.md` makes Risk 1 the top risk: if the design isn't good, the runtime and the pipeline are worthless. Our front door is the second instance of that same risk.

**Forces:** design attention on the site is not overhead to be minimized. It is the demo.
**Prevents:** shipping a Tailwind template that quietly disproves the thesis.

---

## 2. Aim the appeal

**"Make it more appealing" is a dangerous instruction in this specific product.** `docs/findings.md` → The category records what happened to the last company that followed it: Tome was beautiful, reached millions of users, attracted Gen Z, students, freelancers and artists — people who loved it and would not pay — and shut down at ~$4M ARR. Its own retrospective: *"building AI for everyone at once is fundamentally flawed."*

So the target is not maximum appeal. It is:

> Irresistible to a founder pitching on Thursday. Mildly intimidating to everyone else.

**Updated 2026-08-13.** It used to read *"a marketer with a launch in three weeks and a budget"*. The shape of the test is unchanged and so is Tome's lesson — narrow, high-stakes, budget-holding. The buyer is a marketer or founder with a launch in three weeks; the wedge is the deck that does not look AI-made (`docs/v1/spec.md`).

**The test, applied to any page:** would this make a student want to sign up *more* than it makes a founder three days from a raise want to sign up? If yes, it is wrong, however beautiful.

Practically that means the work shown is commercial work — investor decks, sales pitches, launches — never "my travel photos" or "a deck about my thesis". It means the copy names a job, a deadline, and a stakeholder. It means we never optimize for "free forever" traffic.

**Forces:** every showcase piece, every screenshot, every example prompt is B2B launch work.
**Prevents:** the exact failure mode that killed a better-funded competitor in this category.

---

## 3. The chrome is cold. Three surfaces are hot

[../coderules/performance.md](../coderules/performance.md) has a cold-90% rule for code. It applies to **design attention** just as literally: settings, account, brand kit, asset list, property panel — assemble them from shadcn/ui and move on ([../techstack/frontend.md](../techstack/frontend.md)).

Three surfaces get the craft budget, because they are the only three where a user forms an opinion:

| Surface | Why it's hot |
|---|---|
| **Intake / interview** — the first prompt | The first thing a new user touches. If it feels like a form, the product feels like a form |
| **The generation watch** | Slides arrive one at a time over SSE, images included. This is the wow moment, and it is 40 seconds long — the single highest-leverage piece of motion design in the entire app |
| **The export reveal** | The moment a downloadable `.html` file exists. This is what they screenshot and paste into Slack |

Everything else is furniture. Furniture that is quiet is good furniture.

**Forces:** an explicit budget — polish these three, assemble the rest.
**Prevents:** spending three weeks on a settings page while the generation watch is a spinner.

---

## 4. Our chrome must never compete with the canvas

The editor surrounds output that is supposed to be the most beautiful thing on the screen. **Chrome with a point of view is chrome that fights.** A saturated accent colour, a gradient panel, or a strong brand tint in the editor will sit two inches from a designed hero and lose — or worse, win.

Near-monochrome UI. One accent, used almost nowhere. The canvas supplies all the colour in the room.

**Forces:** the editor's palette is decided *against* the design families, not independently of them, and re-checked when v2 grows the registry.
**Prevents:** an editor that looks fine empty and terrible in use.

---

## 5. No AI slop, and no vibe-code tells

The visual language of "AI product, built fast" is now instantly legible to exactly the audience we want, and it reads as *unserious*. We are selling design judgment. Shipping the defaults is a confession that we have none.

> **This list governs the artifact, not only our chrome.** It was written about the marketing site and the app, it lives in `docs/design/`, and for the whole of the old v1 it was read as being about our surfaces — while the renderer shipped a coloured radial bloom behind every hero and four of five visual generators built from gradients. Nobody decided the output was exempt; the filing decided it. A deck we generate for a customer carries our judgement more directly than our own homepage does, so it is held to this table at least as hard. The design-family registry (`docs/v1/plan/00-foundations.md`) and the acceptance fingerprint (`docs/v2/plan/15-variety-gate.md`) are where the artifact is kept off this list, and the banned patterns below are the family registry's first entries.

**Banned outright** — not "used sparingly", banned:

| Pattern | Why it is fatal *here* |
|---|---|
| Purple→pink or indigo→violet gradients | The single most legible "this is an AI wrapper" signal on the internet |
| Neon, glow, bloom | Reads as a shader demo. Also fights every dark family we publish |
| Gradient text on headlines | 2023's tell, and it wrecks type quality at every size |
| ✨ sparkles, magic wands, robot icons | The universal shorthand for "AI did it and we're nervous about it" |
| Glassmorphism over a blurred mesh blob | Default hero of every no-code template since 2022 |
| Tilted 3D browser mockup with fake traffic lights | Sells a UI. We sell output — see principle 6 |
| Bento grid of icon + three words + one sentence | Says nothing, and every competitor's page says it too |
| Infinite-scrolling logo marquee | Especially before we have customers. See principle 10 |
| Counting-up stat numbers with no source | Theatre |
| Generated-avatar testimonials | Fabricated social proof, and it is the fastest way to lose a skeptical buyer |
| Emoji as section markers | |
| Autoplaying hero video of a UI too small to read | |
| `rounded-2xl` + `shadow-lg` + `border-neutral-800` everywhere | The shadcn defaults are a starting point, not an identity |
| "Meet ⟨product⟩" · "Supercharge your…" · "The AI-powered platform for…" · "10x your…" | LLM house style. Our copy has to sound like a person with an opinion |
| Dark mode chosen because it hides weak typography | Dark is a decision, not a hiding place |
| Five consecutive centred sections at `max-w-3xl` | No rhythm, no hierarchy, no editing |

Four of those rows are now automated for the artifact, and it is worth knowing which: gradients and gradient text are a no-styling backstop check (`docs/v1/plan/01-schema.md`), glow/bloom/glassmorphism-blur is part of the design-family validation, and the consecutive-centred-sections row is a layout-distribution constraint in the mapping pass (`docs/v1/plan/03-mapping.md`). The rest remain judgement, which is why the positive rule below is the one that actually does the work.

**The positive rule that replaces the list:** every visual decision on our surfaces should be defensible in one sentence that isn't *"it looks modern"*. Type, spacing, and one restrained colour idea are enough to look expensive; that is the same bet [../techstack/frontend.md](../techstack/frontend.md) makes when it calls buying type the highest-leverage money in the product.

**Forces:** a real typographic point of view, since we have removed every cheap substitute for one.
**Prevents:** looking like the thing we are arguing against.

---

## 6. Show the artifact, not the app

Linear and Vercel sell tools, so their pages show product UI. **Our differentiator is not the tool, it is what comes out of it.** `docs/v1/spec.md` is explicit that the gap against Gamma is *creative ceiling*, not speed — and a screenshot of an editor cannot show a ceiling.

So the hero is the output: a real, exported **deck**, in the page, advancing and animating exactly as a room would see it. Not a picture of one.

**Changed 2026-08-13.** This read *"scrolling and animating exactly as a recipient would see it"* — the drift showing up in our own marketing. The artefact advances now (slide mode, never scroll), and the hero should let a visitor click through it — which is a better hero anyway, because clicking is the product's actual gesture and scrolling was everyone's.

We can do this cheaply for a reason baked into the architecture: the exported deck is **one self-contained HTML file with almost no JS and zero network requests** ([../techstack/frontend.md](../techstack/frontend.md)), so embedding real work costs approximately nothing per visitor.

**Forces:** the marketing site depends on the renderer being genuinely good — which is the correct dependency, and an honest one.
**Prevents:** selling a UI, which is what every competitor's page already does.

---

## 7. The demo must cost nothing and be unabusable

A deck costs model calls and image generations and takes tens of seconds (`docs/v1/spec.md`). Anonymous "type a prompt, watch it build" on the homepage is therefore a bill and an abuse surface with a public front end — and [../security/adversarial-ai.md](../security/adversarial-ai.md) has a name for that shape.

The lazy answer is also the better demo:

| | |
|---|---|
| **Exported examples** | Real decks, real files, static. Zero marginal cost, infinite scale |
| **A recorded generation** | The SSE event log of a real run — `slide`, `repair`, `done` — captured once and replayed client-side. It looks *identical* to a live generation because it is the same event stream, and it costs one model call ever |
| **A real generation** | Behind signup, metered, quota'd, kill-switchable (`docs/v3/plan/19-billing.md`) |

The recorded replay is the interesting one. It is honest — those slides really were generated — it never fails on stage, and it is the closest thing to letting someone feel the product before they own an account.

**Forces:** the SSE event log is worth recording and versioning from the first successful golden-brief run.
**Prevents:** a homepage that a scraper can turn into a four-figure invoice overnight.

---

## 8. Design the absence of the colour picker

Users will look for a font size and a colour picker. They will not find them, **and they cannot** — the panel is generated from a schema with no presentational fields, so the control is not hidden, it is unrepresentable (`docs/v1/plan/01-schema.md`).

That is the product's spine, and it is also the moment a first-time user decides whether this is a tool or a toy. **Nothing is more important in the app's UX than making that absence read as luxury rather than as a missing feature.**

Undesigned, it is a bug report. Designed, it is the pitch: *you cannot make this ugly.* The affordances that replace it — design family, emphasis, brand kit, reroll — must be visibly *more* powerful than the thing they replace, and reachable in the same instant the user reaches for the picker.

**Forces:** an explicit answer at the exact point of reaching. Not a docs page, not a tooltip, not an onboarding tour.
**Prevents:** the single most likely first-session churn cause in the whole product.

---

## 9. Our brand is not a design family. Our site is the gallery wall

If our site *is* a design family, we have shown that the product makes exactly one thing — which is precisely the accusation this product levels at template tools (`docs/v1/spec.md`). The abstraction claim is already unproven while the registry is young; a site wearing a family makes it look like a skin, not a layer.

**The frame: our surfaces are the gallery wall, the output is the art.** Gallery walls are quiet, bright, and typographic on purpose — and a dark, cinematic, motion-heavy deck hung on a quiet wall reads as *work*, while the same deck on a dark, glowing site reads as *theme*.

It also solves principle 5 for free. Going dark-and-atmospheric on our own site is a straight line into neon and glow; going editorial is a straight line away from it.

**Forces:** a distinct identity for our chrome — type-led, restrained, likely light or neutral, with the accent doing almost nothing.
**Prevents:** proving the opposite of the thesis with the site that argues for it.

---

## 10. Nothing on our surfaces may be a claim the product can't back

Every number, badge, logo, and superlative maps to something shipped and verified. No customer logos before customers. No "10,000 teams". No before/after that we staged. `docs/v3/spec.md` makes some of this a legal obligation rather than a taste one — AI-generated content carries disclosure duties, and that is a design constraint on the deck *and* on the page that markets it.

The competitive claim in particular has to be demonstrated, never asserted: "Gamma's output looks like Gamma" is a sentence anyone can write. Two live decks side by side is an argument.

**Forces:** the showcase is real work or it does not exist.
**Prevents:** the credibility loss that is unrecoverable with exactly the buyer we want.

---

## 11. Version discipline applies to design too

Design early, build when a version needs it — the same rule [../security/README.md](../security/README.md) uses. v1 is the lean flow (interview → mapping → build → review → export) with no auth and no deployment ([../techstack/infrastructure.md](../techstack/infrastructure.md)), so a marketing site built in v1 is a site with no product behind it and no URL to put it on.

But the parts that are expensive to retrofit get decided in v1 anyway, for the same reason CSS logical properties do (`docs/v1/spec.md`): name, vocabulary, voice, and the app chrome's palette all leak into hundreds of strings and components, and changing them later is an audit rather than an edit.

The gating table is in [README.md](README.md).

**Forces:** naming and vocabulary get settled now; the pricing page does not.
**Prevents:** building a front door for a house with no rooms.

---

## The dogfood ladder

The end state is obvious and worth naming as a goal rather than discovering as an irony: **our marketing site should eventually be a deck this product generated.** That is the most convincing possible demonstration and the most brutal possible dogfood.

It is not a v1 goal. The renderer renders slides, not marketing sites; a marketing site needs navigation, a pricing table, and a footer, none of which are in `docs/v1/plan/01-schema.md`, and none of which should be added to it to serve our own website.

| Rung | When |
|---|---|
| The hero section is a real exported deck, embedded | v3 — as soon as there is a hosted URL |
| The showcase is entirely product output | v3 |
| Individual landing pages for campaigns are generated | v3 |
| The whole site is generated | Only if it becomes true without bending the schema. **Never add a primitive to the `Deck` schema for our own website** — that is the tail wagging the dog, and it is how a product's IR fills with special cases |
