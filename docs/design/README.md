# design — our own app and website

> How **this product** looks and feels. Not what it produces.

## The disambiguation, because this repo is full of the other kind of design

There are two design systems in this project and they are deliberately separate.

| | Governs | Lives in |
|---|---|---|
| **Art direction** | The experiences the engine *emits*. Tokens, motion vocabulary, the renderer | [../v1/art-direction.md](../v1/art-direction.md), [../v2/art-direction-system.md](../v2/art-direction-system.md) |
| **Product design** — this directory | The marketing site, the app chrome, onboarding, pricing, the editor UI | here |

They must not merge. The moment our own chrome is styled by `cinematic-dark`, the art-direction layer stops being a product boundary and becomes a global stylesheet — and rule 7 in [../../AGENTS.md](../../AGENTS.md) is the reason that matters. Tailwind for our chrome, CSS variables for the output, and no path between them ([../techstack/frontend.md](../techstack/frontend.md)).

## The thesis

**Our own surfaces are the first proof of the central claim.** The product says AI-generated experiences can be genuinely beautiful. Anyone who lands on a generic SaaS marketing page has already been told the opposite, before reading a word.

And the counterweight, from [../v1/market.md](../v1/market.md): **appeal has to be aimed.** Tome was beautiful, reached millions, and died at ~$4M ARR because the people it attracted would not pay. The goal is not maximum appeal. It is *irresistible to a marketer with a launch in three weeks*, and mildly intimidating to everyone else.

Both of those are argued in [principles.md](principles.md).

## Files

| Doc | What's in it |
|---|---|
| [principles.md](principles.md) | Eleven principles for our own surfaces, each with the decision it forces and the failure it prevents. Principle 5 is the banned-pattern list |
| [questions.md](questions.md) | **The question bank.** 276 open questions across 24 areas, each with a recommended default. Answer by exception |
| [brand.md](brand.md) | Identity: the gallery-wall decision, naming, type, colour, motion, voice |
| [website.md](website.md) | The marketing site: the hero, the recorded build, homepage order, showcase, pricing |
| [app.md](app.md) | The product UI: four hot surfaces, the editor, the missing colour picker, first run, failure states |

**Four decisions are locked** and the rest of the bank is open: the name is a placeholder (`brand.md`), our surfaces are a light editorial gallery wall (`brand.md`), the hero is a live artifact plus a recorded build (`website.md`), and the paywall is on publishing rather than generating (`website.md`).

## Version gating

Product design follows the same discipline as [../security/README.md](../security/README.md): designed early, built when a version needs it. v1 is a single local user with no auth and no deployment ([../techstack/infrastructure.md](../techstack/infrastructure.md)), so almost nothing here *ships* in v1 — but the parts that are expensive to retrofit are decided in v1, exactly like CSS logical properties.

| Surface | Designed | Built |
|---|---|---|
| Name, voice, vocabulary | v1 | v1 — it leaks into every UI string and every doc |
| Our brand identity | v1 | v1, at whatever fidelity a solo builder can hold |
| App chrome: intake, outline gate, generation watch, editor | v1 | v1 — it is the only UI that exists |
| Empty, error, and refusal states | v1 | v1 — the AI refuses in v1 and something has to be on screen |
| Marketing site | v1 | v3, when there is a URL to give someone |
| Pricing page | v2 | v3. [../v1/spec.md](../v1/spec.md) defers the *pricing*, not the page |
| Signup, auth, account | v3 | v3 ([../techstack/backend.md](../techstack/backend.md)) |
| Gallery, showcase, "made with" badge | v2 | v3 — it needs published work to show |

## What this directory obligates elsewhere

Design decisions that turned into requirements in other documents. Listed here so the trail is walkable in both directions — each row is owned by the document on the right, not by this one.

| Obligation | Landed in |
|---|---|
| Keep the SSE event logs of good runs — the marketing demo is built from one | [../v1/plan/06-model-seam-and-build.md](../v1/plan/06-model-seam-and-build.md) |
| The generation watch renders real scenes; `repair` stays silent | [../v1/plan/06-model-seam-and-build.md](../v1/plan/06-model-seam-and-build.md) |
| The outline gate shows claim provenance and is not a list with a button | [../v1/plan/07-director.md](../v1/plan/07-director.md) |
| Intake is an interview, not a chat; no upload affordance, no templates | [../v1/plan/08-intake.md](../v1/plan/08-intake.md) |
| The refusal of "make the headline smaller" is a written deliverable | [../v1/plan/09-editor.md](../v1/plan/09-editor.md) |
| Designed 404 for an unpublished artifact; unfurls are a launch requirement | [../v1/plan/05-publish-present-embed.md](../v1/plan/05-publish-present-embed.md) |
| Six upload controls means six messages; brand kit is asked second | [../v1/plan/10-brand-and-uploads.md](../v1/plan/10-brand-and-uploads.md) |
| Settle the name before phase 09 | [../v1/plan/README.md](../v1/plan/README.md) |
| **`editorial-light` must not converge on our own chrome** | [../v2/spec.md](../v2/spec.md) |
| Badge + AI disclosure are one mark, and only one of them is removable | [../v3/compliance.md](../v3/compliance.md), [../v3/spec.md](../v3/spec.md) |
| Showcase requires written per-artifact release after the customer's launch | [../security/tenancy-and-data.md](../security/tenancy-and-data.md) |
| Marketing analytics is self-hosted, so it adds no subprocessor | [../security/third-parties.md](../security/third-parties.md) |
| Publish-before-payment is this product's real business-logic exposure | [../security/adversarial-ai.md](../security/adversarial-ai.md) |
| The marketing site is a route group; recordings are fixtures | [../coderules/structure.md](../coderules/structure.md) |

## Find it fast

| If you need… | Go to |
|---|---|
| Why our site must not use `cinematic-dark` | [principles.md](principles.md) → principle 9 |
| Why "make it more appealing" is a dangerous instruction here | [principles.md](principles.md) → principle 2 |
| Which three surfaces get the craft budget | [principles.md](principles.md) → principle 3 |
| How to demo a product whose demo costs $0.40 a run | [principles.md](principles.md) → principle 7 |
| The colour picker users will look for and never find | [app.md](app.md) → "The colour picker that does not exist" |
| What to name this thing | [brand.md](brand.md) → "Naming" |
| The one v1 action item hiding in a v3 document | [website.md](website.md) → "Watch it build" — start keeping SSE recordings in phase 06 |
| Every open decision, with a default | [questions.md](questions.md) |

## Connects to

| | |
|---|---|
| [../v1/market.md](../v1/market.md) | Who we are aiming at, and who killed a competitor by being appealing to the wrong people |
| [../techstack/frontend.md](../techstack/frontend.md) | shadcn/ui, Tailwind-on-chrome-only, and the cold 90% |
| [../coderules/performance.md](../coderules/performance.md) | The cold-90% rule this directory applies to *design attention*, not just code |
| [../v3/compliance.md](../v3/compliance.md) | AI-disclosure obligations that are a design constraint on both our site and the output |
