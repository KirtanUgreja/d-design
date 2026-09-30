# Brand

> Our own identity. Type, colour, rhythm, name, voice. **Decided in v1** because it leaks into every route, string, and component, and changing it later is an audit rather than an edit ([principles.md](principles.md), principle 11).

---

## The decision: gallery wall

**Light, warm-neutral, editorial, type-led.** One restrained accent doing almost nothing. Hairline rules instead of shadows. Real editorial typography instead of a variable grotesk at default tracking.

Three reasons, in order of how much they matter:

| | |
|---|---|
| **It makes the output read as work, not as theme** | A deck on a quiet bright wall is a piece of work. The same deck on a dark, atmospheric site is the site's theme, and the product looks like it makes one thing — the exact accusation this product levels at template tools |
| **It is the shortest path away from the slop aesthetic** | Dark leads to glow, glow leads to gradient, gradient leads to violet. Editorial has no such gravity. The banned list in [principles.md](principles.md) becomes easy to obey instead of a constant fight |
| **It survives the registry** | v4 ships a look registry — about 50 type pairings over 30–40 OFL families, six palette strategies, many of them light ([../v4/design-engine.md](../v4/design-engine.md) → "Registry"). A dark site would then be arguing for one of our looks. A neutral wall argues for none of them, which is the honest position |

**What would reverse it:** if light looks turn out to read better on a dark wall than on a light one, the wall was wrong. That is a real test and it arrives on its own.

**What this is not:** it is not minimalism as a default, and it is not "clean". A gallery wall has proportion, rhythm, and an obvious point of view about scale. Blank is not the same as quiet.

### The collision this decision walks into

**Updated 2026-09-26 for v4.** The look registry is about 50 pairings over 30–40 OFL families ([../v4/design-engine.md](../v4/design-engine.md) → "Registry"), and "ink + one accent on paper" with an editorial pairing is one of the looks the sampler can produce. If our wall converges with the most editorial of them, principle 9 fails in a subtler and more damaging way than the one it was written to prevent: the site stops being a neutral wall and becomes "just another look", and "this product makes exactly one thing" comes back as "this product has a house style."

It is cheap to prevent at authoring time and expensive to discover afterwards, so it is a constraint on the **registry**, not on the wall:

- **Different display face.** Our chrome's display face must not appear in the deck registry as a display face. The registry states this as its own rule, so it is checked where fonts are added, not remembered here. It is the rule under the most pressure, because the obvious right answer for both is the same kind of face
- **Different ground.** If ours is warm paper, the editorial looks' paper is cool or bright white, or the reverse. Not both warm
- **Different accent behaviour.** Ours appears twice on a screen. A look is allowed to be much louder, and here it should be

**The test:** put any look's deck in the editor canvas with our chrome around it. If a stranger cannot tell which pixels are the product and which are the artifact, one of the two has to move — and it is the wall that moves, because the look is the thing we sell. Run it at the phase-23 wall, when the registry first reaches full size ([../v4/plan/23-design-system.md](../v4/plan/23-design-system.md)).

---

## Naming

`d-design` is a placeholder. It describes the repository.

### Criteria

| Rule | Why |
|---|---|
| The name survives being said next to Gamma, Canva, Framer | The comparison set is deck tools and design tools ([../findings.md](../findings.md) → "The category"). "Deck", "slides", "present" are fine as descriptors, but the *name* should not be one of them |
| No `AI`, no `.ai` | Everyone has it, it says nothing, and it dates the product to this exact wave |
| No `-ify`, `-ly`, `-r`, invented compound | These read as 2014 and they signal "built fast" — the same tell as a violet gradient |
| One word, pronounceable, spellable on a phone call | A founder says this name out loud to an investor |
| Not a verb we need for the UI | `generate` and `export` must stay available as plain verbs |

### Three directions, with candidates

Domains unverified — treat these as prompts for the direction, not a shortlist to register.

**Editorial / print.** The strongest fit: it borrows a vocabulary that already means *considered publishing*, and it is the furthest possible read from AI tooling.

- **Lede** — the opening line that earns the rest. Every storyline arc opens on a hook. Short, editorial, no baggage
- **Broadside** — a single large printed sheet announcing news. Also a full salvo. The two meanings are *launch page* and *launch*
- **Standfirst** — the paragraph between headline and body. Precise, British, slightly severe
- **Vellum** — surface, craft, permanence. Softer, more premium, less specific

**Direction / staging.** Names the thing the product actually does — design direction over content.

- **Directive** — has the word direction inside it and reads as decisive. Slight corporate-process collision
- **Marque** — a mark of make, as in a car marque. Premium, short, brand-adjacent

**Optical / light.** Cinematic without being dark.

- **Aperture** — the opening that decides what the light does. Widely used elsewhere
- **Foil** — the reflective sheet, and the thing that sets off what it sits behind. Very short, slightly cold

**Recommendation:** the editorial direction, and `Lede` or `Broadside` from it. Both make the positioning argument before anyone reads a word of copy.

### What the name blocks

Nothing in the build. But settle it before the app is built ([../v4/plan/27-app-create-flow.md](../v4/plan/27-app-create-flow.md)), because the composer and the interview are the first place user-facing strings accumulate, and renaming across a UI is exactly the audit this section exists to avoid.

---

## Type

Type is most of why anything looks expensive, and [../techstack/frontend.md](../techstack/frontend.md) already calls buying it the highest-leverage money in the product. That argument was made about the *output*. It applies at least as strongly to our own surfaces, where the budget is one licence rather than a redistribution question.

| | Requirement |
|---|---|
| **Display** | A licensed editorial face with real character at large sizes. This is where the money goes |
| **Text** | Highly legible at 15–17px with a true italic and real small caps if affordable |
| **Mono** | Only for the recorded prompt and any code sample. Not a design element |
| **Never** | Inter, Geist, or a default-tracked variable grotesk as the whole identity. Not because they are bad — because they are the uniform |

**Our display face must not be a deck display face.** The v4 registry holds 30–40 OFL families and forbids ours as a display face ([../v4/design-engine.md](../v4/design-engine.md) → "Registry"); if a look shares it, the chrome starts looking like a look and principle 9 quietly fails. A licensed face solves this for free, because the registry is OFL-only.

**Licensing is simpler here than for the output.** Fonts in our chrome are served to visitors of our site, not redistributed to our customers' audiences — so a normal webfont licence is fine, and the open-licence constraint in [../techstack/frontend.md](../techstack/frontend.md) does not bind this decision.

---

## Colour

**Ground:** warm neutral, not white. Paper rather than screen. One or two steps of warm grey for structure, and a near-black for text that is not `#000`.

**Accent:** one, and it is open — question 36 in [questions.md](questions.md). The constraint on it is more useful than the hue:

- It appears in roughly two places: the focus ring and the primary action. That is all
- It must pass contrast at its *smallest* use, not its largest ([questions.md](questions.md), §21)
- It must not be purple, violet, magenta, or a gradient of any two of those ([principles.md](principles.md), principle 5)
- It must not compete with a dark look when they are two inches apart, which is the editor's normal state (principle 4)

**Recommended families:** a deep ink blue-black, an oxide red, or a dark olive. All three are hard to make look cheap and none of them reads as "AI product".

**No gradients anywhere in the chrome.** Not subtle ones either. A flat ground with real typographic hierarchy is the whole aesthetic.

---

## Structure, rhythm, surface

| | |
|---|---|
| **Grid** | Asymmetric, with a real baseline rhythm. Five consecutive centred `max-w-3xl` sections is a banned pattern, and it is the default shape of every generated landing page |
| **Separation** | Hairline rules. Layered shadows read as template, and they will not survive next to a real designed artifact |
| **Radius** | Small and consistent. `rounded-2xl` on everything is a tell |
| **Density** | The marketing site is generous. The editor is dense — it is a working tool used for hours |
| **Imagery** | Only real output and real screenshots. No stock, no illustration, no 3D |

---

## Motion

**Our signature is restraint.** The chrome barely moves; the canvas moves. That is a legible, deliberate contrast and it costs nothing to maintain.

One exception, and it is the whole motion budget: **the recorded build on the homepage** ([website.md](website.md)). Everything else transitions fast enough to read as response rather than animation.

`prefers-reduced-motion` is respected on our own surfaces too, not only in the output. We are about to publish accessibility requirements for other people's pages.

---

## Logo

**Wordmark only.** Set in the display face, spaced by hand, and that is the entire identity system for v1–v3. A mark is a v3 problem at the earliest and usually a distraction from the work that decides whether anyone cares.

Favicon and OG image are a crop of real output, not a logo on a gradient ([questions.md](questions.md), §4).

---

## Voice

Second person, imperative, short sentences, one opinion per paragraph. No "we". No "beautiful" as a claim — show it.

**The tell to avoid is LLM house style**, because it is the one our buyer is most sensitised to: *"Meet ⟨product⟩"*, *"Supercharge your…"*, *"The AI-powered platform for…"*, tricolons everywhere, and a closing sentence that restates the opening one. Copy that sounds generated undermines a product arguing that generated things need not sound generated.

---

## The editor palette check

Principle 4 says the chrome must not compete with the canvas. That is testable, not a matter of taste:

- [ ] Put the editor chrome next to a full dark-ground deck on the canvas. Nothing in the chrome should pull the eye first
- [ ] The selection affordance is a hairline and a label, not a saturated box over a designed page
- [ ] The accent appears at most twice on screen
- [ ] Re-run all three checks against the light looks at the phase-23 wall — a light chrome around a light deck is the case this decision has not been tested against

---

## Connects to

| | |
|---|---|
| [principles.md](principles.md) | Principle 5 is the banned-pattern list this document assumes and does not repeat |
| [website.md](website.md) | Where the identity is first spent |
| [app.md](app.md) | Where it has to survive eight hours of use |
| [../v4/design-engine.md](../v4/design-engine.md) | The *other* design system — the look registry. Nothing here may reference its tokens |
