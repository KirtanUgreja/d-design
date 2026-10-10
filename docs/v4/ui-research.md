# v4 — UI research: attention, motivation, trust

> What the user side of the product should do to the person using it, and the evidence for each choice. Written 2026-10-05 while the engine waits on a credit top-up. [../design/app.md](../design/app.md) already specifies the screens; this document adds **why people will stay, trust it and come back**, and the line we will not cross to get there. It feeds phases 30–35 (plan/README.md).

---

## The user, the job, the feeling

**Who.** A founder or a salesperson who has to stand in front of a room soon: investors, a buyer, a partner ([spec.md](spec.md)). They are short on time, a little anxious, and they will be judged on the deck within seconds.

**The job.** *"Help me walk in with something that looks designed, says one clear thing, and that I can defend when someone asks where a number came from."*

**The feeling we are designing for, in order:**

| Moment | They should feel | Not |
|---|---|---|
| First 10 seconds | "This understands what I'm doing" | "Another blank AI box" |
| Outline gate | "That's my argument, sharper" | "It made things up" |
| The cover arriving | "Oh — that's *mine*, and it's beautiful" | "Which template is this?" |
| The watch | "It's actually working on it" | "Is it stuck?" |
| The reveal | Pride. They want to show someone | Relief that it finished |
| On stage | Calm. They know what comes next | Lost in their own slides |

The peak of the product is **their own headline set in a designed look** (the cover arriving first, in a look made for this deck). The end is **the reveal and the first time they present it**. Those two moments get the most craft, because people remember an experience by its peak and its end (below).

---

## The ethics line

Persuasion that helps the user do what they came to do is design. Persuasion that makes them do what we want instead is a dark pattern. The EU's Digital Fairness Act, expected in Q4 2026, targets exactly these — fake urgency, streaks that punish breaks, pre-ticked boxes, cancellation mazes — and a 2022 Commission study found 97% of popular sites used at least one ([sources](#sources)). We sell to people who present to skeptics; being caught manipulating them would end the product.

**Never, on any surface:**
- Fake progress, invented steps or theatrical waits ("Crafting magic…"). Already banned in [../design/app.md](../design/app.md) → the watch.
- Fake scarcity or urgency: countdowns, "only today", "3 people are viewing".
- Streaks, daily-use rewards, or anything that penalises taking a break.
- Confirmshaming ("No thanks, I like ugly slides").
- Pre-ticked consent, hidden costs, or a cancel path harder than the sign-up path.
- Push notifications or emails whose purpose is re-engagement rather than the user's own deck.
- A slower experience to look more valuable. The labor illusion (below) is used only to *show real work*, never to add delay.

**The test for any technique:** would we be comfortable if the user saw the design rationale written next to it? If not, it does not ship.

---

## The techniques, with the strength of their evidence

Evidence is graded: **strong** (replicated, field-tested), **moderate** (solid lab evidence, some limits), **mixed** (contested), **failed** (did not replicate). A technique graded mixed or failed is not a reason to build anything.

| Technique | What it says | Evidence | How we use it | Where | We measure |
|---|---|---|---|---|---|
| **First impressions in 50 ms** (Lindgaard et al., 2006) | People judge visual appeal in about 50 ms, and the judgement agrees with one made after longer looking; it then colours judgements of credibility (halo) | Strong | The first screen is the product's proof: one prompt box, real example briefs, and a real deck visible behind it. Nothing generic above the fold | Composer, landing hand-off | 5-second test: what did they think this is for? |
| **Aesthetic-usability effect** (Kurosu & Kashimura, 1995; Tractinsky) | Attractive interfaces are perceived as easier to use | Moderate | Our chrome stays quiet so the *deck* carries the beauty ([../design/principles.md](../design/principles.md) § 4). Craft budget goes to the five hot surfaces only | All hot surfaces | SUS score per phase; time-on-task |
| **Labor illusion / operational transparency** (Buell & Norton, 2011) | Showing the work being done raises perceived value — about 8% in their studies — even when the wait is longer | Strong | The watch shows the real work: the outline as ghost slots, each slide arriving rendered and measured, real phase labels. **Never added delay, never invented steps** | Generation watch | Abort rate; "felt stuck" in interviews |
| **Doherty threshold** (Doherty & Thadani, 1982) | Below ~400 ms per response people stay in flow | Strong | Every direct action in the UI (typing, a tile shuffle, a chip, reorder) answers in under 400 ms. Model work is shown as streamed progress, never a blocking spinner | All | p95 interaction latency in the browser |
| **Skeletons vs spinners** | Skeletons can feel faster for 0.4–3 s waits; studies disagree outside that window | Mixed | Ghost slots are not decoration: they are the real outline. For short waits, skeletons in the true layout; for long ones, real progress | Watch, editor thumbnails | Perceived-wait rating in tests |
| **Goal-gradient** (Hull, 1932; Kivetz et al., 2006) | Effort rises as a goal gets closer | Moderate | The flow is visibly short and finite: four steps with their names, the current one marked. The watch fills known slots, so the end is in sight | Interview, watch | Drop-off per step |
| **Endowed progress** (Nunes & Drèze, 2006) | People given a head start persist more | Moderate | Only with **real** progress: their waitlist answer or pasted notes already in the brief, interview answers pre-filled from the brief. Never a fake "2 of 10 done" | Composer, interview | Interview completion with vs without pre-fill |
| **IKEA effect** (Norton, Mochon & Ariely, 2012) | People value what they helped make | Moderate | The user makes the decisions that matter — the argument (outline gate) and the edits — and the machine does the labour, including a look made for this deck alone. The deck feels authored, not received | Outline gate, editor | "Whose deck is this?" in interviews |
| **Peak-end rule** (Kahneman et al., 1993) | An experience is remembered by its peak and its end | Strong | Peak: their headline in a look generated for them, the cover arriving first. End: a reveal worth screenshotting, and a calm first presentation. A failure is never the last thing they see | Watch, reveal, present | Post-session rating; share rate |
| **Choice overload** (Iyengar & Lepper, 2000) | More options can lower choosing and satisfaction | Mixed (meta-analyses find ~zero mean effect, but it appears when people must justify a choice) | **No style choice at all** (owner, 2026-10-05): the look is generated for the deck; a user who dislikes it asks for another, one at a time, never a gallery | Editor | *Try another look* rate |
| **Zeigarnik effect** | Unfinished tasks are remembered better | **Failed** (2025 meta-analysis of 59 studies: recall ratio 0.99) | Not used. The related Ovsiankina effect — people tend to *resume* interrupted tasks — does hold, so an unfinished deck reopens exactly where it stopped | Recent decks | Resume rate |
| **Control and reversibility** | AI output feels safe to try when it can be edited, compared and undone | Moderate (consistent across practitioner research; few controlled studies) | Every AI change arrives as a before/after to accept or discard; labelled undo; nothing replaces a slide silently ([../design/app.md](../design/app.md) → editor) | Editor | Accept rate; undo-after-accept rate |
| **Provenance as trust** | People trust a claim more when they can see its source | Moderate | YOU / WEB / AI chips, the quoted line behind every WEB number, unsourced numbers flagged until approved ([content.md](content.md)) | Outline gate, editor | Source popovers opened; numbers rejected |
| **Rehearsal reduces speaking anxiety** | Repeated, realistic practice lowers anxiety and improves delivery; notes as prompts, not scripts | Moderate | A rehearse mode: the real deck, notes, a per-slide timer against their stated minutes, a "you ran long on slide 4" summary. No AI judging their voice | Present | Rehearsals before a first presentation |

Practitioner statistics found in this research — "aha within 5 minutes means 40% better 30-day retention", "median time to first value is 9 days" — come from vendor blogs and are **direction, not evidence**. Our own targets come from our own measurements (phase 35).

---

## What competitors teach

| | What they do | Our answer |
|---|---|---|
| **Gamma** | A prompt to a deck in under two minutes; uses the generation wait to teach the editor; a four-question segmentation quiz before anything happens, with no progress shown, and an account required first | Keep the speed and the teach-while-waiting. Drop the quiz: our interview is about *this deck*, skippable, and starts from the brief typed before sign-up. Show a recorded real generation before asking for an account |
| **Beautiful.ai** | Design decisions happen invisibly; layouts keep themselves balanced | Same promise, plus the user sees and picks the look. Invisible design is impressive; chosen design is *theirs* (IKEA effect) |
| **Canva** | Hands-on control; several variations at once | We refuse the colour picker on purpose ([../design/app.md](../design/app.md) → "The colour picker that does not exist") and make that refusal the pitch: you cannot make this ugly |
| **Pitch** | Fonts and colours chosen before content | Looks are chosen after the argument exists, in the user's own words — never against lorem ipsum |

---

## Ten rules for the user side

1. **The first screen is the proof.** One prompt box, a real brief as the placeholder, a real deck behind it. Before sign-up, a recorded replay of a real generation shows the product working for $0 ([../design/principles.md](../design/principles.md) § 7); the brief they type survives a one-step sign-up.
2. **Every action answers in under 400 ms.** Model work streams; nothing blocks.
3. **Show the real work, never theatre.** Ghost slots that fill; real phase names; no invented steps; no added delay.
4. **The user decides, the machine labours.** Argument, look and edits are theirs.
5. **No style menu.** Every deck gets a look generated for it; *Try another look* gives one more, never a gallery.
6. **Design the peak and the end.** Their headline in a look; the cover first; a reveal they want to show; a calm first presentation.
7. **Every AI change is a proposal.** Before/after, accept or discard, labelled undo.
8. **Every number shows where it came from.** Unsourced numbers wait for a human.
9. **Resume exactly where they stopped.** No lost work, ever.
10. **Never manipulate.** The ethics line above is part of the gate.

---

## Sources

- Buell & Norton, *The Labor Illusion*, Management Science (2011): https://pubsonline.informs.org/doi/fpi/10.1287/mnsc.1110.1376
- Lindgaard et al. (2006), reported in Nature: https://www.nature.com/news/2006/060109/full/news060109-13.html
- Doherty threshold: https://lawsofux.com/doherty-threshold/index.md
- Skeleton screens, mixed findings: https://virtuslab.com/blog/frontend/ux-patterns-beyond-raw-performance
- Peak-end rule: https://lawsofux.com/articles/2020/peak-end-rule
- Endowed progress: https://andrewclark.super.site/papers-for-product-managers/the-endowed-progress-effect-how-artificial-advancement-increases-effort
- IKEA effect: https://atticusli.com/behavioral-science-glossary/ikea-effect-bias/
- Choice overload meta-analysis (Scheibehenne et al., 2010): https://abcwest.cogs.indiana.edu/pmwiki/pdf/scheibehenne.options.2010.pdf
- Zeigarnik and Ovsiankina meta-analysis (Ghibellini & Meier, 2025): https://ideas.repec.org/a/pal/palcom/v12y2025i1d10.1057_s41599-025-05000-w.html
- EU Digital Fairness Act and dark patterns: https://www.goodwinlaw.com/en/insights/publications/2025/11/alerts-practices-antc-from-dark-patterns-to-fair-play
- Gamma onboarding teardown: https://pearlshu.substack.com/p/the-best-onboarding-flows-ive-seen
- AI UX control patterns: https://smashingmagazine.com/2026/02/designing-agentic-ai-practical-ux-patterns/
- Rehearsal and presentation anxiety: https://poorvucenter.yale.edu/media/833/download
- Time-to-value benchmarks (vendor figures, direction only): https://www.growthspreeofficial.com/blogs/b2b-saas-time-to-first-value-ttfv-benchmarks-2026-by-product-category-onboarding-impact-conversion
