# Phase 36 — independent design

> This phase makes true that **no slide is ever designed from a stored list**. Every slide's composition is generated for it, aimed at a part of the design space nothing has used yet, and checked against an archive of every slide ever made; every deck's colour and type are generated instances, not entries in a menu. Uniqueness becomes a measured guarantee, not a shuffle of parts that repeats after enough decks.

**Depends on:** 23, 25 (the measured QA loop) · **Blocks:** 25's gate 2 run · **Spec step:** Locked decisions → Diversity · **Size:** L · **Owner's decision:** 2026-10-05 — "every slide should be independent, unique — not font from template X and layout from template Y"

## Why the current engine repeats

Phase 23 made the *look* continuous, but slides still come from finite parts:

| Finite part today | Why it repeats |
|---|---|
| 12 exemplar slides in every compose prompt | Few-shot examples and fixed prompt structure **anchor** a model to the same outputs ("The Price of Format", 2025; "Is Convergence Inevitable?", 2026) |
| 10 archetype names (poster, split, band…) | Ten names are ten templates with extra steps |
| 7 palette strategies, 10 motif kinds, 24 pairings | A menu, however it is shuffled, is exhausted; after enough decks every combination recurs |
| Exemplar-fill as the fallback | Literally a template library |
| Nothing measures similarity across decks | Sameness is invisible until a user sees it |

A language model asked the same way every time **collapses onto a few favourite layouts** — alignment training rewards the typical (Verbalized Sampling, 2025). Randomising inputs does not fix that: picking at random from any finite set repeats. Two things do: **an unbounded design space**, and **a memory that refuses repeats**.

## The method: quality-diversity, applied to slides

Quality-diversity search (MAP-Elites, Mouret & Clune 2015; novelty search, Lehman & Stanley) is the established way to produce endless *different* solutions that are each *good*: describe every solution by a few measured **behaviour descriptors**, keep an **archive** of what has been made, and accept a new one only if it passes the quality bar **and** lands somewhere new. QDAIF (2023) drives it with language models. Here the "solution" is a slide, quality is our QA, and the descriptors are measured in the browser.

```
content + deck identity
        │
        ▼
  ① a composition TARGET, drawn from an under-used region of the descriptor space
        │                       (code; continuous; shaped by what the slide holds)
        ▼
  ② the model designs toward the target — no example slides in the prompt;
        it sketches 3 different ideas, rates how typical each is, builds the least typical that fits
        │
        ▼
  ③ render → QA (quality)  +  measure descriptors + layout hash (behaviour)
        │
        ▼
  ④ NOVELTY GATE: far enough from every archived slide and every slide in this deck?
        │  no → one steered retry ("too close to slide N: move the mass, change the split")
        ▼  yes
  ⑤ accepted → descriptors (never content) join the archive
```

## Make

**1. Composition descriptors** (`qa/descriptors.py`, from `measure.js` boxes and the screenshot) — about ten continuous numbers per slide, the slide's "behaviour":
- visual-mass centroid (x, y), and its spread
- empty space: largest empty rectangle share, and where it sits
- hero scale: largest type size ÷ body size, and the hero's area share
- structure: number of distinct blocks, dominant split axis and ratio, alignment axes in use
- edge use: how much touches or bleeds off the canvas edges
- colour-field share (accent and ink fields as a fraction of the canvas)
- plus a **layout hash**: the screenshot reduced to a 32×18 occupancy map with text hidden, compared by Hamming distance — a second, perceptual guard

**2. The archive** (`store`, descriptors and hashes only — **never text, never screenshots**): every accepted slide, every deck, every user. MAP-Elites grid over the descriptors for coverage; k-nearest-neighbour distance for novelty.

**3. Composition targets** (`compose/targets.py`) — replaces the 10 archetype names. Code draws a target point in the continuous descriptor space:
- from an **under-filled region** of the archive (illumination), so the system keeps exploring rather than circling its favourites;
- **conditioned on content**: a slide whose job is one number needs a high hero scale; a five-point comparison needs structure; the cover and the ask get the most freedom;
- far from the previous slide in the deck.
The target is given to the model as concrete geometry ("visual mass in the lower-left third; 40% of the canvas empty, as one field on the right; the hero at about 6× body size, cropped by the left edge; two blocks, split vertically about 2:5").

**4. The compose prompt without examples** (`compose.v6`): the contract, the deck's tokens, the content, the target, and design principles — **no exemplar slides**. Inside the same call the model first writes three genuinely different composition ideas with how typical each is, then builds the least typical one that meets the target (verbalized sampling, 1.6–2.1× more diverse output in the paper). The exemplars stay as **QA fixtures only**.

**5. The novelty gate** in the pipeline ladder: after QA passes, measure the descriptors and hash; if the slide is within ε of anything in the archive or the deck, **one** steered retry naming what to change. A slide still too close is accepted with a warning (cost stays bounded) and counted on the bench.

**6. A procedural fallback** (`compose/procedural.py`) — replaces exemplar-fill. When the model cannot produce a clean slide, code builds one *from the target* (grid tracks and positions computed from the descriptors). No stored layout exists anywhere in the product.

**7. Deck identity without menus** (`design/`):
- **Palette:** the 7 strategies become one continuous palette space — ground lightness and chroma, ink tint, accent hue offset, accent lightness and chroma, a second accent's presence — still fitted to WCAG 2 + APCA by construction.
- **Type:** the registry moves to **variable fonts**, and each deck draws continuous axis values — weight, width, optical size, and family axes where they exist (Fraunces SOFT and WONK, Recursive CASL, Roboto Flex's parametric axes, Bricolage's width). Families are still finite — typefaces are drawn by people — but the instance is continuous, and families are weighted toward what the archive has used least.
- **Motif:** the 10 kinds become a procedural grammar (marks, fields, rules, dots, lines and their parameters), drawn per deck.

**8. The sameness bench** (`cli bench sameness`): N decks from N briefs, every slide's descriptors and hash, reporting coverage, repeat rate and nearest-neighbour distances, plus a blind wall of random slide pairs.

### Design decisions

- **Uniqueness comes from generation plus memory, never from shuffling stored parts.** A shuffle of finite parts is a template system with a delay.
- **Within a deck, slides share one generated identity; between any two slides anywhere, compositions are never shared.** A deck whose slides share nothing reads as a collage, not a deck. Identity is per deck and generated; composition is per slide and novel.
- **Quality first, then novelty.** A slide must pass QA before novelty is even measured; the novelty gate never accepts a broken slide to be different.
- **Code decides where to explore; the model designs there.** The model is not asked to "be different" — it is given a concrete, unexplored target. Asking a model for novelty in words is what collapses.
- **The archive holds geometry, not content.** Descriptors and occupancy hashes are not customer data; no slide text or image is ever stored in it.
- **Bounded cost.** At most one novelty retry per slide; a near-repeat after that is accepted, flagged and counted, never looped.

## Verify

- [ ] Descriptor fixtures: hand-built slides with known geometry produce the expected descriptors
- [ ] The layout hash ignores colour and text, and separates two known-different compositions
- [ ] A target is honoured: generated slides land within tolerance of their target on most descriptors
- [ ] No compose prompt contains an exemplar (a test asserts it)
- [ ] The procedural fallback passes QA for every bench slide under 50 generated identities
- [ ] Palette: 1,000 continuous palettes, zero contrast failures
- [ ] Variable fonts: every axis value drawn loads, measures and embeds offline
- [ ] **Bench:** 30 decks (~300 slides, roughly $2–3): the archive's coverage keeps growing with no plateau; repeat rate ≤ 1%; no two slides in a deck within ε
- [ ] **Human:** a blind wall of 40 slides from 20 decks — the owner finds no pair with the same design, and rates quality no lower than before

## Skipped

- **Generating new typefaces** (parametric type à la Metafont / Prototypo) — trigger: the wall shows variable axes are not enough. Type design is its own craft; continuous instances of real families come first.
- **A vision model judging similarity** — trigger: descriptors and hashes miss sameness the owner can see.
- **Per-user archives** — one global archive first; trigger: a team wants its decks to share a house style on purpose.

## Exit gate

- [ ] Repeat rate ≤ 1% at 300 slides, and not rising with the archive's size
- [ ] Archive coverage still rising at 300 slides
- [ ] Owner's blind wall: zero same-design pairs; quality not lower than the phase-25 wall
- [ ] Median deck cost rises by at most 30%; novelty retries on at most 20% of slides
- [ ] No stored layout, archetype list or exemplar is reachable from the compose path

## Research

- Mouret & Clune, MAP-Elites; Lehman & Stanley, novelty search — quality-diversity: https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2021.639173/pdf
- QDAIF, quality-diversity driven by language models: https://arxiv.org/pdf/2310.13032
- Verbalized Sampling — mode collapse and how to undo it: https://arxiv.org/html/2510.01171v1
- The Price of Format — structure and few-shot anchors collapse diversity: https://arxiv.org/pdf/2505.18949v1.pdf
- Layout similarity measures (LTSim, DocSim): https://arxiv.org/html/2407.12356v1
- Variable fonts with parametric axes (Roboto Flex): https://github.com/dberlow/roboto-flex
- Generative identities — rules, not menus: https://cdv.dei.uc.pt/2018/dynamic-identities
