# Phase 14 — pdf-export

> This phase makes true that the deck can be distributed as PDF — a faithful print of the single-file HTML, not a lossy screenshot.

**Depends on:** 12 · **Blocks:** 15 · **Spec step:** Locked decisions → PDF export

## Search

**Read first** — docs/v1/plan/05-export.md (the single-file exporter), docs/techstack/frontend.md (the published artifact), docs/findings.md → The category (lossy web-to-PPTX export is the category's worst-reviewed feature; native generation is the only version that does not lose)

**Grep for** — the exporter, the renderer, the `@page` print CSS

**Verify externally** — current best practice for printing a deck-sized HTML to PDF without losing fonts, texture, or motion states; Playwright's PDF route

## Make

PDF export: the single-file HTML is the source of truth, and the PDF is a faithful print of it — slide-sized pages, embedded fonts, textures rendered. The print CSS (`@page`, slide-sized pages) was designed in v1 phase 05; this phase builds the actual export path.

### Design decisions

- **PDF is a print render of the HTML, not a screenshot.** The category's worst-reviewed feature is lossy web-to-format export — Gamma's PPTX export breaks text, spacing, and fonts. A screenshot would inherit exactly that failure. The PDF is rendered from the same bytes as the HTML.
- **The HTML stays the source of truth.** PDF is a distribution add-on. What you edit is what you export — the byte-identity guarantee extends to the PDF as a faithful print.
- **Motion does not print; the finished state does.** The PDF shows each slide's resting state (the progressive-enhancement floor: the finished state is the default).
- **Playwright is the print path**, already in the stack for the vision critic and e2e.

## Verify

- [ ] PDF export produces slide-sized pages with embedded fonts and rendered textures
- [ ] A PDF slide matches the HTML slide's resting state
- [ ] The PDF is a faithful print — no text shift, no font substitution
- [ ] **Human:** compare a PDF slide to the HTML slide at full size

## Skipped

- Native PPTX/OOXML export — v3, and only if the market asks. It is the hardest export and the category's worst-reviewed feature

## Exit gate

- [ ] Faithful PDF print of the HTML
- [ ] No lossy conversion
