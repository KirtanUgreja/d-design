# Phase 20 — Offline and export

> One file you double-click that presents with the wifi off, and a PDF that prints. Both are the same act — freezing a live deck into something that survives leaving the product — and both are small only because the renderer is pure and the published page already makes zero requests.

**Depends on:** [10](10-slides-mode.md), [18](18-presentation-frame.md) · **Blocks:** — · **Spec step:** presentation delta

---

## Search

**Read first**

- [../presentation.md](../presentation.md) → "Getting it out of the product", and the reasoning for why editable `.pptx` is deliberately absent
- [../../v1/spec.md](../../v1/spec.md) → Risk 3. *"PPTX, PDF, speaker notes will all be asked for in week one. Have a real answer ready, not 'coming soon.'"* This phase is two thirds of that answer
- [../../techstack/infrastructure.md](../../techstack/infrastructure.md) → where `render` runs and what it is allowed to reach

**Grep for**

- `web/src/app/` → the publish route. A published page that already makes zero network requests is most of an offline bundle; find out what it actually still fetches
- `api/features/reskin/__init__.py` and the `render` service from [00](00-foundations.md) → the same Playwright process does the PDF. **No second headless browser**
- `web/src/features/art-direction/to-css-vars.ts` → the CSS variable bundle. Inlining it is the bulk of the self-contained file
- `@fontsource` usage → the two font families per art direction. These are the largest thing being inlined and the reason a bundle has a size budget
- `api/features/assets/` → image storage keys. Every image becomes a data URI in the bundle, which is where the size goes

**Verify externally**

- Playwright's `page.pdf()` behaviour with a fluid, container-query-driven layout at a fixed page size — specifically whether `container-type: size` resolves against the PDF page box
- Whether `page.pdf()` is Chromium-only in the installed Playwright version, and whether print CSS or `screen` media is used
- Font subsetting and licence terms for the `@fontsource` families being embedded. **Embedding a font in a downloadable file is a redistribution question, not a technical one** — check each licence before it ships

---

## Make

```
api/features/export/
  bundle.py              self-contained HTML: fonts, images, CSS inlined
  pdf.py                 render service → PDF at 16:9
web/src/features/present/
  download.tsx           the two buttons and their honest labels
```

### The offline bundle

A single `.html` file with everything inlined: the scene tree, the resolved CSS variables, the two font families as base64, every image as a data URI, and the playback JavaScript. Double-click it and it presents.

**This is small work for a large payoff, and the reason is architectural rather than clever.** Rule 6 made the renderer pure, so it does not need a server. The published page was designed to make zero requests, so there is nothing to strip out. The art direction is already CSS variables, so there is no build step. The bundle is the existing output with its references resolved — and if it turns out to need a second rendering path, one of those three properties has quietly stopped being true and that is the bug to fix.

What it carries and what it does not:

| In the bundle | Not in the bundle |
|---|---|
| All slides, in order | Speaker notes ([19](19-presenter-view.md) — audience-facing surface rules apply) |
| Fonts, images, textures | The editor, the pipeline, any API call |
| Keyboard and click advance | Phone remote ([23](23-phone-remote.md) needs a server) |
| Reduced-motion handling | Analytics of any kind |

**The phone-remote contradiction is stated in the UI, not discovered on stage.** The download says what it cannot do.

There is a size ceiling. Two font families plus a deck of photographs is tens of megabytes, and a bundle nobody can email is not a deliverable. Measure it, set a budget, and when a deck exceeds it, say so at download time with the reason — images, almost always — rather than producing a file that fails silently in a mail client.

### The PDF

The `render` service loads the deck at 1920×1080 and prints one page per slide. 16:9 is chosen because it is the most common projector ratio and because [18](18-presentation-frame.md)'s preflight already guarantees every slide works at it — **the export ratio is one of the four the product already promises**, so the PDF cannot show something the author was never warned about.

Motion does not exist in a PDF, so every slide is captured in its **finished** state. This is free: [../../v1/art-direction.md](../../v1/art-direction.md) requires the finished state to be the authored default with animation layered on top, precisely so a browser that cannot animate shows a complete page rather than a blank one. The same decision makes the PDF correct.

### What is deliberately not here

Editable `.pptx`. The research is unambiguous that lossy web-to-PowerPoint conversion is the single most-complained-about feature in this category, and the losses are exactly the things this product is made of — custom fonts substitute, textures flatten, motion vanishes. **An export that looks worse than the artefact damages the product more than its absence does.**

The answer to *"can I get a file?"* is yes: a PDF that is exact, and an HTML file that presents. If paying users still ask for editable PowerPoint after that, it is a v3 phase built on native OOXML generation — not a converter bolted onto this one.

---

## Verify

**The gate** — green.

**Offline**

- [ ] Download a bundle, disconnect the network entirely, open the file, present the whole deck. **Network off, not throttled**
- [ ] Zero outbound requests from the opened file. Assert against the browser's network log, not by inspection
- [ ] Fonts render as the art direction's fonts, not fallbacks. A substituted font offline is the same defect as a substituted font in `.pptx`
- [ ] Speaker notes appear nowhere in the file's bytes. `grep` the bundle
- [ ] Reduced motion is honoured inside the bundle
- [ ] A deck over the size budget is refused at download time with the reason, not produced and left to fail

**PDF**

- [ ] One page per slide, in order, at 16:9, every slide in its finished state
- [ ] A deck that passes the four-ratio preflight produces a PDF with nothing clipped
- [ ] Text is selectable rather than a flat image, unless a texture makes that impossible — in which case record why
- [ ] The `render` service does the work. **No second headless browser was installed.** Check `dependencies.md`

**Human**

- [ ] Email the PDF to yourself and open it on a phone. Email the bundle to yourself and open it on a different machine. Both of these are how a user will actually first meet these files

---

## Skipped

| Not built | Trigger |
|---|---|
| Editable `.pptx` | Real demand from paying users. Then native OOXML, never a converter |
| PDF at ratios other than 16:9 | If someone asks. The preflight guarantees all four, so it is a parameter rather than a design change |
| Speaker notes on the PDF | Deliberate. Notes are private, and a PDF gets forwarded |
| Offline *editing* | Never. The editor needs the pipeline; a bundle is a frozen artefact and pretending otherwise creates a sync problem |
| Service-worker offline for the live URL | Rejected in favour of the file. It fails silently when storage is cleared, and it fails on stage |
| Video export | v3+ at the earliest, and only if the shared-link case demands it |

---

## Exit gate

- [ ] A bundle presents completely with the network off and makes zero requests
- [ ] Fonts are embedded, licensed for it, and render correctly offline
- [ ] Notes are absent from the bundle bytes and from the PDF
- [ ] PDF is one page per slide at 16:9, finished state, nothing clipped
- [ ] Size budget enforced at download time with an honest reason
- [ ] No second headless browser, no new dependency without a ledger line
- [ ] The gate is green
