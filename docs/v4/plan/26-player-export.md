# Phase 26 — player and export

> This phase makes true that the file holds up on stage: one offline `.html` that presents properly on real hardware, and a PDF that matches it.

**Depends on:** 22 (25 for real decks) · **Blocks:** 27 · **Spec step:** Locked decisions → Export, Presenting · **Size:** M

## Search

**Read first** — [../engine.md](../engine.md) → "Security of AI-written HTML", [../spec.md](../spec.md) → Export, [../../security/content-and-web.md](../../security/content-and-web.md)

**Grep for**
- `render/src/export.tsx` at `v3-final` — the navigation shell, print CSS and disclosure footer.
- `render/src/pdf.ts` and `render/tests/offline.test.ts` at `v3-final`.
- `git show cbfebfa^:web/src/features/present/fullscreen.tsx` — the fullscreen overflow lesson.

**Verify externally**
- A blank popup opened from a `file://` page: can the opener script it in Chrome, Safari and Firefox?
- What the EU AI Act Code of Practice requires as a machine-readable marker.
- Declarative Shadow DOM when printing to PDF.

## Make

- `export/player/player.js` and `player.css`, ours and static:
  - Arrows, Space, PgUp/PgDn, Home/End, number + Enter to jump, swipe.
  - `F` fullscreen; the stage scaled to fit, letterboxed in the slide's ground colour.
  - `O` overview grid, `B` black screen, `#n` deep links.
  - `P` presenter popup: current and next slide, notes, timer, clock. The deck opens a blank popup and writes into it directly; no `BroadcastChannel`. Key listeners are attached to the popup too, so a clicker works whichever window has focus.
  - Per-field reveals from `data-build` and the theme's motion; reduced motion respected.
- `export/assemble.py`: the CSP, fonts embedded once, one shadow root per slide, webp images, the AI markers, the visible disclosure in the player chrome.
- **Two flavours:** "present" (notes as an inert `application/json` block) and "send" (no notes).
- Print CSS at 1920×1080 per page, and `export/pdf.py` from the send flavour.

### Design decisions

- **The popup, not `BroadcastChannel`.** Every `file://` page has its own opaque origin, so a channel is unreliable offline; a blank popup inherits the opener's origin.
- **Notes never ship in a file meant to be sent.**

## Verify

On Chromium, Firefox and WebKit:
- [ ] Zero network requests from `file://`, including with the presenter popup open
- [ ] Renders with the network fully blocked
- [ ] Keyboard navigation end to end
- [ ] PDF page count equals slide count
- [ ] Notes absent from the send flavour and the PDF
- [ ] **Human:** present one deck on a laptop with an external display and a clicker
- [ ] **Human:** open the file from an email attachment in 3 browsers

## Skipped

- Window Management API placement of the popup — trigger: presenters ask.
- PPTX — trigger: repeated user demand ([../../findings.md](../../findings.md) → The category).
- Phone remote — trigger: users ask.

## Exit gate

- [ ] All checks green on 3 engines
- [ ] Zero stage defects in the human run
