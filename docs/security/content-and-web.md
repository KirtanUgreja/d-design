# Content & Web

Defending the viewer. Everything here protects someone who opens a published experience — your customer's prospect, on your customer's launch page.

## Three origins

```
app.<domain>       the editor, sessions, auth
pages.<domain>     published experiences, custom domains
assets.<domain>    uploaded and generated files
```

The single highest-leverage decision in this directory. An XSS in published content cannot reach an app session, because it is not the same origin — no shared cookies, no shared storage, no reachable DOM.

**Custom domains are where this silently breaks.** A customer domain must be served from the published-content origin and must never be same-origin with the app. If a custom domain ever resolves to the app origin, the isolation is gone and nothing else in this document compensates.

## CSP

**Published pages:**

```
default-src 'none';
script-src  'self';
style-src   'self' 'unsafe-inline';
img-src     'self' https://assets.<domain> data:;
font-src    https://assets.<domain>;
connect-src 'none';
frame-ancestors *;
base-uri    'none';
form-action 'none';
```

`connect-src 'none'` is load-bearing: it is the enforcement of the claim in [../v3/live-data.md](../v3/live-data.md) that a published page makes zero outbound requests. Data is baked in server-side, so the page has no reason to talk to anything — and now it cannot.

`frame-ancestors *` is deliberate. Embedding published experiences is a feature.

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

**GLB/USDZ** (v3) parse in an isolated worker with triangle, texture, and file-size caps enforced *before* full decode. Draco and meshopt compression are decompression-bomb vectors with the same shape as image bombs. Failure produces the poster frame that [../v3/dimensional.md](../v3/dimensional.md) already requires.

## Custom domains

| Control | |
|---|---|
| TXT-record ownership challenge before serving | Stops claiming a domain you do not control |
| Periodic re-verification, auto-unbind | Prevents hosting content for a domain the customer no longer owns |
| Served from the published-content origin only | Never same-origin with the app. Restated because this is where origin separation breaks |
| Per-account domain cap | Limits spam and SEO abuse |

Certificate issuance is automated per verified hostname. Rate-limit issuance requests — an unbounded issuance path is both a cost problem and a way to hit a CA's rate limits and take down legitimate provisioning.
