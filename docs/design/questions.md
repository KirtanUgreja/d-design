# The question bank

> Every open decision about our own app and website, with a recommended default for each. **Answer by exception.**

## How to use this

Reply with numbers only — `4 page · 36 ink blue · 63 "Watch it build" · 107 publishing`. Anything you don't answer, the default stands and gets written into the design docs as a decision, marked as unconfirmed.

Defaults are opinionated on purpose. A question with no recommendation is a question that generates a meeting instead of a decision. Every default here is consistent with [principles.md](principles.md), and where a default is genuinely close, the alternative is named in the same cell.

**★ = blocking.** Fourteen of them. The other 260 can be answered late or never; these fourteen change what the other documents say.

---

## What v4 answered (2026-09-26)

The v4 re-decide ([../v4/spec.md](../v4/spec.md)) settled or overtook the questions below. The rows further down keep their original wording; where this table and a row disagree, **this table and the linked document win**. Rows that cite `v1/`, `v2/` or `v3/` paths point at documents that no longer exist.

| Questions | What v4 decided | Where |
|---|---|---|
| §2 preamble, 21, 29 | The first users are founders and salespeople, not marketers. Five deck types | [../v4/spec.md](../v4/spec.md) → Locked decisions → First users |
| 7, 71, 99, 195 | "Design family" is now a **look**: sampled per deck, generated per deck since 2026-10-05 (no picking), changed in the Design tab | [app.md](app.md) → "Pick a look"; [../v4/design-engine.md](../v4/design-engine.md) → "Sampler" |
| 23 | Superseded. The model now composes each slide's HTML; colour and type come only from the look's tokens. The public line is *the AI designs every slide inside one design system* | [../v4/spec.md](../v4/spec.md) → Locked decisions → Token rule |
| 20, 134, 135, 194 | Brand colours are asked for after the first deck exists, in the Design tab. Never in the interview | [app.md](app.md) → "First run" |
| 78 | Reversed. An edit is saved and re-measured by the backend, so an anonymous editable demo is no longer free | [website.md](website.md) → "Watch it build" |
| 138, 176, 270, 272 | The watch is one to three minutes, not forty seconds; first slides within ~90 seconds of approval | [../v4/spec.md](../v4/spec.md) → Risks |
| 141 (§7 preamble) | A deck costs roughly $1.5–3.5, not $0.20–0.40 (estimate until phase 22 measures it) | [../v4/bench.md](../v4/bench.md) → "Budgets" |
| 145–149, 153 | Answered: a composer, then one model call writing ≤5 questions with suggested answers, shown one at a time, skippable; one asks whether the deck is presented live or sent | [app.md](app.md) → §1–2; [../v4/content.md](../v4/content.md) → "Interview" |
| 150 (both), 166 | Answered: YOU / AI / WEB chips, source popovers, unsourced numbers flagged. No accounts until phase 29 | [app.md](app.md) → §2 |
| 151, 152 | Nothing is fetched and nothing is uploaded in v4; a URL on a slide is plain text. Research runs through the model gateway's search | [../v4/content.md](../v4/content.md) → "Research and the Fact ledger" |
| 159–167 | Answered as defaulted, plus inline edit and regenerate on the cards | [app.md](app.md) → §2 |
| 169–179 | Answered. Changes: slides arrive already measured; an unfixable slide arrives flagged "needs attention"; a separate worker runs the job, so a reload reconnects without gaps | [app.md](app.md) → §4 |
| 181–191, 196 | Answered: filmstrip left, scaled 16:9 canvas, Slide / Notes / Design tabs. The canvas scales uniformly, the instruction box lives in the Slide tab, undo is one snapshot per operation | [app.md](app.md) → §5 |
| 197–204 | Rewritten. Still no picker and no HTML/CSS authoring. Slide-level changes are requests; look-level changes are the Design tab. "Emphasis" is no longer a schema field | [app.md](app.md) → "The colour picker that does not exist" |
| 207, 208, 214 | Answered: two export flavours. **Present** carries speaker notes; **send** and its PDF do not | [app.md](app.md) → §6 |
| 215 | Reversed: version history is built, labelled, one version per operation | ../v4/plan/28-editor.md |
| 209–213, 216–218, 89, 102–105, 117, 118 | Not in v4. There is no hosted URL; sharing means sending the file | ../v4/plan/29-accounts-deploy.md → Skipped |
| 107–116 | Open again. v4 has no tiers or billing, and per-deck cost changed the trade | [website.md](website.md) → "Pricing" |
| 123 | Overtaken: a managed auth provider, chosen at phase 29 | [../v4/spec.md](../v4/spec.md) → Locked decisions → Auth |
| 219–230 | Answered, with new rows for a flagged slide, a broken edit and a dropped connection | [app.md](app.md) → "The states nobody designs" |
| 250 | Artefact accessibility (contrast, minimum type size) is measured by the engine | [../v4/design-engine.md](../v4/design-engine.md) → "QA metrics" |
| 256 | The hero is one HTML file, typically under 3 MB. Not React plus Motion | [website.md](website.md) → "Weight and instrumentation" |
| 259 | v4 ships the machine-readable marker in every export; the visible mark is still ours to design | [../v4/spec.md](../v4/spec.md) → Locked decisions → Export |
| 276 | Still never bend the engine for our own website | [principles.md](principles.md) → "The dogfood ladder" |

---

## §1 Name and vocabulary

The one section that must be settled in v1, because it leaks into every string, route, and doc ([principles.md](principles.md), principle 11).

| # | Question | Default |
|---|---|---|
| 1 ★ | Is `d-design` the product name, or a repo placeholder? | Placeholder. It describes the repo, not the product |
| 2 | Must the name survive the presentation→web-experience drift? | Yes. No `deck`, `slide`, `present`, or `AI` in the *name* (they are fine as descriptors of what the file is) |
| 3 | Is a matching `.com` a hard requirement? | Yes, or one clean word on `.co`. Never a hyphen |
| 4 ★ | What do we call the thing it makes, in the UI? | A **deck**. It is what the user actually has — a deck, in a file, presented slide by slide |
| 5 | What do we call a slide in the UI? | Slide. It is honest, it is what the user presents, and the old "never say slide" rule died with the old product |
| 6 | Do we ever use the word "slide"? | Yes, freely. The product is a deck of slides, presented |
| 7 | Is "art direction" user-facing? | No. It is the *design family*, and the user-facing concept is "a design system for your deck." Teaching the buyer that two decks never look alike is most of the sale |
| 8 | Does "AI" appear in the headline? | No. Everyone says it, so it says nothing |
| 9 | The verb for generating? | "Generate". Honest and expected. Do not invent a cute verb |
| 10 | Does the AI have a persona or a name? | No. Personas invite chat, and this is not a chat product |
| 11 | Voice: do we say "we"? | No. Second person, imperative, short sentences, one opinion per paragraph |
| 12 | Do we use "beautiful" as a claim word? | No. Show it. Claiming it is what template tools do |

---

## §2 Positioning and the promise

Constrained by `v1/spec.md` — the wedge is locked (a marketer with a launch in three weeks), only its expression is open.

| # | Question | Default |
|---|---|---|
| 13 ★ | The one-sentence promise? | Something in the shape of *"Your launch messaging, designed into a deck you can download and present offline."* Needs your voice, not mine |
| 14 | Which category do we claim? | AI-designed decks. The offline single-file artefact is the differentiator, not the category |
| 15 | Do we name Gamma on the homepage? | No. On one comparison page, yes |
| 16 | Do we admit Framer and Webflow are the real comparison set? | No — those are website builders. Gamma, Canva, and Beautiful.ai are the deck-tool comparison set |
| 17 | Lead with speed or with quality? | Quality. Speed is table stakes since Gamma; quality is the wedge |
| 18 | Lead with beauty or with "runs offline"? | Beauty. Offline is the objection-answer; the beauty is the reason to care |
| 19 | Do we say "no design skills needed"? | No. That sentence recruits the audience that killed Tome |
| 20 | Do we promise on-brand output? | Yes, prominently. Marketers cannot ship off-brand (`v1/spec.md`) |
| 21 | Does the headline name a job or a deadline? | Yes. "Launch in three weeks" is a better qualifier than any form field |
| 22 | Do we say "no templates"? | Yes. Sharpest two words we have |
| 23 | Do we explain publicly that the AI never writes styling? | **Superseded in v4 → [../v4/spec.md](../v4/spec.md) (Token rule).** Was: Yes, as a feature — *the AI writes the story, a design system does the styling*. It is why the output does not look generated |
| 24 | Do we publish a point-of-view essay? | One, at v3 launch. It is how designers hear about this without being sold to |

---

## §3 Who we deliberately repel

Principle 2. This section is the one most likely to feel wrong and be right.

| # | Question | Default |
|---|---|---|
| 25 | Free-forever tier? | No. Trial, then paid. Free-forever recruits exactly the wrong cohort |
| 26 | Do we ever show non-commercial examples? | Never. No travel decks, no thesis defences, no wedding invites |
| 27 | Do we optimise for a Product Hunt launch? | No. It is a Tome-audience channel. Ship it, do not build for it |
| 28 | Do we court designers as users? | No. Court them as an audience for the POV essay — they are the credibility layer, not the buyer |
| 29 | Are example prompts generic? | No. Every example prompt in the product is a real launch brief |
| 30 | Is price a filter? | Yes. The entry tier should be obviously a business expense |
| 31 | Waitlist with a qualifying question? | Yes, exactly one: *what are you launching, and when?* It qualifies and it becomes their first brief |
| 32 | Should the site feel hostile to tyre-kickers? | Not hostile. Uninteresting. Different thing, better outcome |

---

## §4 Our brand identity

Principle 9: our surfaces are the gallery wall, the output is the art. Every default here follows from that plus principle 5.

| # | Question | Default |
|---|---|---|
| 33 ★ | Light or dark for our own surfaces? | **Light / warm neutral.** A dark, glowing site is one step from the banned list, and it makes a dark artifact read as theme rather than work |
| 34 | Is the editor chrome light too? | Yes. A light frame around a dark-family deck is a gallery frame. Re-check when v2 grows the registry with light families |
| 35 | How many accent colours? | One, used for almost nothing — focus rings and the primary action |
| 36 ★ | Which accent family? | Not purple, not pink, not neon, not a gradient. Recommend a deep ink or an oxide red. Your call decides the whole palette |
| 37 | Display typeface? | A licensed editorial face with real character. Not Inter, not Geist, not a variable grotesk at default tracking |
| 38 | Do we buy type for our own brand? | Yes. [../techstack/frontend.md](../techstack/frontend.md) already calls type the highest-leverage money in the product. This is the cheapest possible way to not look default |
| 39 | Can our brand share a face with a design family? | No. Our chrome must be visibly not-the-product |
| 40 | Logo: wordmark or mark? | Wordmark only. A mark is a v3 problem and usually a distraction before then |
| 41 | Do we have a motion signature? | Yes, and it is restraint. Our chrome barely moves; the canvas moves |
| 42 | Layout system? | Asymmetric, with a real baseline rhythm. Five centred `max-w-3xl` sections is the banned pattern |
| 43 | Stock photography? | None, ever. Only real output and real screenshots |
| 44 | Illustration? | None. Illustration is where "friendly AI product" lives |
| 45 | Corner radius? | Small and consistent. `rounded-2xl` everywhere is a tell |
| 46 | Borders or shadows for separation? | Hairline borders. Layered shadows read as template |
| 47 | Favicon and OG image? | A crop of real output. Not a logo on a gradient |
| 48 | Public brand or design-system page? | No. Not before v3, possibly never |

---

## §5 Marketing site structure

| # | Question | Default |
|---|---|---|
| 49 | Page inventory? | Home, showcase, one comparison, pricing, docs, changelog, one essay, legal. Eight |
| 50 | One long homepage or many? | One long homepage plus showcase. Everything else is support |
| 51 | Sticky nav? | Minimal, and it gets out of the way over the embedded artifact |
| 52 | Blog? | No. A changelog instead, until there is something real to say |
| 53 | Public docs? | Yes at v3, small |
| 54 | Comparison pages for SEO? | Three at most, and honest about where we lose. Dishonest ones lose the buyer we want |
| 55 | Footer? | Minimal. A fat sitemap footer on an eight-page site is theatre |
| 56 | An "for agencies" page? | No, through v3 |
| 57 | Careers page? | No |
| 58 | Status page? | v3, when someone else's launch depends on our uptime |

---

## §6 The hero

Principle 6: show the artifact, not the app.

| # | Question | Default |
|---|---|---|
| 59 ★ | What is the hero? | A **real published artifact, live in the page**, scrolling and animating as a recipient sees it. Static on a CDN, so it costs nothing |
| 60 | Does it move on load? | It animates on scroll, like the real thing. Nothing autoplays, nothing has sound |
| 61 | Whose work is it? | Ours first — our own launch, generated by the product. Customer work from v3 |
| 62 | Headline above it, or is the artifact the headline? | Short headline above, artifact starting at the fold. Do not make people guess what they are looking at |
| 63 ★ | Primary CTA copy? | "Watch it build" → the recorded generation. "Start" is secondary. The demo converts better than the signup |
| 64 | Do we show the prompt that produced it? | Yes. Prompt and output in one screen is the entire pitch with no copy at all |
| 65 | Scroll-jacking? | Never. It is an accessibility failure and it reads as a 2019 agency site |
| 66 | Can you open the hero artifact fullscreen? | Yes, one click to its real URL. It should be provable, not a mockup |
| 67 | Mobile hero? | The same artifact. Artifacts are responsive by definition, and that is worth demonstrating |
| 68 | Time-to-first-output-pixel budget? | Under 1.5s on 4G. The proof cannot arrive late |
| 69 | Browser chrome frame around it? | No. Banned pattern. One line of text showing the URL is enough |
| 70 | A/B test the hero? | Not before there is v3 traffic to test with |
| 71 | Does the hero rotate design families? | From v2, yes — same content, different design family, on a control. That is the abstraction claim demonstrated in four seconds |
| 72 | JS disabled? | Already handled: artifacts are progressively enhanced ([../techstack/frontend.md](../techstack/frontend.md)) |

---

## §7 The demo

Principle 7. The constraint that makes this section interesting: a real generation costs ~$0.20–0.40 and takes tens of seconds.

| # | Question | Default |
|---|---|---|
| 73 ★ | Recorded-generation replay on the homepage? | Yes. Capture a real SSE event log once and replay it client-side. It is indistinguishable from live because it is the same event stream |
| 74 | Real-time or compressed? | Real time, with a skip control. The honest forty seconds *is* the product |
| 75 | Do we label it a recording? | Yes, plainly. Principle 10, and the label costs nothing because the scenes are genuinely generated |
| 76 | Anonymous live generation, ever? | No through v3. Revisit only with a hard per-IP cap, a kill switch, and a bill alarm |
| 77 | A playground with pre-baked briefs? | Yes at v3 — pick one of three briefs, watch its recorded run. Three recordings, zero marginal cost |
| 78 ★ | Can a visitor edit the demo deck without an account? | **Reversed in v4 → [website.md](website.md).** Was: **Yes (v2).** Editor edits are local patches with no model call (`docs/v2/plan/12-editor.md`). Letting someone change real copy on a real deck, in the browser, for free, is the strongest thing we can offer and it costs nothing |
| 79 | Does the free demo include an AI edit? | No. That is a model call. Show a recorded one |
| 80 | Do we demo the outline gate? | Yes. It is the trust feature, and no competitor has one |
| 81 | Do we demo the generation watch? | Yes, quietly — it is the wow moment |
| 82 | Third-party interactive-demo tooling? | No. Our product is the demo. A Guideflow tour of a design product is an admission |
| 83 | A video? | One 60-second film, muted, captioned, click-to-play |
| 84 | GIFs? | No. Weight, and they make good design look bad |

---

## §8 Proof and credibility

| # | Question | Default |
|---|---|---|
| 85 | Customer logos? | None until there are customers who agreed. Principle 10 |
| 86 | Testimonials? | Real, named, with role and company. Zero generated avatars |
| 87 | Case study format? | Brief in, artifact out, one number if there is one. Not a narrative |
| 88 | Which metrics can we claim? | Only what we can actually measure. In v1 the deck is offline (`connect-src 'none'`) — there is no beacon. Analytics on a hosted deck is a v3 question, and it must not break the zero-network guarantee ([../techstack/frontend.md](../techstack/frontend.md)) |
| 89 | A "made with" badge on published artifacts? | Yes, small, removable on a paid tier. It is the only free acquisition loop this product has — and it shares its space with a legally required disclosure, so design them as one mark ([website.md](website.md)) |
| 90 | Side-by-side against Gamma? | Yes, but as two live decks, not a doctored screenshot. Same brief, both tools, both linked |
| 91 | Do we publish what the product cannot do? | Yes. In v1: no PPTX, no hosted URL, no editor (it is v2). Naming limits early is how we survive the "give me a link" objection |
| 92 | A security page? | Yes at v3. We have unusually good material for one |
| 93 | Do we disclose AI use on artifacts? | Yes, and it is not optional — `docs/v3/spec.md` |
| 94 | Do we say who built it? | Yes. Solo and opinionated is an asset with this buyer, not a liability |
| 95 | Do we talk about the stack? | Only in the essay. Buyers do not care and it invites the wrong audience |
| 96 | Do we show the eval numbers? | Not publicly. Repair rate is an internal instrument ([../techstack/ai-stack.md](../techstack/ai-stack.md)) |

---

## §9 Gallery and showcase

The sharpest constraint in this section is not design: **a brief is a customer's unreleased launch messaging under embargo** ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)).

| # | Question | Default |
|---|---|---|
| 97 ★ | How does work enter the showcase? | Explicit written per-artifact release, after their launch is public. Never a checkbox at signup, never opt-out |
| 98 | Do we show the brief next to the artifact? | Only with separate consent. The interview is more sensitive than the output |
| 99 | Filter by design family? | From v2, yes. It is the clearest way to show range |
| 100 | Minimum pieces to launch a showcase? | Six. Fewer looks like we have three customers |
| 101 | Do we seed it with our own work? | Yes, marked as ours. Honesty costs nothing and the work is real |
| 102 | Can a visitor fork a showcase piece? | v3, and only into their own account with their own copy |
| 103 | Do hosted decks link back to us? | Only via the badge. No injected backlinks |
| 104 | Is the badge removable? | On a paid tier, yes. Trapping a marketer's client work behind our logo loses the account. **The AI-content disclosure in the same mark is not removable** (`docs/v3/spec.md`) — one boolean, two very different meanings |
| 105 | Are showcase pieces the live customer URL or a copy? | A copy we host. Their URL can change or go down and take our showcase with it |
| 106 | Do we ever showcase without asking because it is public anyway? | No. Public does not mean endorsed, and this buyer talks to other buyers |

---

## §10 Pricing

`v1/spec.md` defers the *price*, not the page. These decide the page.

| # | Question | Default |
|---|---|---|
| 107 ★ | What is behind the paywall — generating, or publishing? | **Publishing (v3).** Let them generate and see the quality; charge when they need the hosted URL or the team. The single-file download is the free wow; the URL is the paid convenience. It inverts the usual AI-product paywall and it is the single highest-leverage pricing decision here |
| 108 | Seats or usage? | Seats, with a generous generation allowance. Marketers cannot forecast usage and hate metering |
| 109 | Credits UI? | Avoid credits entirely if possible. Opaque credit balances are the most-complained-about pattern in AI pricing |
| 110 | Do we show the AI cost honestly? | Not on the pricing page. Internally it decides the tiers (`docs/v1/spec.md`) |
| 111 | Free tier? | **Narrower than it sounds, and already locked in `v3/spec.md`:** free is generate, edit, preview, and download; one hosted URL with the badge is the paid entry. Not free-forever unlimited. The reverse trial sits on top — full features for 14 days, then that restricted plan |
| 112 | Why a reverse trial? | It converts comparably to a free trial with freemium's signup volume, and AI-native products convert notably better on this shape than general SaaS |
| 113 | Card up front? | No. Card at the hosted URL (v3). Consistent with 107 |
| 114 | Annual discount? | Two months. Standard, not a differentiator |
| 115 | Enterprise "contact us"? | Not before v3. It is a tier for a sales motion we do not have |
| 116 | What happens at the limit? | Fails closed and says so plainly. Rule 10 in [../../AGENTS.md](../../AGENTS.md) |
| 117 | Do hosted decks die when a plan lapses? | No. Killing a customer's live launch URL is a lawsuit and a Twitter thread. Downgrade the badge, keep the deck |
| 118 | Custom domain — which tier? | The top self-serve tier, v3 |
| 119 | Is pricing on the nav? | Yes. Hiding pricing signals enterprise sales and repels self-serve |
| 120 | Do we publish prices at all? | Yes. Every one of them |

---

## §11 Front door, signup, account

All v3 ([../techstack/backend.md](../techstack/backend.md)).

| # | Question | Default |
|---|---|---|
| 121 | Waitlist before v3? | Yes, with the one qualifying question from #31 |
| 122 | Invite codes? | Yes for the first cohort. Scarcity aimed at the right people is qualification, not growth hacking |
| 123 | Auth method? | Email link plus Google. No passwords |
| 124 | SSO? | Not before an enterprise tier exists |
| 125 | Onboarding questions at signup? | Exactly one, and it is the brief. Gamma asks industry and use case; we ask what they are launching and generate from it |
| 126 | Do we ask industry or role? | No. It is analytics dressed as onboarding |
| 127 | Email verification before first generation? | Yes. It is the cheapest abuse control we have |
| 128 | Team accounts? | v3, single-tenant per user first ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)) |
| 129 | Abandoned-signup email? | One, with their own generated artifact in it. Nothing else converts as well as their own work |
| 130 | Can you delete your account yourself? | Yes, and it deletes the artifacts. Compliance, and it is trust-building to say so |

---

## §12 First run

Research floor: median self-serve time-to-value is ~11 minutes, top performers under 5, and activation before 14 days is the strongest retention predictor there is. Ours should be **under 90 seconds** because we know what they are launching before they arrive.

| # | Question | Default |
|---|---|---|
| 131 ★ | What is on screen at second zero? | Their waitlist answer, already in the prompt box, cursor at the end. Not an empty state, not a tour |
| 132 | Empty prompt or example briefs? | Pre-filled from #125 where we have it, three real launch briefs where we do not |
| 133 | Is there a product tour? | No. A tour is what you build when the first screen failed |
| 134 | Do we force the brand kit first? | No. Wow first, brand second. Asking for six brand fields before anything happens is how you lose the session |
| 135 | When do we ask for the brand kit? | Immediately after the first artifact exists, framed as *make this yours* |
| 136 | When do we ask for assets? | When a scene visibly wants one, in place, not in a setup step |
| 137 | What is the aha moment, exactly? | Their own words appearing in a designed scene that they did not lay out. It is not the URL — that comes later |
| 138 | Time-to-first-artifact budget? | 90 seconds from landing, including the generation |
| 139 | Is there a sample project in a new account? | Yes, one real artifact they can open and break. It teaches the editor with no risk |
| 140 | Do we show cost or quota in the first session? | No. Nothing about limits until they have succeeded once |
| 141 | What if the first generation is bad? | One prominent control: *try a different direction*. Retry has to be one click and obviously free |
| 142 | Do we set expectations before generating? | Yes — a range, and what will happen at the outline gate |
| 143 | What is the second session's first screen? | Their work, not a dashboard. A list of one artifact is not a dashboard |
| 144 | Do we email the first artifact to them? | Yes. It is their proof and our best re-engagement asset |

---

## §13 Intake

The app's front door (`docs/v1/plan/02-interview.md`). Import is deferred, so v1 is prompt plus AI-led Q&A.

| # | Question | Default |
|---|---|---|
| 145 ★ | Prompt box, guided Q&A, or a form? | **Answered in v4 → [app.md](app.md) §1–2.** Prompt box first, then a **short structured interview** — not a chat. Chat implies memory and invites off-task use |
| 146 | How many questions does the AI ask? | Three to five, with visible progress. Never open-ended, never more than five |
| 147 | Can you skip straight to generate? | Yes, always. The interview improves output; it must not gate it |
| 148 | Does it look like a chat UI? | No. Bubbles set chat expectations we will not meet, and a chat log is not an interview |
| 149 ★ | Does the interview stay visible and editable? | Yes, permanently. It is the approved-claims record, and Risk 2 in `v1/spec.md` is about invented claims |
| 150 | Can a visitor generate without an account? | In v1 there are no accounts — the flow is open. A hosted editor with auth is v3 |
| 150 | Do we show which claims came from them versus the model? | Yes. This is the trust feature marketers will actually talk about |
| 151 | URL paste? | Allowed as CTA destinations only. Nothing is fetched in v1 — a URL the user types is a string, not a request |
| 152 | File upload for source material? | Deferred to v3 (brand-kit upload). Do not build the UI for it now |
| 153 | Paste-a-document textarea? | Allowed. It is just text and it needs no fetch worker |
| 154 | Character limits on the prompt? | Yes, generous and visible. Caps are already a schema concern (`docs/v1/plan/01-schema.md`) |
| 155 | Autosave the interview? | Yes, continuously |
| 156 | Start from an existing deck? | Yes, v3. It is how a customer makes their second one |
| 157 | Templates or starting points? | No. "No templates" is our positioning; a template picker contradicts the homepage |
| 158 | Voice input? | No |

---

## §14 The outline gate

The human approval step (`v1/plan/02-interview.md`). Nobody else in this category has one, so there is no convention to follow.

| # | Question | Default |
|---|---|---|
| 159 | How is the outline presented? | Slide cards with their intent label and the headline. Not a bulleted list — it should already feel spatial |
| 160 | Can you reorder slides? | Yes, drag. The outline's structure is what it is; reordering does not make the content a lie |
| 161 | Add and delete slides? | Yes, both |
| 162 | Edit copy at the outline stage? | Yes. Fixing a headline here is far cheaper than after the build |
| 163 | Show estimated time or cost? | Time as a range. Never a fake percentage |
| 164 | One-click approve? | Yes, and it is the primary action on the screen |
| 165 | Regenerate the outline? | Yes, cheap and prominent. That is the entire reason the gate exists before the expensive call |
| 166 | Do we show claim provenance here? | Yes. This is the correct gate for Risk 2, not the editor |
| 167 | Can experienced users skip the gate? | No in v1. It is simultaneously the cost control, the quality control and the trust device |
| 168 | What if they approve a bad outline? | They will blame the build. Make the gate feel consequential — this is a copywriting problem, not a UI one |

---

## §15 The generation watch

Principle 3 names this the highest-leverage motion design in the app. It is forty seconds long and it is what people will describe to a colleague.

| # | Question | Default |
|---|---|---|
| 169 ★ | What is on screen while it builds? | **Answered in v4 → [app.md](app.md) §4.** **The slides themselves, full size, appearing in place as they arrive.** Not a progress bar next to a spinner. The SSE stream already delivers whole validated slides ([../techstack/frontend.md](../techstack/frontend.md)) |
| 170 | Is the outline visible ahead of the build? | Yes, ghosted. Watching known slots fill is dramatically better than watching an unknown list grow |
| 171 | How does each slide arrive? | With the deck's own design-family motion, not chrome animation. The reveal you watch is the reveal your audience gets. A slide with an image arrives with its image |
| 172 | Do we surface repairs? | No. The `repair` event is instrumentation (`docs/v1/spec.md`). Showing users a self-correction is honesty nobody asked for and it undermines the moment |
| 173 | Abort control? | Yes, prominent. Aborting a bad direction early is the stated reason streaming exists |
| 174 | Failure at slide 6 of 8? | Keep the five, offer to continue. Never discard completed work |
| 175 | Sound? | No |
| 176 | Time estimate? | A range that does not lie. No percentage that stalls at 90% |
| 177 | Can they leave the page? | Yes, and it resumes. Generation is server-side |
| 178 | Fake progress steps like "writing headline"? | No. Real phase labels only. Invented steps are the most common slop pattern in AI UI |
| 179 | Does the first slide need to be special? | Yes. It is the single most important frame in the product. Budget time for it specifically |
| 180 | Mobile? | Watch works, editing does not. See #193 |

---

## §16 Editor chrome

Principle 4: quiet, because it surrounds the thing that is supposed to be beautiful.

| # | Question | Default |
|---|---|---|
| 181 | Layout? | Outline left, canvas centre, properties right. Boring on purpose |
| 182 | Does the canvas render at true scale? | Yes. What you edit is byte-for-byte what you export, and any scaling weakens that |
| 183 | Zoom control? | Fit-width and 100%. Nothing more |
| 184 | Selection affordance? | A hairline and a label. Not a saturated blue box over a designed page |
| 185 | Where does the element-scoped prompt live? | Inline, directly under the selected block, always in the same place. It is a primary interaction, not a panel tab |
| 186 | Is the AI edit input always visible? | Only with a selection. An always-present prompt box invites page-level requests we cannot serve |
| 187 | Undo affordance? | Visible and labelled, not just a shortcut. It is what makes AI edits safe to try ([../techstack/frontend.md](../techstack/frontend.md)) |
| 188 | Keyboard shortcuts? | Undo, redo, select, escape, present. Not a whole system |
| 189 | Autosave indicator? | Quiet, and honest about failures |
| 190 | Present/preview toggle? | Yes, and it is real fullscreen with arrow keys — the thing that keeps the word "presentation" honest |
| 191 | Slide navigator? | The outline panel doubles as it. Do not build two |
| 192 | Dark editor option? | Not in v2. One good frame beats two mediocre ones |
| 193 | Mobile editor? | View and present only. Editing a design surface on a phone is a different product |
| 194 | Where does the brand kit live? | One click from the canvas, not buried in settings. It is a v1 primitive |
| 195 | Where does the design-family switcher live? | v2. Reserve the space now so it does not get retrofitted into a menu |
| 196 | Where does export live? | Top right, always, and it is the only high-emphasis control in the chrome. The download is the primary action |

---

## §17 The colour picker that does not exist

Principle 8. The most important ten questions in this document, because this is where a first-time user decides whether this is a tool or a toy.

| # | Question | Default |
|---|---|---|
| 197 ★ | What happens when a user goes looking for styling controls? | **Answered in v4 → [app.md](app.md), "The colour picker that does not exist".** They get a designed, positive answer **at the moment of reaching** — inline, once, in the panel where they expected the control. Not a docs page, not a tooltip, not a tour |
| 198 | What is the copy? | Something in the shape of *"Type, colour and spacing come from the design family, so this cannot go off-brand. Change the family, not the pixel."* Needs your voice |
| 199 | What replaces the picker? | Four visible affordances: design family, emphasis level, brand kit, reroll. They must look more powerful than what they replace, because they are |
| 200 | Do we teach "emphasis" as the replacement vocabulary? | Yes. It is intent, it is in the schema, and it is the concept that makes the constraint learnable |
| 201 | Can power users see the resolved tokens? | Yes, read-only. Seeing the system is disarming; editing it is the whole product's collapse |
| 202 | What if they type "make the headline smaller" into the AI edit? | The model has no field for it, so it must **refuse well** and offer emphasis instead. That refusal copy is a designed artifact, not an error string |
| 203 | Is there ever an escape hatch? | No. The v1 artefact is the generated HTML file, and it is not hand-editable — hand-editing is how the design family stops being the single source of visual truth |
| 204 | CSS or HTML authoring? | No. The download is the point, not the canvas. It is the fastest route to becoming a worse Webflow |
| 205 | Do we call it a constraint publicly? | Yes, and we lead with it. A constraint you hide is a limitation; a constraint you explain is a philosophy |
| 206 | Do we measure reaching-for-the-picker? | Yes — see #273. It is the best single signal in the product |

---

## §18 Export, and the hosted URL (v3)

| # | Question | Default |
|---|---|---|
| 207 | Is the export moment designed? | Yes. It is one of the three hot surfaces, and it is what gets screenshotted into Slack |
| 208 | What does the reveal show? | **Answered in v4 → [app.md](app.md) §6** (two flavours: present with notes, send without). Was: The **download** — one self-contained `.html` file — large and prominent, with the deck preview behind it. One click to download, one to present, one to send. The hosted URL is v3 |
| 209 | OG image for hosted decks? | Auto-screenshot (v3). Playwright is already in the stack ([../techstack/frontend.md](../techstack/frontend.md)) |
| 210 | Password protection? | v3. Launch material is under embargo more often than not |
| 211 | Embed dialog? | v3, with the hosted URL. One snippet, copy button, nothing configurable |
| 212 | Custom domain? | v3, top self-serve tier |
| 213 | Unpublish? | v3. Instant, and it really removes the URL |
| 214 | Re-export after edits? | Explicit. A downloaded file never changes under you; a new generation is a new file |
| 215 | Version history? | **Reversed in v4 → ../v4/plan/28-editor.md:** built, one labelled version per operation |
| 216 | Slack and LinkedIn preview quality? | v3, when the URL exists. Treat as a launch requirement — a bad unfurl on the buyer's own share is a product failure |
| 217 | QR code for in-person? | Cheap, and marketers at events will use it. Low priority, high delight |
| 218 | Analytics summary? | v3, if a beacon can exist without breaking the zero-network guarantee. It is a thing we sell, not a thing we bolt on |

---

## §19 Empty, error, limit and refusal states

Twelve screens nobody designs and everybody sees. Rule 10 in [../../AGENTS.md](../../AGENTS.md) governs all of them: **anything that grants, fails closed** — and a closed failure still needs human copy.

| # | Question | Default |
|---|---|---|
| 219 | Quota exceeded? | Says what ran out, when it resets, and what still works. Never a raw 429 |
| 220 | The model refused? | Plain language, no apology theatre, and an actionable next step |
| 221 | Generation failed entirely? | Keep the interview and the outline. Retrying must not mean re-typing |
| 222 | Upload rejected? | Each brand-kit control needs its own human sentence (v3, `docs/v3/plan/17-brand-kit-at-scale.md`). "Invalid file" is not one |
| 223 | Do we ever show internal error classes? | Never. They are logged, not displayed ([../security/operations.md](../security/operations.md)) |
| 224 | Offline? | The editor (v2) holds state and says so. The deck itself is offline by design — the editor is not |
| 225 | Session expired mid-edit? | Preserve the tree, re-auth in place |
| 226 | 404 on a removed hosted deck? | v3. A designed page — it is a page a customer's audience will hit |
| 227 | Kill switch active? | An honest maintenance state on the generation path only. Export and the editor keep working |
| 228 | Rate limited? | Same shape as quota. Never silent |
| 229 | A slide fails validation after an edit? | Reject the patch, keep the previous deck, say which rule (`v2/plan/12-editor.md`) |
| 230 | Zero-state of the artifact list? | One sentence and the prompt box. Not an illustration of an empty box |

---

## §20 Motion and sound in our own chrome

| # | Question | Default |
|---|---|---|
| 231 | How much does our chrome move? | Almost not at all. Principle 4 |
| 232 | Duration ceiling for chrome transitions? | Fast enough to feel like response, not animation |
| 233 | `prefers-reduced-motion` on our own surfaces? | Respected everywhere, including marketing. We already require it for output |
| 234 | View Transitions for page changes? | Available in React 19.2, and not a reason to use them. Restraint |
| 235 | Loading: skeletons or spinners? | Neither where possible. The generation watch shows real content instead |
| 236 | Sound anywhere? | No |
| 237 | Scroll-triggered reveals on marketing? | Minimal, and never from `opacity: 0` — same progressive-enhancement floor as the artifact |
| 238 | One signature motion moment on the site? | Yes: the recorded build. Nothing else needs to move |
| 239 | Cursor effects, trails, magnetic buttons? | Banned |
| 240 | Parallax? | No |

---

## §21 Accessibility and internationalisation of our chrome

| # | Question | Default |
|---|---|---|
| 241 | WCAG target? | AA, and it is not negotiable for a product whose output is public web pages |
| 242 | Is the editor keyboard-complete? | Yes. Radix gives most of it ([../techstack/frontend.md](../techstack/frontend.md)) |
| 243 | Visible focus? | Everywhere, and it is one of the two jobs of the accent colour |
| 244 | What does a screen reader announce on the canvas? | Genuinely open. Default: the canvas is a document, announced structurally, with selection as an application region. Worth real research |
| 245 | Editor at 200% zoom? | Must work. Panels collapse, canvas stays true-scale |
| 246 | Logical properties in our chrome too? | Yes. Free now, and it makes a future RTL UI a `dir` attribute |
| 247 | UI language? | English through v3. The *output* is multilingual long before the chrome is |
| 248 | Contrast of the accent? | Must pass at its smallest use, not its largest |
| 249 | Motion preferences in the editor? | Respected — including in the generation watch, which is the hardest one to get right |
| 250 | Is artifact accessibility this directory's problem? | No. It belongs to the design family registry and the renderer (`docs/v1/plan/06-renderer.md`). Do not duplicate the rules here |

---

## §22 Performance and weight of our own site

| # | Question | Default |
|---|---|---|
| 251 | Performance budget for the marketing site? | Stricter than the artifact's. We are selling craft |
| 252 | Analytics on our marketing site? | One cookieless, self-hosted tool. **Never on a deck** — the zero-network guarantee is a product feature ([../techstack/frontend.md](../techstack/frontend.md)) |
| 253 | Cookie banner? | Avoid by not setting cookies. A cookie banner on a design product's homepage is a self-inflicted wound |
| 254 | Third-party scripts? | None. [../security/third-parties.md](../security/third-parties.md) |
| 255 | Font loading? | Subset, preload the display face, `font-display: swap` |
| 256 | What does the embedded hero artifact cost the page? | Measure it explicitly. It is React plus Motion, and it is the one heavy thing we accept |
| 257 | LCP target? | The artifact's first frame, under 1.5s on 4G |
| 258 | Do we ship a chat widget? | No |

---

## §23 Trust, legal and AI disclosure

| # | Question | Default |
|---|---|---|
| 259 | Where does AI disclosure appear on decks? | Designed into the footer of the deck, not bolted on. The EU AI Act has been in force since 2 August 2026 (`v3/spec.md`) |
| 260 | Who owns making it not ugly? | This directory. A compliance element designed by a lawyer is how the whole deck loses its finish |
| 261 | Do we promise not to train on customer content? | Yes, prominently. It is a headline-level trust claim with this buyer |
| 262 | Do we say briefs are treated as embargoed? | Yes, and in those words. It is true ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)) and no competitor says it |
| 263 | Privacy policy tone? | Readable. It is a design surface |
| 264 | Subprocessor list public? | Yes at v3 |
| 265 | DPA available? | v3 |
| 266 | Self-serve data deletion? | Yes, and it deletes artifacts too |
| 267 | Where does trust material live in the IA? | One page, linked from the footer and from pricing |
| 268 | Do we disclose which model vendor? | No. There is no preferred vendor by design ([../techstack/ai-stack.md](../techstack/ai-stack.md)), and naming one creates an expectation we will break |

---

## §24 Measurement and the dogfood ladder

| # | Question | Default |
|---|---|---|
| 269 | The single activation metric? | **A deck exported within 24 hours of signup.** Not signups, not generations |
| 270 | Time-to-value target? | Under 90 seconds to first deck, under 24 hours to first export |
| 271 | Do we track the outline-gate approval rate? | Yes. A low rate means the interview is bad; a rate near 100% means the gate is theatre |
| 272 | Do we track abandonment during the generation watch? | Yes, by second. It tells us whether forty seconds is actually tolerable |
| 273 | Do we track reaching for a styling control? | Yes — every time a user hunts for a colour or size control. It is the best single signal for principle 8 and the cheapest to instrument |
| 274 | Session recordings? | No. We hold embargoed launch messaging; recording sessions over it is indefensible |
| 275 | NPS? | No. Ask the one question that matters: did you send it to anyone |
| 276 | When does our own site become product output? | Hero at v3, showcase at v3, whole site only if it happens without adding a primitive to the schema. **Never bend the `Deck` schema for our own website** |

---

## Answered questions live here

When you answer, the decision moves into the relevant design document and this file keeps only the question and a pointer. A question bank that also stores decisions becomes two sources of truth, which is the thing [README.md](../README.md) exists to prevent.
