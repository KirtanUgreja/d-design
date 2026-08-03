# Content & Web

Defending the viewer. Everything here protects someone who opens a published experience — your customer's prospect, on your customer's launch page.

## Three origins

```
app.<domain>       the editor, sessions, auth        → Vercel
pages.<domain>     published experiences, domains    → CloudFront ← S3
assets.<domain>    uploaded and generated files      → CloudFront ← S3
```

The single highest-leverage decision in this directory. An XSS in published content cannot reach an app session, because it is not the same origin — no shared cookies, no shared storage, no reachable DOM.

**The separation is now physical, not merely configured.** Published experiences are static objects in S3 with no origin server behind them ([../techstack/infrastructure.md](../techstack/infrastructure.md)) — there is no route to attack, no database to reach, and no router that could disagree with the CDN about what a URL means. That last property is what removes most of the web-cache-deception surface described in [platform-and-packages.md](platform-and-packages.md); it still applies to the `/r/` fields endpoint, which is a real route.

**Custom domains are where this silently breaks.** A customer domain must be served from the published-content origin and must never be same-origin with the app. If a custom domain ever resolves to the app origin, the isolation is gone and nothing else in this document compensates.

## CSP

**Published pages:**

```
default-src 'none';
script-src  'self';
style-src   'self' 'unsafe-inline';
img-src     'self' https://assets.<domain> data:;
font-src    https://assets.<domain>;
connect-src https://api.<domain>/r/fields https://api.<domain>/v/beacon;
frame-ancestors *;
base-uri    'none';
form-action 'none';
```

`connect-src` is load-bearing and it is **two exact paths — not `'self'`, not a host**. Live data is still baked in server-side ([../v3/live-data.md](../v3/live-data.md)), so nothing about the content requires network. Two product features do: per-recipient field substitution on `/r/` pages and the analytics beacon.

This is weaker than the original `connect-src 'none'`, and the weakening is recorded deliberately in [../techstack/decisions.md](../techstack/decisions.md) rather than absorbed quietly. The guarantee is now *"this page talks to two endpoints you own and nothing else"*, and the browser test in [testing.md](testing.md) asserts exactly that — two requests, no more. It comes back to `'none'` if analytics ever moves to CDN access logs and personalization to per-recipient pre-rendering.

The consequence to hold onto: **a recipient token now travels in a client-side request**, which raises rather than lowers the importance of the referrer and cache headers below.

`frame-ancestors *` is deliberate. Embedding published experiences is a feature.

**It also means published pages can be framed by anyone, which is a residual risk worth naming rather than discovering.** An attacker can frame a customer's launch page inside a page of their own construction — overlaying it, surrounding it with their own copy, or positioning it so a `CTA` click lands somewhere the viewer did not intend. Classic clickjacking.

This is accepted, not solved, and the reasoning is that the alternative is worse: an allowlist of embedding origins would break the embed feature for every customer who has not pre-registered their site, which is all of them. Three things bound the damage:

- The framed page has **no session and no privileges** — there is nothing to hijack a click *into*. Clickjacking against an authenticated app is an account-takeover primitive; against a static marketing page it is a presentation problem
- `CTA.href` comes from the Brief, so the destination of any click is a URL the customer supplied
- **App routes are `frame-ancestors 'none'`.** The origin separation means the framing risk never reaches the surface where it would matter

If a future feature puts anything interactive and consequential on a published page — a form, a purchase, an authenticated action — this trade stops being acceptable and `frame-ancestors` has to be revisited with it.

`style-src 'unsafe-inline'` is required for art-direction CSS variables and is the reason the next section exists.

**App routes:** `frame-ancestors 'none'`, no `unsafe-inline`.

Also on published pages:

```
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
```

`Referrer-Policy: no-referrer` fixes a quiet leak: without it, a viewer clicking your `CTA` sends the full personalized URL — **including the recipient token** — to the destination site in the `Referer` header. The destination now has a working link to that recipient's personalized page. Nobody notices this happening.

**Personalized pages carry `X-Robots-Tag: noindex`.** A `/r/[token]` URL indexed by a search engine publishes a named prospect's personalized page to the world. Locale pages are indexable; recipient pages never are.

**And `Cache-Control: private, no-store`.** The referrer and robots headers stop a token leaking *outward*; this one stops the page leaking *sideways*, to someone who never received the link. A CDN that caches a personalized response under a token-free key serves one recipient's page to the next visitor — and Next.js shipped two cache-confusion CVEs with exactly this effect in July 2026. The full treatment, including web cache deception via `/r/<token>/x.css`, is in [platform-and-packages.md](platform-and-packages.md). It belongs to this document's threat model too: **the cache is a third party that gets a vote on who sees what.**

## The two public endpoints

Static publishing removed the origin server behind `pages.<domain>` — and moved the entire dynamic surface of a published experience into two endpoints on `api.<domain>`. They are small, unauthenticated, and reachable by anyone. They deserve the scrutiny the origin server used to get.

### `/r/fields` — the one that returns PII

Takes a recipient token, returns five personalization fields: a name and a company at minimum ([../v3/personalization.md](../v3/personalization.md)). **The token is the entire authentication**, and the response is personal data.

| | |
|---|---|
| **Rate limit per token and per IP** | Guessing a 128-bit token is infeasible; scanning tells you someone is trying. Alert on the pattern, not just the count |
| **Constant-time comparison, indexed lookup** | Already specified in [tenancy-and-data.md](tenancy-and-data.md); it applies here because this is now the only path that uses it |
| **Returns exactly five fields** | Shaped in the data module, never a row spread into JSON. A `recipients` row has columns that must never reach a browser ([../coderules/structure.md](../coderules/structure.md)) |
| **`Cache-Control: private, no-store`** | Same reasoning as the page itself |
| **Fails closed** | An expired, revoked, or unresolvable token returns nothing — never a partial or default response |

**CORS is the part that is easy to get wrong.** The endpoint is called from `pages.<domain>` *and from every customer's custom domain*, which is a set that changes at runtime. The tempting implementation reflects the `Origin` header, and origin reflection is how a CORS policy becomes no CORS policy.

**Validate the origin against the verified-domains table, then echo it — never reflect it unchecked.** The same table that already gates custom-domain serving gates this. An unrecognized origin gets no CORS header at all. `Access-Control-Allow-Origin: *` is not an option, because the response is personal data.

### `/v/beacon` — the unauthenticated write

Scroll depth, CTA reach, duration. No authentication is possible: the sender is an anonymous viewer.

So accept what it is — **analytics from this endpoint are indicative, not authoritative** — and bound the damage:

- **Rate limit hard, per IP and per experience.** It is a free write path into your database
- **Strict payload schema, small body cap.** Zod-parsed like any external input
- **No PII accepted, ever** — the endpoint takes an experience id, an optional token, and metrics. If a field arrives that could identify someone, the schema rejects it rather than storing it
- **Fire-and-forget, `204`.** No response content means nothing to probe

Someone can inflate a view count. That is a product annoyance, not a breach, and it is worth stating plainly so nobody later builds billing on top of these numbers.

## S3 and CloudFront

Publishing writes artifacts to object storage, which moves a class of misconfiguration into scope that did not exist when pages were rendered by a server.

| | |
|---|---|
| **Block Public Access on, at bucket and account level** | The bucket is never public. This is the control that fails loudest and matters most |
| **CloudFront Origin Access Control** | The distribution is the only reader. No public bucket, no legacy OAI |
| **Uploads land in a quarantine prefix** | Presigned direct-to-S3 puts arbitrary bytes in your bucket. The object is not servable until the fetch worker has verified magic bytes and re-encoded it ([../techstack/infrastructure.md](../techstack/infrastructure.md)) |
| **`Content-Type` set by the server, `nosniff`, no inline HTML from assets** | An HTML file on the assets origin is an XSS on the assets origin |
| **Separate buckets per origin** | Published artifacts and uploaded assets do not share a bucket, a policy, or a blast radius. Terraform state shares neither ([build-pipeline.md](build-pipeline.md)) |
| **Versioning and lifecycle rules** | Versioning is the recovery path from a bad publish or a destructive bug; lifecycle rules are how retention actually happens rather than being intended |

## CSS injection via art-direction tokens

**This is the newest attack surface and the one most likely to be missed.** It arrives in v2 with user-authored art directions and is amplified in v3 when the AI derives them.

An art direction is a bundle of token values that become CSS custom properties. From v2 those values are partly user-controlled; from v3 they can originate from an AI reading an attacker-supplied reference. Combined with the `style-src 'unsafe-inline'` that art directions require, an unvalidated token value is a script-adjacent injection point.

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

## The Slot sandbox

```html
<iframe srcdoc="..." sandbox="allow-scripts" referrerpolicy="no-referrer"></iframe>
```

**`allow-same-origin` must never be added.** With `allow-scripts` alone the frame has an opaque origin: `localStorage` throws, `document.cookie` is unavailable, `parent.document` throws, and no credentialed request is possible. Adding `allow-same-origin` alongside `allow-scripts` lets the frame remove its own sandbox attribute and defeats the entire control.

Also never granted: `allow-top-navigation` (prevents redirecting the viewer to a phishing page), `allow-popups`, `allow-modals`, `allow-forms`, `allow-downloads`.

A CSP inside the `srcdoc` provides the second layer:

```
default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:;
```

Brand and art-direction tokens are injected as CSS variables into the srcdoc — through the same validation as above, since srcdoc content is assembled by string concatenation and is the one place a bad token value would land directly in markup.

Sandbox correctness is asserted by tests that execute inside a real frame. See [testing.md](testing.md).

## XSS in the renderer

The scene tree is JSON rendered by React, which escapes by default. `dangerouslySetInnerHTML` appears nowhere outside the Slot iframe path — this is a lint rule, not a convention.

Specific paths that need care:

**`CTA.href`** — restricted to URLs from the Brief, plus a scheme allowlist rejecting `javascript:`, `data:`, `vbscript:`, and protocol-relative URLs. See [prompt-injection.md](prompt-injection.md).

**`AbstractVisual`** — generates SVG and CSS from an enum generator and a numeric seed. No user string reaches the output.

**Live data values** — rendered as text nodes, formatted by a locale-aware number formatter. A cell containing `<script>` renders as visible characters. It must never be formatted into a template string that becomes markup.

**Personalization fields** — same treatment. A company name is a text node, always.

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

**GLB/USDZ** (v3) parse in an isolated worker with triangle, texture, and file-size caps enforced *before* full decode. Draco and meshopt compression are decompression-bomb vectors with the same shape as image bombs. Failure produces the poster frame that [../v3/dimensional.md](../v3/dimensional.md) already requires.

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
