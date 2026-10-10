# Research, 2026-10-08 — Gamma 5, the competitors, and the papers

> Why: the owner rated the 2026-10-08 walls "messy" (art-direction run) and "one design in many fonts" (gate run). Four research passes, run in parallel, on what the market and the literature now do. Directional: most reviews are written by competitors, and the 2026 papers are preprints.

## 1. Gamma 5 (released 6 Oct 2026)

Gamma's stated goal for Gamma 5 is to remove "AI smell" (decks that repeat the same layouts, the same three-column feature blocks, stock imagery, a predictable rhythm). That is our pitch, now theirs too.

| What they did | How |
|---|---|
| A **plan step** before building | Clarifying questions, then a plan of story, **style** and **visuals** the user sees — "the highest-leverage moment" |
| An **agent** that designs | Writes custom code, draws shapes, arranges elements, generates images, **reviews its own work** (overflow, bad crops) |
| **About 3,000 templates** made by humans and AI, a large style library | Variety from a big, human-quality reference set, not from free invention |
| **Consistent styled images** | One image style per deck, suggested from the topic; prefers illustration over photoreal |
| Restyle | Keeps the words, changes the look |
| Classic mode underneath | Cards of typed blocks: accent image (left, right, top, background), smart layouts (columns, timelines, comparisons), Smart Diagrams (12+ types), Smart Charts; a theme sets fonts, palette, roundness, stroke, shadow |

Reviewers' main complaint about Gamma before 5: **"every deck looks like a Gamma deck"** — the fixed component library is both why it looks clean and why it looks the same. Second: AI images are repetitive or irrelevant.

## 2. The other tools

| Approach | Who | Result in reviews |
|---|---|---|
| Constrained smart layouts (an auto-layout engine) | Beautiful.ai, Presentations.ai, Plus | Most reliably clean; called rigid and recognisable |
| Template families, several variants | Canva, Pitch | Varied but "formulaic" |
| A reference deck's style copied | Gemini in Slides, Kimi | Quality jumps when a concrete design system exists first |
| Whole slide drawn by an image model | NotebookLM, Genspark Creative, Manus | **Most striking** — one art direction, hero imagery, bold scale — but uneditable and numbers unreliable |
| Free HTML by a model | Genspark Professional, Manus | "Basic", "generic, messy" |

**What reliably reads as designed:** one coherent art direction; **imagery on most slides**; real charts and semantic diagrams; something that enforces composition; content that is good.

## 3. The papers (2024–26)

| Finding | Evidence |
|---|---|
| **Plan, then code** — a small validated layout structure before HTML | DeepSlides (2026, ≈ parity with commercial tools), PosterGen, Paper2Poster |
| **Adapt a retrieved reference** beats inventing from nothing | PPTAgent (design 3.27 vs 2.95 template, 2.33 rules), SlideCoder (+40.5 layout fidelity), LayoutPrompter |
| Free-form code from frontier models "frequently produces aesthetic layout issues"; templates "exhibit limited diversity" | AeSlides (2026), SlidesGen-Bench |
| **Measured checks beat a vision-model judge** (render-computed balance, collisions, empty space, clutter); a VLM judge agreed with humans at κ≈0.19 | AeSlides, SlidesGen-Bench (0.71 vs 0.57) |
| **Several candidates, ranked** | LayoutPrompter, AeSlides |
| **Targeted, step-level repairs** beat whole-slide regeneration | ReDeck (2026), DesignLab |

## 4. What this says about d-design

| Our decision | Verdict |
|---|---|
| Model writes slide HTML inside tokens, measured in a browser (v4) | Right foundation — Gamma 5 moved the same way |
| **Phase 36 removed every reference slide** from the prompt | **Wrong per the literature**: references are the main quality lever. The model then designs from nothing → one house style, or mess when pushed |
| Per-deck art direction (2026-10-08) | Right idea (Gamma 5's plan step), wrong execution: it only gave the model decorative shapes |
| **No imagery** (phase 25's image half never built) | **Our largest visible gap.** Every tool that looks designed leans on images |
| Geometric novelty metric | Measures placement, not design; keep only as a guard |
| One composition per slide | The papers generate several and rank them |

Key sources: siliconangle.com (2026-10-06, Gamma 5), developers.gamma.app (API, changelog), help.gamma.app, arxiv.org/abs/2501.03936 (PPTAgent), 2506.07964 (SlideCoder), 2604.22840 (AeSlides), 2605.26451 (DeepSlides), 2601.09487 (SlidesGen-Bench), 2609.00194 (ReDeck).
