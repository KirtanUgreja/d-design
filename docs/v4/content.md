# v4 — content

> What the engine writes, and why a skeptical audience can trust it. Covers the interview, research and the `Fact` ledger, the storyline arcs, the rules every slide's copy obeys, and the evals that check them. The pipeline around these stages is in [engine.md](engine.md); the decisions are in [spec.md](spec.md).

---

## The job

**The first users are founders and salespeople presenting live to win something:** a round, a deal, a launch, a partner. Their deck has three jobs:
- Make **one argument**.
- **Back every number.**
- **End with the ask.**

The v3 sample deck failed all three:
- Its titles were topic labels ("Visual Data Representation", "Conclusion and Future Outlook").
- Its chart was `{"Growth": 85}`.
- Its body copy was a stage direction ("Prominent statistics will illustrate growth…").
- Its call to action pointed at `https://example.com` ([../findings.md](../findings.md) → "Measured 2026-09-26").

---

## Interview

**The interview asks at most six questions, adapts to the brief, and is always skippable.** One model call writes all the questions, and the app shows them one at a time. Each question comes with three suggested answers written for this brief, except the product question, which only the speaker can answer. The user can click one, edit it, or type their own. **Skip all** is always visible, because the interview improves the output and must never gate it ([../design/app.md](../design/app.md)).

| # | Asks | Fills | Skip when |
|---|---|---|---|
| 0 | What does the product do, for whom, and what are its two or three main features? No suggestions: a guess would put invented features on the slides (live deck, 2026-10-09: the deck never said what the product does) | `pasted` ("What it does") | The brief already says what it does, or names no product |
| 1 | Who is in the room — investors, a buyer, a champion and their boss, a partner — and what do they already believe? | `audience` | The brief names the audience |
| 2 | What should they do at the end? (the amount, the decision, the next meeting) | `ask` | The brief states the ask |
| 3 | What is the one sentence they must remember? The suggestions are candidate governing thoughts | `governing_thought` seed | Never |
| 4 | What proof do you have? Paste traction, revenue, customers, pilots, quotes. The suggestions include "none yet" and "search the web". The third names a kind of proof; picking it opens a box to paste it, and picked without pasting it is dropped, never kept as proof | `pasted` → `Fact`s (user) | The pasted material already carries numbers. Ask for confirmation instead |
| 5 | How long do you have, and are you **presenting live or sending it**? | `minutes`, `delivery` | The brief covers them |

Deck-type additions replace a skipped question and never add a sixth:

| Deck type | Asks for |
|---|---|
| Investor update | The reporting period and the KPIs tracked |
| Sales | The buyer's words for their pain |
| Launch | The availability date |

**Brand colours are not an interview question.** They are asked after the first deck exists, framed as "make this yours" ([../design/app.md](../design/app.md) → First run).

**`delivery` changes density.** A deck that is sent must explain itself, so its word budgets are about 1.5× the live ones.

**After the outline exists, the conversation continues.** "Lead with traction" or "cut it to 8 slides" patches the outline, and nothing is generated until approval. This is the iterate-until-satisfied loop the owner asked for, kept cheap because it touches only the outline.

---

## Research and the Fact ledger

**Every number on a slide traces to a `Fact`, or it is flagged.** This is the answer to the one-bar chart.

**When research runs:**
- Research runs when `brief.research` is true, which is the default. It runs after the interview and before the storyline.
- Queries come from the **arc's evidence needs**, not from the topic alone. A pitch needs problem cost, market size, why-now signals and the competitive landscape. A sales deck needs the cost of the status quo in the buyer's industry.
- When the brief names a product or company, research also looks it up: what it does, for whom, its features, from its own site, docs or press. What it finds becomes cited `Fact`s with no number, under the same quote rule.
- A deck left on **auto** takes its arc from the brief's words: "launch" is a launch, "investor update" an update, and so on; otherwise a pitch.
- At most 30 results per deck through `openrouter:web_search`, and at most $0.25 of research per deck.

**How a fact is extracted:**

| Rule | Why |
|---|---|
| **No quote, no fact.** A `Fact` stores the exact source passage containing its number. If no returned highlight contains the number verbatim, the fact is discarded | Quote-level verification is the cheapest guard against a model "remembering" a statistic |
| Primary sources first: filings, government and statistical offices, research institutions, the company's own reports, reputable press. Reject content farms, undated pages and AI-written listicles | Our users present to people who check |
| `as_of` is the year the source was published or the data collected, never a forecast's target year ("2030"). Anything older than 3 years is flagged, not dropped | "In 2019…" is fine if the slide says so |
| Conflicting numbers are both kept and flagged; the primary source wins by default | The user decides, and sees why |
| Pasted material becomes `Fact`s with source `user`. The quote must be found verbatim in what the user pasted | The user's own numbers get the same traceability as the web's |
| Search results and pasted material are wrapped as **quoted data** in every prompt | They are untrusted input ([engine.md](engine.md) → "Security of AI-written HTML") |

**How facts reach the slides.** A cited number on a slide gets a short source line (`data-field="source"`, e.g. "Owl Labs, 2025"). The speaker notes name the source in full.

**Unsourced numbers.** A number with no user or cited `Fact` becomes a `Fact` with source `illustrative` and status `proposed`. It shows in the outline as a highlighted chip the user must **approve** or **reject**. Approving the outline with a `proposed` number is not possible. An approved illustrative number carries the source line "Illustrative" on its slide.

---

## Storyline

One call writes the whole storyline. Speaker notes are a second call after approval, run in parallel with composition, so iterating on the outline stays cheap. The design stages never rewrite copy: v3's builder rewrote Sonnet's copy one slide at a time with no context, and that was spend on the wrong stage.

| Field | Rule |
|---|---|
| `governing_thought` | One sentence of ≤25 words: the deck's thesis. It is stated on slide 1 or 2 and again at the close, and every headline must support it |
| `arc` | Picked by `deck_type` (below) and adapted, never followed blindly |
| Slide count | Honours `brief.slide_count` exactly. If the material cannot fill it, the storyline says so in a note instead of padding |
| `headline` | An **assertion**: ≤12 words, containing a verb, in sentence case; a full claim that stands alone. "Remote staff get back 72 minutes a day", never "Commuting" |
| One idea per slide | A slide that needs "and" in its headline is two slides |
| Budgets by intent (live) | Statement ≤15 words. Points ≤3 × 10 words. Body ≤35 words. Number: 1 figure + a ≤15-word label. Quote: ≤30 words. Each field carries its own `budget_words`. QA enforces these as density ([design-engine.md](design-engine.md) → "QA metrics") |
| `notes` | 40–120 words in a spoken register, on **every** slide. They add what the slide does not say: word overlap (Jaccard) with the headline stays below 0.5 |
| Closing slide | The ask: a verb, an object, and a date or an amount. Not "Thank you" or "Questions?" unless the user asks for it |
| `provenance` | Per field: YOU (the brief, answers, pasted material) · WEB (a cited `Fact`) · AI (written by the model, including approved illustrative numbers). Shown on the outline cards |

---

## Arcs

Five deck types ship first. The rest are Skipped with a trigger in [plan/24-content-engine.md](plan/24-content-engine.md).

| Deck type | Arc | Typical length |
|---|---|---|
| **Pitch** | hook → problem → why now → solution → how it works → traction/proof → market → business model → competition → team → the ask | 10–14 |
| **Sales** | their pain, in their words → the cost of doing nothing → the new way → how it works → proof (case, numbers) → the offer → the next step | 8–12 |
| **Launch** | the change → who it is for → what is new, one idea per slide → proof or demo → availability → call to action | 6–10 |
| **Investor update** | the headline number → KPIs vs plan → wins → misses and why → burn and runway → asks | 6–10 |
| **Partnership** | the shared opportunity → what each side brings → the model → the plan → the ask | 6–9 |

---

## Content rules

The rules for words, checked in the product and on the bench.

1. **Headlines are assertions.** Banned openers include "Introduction to", "Overview of", "Key …", "Conclusion", "Agenda" (as a claim), and "About us".
2. **No meta-copy.** Never "This slide shows", "Here we will", "Prominent statistics will illustrate", or any sentence about the deck instead of the subject.
3. **No invented numbers.** See the ledger above.
4. **Banned phrases**, LLM house style: "in today's fast-paced world", "delve", "unlock", "unleash", "harness", "leverage" (as a verb), "game-changer", "seamless", "robust", "cutting-edge", "revolutionize", "supercharge", "elevate", "empower", "synergy", "tapestry", "landscape", "AI-powered", "not just X, it's Y", "imagine a world", "let's dive in", "in conclusion", "Meet ⟨product⟩". The list lives in `content/rules.py` and grows whenever the wall finds a new one.
5. **No emoji** in slide copy.
6. **Sentence case, active voice, concrete nouns, numbers with units.** "$4.2M ARR", not "significant revenue".
7. **Tone** follows `brief.tone` (plain · confident · warm · bold) and never changes between slides.
8. **One language per deck**, set by `brief.language`, including number and date formats.

---

## Evals

| Eval | Runs | Threshold |
|---|---|---|
| Topic-label headline detector (patterns + a model check) | In product (regenerate the headline) · bench | ≤1 per deck before regeneration, 0 after |
| Banned phrases | In product (rewrite) · bench | 0 |
| Unsourced numbers | In product (flag) · bench | 0 numbers without an approved `Fact` |
| Notes present and within budget | In product | 100% of slides |
| Word budget per intent | In product (the QA density metric) | Per intent |
| **Inverse spec** — a model reads only the deck's text and reconstructs the audience, the ask and the key message, scored against the brief 0–1 | Bench | Average ≥0.8 |
| Fact spot check — 20 random `Fact`s opened at their source by a human | Bench, at phase exits | ≤1 wrong |
| Injection corpus — hostile pasted material and search results (`bench/injection/`) | Bench | 0 cases change the output channel |

The inverse-spec eval comes from "Learning to Present" (arXiv 2603.16839). It is the cheapest check that a deck *communicates its purpose*, not just that it is well formed.
