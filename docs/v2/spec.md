# v2 — spec

## Theme

**One paragraph. What this release proves that the last one did not.**

v1 proved the flow works and the variety claim holds for a curated registry with human review. v2 proves the variety claim is *scalable*: the design system becomes a real **engine** — a much larger combinatorial space, per-slide layout **generation** rather than catalogue-picking — and the product gains the loops that make it a product rather than a one-shot generator: a **real editor** (change copy, reorder, re-skin), **charts**, **PDF export**, and an automated **vision critic** that catches presentational defects between human reviews.

## Commitments vs bets

### Commitments

| Commitment | Why it holds |
|---|---|
| **The design system stays generated per deck, never a fixed skeleton** | The v1 spine. It does not move |
| **Layout variety is structural, not prompted** | The design engine + per-slide generation, from findings.md's mode-collapse evidence |
| **A vision critic is bounded — at most one revision per slide** | The old rule survives: a bounded loop is not autonomy; an unbounded critic is an agent |
| **PDF export is a real render, not a screenshot** | The single-file HTML is the source of truth; PDF is a faithful print of it |
| **Editor changes are local patches, no model call per keystroke** | The old rule survives: instant, undoable, and it keeps the renderer pure |

### Bets

| Bet | What would disprove it |
|---|---|
| **Per-slide layout generation produces layouts as good as curated ones** | A blind comparison where curated layouts beat generated ones at > chance |
| **The editor is the retention loop** (users come back to edit, not just generate) | Users generate once, download, and never return |
| **A vision critic catches real defects without being annoying** | It flags false positives that human reviewers override more often than it catches real ones |
| **Charts are a differentiator** | Users import to Excel/Sheets anyway and never use native charts |
| **The fingerprint gate scales** — a 30+ family space stays distinguishable | Two sampled decks converge on a fingerprint above threshold |

## Locked decisions

| Axis | Decision | Why |
|---|---|---|
| **Design space** | 30+ families in the registry, still data-driven | Big enough to never see the same deck twice; the engine (not prompting) keeps them distinct |
| **Layouts** | Per-slide layout **generation** within the family's grammar | The model designs new layouts; the grammar keeps them on-family |
| **Editor** | Real editor: copy, reorder, re-skin, undo/redo. Local patches, no model call per keystroke | The retention loop; the v1 lean flow becomes a product |
| **Re-skin** | Switch a deck's design family in seconds | The abstraction claim demonstrated: same content, different design system |
| **Charts** | First-class blocks, schema-owned, rendered by the deck's design system | Charts are content; the deck's tokens style them |
| **Vision critic** | Render → screenshot → critic → at most one revision | Catches presentational defects between human reviews; bounded, not an agent |
| **PDF export** | Real print render of the HTML | Distribution add-on; the HTML stays the source of truth |
| **Fingerprint gate** | Variety metric in CI | The v1 acceptance measurement becomes a standing gate |
| **Brand kit** | **File upload** arrives: logo, colors, fonts. Extracted, mapped to the design family's semantic roles, contrast-checked | The v1 typed-text kit becomes real; the upload security surface is now justified |

## What changes from v1

| Old | New | Why |
|---|---|---|
| ~10–15 families | 30+ families | Scale the variety claim |
| Curated layout catalogue | Per-slide layout generation within a grammar | The model designs, constrained |
| No editor | Real editor with undo/redo, reorder, re-skin | The retention loop |
| Human review only | Human review + bounded vision critic | Catch presentational defects between humans |
| HTML only | HTML + PDF | Distribution |
| No charts | First-class charts | Content variety |
| Typed-text brand kit | File-upload brand kit, extracted and mapped | What marketers actually expect |
| Variety measured in acceptance run | Variety gated in CI | The claim is standing, not one-off |
