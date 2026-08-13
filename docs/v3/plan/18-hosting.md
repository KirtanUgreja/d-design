# Phase 18 — hosting

> This phase makes true that a deck has a hosted URL — static, CDN-served, and un-attackable — while the single-file HTML remains the primary artefact.

**Depends on:** 17 · **Blocks:** 19 · **Spec step:** Locked decisions → hosting

## Search

**Read first** — docs/v1/plan/05-export.md (the single-file exporter), docs/security/content-and-web.md (CSP, origins), docs/techstack/infrastructure.md (S3 + CloudFront, no origin server)

**Grep for** — the exporter, the renderer, the `Deck` schema

**Verify externally** — current S3 + CloudFront static hosting; the CDN cache-deception controls from the old docs

## Make

A hosted URL for a deck: the exported single-file HTML is uploaded to S3 and served via CloudFront at a per-deck URL. The offline file remains downloadable. No origin server exists — there is nothing to route around.

### Design decisions

- **The hosted URL is the same bytes as the downloadable file.** Publish uploads the single-file HTML to S3; the URL serves it. There is no server render, no second implementation — the file is the artefact, the URL is a distribution layer.
- **The hosted page inherits the file's security posture.** `connect-src 'none'`, embedded fonts, no origin server. The CDN cache-deception class nearly vanishes — there is no origin for a cache-key disagreement.
- **The URL is the business layer.** It is what a marketer shares with an audience, embeds in an email, puts on a launch page. The file is the free wow; the URL is the paid convenience (phase 19).
- **The badge and AI-disclosure are designed into the deck's footer**, not bolted onto the URL. One mark, two layers: ours (badge, removable on paid) and the law (AI-content disclosure, not removable).

## Verify

- [ ] A deck publishes to a hosted URL
- [ ] The URL serves byte-identical content to the downloadable file
- [ ] `connect-src 'none'` holds on the hosted page
- [ ] **Human:** open the hosted URL, confirm it is the same deck as the file, offline-grade, with the badge/disclosure in the footer

## Skipped

- Custom domains — a later v3 concern (the old decision: deferred until there are enough customers to justify the SAN limits)
- Embed — follows hosting

## Exit gate

- [ ] Hosted URL serves the same bytes as the file
- [ ] No origin server; `connect-src 'none'` holds
- [ ] Badge + AI-disclosure in the footer
