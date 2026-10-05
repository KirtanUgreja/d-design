# design — our own app and website

> How **this product** looks and feels. Not what it produces.

## The disambiguation, because this repo is full of the other kind of design

There are two design systems in this project and they are deliberately separate.

| | Governs | Lives in |
|---|---|---|
| **The design engine** | The decks the product *emits*. The per-deck look (type pairing, palette, grid, motif, motion) and the slides the model composes inside it | [../v4/design-engine.md](../v4/design-engine.md) |
| **Product design** — this directory | The marketing site, the app chrome, onboarding, pricing, the editor UI | here |

They must not merge. The moment our own chrome is styled by a generated deck's tokens, the design engine stops being a product boundary and becomes a global stylesheet. Tailwind for our chrome, theme tokens for the output, and no path between them ([../techstack/frontend.md](../techstack/frontend.md)). Since v4 the app never renders a slide itself: it shows backend-produced slides in a script-less iframe, so the two stylesheets cannot meet ([../v4/engine.md](../v4/engine.md)).

## The thesis

**Our own surfaces are the first proof of the central claim.** The product says AI-generated experiences can be genuinely beautiful. Anyone who lands on a generic SaaS marketing page has already been told the opposite, before reading a word.

And the counterweight, from [../findings.md](../findings.md) → "The category": **appeal has to be aimed.** Tome was beautiful, reached millions, and died at ~$4M ARR because the people it attracted would not pay. The goal is not maximum appeal. It is *irresistible to a founder pitching on Thursday*, and mildly intimidating to everyone else. The first users are founders and salespeople ([../v4/spec.md](../v4/spec.md) → Locked decisions → First users).

Both of those are argued in [principles.md](principles.md).

## Files

| Doc | What's in it |
|---|---|
| [principles.md](principles.md) | Eleven principles for our own surfaces, each with the decision it forces and the failure it prevents. Principle 5 is the banned-pattern list |
| [questions.md](questions.md) | **The question bank.** 276 open questions across 24 areas, each with a recommended default. Answer by exception |
| [brand.md](brand.md) | Identity: the gallery-wall decision, naming, type, colour, motion, voice |
| [website.md](website.md) | The marketing site: the hero, the recorded build, homepage order, showcase, pricing |
| [app.md](app.md) | The product UI for v4: composer, interview + outline gate, generation watch, editor, present and export, the missing colour picker, first run, failure states |

**Four decisions are locked** and the rest of the bank is open: the name is a placeholder (`brand.md`), our surfaces are a light editorial gallery wall (`brand.md`), the hero is a live artifact plus a recorded build (`website.md`), and the paywall is on publishing rather than generating (`website.md`).

## Version gating

**Updated 2026-09-26 for v4.** Product design follows the same discipline as [../security/README.md](../security/README.md): designed early, built when a phase needs it. v4 builds the engine first (phases 21–26) and the app after it (27–28); accounts and deployment are phase 29 ([../v4/plan/README.md](../v4/plan/README.md)). The parts that are expensive to retrofit are decided now.

| Surface | Designed | Built |
|---|---|---|
| Name, voice, vocabulary | Now | Phase 27 — it leaks into every UI string |
| Our brand identity | Now | Phase 27, at whatever fidelity a solo builder can hold |
| Composer, interview + outline gate, generation watch | Now ([app.md](app.md)) | Phase 27 |
| Editor, present, export reveal | Now ([app.md](app.md)) | Phase 28 |
| Empty, error, and refusal states | Now | Phases 27–28 — the AI refuses and something has to be on screen |
| Signup, auth, account, budget-cap states | Now | Phase 29 |
| Marketing site, pricing page | Now ([website.md](website.md)) | After phase 29, when there is a URL to give someone |
| Gallery, showcase, "made with" badge, hosted URL | Now | Skipped in v4 — needs published work and a hosted URL ([../v4/plan/29-accounts-deploy.md](../v4/plan/29-accounts-deploy.md) → Skipped) |

## What this directory obligates elsewhere

Design decisions that turned into requirements in other documents. Listed here so the trail is walkable in both directions — each row is owned by the document on the right, not by this one.

| Obligation | Landed in |
|---|---|---|
| The interview is an interview, not a chat: ≤5 questions with suggested answers, skippable | [../v4/content.md](../v4/content.md) → "Interview" |
| The outline gate shows YOU / AI / WEB provenance and flags unsourced numbers | [../v4/content.md](../v4/content.md) → "Research and the Fact ledger" |
| Design is judged by a human on the bench wall, not by an AI judge | [../v4/bench.md](../v4/bench.md) |
| The banned-pattern list governs generated slides | [../v4/design-engine.md](../v4/design-engine.md) → "Slide lint" |
| The export carries a machine-readable AI marker; a badge, if one ever exists, is separate and removable | [../v4/spec.md](../v4/spec.md) → Locked decisions → Export |
| Our chrome's display face is never a deck display face | [../v4/design-engine.md](../v4/design-engine.md) → "Registry", [brand.md](brand.md) |
| The marketing hero is a real exported deck, not a canned template | [website.md](website.md), [../v4/plan/26-player-export.md](../v4/plan/26-player-export.md) |
| Showcase requires written per-artifact release after the customer's launch | [../security/tenancy-and-data.md](../security/tenancy-and-data.md) |
| Marketing analytics is self-hosted, so it adds no subprocessor | [../security/third-parties.md](../security/third-parties.md) |

## Find it fast

| If you need… | Go to |
|---|---|
| Why our site must not use a generated design family's tokens | [principles.md](principles.md) → principle 9 |
| Why "make it more appealing" is a dangerous instruction here | [principles.md](principles.md) → principle 2 |
| Which three surfaces get the craft budget | [principles.md](principles.md) → principle 3 |
| How to demo a product whose demo costs a real generation | [principles.md](principles.md) → principle 7 |
| The colour picker users will look for and never find | [app.md](app.md) → "The colour picker that does not exist" |
| What to name this thing | [brand.md](brand.md) → "Naming" |
| The one early action item hiding in a late document | [website.md](website.md) → record generation event logs from the first good bench run |
| Every open decision, with a default | [questions.md](questions.md) |

## Connects to

| | |
|---|---|
| [../v4/spec.md](../v4/spec.md) | Who we are aiming at, and the decisions the app is built on |
| [../v4/design-engine.md](../v4/design-engine.md) | The *other* design system: the looks and the slides |
| [../techstack/frontend.md](../techstack/frontend.md) | shadcn/ui, Tailwind-on-chrome-only, and the cold 90% |
| [../coderules/performance.md](../coderules/performance.md) | The cold-90% rule this directory applies to *design attention*, not just code |
| [../findings.md](../findings.md) | The category evidence, and the platform fact behind the AI-disclosure obligation (EU AI Act Art. 50) |
