# Phase 05 — export

> This phase makes true the artefact: one self-contained `.html` file with fonts, styles, and motion embedded, that runs offline in any modern browser with zero network requests.

**Depends on:** 06 · **Blocks:** 07 · **Spec step:** Commitments vs bets → artefact

## Search

**Read first** — docs/techstack/frontend.md (published artifact, progressive enhancement), docs/coderules/performance.md (weight), docs/security/content-and-web.md (CSP)

**Grep for** — the renderer output, the `Deck` schema, any existing export code

**Verify externally** — the current best practice for inlining fonts as data URIs in a self-contained HTML file; `@page` / print CSS for PDF; whether a `file://` page can load embedded fonts (it can, if they are data URIs)

## Make

The single-file exporter: takes the built slides + design tokens, inlines fonts (as data URIs from the open-license Fontsource families), inlines styles and motion, and emits one `.html` file. The offline check asserts the file makes zero network requests.

### Design decisions

- **Fonts are embedded as data URIs**, not linked. The file must work from `file://` with no network. Open-license families (Fontsource) make embedding unambiguous — see `docs/techstack/frontend.md`.
- **Images are embedded as data URIs too.** Generated images (backgrounds, heroes, illustrations, chart companions) are inlined in the single file. This is what keeps `connect-src 'none'` honest — an `<img src="data:...">` makes no network request. Dimension caps keep the file lean.
- **Motion is in the file** — CSS and a tiny JS runtime, no external library. The progressive-enhancement floor from `frontend.md`: the file is readable and complete without JS; motion is enhancement.
- **Navigation is slide-based, not scroll.** Arrow keys, Space, on-screen prev/next buttons, fullscreen, a slide counter. A deck is presented, not read — scroll is Gamma's vertical-card pattern, the page-shaped disease this product exists to cure (`docs/v1/spec.md` → Deck navigation). Touch degrades to swipe + buttons. Autoplay is banned.
- **The file makes zero network requests.** `connect-src 'none'`, enforced by a browser test. Offline is the product; it also happens to be the strongest security posture possible — no CDN, no origin, nothing to attack.
- **Progressive enhancement is the floor.** The file is complete without JS — text, images, layout are in the HTML. If JS never arrives, a viewer sees a finished deck without motion, not an empty one.
- **PDF is v2.** v1 ships the `.html` file. The print CSS (`@page`, slide-sized pages) is designed in v1 but the PDF export path is v2.

## Verify

- [ ] Export produces one `.html` file
- [ ] Fonts are embedded (no external font request)
- [ ] **Images are embedded as data URIs** (no external image request; `connect-src 'none'` holds)
- [ ] The offline check (a real browser, no network) passes — `connect-src 'none'`
- [ ] The file is complete and readable without JS
- [ ] Navigation is slide-based: arrow keys, Space, on-screen prev/next buttons, fullscreen, a slide counter — no scroll
- [ ] Touch degrades to swipe + buttons
- [ ] **Human:** open the exported file from `file://`, present it, it works offline with motion

## Skipped

- PDF export — v2
- Hosted URL / publishing — v3
- Embed — v3

## Exit gate

- [ ] One self-contained `.html` file
- [ ] Zero network requests, asserted in a real browser
- [ ] Works from `file://`, with motion
