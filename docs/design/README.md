# design — our own app and website

> How **this product** looks and feels. Not what it produces.

## The disambiguation, because this repo is full of the other kind of design

There are two design systems in this project and they are deliberately separate.

| | Governs | Lives in |
|---|---|---|
| **The design engine** | The decks the product *emits*. The per-deck generated design system (type pairing, layout grammar, spacing, texture, color, motion) | `v1/`, `v2/` — the design registry and layout engine |
| **Product design** — this directory | The marketing site, the app chrome, onboarding, pricing, the editor UI | here |

They must not merge. The moment our own chrome is styled by a generated deck's tokens, the design engine stops being a product boundary and becomes a global stylesheet — and rule 7 in [../../AGENTS.md](../../AGENTS.md) is the reason that matters. Tailwind for our chrome, CSS variables for the output, and no path between them ([../techstack/frontend.md](../techstack/frontend.md)).

## The thesis

**Our own surfaces are the first proof of the central claim.** The product says AI-generated experiences can be genuinely beautiful. Anyone who lands on a generic SaaS marketing page has already been told the opposite, before reading a word.

And the counterweight, from `v1/spec.md`: **appeal has to be aimed.** Tome was beautiful, reached millions, and died at ~$4M ARR because the people it attracted would not pay. The goal is not maximum appeal. It is *irresistible to a marketer with a launch in three weeks*, and mildly intimidating to everyone else.

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

Product design follows the same discipline as [../security/README.md](../security/README.md): designed early, built when a version needs it. v1 is a lean flow (interview → mapping → build → review → export) with no auth and no deployment, so almost nothing here *ships* in v1 — but the parts that are expensive to retrofit are decided in v1, exactly like CSS logical properties.

| Surface | Designed | Built |
|---|---|---|
| Name, voice, vocabulary | v1 | v1 — it leaks into every UI string and every doc |
| Our brand identity | v1 | v1, at whatever fidelity a solo builder can hold |
| App chrome: intake interview, outline gate, generation watch, review | v1 | v1 — it is the only UI that exists |
| Empty, error, and refusal states | v1 | v1 — the AI refuses in v1 and something has to be on screen |
| Marketing site | v1 | v3, when there is a URL to give someone |
| Pricing page | v2 | v3 |
| Signup, auth, account | v3 | v3 |
| Editor (post-generation editing, re-skin) | v2 | v2 |
| Gallery, showcase, "made with" badge | v2 | v3 — it needs published work to show |

## What this directory obligates elsewhere

Design decisions that turned into requirements in other documents. Listed here so the trail is walkable in both directions — each row is owned by the document on the right, not by this one.

| Obligation | Landed in |
|---|---|---|
| The interview is an interview, not a chat | `docs/v1/plan/02-interview.md` |
| The outline gate shows claim provenance and is not a list with a button | `docs/v1/plan/02-interview.md` |
| The review loop is human in v1, not an AI judge | `docs/v1/plan/07-visual-review.md` |
| The badge + AI disclosure are one mark, and only one of them is removable | `docs/v3/spec.md`, `docs/v3/plan/18-hosting.md` |
| Our chrome must not converge on any generated design family | `docs/v2/plan/12-editor.md`, [principles.md](principles.md) → principle 9 |
| The marketing hero is a real exported deck, not a canned template | [website.md](website.md), `docs/v1/plan/05-export.md` |
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
| The one v1 action item hiding in a v3 document | [website.md](website.md) → keep real exported decks for the hero |
| Every open decision, with a default | [questions.md](questions.md) |

## Connects to

| | |
|---|---|
| `v1/spec.md` | Who we are aiming at, and the per-deck design engine the output comes from |
| [../techstack/frontend.md](../techstack/frontend.md) | shadcn/ui, Tailwind-on-chrome-only, and the cold 90% |
| [../coderules/performance.md](../coderules/performance.md) | The cold-90% rule this directory applies to *design attention*, not just code |
| `v3/spec.md` | AI-disclosure obligations that are a design constraint on both our site and the output |
