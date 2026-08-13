# Content & Web

Defending the viewer. Everything here protects someone who opens a deck — your customer's prospect, on your customer's launch page, from a downloaded file.

## The artefact is a file

The v1 artefact is a **single self-contained `.html` file** that runs offline — `connect-src 'none'`, fonts and images embedded as data URIs, motion inlined. It talks to *nothing*. That is the strongest possible distribution posture: there is no CDN to poison, no origin to route around, no beacon to misdirect, no personalization endpoint to leak a token. It is the product rather than a constraint (`docs/v1/plan/05-export.md`).

**A hosted URL (v3) serves the same bytes.** Publishing uploads the single-file HTML to S3 and serves it via CloudFront; there is no origin server behind it, so the offline posture carries to the URL. The separation in v3 is physical, not merely configured — static objects, no route to attack, no router that could disagree with the CDN about what a URL means.

## CSP

**The exported deck (v1) — and the hosted URL (v3), which serves the same bytes:**

```
default-src 'none';
script-src  'self';
style-src   'self' 'unsafe-inline';
img-src     'self' data:;
font-src    'self' data:;
connect-src 'none';
frame-ancestors *;
base-uri    'none';
form-action 'none';
```

`connect-src 'none'` is the whole point — the deck talks to nothing. `img-src data:` and `font-src data:` are what make the embedded fonts and generated images legal under that. The browser test in [testing.md](testing.md) asserts **zero requests**, in a real browser, from `file://`.

This reverses the old framing: the previous product weakened `connect-src 'none'` to two endpoints for personalization and analytics. The offline single-file deck has neither.

`frame-ancestors *` is deliberate. Embedding a deck is a feature.

**It also means a deck can be framed by anyone, which is a residual risk worth naming rather than discovering.** An attacker can frame a customer's deck inside a page of their own construction — overlaying it, surrounding it with their own copy, or positioning it so a click lands somewhere the viewer did not intend. Classic clickjacking.

This is accepted, not solved, and the reasoning is that the alternative is worse: an allowlist of embedding origins would break the embed feature for every customer who has not pre-registered their site, which is all of them. Three things bound the damage:

- The framed deck has **no session and no privileges** — there is nothing to hijack a click *into*. Clickjacking against an authenticated app is an account-takeover primitive; against a static deck it is a presentation problem
- A CTA destination comes from the approved outline, so the destination of any click is a URL the customer supplied
- **App routes are `frame-ancestors 'none'`.** The app's origin separation means the framing risk never reaches the surface where it would matter

If a future feature puts anything interactive and consequential on a deck — a form, a purchase, an authenticated action — this trade stops being acceptable and `frame-ancestors` has to be revisited with it.

`style-src 'unsafe-inline'` is required for the design family's CSS custom properties and is the reason the next section exists.

**App routes:** `frame-ancestors 'none'`, no `unsafe-inline`.

Also on a deck:

```
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
```

`Referrer-Policy: no-referrer` fixes a quiet leak: without it, a viewer clicking a CTA sends the full deck URL — including any query parameters — to the destination site in the `Referer` header. A `file://` deck has no URL to leak, and the hosted URL (v3) must not leak one either. There are no recipient tokens in the offline artefact — the personalization endpoints that made them exist were a feature of the old served page and are gone with it.

## S3 and CloudFront

Publishing (v3) writes the single-file HTML to object storage, which moves a class of misconfiguration into scope that did not exist when the artefact was a download.

| | |
|---|---|
| **Block Public Access on, at bucket and account level** | The bucket is never public. This is the control that fails loudest and matters most |
| **CloudFront Origin Access Control** | The distribution is the only reader. No public bucket, no legacy OAI |
| **Brand-kit uploads land in a quarantine prefix** | Presigned direct-to-S3 puts arbitrary bytes in your bucket. The object is not servable until the worker has verified magic bytes and re-encoded it ([../techstack/infrastructure.md](../techstack/infrastructure.md)) |
| **`Content-Type` set by the server, `nosniff`, no inline HTML from assets** | An HTML file on the assets origin is an XSS on the assets origin |
| **Separate buckets per origin** | Hosted decks and uploaded assets do not share a bucket, a policy, or a blast radius. Terraform state shares neither ([build-pipeline.md](build-pipeline.md)) |
| **Versioning and lifecycle rules** | Versioning is the recovery path from a bad publish or a destructive bug; lifecycle rules are how retention actually happens rather than being intended |

## CSS injection via design-family tokens

**This is the attack surface most likely to be missed.** It arrives in v3 with user-influenced brand-kit values: the brand kit maps to a design family's semantic roles, and an attacker-controlled logo, color, or font id becomes a CSS custom property value. Combined with the `style-src 'unsafe-inline'` that the families require, an unvalidated token value is a script-adjacent injection point.

**Every token value is validated by type before it becomes CSS. No exceptions, no free-text tokens.**

| Token kind | Validation |
|---|---|
| Colors | Parsed into a color object, re-serialized. Never passed through as a string |
| Numbers | Numeric, range-checked against the linter bounds |
| Enums | `lighting`, `material`, `background`, `texture` — matched against known values, rejected otherwise |
| Font families | Selected from a curated registry by id. **Never a user-supplied string** |
| Easing curves | Parsed as `cubic-bezier(a,b,c,d)` with numeric components, or a known keyword |

Rejected outright, everywhere: `url(`, `expression(`, `@import`, `</style`, `javascript:`, backslash escapes, and any character outside the expected grammar for that token type.

The v2 AD linter already validates ranges for design reasons. **Extend it with these grammar checks and treat a failure as a hard failure**, exactly like a contrast violation. One validator, two purposes.

Font families deserve the emphasis: a user-supplied family string is the most natural-looking free-text token in the whole system, and it is the one that most easily carries a payload. Fonts are chosen from a registry by id, and the registry maps id to a vetted family and file.

## The deck is the sandbox

The old product had a `Slot` — a sandboxed `srcdoc` iframe for generated code. The offline single-file artefact has no equivalent: there is no user-authored executable surface inside a deck. The deck is generated from a schema-validated tree, rendered by React (which escapes by default), and the exported file carries `connect-src 'none'` so nothing inside it can phone home. A compromised generation produces an ugly deck, not a dangerous one — the "assume the model is compromised" principle, enforced by the schema parse and the CSP rather than by a sandbox.

## XSS in the renderer

The deck tree is JSON rendered by React, which escapes by default. `dangerouslySetInnerHTML` appears nowhere — this is a lint rule, not a convention.

Specific paths that need care:

**CTA destination** — restricted to URLs from the approved outline, plus a scheme allowlist rejecting `javascript:`, `data:`, `vbscript:`, and protocol-relative URLs. See [prompt-injection.md](prompt-injection.md).

**Abstract visuals** — generates SVG and CSS from an enum generator and a numeric seed. No user string reaches the output.

**Generated images** — embedded as data URIs, rendered through `<img>`. An image cannot execute. The image *prompt* is a seam action with a cost cap, not a vector — see [../techstack/pipeline-tools.md](../techstack/pipeline-tools.md).

**Chart data** — rendered as SVG paths and text nodes, never interpolated into markup. A cell containing `<script>` renders as visible characters.

**Locale codes and hostnames** — reach routing and headers. Validated against BCP-47 and a hostname grammar respectively, never interpolated raw.

## Uploads

Every uploaded file is hostile until proven otherwise.

| Control | Why |
|---|---|
| Magic-byte verification | Extension and `Content-Type` are attacker-supplied |
| Server-side re-encode for raster images | Strips EXIF, kills polyglots, normalizes format |
| Dimension and size caps before decode | Decompression bombs: a 200KB PNG can decode to gigabytes |
| Server-generated UUID storage keys | User filenames mean path traversal; never use them |
| `Content-Type` set by the server, `nosniff` | Prevents an image being interpreted as HTML |
| Served only from `assets.<domain>` | Contains any content-type confusion to a useless origin |

**SVG** is accepted, sanitized, and served only via `<img>`. Sanitization removes `<script>`, `<foreignObject>`, event handler attributes, external references, and `<use href>` pointing off-document. Referenced through `<img>`, an SVG cannot execute at all even if sanitization missed something — that layering is the actual defense. Rejecting SVG outright would hurt real users, since logos are almost always SVG.

> The layering is not caution, it is the control. DOMPurify — the best tool available for this and the right choice — had **four distinct XSS bypasses disclosed in 2025–2026**, and its 2.x branch was never patched for one of them. A design that trusted sanitization alone would have been exploitable four times in eighteen months. Versions and the full list are in [platform-and-packages.md](platform-and-packages.md).
>
> SVG also carries a **denial-of-service** shape distinct from XSS: billion-laughs entity expansion, deeply nested groups, and pathological filter chains. Next.js shipped a CVE in July 2026 for exactly this — CPU exhaustion at `/_next/image` from malicious SVG. Cap entity expansion and nesting depth at sanitization, and keep SVG out of any image-optimization path.

**GLB/USDZ** (a v3 question, not a v1 one) would parse in an isolated worker with triangle, texture, and file-size caps enforced *before* full decode. Draco and meshopt compression are decompression-bomb vectors with the same shape as image bombs. The v1 artefact embeds images and fonts as data URIs only — no 3D until it is a deliberate feature with a threat model.

## Custom domains

| Control | |
|---|---|
| TXT-record ownership challenge before serving | Stops claiming a domain you do not control |
| Periodic re-verification, auto-unbind | Prevents hosting content for a domain the customer no longer owns |
| Served from the published-content origin only | Never same-origin with the app. Restated because this is where origin separation breaks |
| Per-account domain cap | Limits spam and SEO abuse |

Certificate issuance is automated per verified hostname. Rate-limit issuance requests — an unbounded issuance path is both a cost problem and a way to hit a CA's rate limits and take down legitimate provisioning.

### Dangling DNS, in both directions

Custom domains create a subdomain-takeover surface that runs *both ways*, and the second direction is the one usually missed.

**Customer → you.** A customer points `launch.theircompany.com` at your platform, later cancels, and leaves the CNAME in place. If your side then serves whatever any account claims for that hostname, the next person to claim it is publishing content on the customer's brand domain. This is why re-verification and auto-unbind are in the table above — but unbinding is only half of it. **A hostname that is unbound must stop being servable, not merely stop being owned.** An unclaimed-but-routable hostname is the vulnerability; claim-checking on request is what closes it.

**You → the internet.** Any subdomain of your own domain pointed at a third-party service you later stop using is takeable by whoever registers that service next — and a takeover of `assets.<domain>` or `pages.<domain>` collapses the origin separation this entire document rests on. Inventory your own DNS records and remove them when a service is retired. This is unglamorous and it is how well-run companies lose an origin.

**Verification is per-binding, not per-domain, and it expires.** A TXT challenge proves control at one moment. Re-verify on a schedule, and treat verification failure as unbind-and-stop-serving rather than as a warning to follow up on.
