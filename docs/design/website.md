# The marketing site

> Designed in v1, built in v3 — the first version with a URL worth giving someone ([README.md](README.md)). One thing in it must be captured much earlier, and that is the point of this document.

---

## The hero, decided

**A real published artifact, live in the page, plus a recorded generation you can watch.**

```
┌──────────────────────────────────────┐
│  headline, one line                  │
│  ▸ Watch it build      Start         │
├──────────────────────────────────────┤
│   [ REAL PUBLISHED ARTIFACT ]        │
│   scrolls + animates in place        │
│   click → opens its real URL         │
└──────────────────────────────────────┘
```

Not a screenshot, not a mockup, not a tilted browser frame with fake traffic lights. The thing itself, at the top of the page, behaving exactly as a recipient's would.

**Why this is affordable:** a published artifact is static HTML on a CDN with almost no JS ([../techstack/frontend.md](../techstack/frontend.md)). Embedding real work costs approximately nothing per visitor and scales to any amount of traffic. The most convincing asset we have is also the cheapest one we own.

**Why it is the right proof:** the gap against Gamma is *creative ceiling*, not speed ([../v1/market.md](../v1/market.md)), and a screenshot of an editor cannot show a ceiling. Principle 6 in [principles.md](principles.md).

Supporting decisions:

| | |
|---|---|
| Headline above, artifact starting at the fold | Do not make people guess what they are looking at |
| The prompt that produced it, shown | Prompt and output in one screen is the entire pitch with no marketing copy at all |
| Click opens the real URL | It must be provable. A hero you cannot open is a mockup with extra steps |
| Nothing autoplays, no sound, no scroll-jacking | [principles.md](principles.md), principle 5 |
| Same artifact on mobile | Artifacts are responsive by definition, and demonstrating that is free |
| From v2, a control that switches art direction | Same content, radically different experience, in four seconds. That is the abstraction claim demonstrated rather than asserted ([../v2/spec.md](../v2/spec.md)) |

**Budget: first output pixel under 1.5s on 4G.** The proof cannot arrive late.

---

## "Watch it build" — and the one thing to capture in v1

The primary CTA does not go to signup. It goes to a **recorded generation**: the SSE event log of a real run — `scene`, `repair`, `done` ([../techstack/frontend.md](../techstack/frontend.md)) — captured once and replayed client-side.

It is indistinguishable from a live generation because it is the same event stream driving the same renderer. It costs one model call, ever. It never fails on stage. And it is honest: those scenes really were generated, and we say plainly that it is a recording ([principles.md](principles.md), principle 10).

> **This is the v1 action item in an otherwise v3 document.** Start recording SSE event logs from the first successful golden-brief run in [../v1/plan/06-model-seam-and-build.md](../v1/plan/06-model-seam-and-build.md). Keep the good ones, versioned alongside the fixtures. A log costs bytes; re-creating a run whose output you loved costs a model call and may not reproduce.

The alternatives were considered and are worse:

| | Why not |
|---|---|
| Live anonymous generation | ~$0.20–0.40 a run, tens of seconds, on a public front end with no auth. That is a bill and an abuse surface with a URL ([../security/adversarial-ai.md](../security/adversarial-ai.md)) |
| Prompt box that always returns a canned result | It implies interactivity it does not have. Small lie, wrong buyer |
| A video of a generation | Compresses badly, ages, and cannot be opened in a real browser tab |
| Third-party demo tooling | A guided tour of a design product is an admission that the product cannot demonstrate itself |

**The free editable demo stays on the table** ([questions.md](questions.md), #78): property-panel edits are local patches with no model call ([../v1/plan/09-editor.md](../v1/plan/09-editor.md)), so letting an anonymous visitor change real copy on a real artifact costs nothing. It is the second-page experience, not the hero, because it leads with the editor and the output is the argument.

---

## Homepage order

Eight sections. The order is the argument, and each one answers the objection the previous one creates.

| | Section | The objection it answers |
|---|---|---|
| 1 | Headline + live artifact | *What is this* |
| 2 | The prompt that made it | *Did a human design that* |
| 3 | Watch it build | *Show me it wasn't hand-tuned* |
| 4 | The outline gate | *So the AI just decides everything?* — no, you approve the story before it builds |
| 5 | Editing without a colour picker | *Can I change it* — and this is where the constraint becomes the pitch ([app.md](app.md)) |
| 6 | On brand, from your kit | *Can it ship in our brand* |
| 7 | Showcase, three pieces, link to the rest | *Has anyone real used this* |
| 8 | Pricing + start | |

Section 5 is the one that is most tempting to soften and must not be. The absence of the colour picker is the product; a homepage that apologises for it teaches users to expect it.

---

## Pages

Eight, total. A larger site before there are customers is a site maintaining itself.

| Page | Notes |
|---|---|
| Home | Above |
| Showcase | Below |
| One comparison page | Honest about where we lose. Framer, Vev, Readymag and Webflow are the real comparison set ([../v1/market.md](../v1/market.md)), and saying so flatters the buyer and happens to be true |
| Pricing | Below |
| Docs | Small, v3 |
| Changelog | Instead of a blog. Nothing to say yet is not a content strategy problem |
| One essay | The point of view. It is how designers hear about this without being sold to |
| Legal + trust | Privacy, subprocessors, the training and embargo promises ([questions.md](questions.md), §23) |

No careers page, no "for agencies", no fat footer sitemap, no chat widget.

---

## Showcase

The sharpest constraint here is not design. **A brief is a customer's unreleased launch messaging under embargo** ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)).

- **Explicit written per-artifact release, after their launch is public.** Never a checkbox at signup, never opt-out, never "it's public anyway"
- The brief is shown only with **separate** consent. It is more sensitive than the output
- We host a copy, not their live URL — theirs can change or disappear and take our showcase with it
- Six pieces minimum at launch. Fewer looks like we have three customers
- Seeded with our own work, marked as ours
- Filter by art direction from v2 — the clearest way to show range

Every piece is commercial launch work. No travel decks, no thesis defences ([principles.md](principles.md), principle 2).

---

## Pricing

**The paywall is on publishing, not generating.**

Let people generate and see the quality; charge when they need the URL. This inverts the usual AI-product paywall on purpose: quality is our entire argument, and putting our argument behind a credit card is backwards. It also matches where the value actually lands — a marketer's deliverable is a link they can send, not a file they made.

| Decision | |
|---|---|
| Generating | Free within a quota, which fails closed and says so ([../../AGENTS.md](../../AGENTS.md), rule 10) |
| Publishing | Paid |
| Card | At publish, not at signup |
| Structure | Seats with a generous generation allowance. Marketers cannot forecast usage and hate metering |
| Credits | Avoided entirely if possible. Opaque balances are the most-complained-about pattern in AI pricing |
| Trial shape | Reverse trial — full product for 14 days, no card, then a restricted plan that **keeps published pages alive** |
| Lapsed plans | Published pages never die. Killing a customer's live launch page is a lawsuit and a thread. Restore the badge instead |
| Prices | Published. All of them, on the nav |

The *numbers* stay deferred until token cost is measurable ([../v1/spec.md](../v1/spec.md)). The page shape does not depend on them.

**Cost exposure, named:** free generation with a paid publish means we pay for output that never converts. That is the deliberate trade, and it is bounded by three things already in the plan — per-user quota, the atomic quota check, and the kill switch ([../v1/plan/06-model-seam-and-build.md](../v1/plan/06-model-seam-and-build.md)). Watch generations-per-publish as the health metric; if it climbs, the quota moves, not the paywall.

---

## Proof

| | |
|---|---|
| Customer logos | None until there are customers who agreed |
| Testimonials | Real, named, role and company. Zero generated avatars |
| Numbers | Only what the analytics beacon actually measures ([../techstack/frontend.md](../techstack/frontend.md)) |
| Versus Gamma | Same brief, both tools, two live URLs, both linked. Not a doctored screenshot |
| Limits | Published. No PPTX, no charts, one signature moment per experience. Naming limits early is how we survive Risk 3 ([../v1/spec.md](../v1/spec.md)) |
| The badge | Small, on published artifacts, removable on a paid tier. It is the only free acquisition loop this product has |

---

## Weight and instrumentation

Stricter budget than the artifact's — we are selling craft, on a page whose whole job is to look like we have it.

- **No third-party scripts** ([../security/third-parties.md](../security/third-parties.md)). No chat widget, no tag manager
- **One cookieless, self-hosted analytics tool** on the marketing site — and **never on published artifacts**. That guarantee is a product feature and it is enforced by CSP ([../techstack/frontend.md](../techstack/frontend.md))
- **No cookie banner**, achieved by not setting cookies. A consent dialog on a design product's homepage is a self-inflicted wound
- Fonts subset, display face preloaded
- Measure what the embedded hero artifact costs the page. It is React plus Motion, and it is the one heavy thing we accept on purpose

The metric that matters is not signups. It is **a published artifact within 24 hours of signup** ([questions.md](questions.md), §24).

---

## Connects to

| | |
|---|---|
| [brand.md](brand.md) | The identity this site spends |
| [app.md](app.md) | What happens after "Start" |
| [../v1/plan/06-model-seam-and-build.md](../v1/plan/06-model-seam-and-build.md) | Where the SSE recordings must start being kept |
| [../v1/market.md](../v1/market.md) | Who this page is for, and who it must not attract |
