# The marketing site

> Designed early, built after v4's phase 29 — the first point with a URL worth giving someone ([README.md](README.md)). **Pointers updated 2026-09-26 for v4**; the decisions are unchanged unless a line says so. One thing in it must be captured much earlier, and that is the point of this document.

---

## The hero, decided

**A real published artifact, live in the page, plus a recorded generation you can watch.**

```
┌──────────────────────────────────────┐
│  headline, one line                  │
│  ▸ Watch it build      Start         │
├──────────────────────────────────────┤
│   [ REAL PUBLISHED DECK ]            │
│   advances + animates in place       │
│   ‹ › to click through it            │
│   click → opens its real URL         │
└──────────────────────────────────────┘
```

Not a screenshot, not a mockup, not a tilted browser frame with fake traffic lights. The thing itself, at the top of the page, behaving exactly as it would in a room.

**Changed 2026-08-13 with the vision re-decide.** The hero is a **real exported deck** — the single-file `.html`, presented as it would be in a room. It advances, and the visitor advances it — which is a stronger hero than a scroll, because clicking through a deck is the product's own gesture and a visitor who clicks twice has already used the product. Autoplay stays banned (principle 5); the deck sits on slide one until someone moves it.

**Why this is affordable:** the exported deck is one self-contained HTML file with a small player script and zero network requests (../v4/plan/26-player-export.md). Embedding real work costs approximately nothing per visitor and scales to any amount of traffic. The most convincing asset we have is also the cheapest one we own.

**Why it is the right proof:** the gap against Gamma is *creative ceiling*, not speed (../findings.md → "The category"), and a screenshot of an editor cannot show a ceiling. Principle 6 in [principles.md](principles.md).

Supporting decisions:

| | |
|---|---|
| Headline above, deck starting at the fold | Do not make people guess what they are looking at |
| The prompt that produced it, shown | Prompt and output in one screen is the entire pitch with no marketing copy at all |
| Click opens the real file | It must be provable. A hero you cannot open is a mockup with extra steps |
| Nothing autoplays, no sound, no scroll-jacking | [principles.md](principles.md), principle 5 |
| Same deck on mobile | The file scales its fixed 16:9 canvas to fit and takes swipe, and demonstrating that is free |
| A control that switches the look | The same deck exported in two or three generated looks, swapped in place. They are separate real files, generated once. That is the variety claim demonstrated rather than asserted ([../v4/design-engine.md](../v4/design-engine.md) → "Generated, not picked") |

**Budget: first output pixel under 1.5s on 4G.** The proof cannot arrive late.

---

## "Watch it build" — and the one thing to capture early

The primary CTA does not go to signup. It goes to a **recorded generation**: the event log of a real run ([../v4/engine.md](../v4/engine.md) → "Generation jobs and events"), captured once and replayed client-side.

It is indistinguishable from a live generation because it is the same event stream driving the same watch screen. It costs one run, ever. It never fails on stage. And it is honest: those slides really were generated, and we say plainly that it is a recording ([principles.md](principles.md), principle 10).

> **This is the early action item in an otherwise late document.** Start keeping generation event logs from the first bench run the owner scores well ([../v4/bench.md](../v4/bench.md)). Keep the good ones, versioned alongside the briefs. A log costs bytes; re-creating a run whose output you loved costs a few dollars and may not reproduce.

The alternatives were considered and are worse:

| | Why not |
|---|---|
| Live anonymous generation | A real run costs model calls and image generations, takes tens of seconds, on a public front end with no auth. That is a bill and an abuse surface with a URL ([../security/adversarial-ai.md](../security/adversarial-ai.md)) |
| Prompt box that always returns a canned result | It implies interactivity it does not have. Small lie, wrong buyer |
| A video of a generation | Compresses badly, ages, and cannot be opened in a real browser tab |
| Third-party demo tooling | A guided tour of a design product is an admission that the product cannot demonstrate itself |

**The editable deck is off the table for now** ([questions.md](questions.md), #78). **Changed 2026-09-26:** in v4 a text edit is saved by the backend and the slide is re-measured in a browser (../v4/plan/28-editor.md), so an anonymous edit is no longer free. Revisit only with the same caps a live generation would need. It is the second-page experience, not the hero, because it leads with the editor and the output is the argument.

---

## Homepage order

Eight sections. The order is the argument, and each one answers the objection the previous one creates.

| | Section | The objection it answers |
|---|---|---|
| 1 | Headline + live deck | *What is this* |
| 2 | The prompt that made it | *Did a human design that* |
| 3 | Watch it build | *Show me it wasn't hand-tuned* |
| 4 | The outline gate | *So the AI just decides everything?* — no, you approve the story before it builds |
| 5 | Editing without a colour picker | *Can I change it* — and this is where the constraint becomes the pitch ([app.md](app.md)) |
| 6 | In your colours | *Can it ship in our brand* — your colours mapped into the look, contrast held |
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
| One comparison page | Honest about where we lose. Gamma, Canva, and Beautiful.ai are the deck-tool comparison set (../findings.md → "The category"), and saying so flatters the buyer and happens to be true |
| Pricing | Below |
| Docs | Small |
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
- Filter by look — the clearest way to show range

Every piece is commercial work: pitches, sales decks, launches. No travel decks, no thesis defences ([principles.md](principles.md), principle 2).

---

## Pricing

**The paywall is on the hosted URL, not generating.**

> **Open since 2026-09-26.** v4 has no hosted URL, no tiers and no billing: all three are Skipped with triggers in ../v4/plan/29-accounts-deploy.md, and a deck now costs roughly $1.5–3.5 to generate ([../v4/spec.md](../v4/spec.md) → Bets), which makes free generation a larger bet than it was. Everything below is the design intent carried over from v3. It gets re-decided when the hosted URL's trigger fires, not before.

Let people generate and see the quality; charge when they need the URL or the team. This inverts the usual AI-product paywall on purpose: quality is our entire argument, and putting our argument behind a credit card is backwards. It also matches where the value actually lands — the deliverable is a deck they can present and a file they can send, and the URL is the convenience.

**The plan shape is not this document's to decide.** The v3 shape was: free is generate, edit, preview, and download; paid is the hosted URL, no badge, and team. No current spec locks it. This document owns how that is *presented* and the four decisions below, which the plan shape does not determine.

| Decision | |
|---|---|
| Generating | Free within a per-user budget cap, which fails closed and says so ([../coderules/README.md](../coderules/README.md), non-negotiable 10) |
| The hosted URL beyond the free one | Paid |
| Card | At the URL, not at signup |
| Structure | Seats with a generous generation allowance. Marketers cannot forecast usage and hate metering |
| Credits | Avoided entirely if possible. Opaque balances are the most-complained-about pattern in AI pricing |
| Trial shape | Reverse trial — full product for 14 days, no card, then a restricted plan |
| Lapsed plans | Hosted decks never die. Killing a customer's live launch page is a lawsuit and a thread. Restore the badge instead |
| Prices | Published. All of them, on the nav |

The *numbers* stay deferred until cost per deck is measured ([../v4/bench.md](../v4/bench.md) → "Budgets"). The page shape does not depend on them.

**Cost exposure, named:** free generation means we pay for output that never converts. That is the deliberate trade, and it is bounded by what phase 29 builds — a per-user daily budget cap, rate limits, and the kill switch (../v4/plan/29-accounts-deploy.md). Watch cost per exported deck as the health metric; if it climbs, the cap moves, not the paywall.

**And a security consequence, because this pricing shape names its own weak spot.** A free tier that generates and a paid gate on the URL is *exactly* the state machine [../security/adversarial-ai.md](../security/adversarial-ai.md) lists as the class most likely to actually get you — "the state machine that allows publish-before-payment." It has no scanner and no pattern. The defense is that the entitlement check is boring, in one place, at the data layer, and fails closed. A pricing page is a specification for an attacker as much as for a buyer.

---

## Proof

| | |
|---|---|
| Customer logos | None until there are customers who agreed |
| Testimonials | Real, named, role and company. Zero generated avatars |
| Numbers | Only what we can actually measure. The deck is offline — no beacon |
| Versus Gamma | Same brief, both tools, two live decks, both linked. Not a doctored screenshot |
| Limits | Published. In v4: no PPTX, no hosted URL, no teams, no links or icons inside a deck. Naming limits early is how we survive the "give me a link" objection |
| The badge | Small, on hosted decks (when they exist), removable on a paid tier. It is the only free acquisition loop this product has — **and it is not the only mark that deck has to carry.** See below |

### The badge and the AI disclosure are one design problem

The AI Act (in force 2 Aug 2026) requires a **machine-readable** marking of AI-generated content, and Article 50 also expects a **human-visible** disclosure, given clearly at first exposure — two layers, not one (../findings.md → Platform). v4 ships the machine-readable marker in every export ([../v4/spec.md](../v4/spec.md) → Locked decisions → Export); the visible mark is designed here.

So a hosted deck is due a "made with ⟨product⟩" badge *and* an AI-content disclosure, and designing them separately produces two small pieces of legal-looking furniture in the corner of somebody's launch page. Design them as **one mark**: provenance is what both are actually saying.

That is a better product too. "Designed by ⟨product⟩ from your brief" is a disclosure, an attribution, and an advertisement in one line, and it is the only version of a compliance obligation that a customer would ever willingly leave switched on. It is set in the deck's own look so it does not read as bolted on.

The trap to avoid: the badge is **removable on the paid tier and the disclosure is not.** Whoever builds the paid-tier toggle must not be able to remove the disclosure with it. That is a single boolean in the render path away from being a compliance defect, and it is the kind of thing found in an audit rather than in review.

---

## Weight and instrumentation

Stricter budget than the artifact's — we are selling craft, on a page whose whole job is to look like we have it.

- **No third-party scripts** ([../security/third-parties.md](../security/third-parties.md)). No chat widget, no tag manager
- **One cookieless, self-hosted analytics tool** on the marketing site. Self-hosted is the load-bearing word: a hosted analytics vendor is a **subprocessor decision**, in the same category as adding a model gateway, and it would land on the list customers' legal teams read ([../security/third-parties.md](../security/third-parties.md)). Umami is the light end of that choice — Node and Postgres next to the app, no cookies, IPs hashed in memory and discarded daily
- **No cookie banner**, achieved by not setting cookies. A consent dialog on a design product's homepage is a self-inflicted wound
- Fonts subset, display face preloaded
- Measure what the embedded hero artifact costs the page. It is one HTML file with embedded fonts and images, typically under 3 MB, and it is the one heavy thing we accept on purpose

**Our analytics never runs on a deck.** The deck is offline (`connect-src 'none'`) — there is nothing to report and nothing to embed. If a hosted-URL analytics feature ever arrives, the rule stays: the deck reports to its owner, never to us, and it must not break the zero-network guarantee. Putting our marketing tag on a customer's launch deck would be surveillance of their audience through their own asset. It is worth stating on the trust page in those words.

The metric that matters is not signups. It is **a deck exported within 24 hours of signup** ([questions.md](questions.md), §24).

---

## Connects to

| | |
|---|---|
| [brand.md](brand.md) | The identity this site spends |
| [app.md](app.md) | What happens after "Start" |
| [../v4/bench.md](../v4/bench.md) | Where the generation recordings must start being kept |
| [../v4/spec.md](../v4/spec.md) | Who this page is for, and who it must not attract |
