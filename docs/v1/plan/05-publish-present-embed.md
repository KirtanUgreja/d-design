# Phase 05 — Publish, present, embed

> Three wrappers around one renderer. Nothing new is drawn; the point is that what you edit is byte-for-byte what ships, and that the published page is a static artifact rather than a route.

**Depends on:** [04](04-renderer.md) · **Blocks:** nothing (phase 06 can run in parallel) · **Spec step:** 4

This is the last phase before any AI is involved. After it, a hand-written scene tree can be published, opened in a private window, presented fullscreen, and embedded in someone else's page — which is the entire v1 delivery promise, proven without a single model call.

---

## Search

**Read first**

- [../../coderules/patterns.md](../../coderules/patterns.md) → rule 2 — how each mode wraps the core rather than configuring it
- [../../security/content-and-web.md](../../security/content-and-web.md) → "CSP", "Three origins" — and note carefully which parts are v3
- [../../coderules/performance.md](../../coderules/performance.md) → hot path 1, page load of a published experience
- [../../techstack/infrastructure.md](../../techstack/infrastructure.md) → "Delivery" — the shape v3 grows into, so v1's publish path is the same path with a different destination

**Grep for**

- `src/lib/storage.ts` — publishing writes an artifact through it. Do not write a second file-writing path
- `src/features/renderer/index.ts` — the only import. If a wrapper reaches into `renderer/blocks/`, the boundary rule failed
- `api/db/tenant.py` — every read of an experience goes through `as_user`, single user or not

**Verify externally**

- Next.js 16.3 route handler response headers, and how `cacheComponents` interacts with a route that streams a stored artifact
- Fullscreen API current behaviour on the browsers you care about — it is ~50 lines and the only part that has ever been quirky is exit handling

---

## Make

```
src/features/publish/
  index.ts
  publish.ts            renderToString → artifact → storage
  publish_data.py       SQLAlchemy, the published-at filter
  csp.ts                the header sets — published, embed, app
  publish.test.ts

src/features/present/
  index.ts
  fullscreen.tsx        Fullscreen API + keydown, wraps SceneRenderer
  motion-toggle.tsx     the in-page reduced-motion control, in the runtime

app/p/[id]/route.ts     serves the stored artifact
app/e/[id]/route.ts     same artifact, embed CSP
```

### Publishing is a render, not a route

```
publish() → renderToString(SceneRenderer) → HTML artifact → storage.ts → /p/[id] serves it
```

**The artifact is produced once, at publish, and served static.** No database query per view, no render per view, no model call ever. That is hot path 1 from [../../coderules/performance.md](../../coderules/performance.md), and building it this way in v1 means v3's move to S3 + CloudFront changes the destination and nothing else.

The page then **hydrates**, and Motion drives the reveals exactly as in the editor. Shipping a hand-written IntersectionObserver runtime instead would produce a lighter page and implement motion twice — and the second implementation is where the edit-equals-publish guarantee quietly leaks away ([../../techstack/frontend.md](../../techstack/frontend.md)).

`publish_data.py` owns the **service-role filter**: `where published_at is not null`. That clause is doing security work, and one data module per feature is what stops it being forgotten at the fiftieth call site ([../../coderules/patterns.md](../../coderules/patterns.md), rule 3).

### CSP — and the one place v1 is stronger than v3

```
default-src 'none';
script-src  'self';
style-src   'self' 'unsafe-inline';
img-src     'self' data:;
font-src    'self';
connect-src 'none';
frame-ancestors *;
base-uri    'none';
form-action 'none';
```

**`connect-src 'none'` genuinely holds in v1**, and it is worth stating plainly. [../../techstack/decisions.md](../../techstack/decisions.md) records the two endpoints that weaken it in v3 — the personalization field fetch and the analytics beacon. Neither exists yet. So v1 gets the original guarantee: *this page talks to nothing*, and the browser test asserts zero requests rather than exactly two.

Write the assertion as **zero** now. When v3 adds the endpoints, the test changes to two and the diff makes the trade visible — which is exactly how a deliberate weakening should read six months later.

Also on published responses:

```
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
```

`frame-ancestors *` is deliberate — embedding is a feature. The residual clickjacking risk is accepted and bounded: a published page has no session and no privileges, so there is nothing to hijack a click *into*, and `CTA.href` is a URL the customer supplied. **App routes are `frame-ancestors 'none'` and carry no `unsafe-inline`.** If a future feature ever puts something interactive and consequential on a published page, that trade has to be revisited with it.

`style-src 'unsafe-inline'` is required for the art-direction CSS variables. It is the reason v2's token grammar validation exists.

### Present

Fullscreen API plus a keydown handler, wrapping `SceneRenderer`. Arrow keys move between scene anchors. About fifty lines, and it is what keeps the word "presentation" honest ([../spec.md](../spec.md), Risk 3).

The **motion toggle** ships here, in the runtime, so every published experience gets it for free rather than each art direction re-implementing it ([../art-direction.md](../art-direction.md)).

### Embed

Publish with a different CSP header. Same artifact, same renderer, no second code path. If embed needs anything else, that is a signal the renderer grew a mode.

### The publish reveal, and the two things around it

The moment a URL exists is the one that gets screenshotted into Slack, and it is one of the four screens with a real design budget ([../../design/app.md](../../design/app.md)). The URL is large and copyable with the real page behind it, and open / embed / present are one click each.

Two adjacent things that are cheap here and awkward later:

**Republishing is explicit, and unpublish is real.** A live launch page must never change because someone typed in the editor. The `published_at` filter already gives unpublish for free; what it does not give is the 404 that follows, and **a customer's audience will hit that page.** Design it — an artifact that has been taken down is a different message from one that never existed.

**Social unfurls are a launch requirement, not a polish item.** The buyer's first act after publishing is pasting the link into Slack or LinkedIn in front of colleagues. A broken unfurl there is a product failure with an audience. OG images come from an auto-screenshot and Playwright is already in the stack ([../../techstack/frontend.md](../../techstack/frontend.md)), so this is a screenshot and four meta tags — as long as it happens at publish, alongside the render, rather than being bolted on once someone complains.

---

## Verify

**The gate** — green.

**End to end, by hand**

- [ ] Publish a hand-written fixture, open `/p/[id]` in a **private window**, and it renders complete
- [ ] Fullscreen, navigate with arrow keys, exit cleanly
- [ ] Embed `/e/[id]` in a blank HTML file on a different port, and it renders
- [ ] Republish after an edit and the served artifact changes
- [ ] Unpublish, then open the URL: a designed page, not a framework 404
- [ ] Paste a published URL into Slack and into LinkedIn. Both unfurl with the right image and title

**Security — the rows that go live here** ([../../security/testing.md](../../security/testing.md))

- [ ] **A published page makes zero network requests**, asserted in a real browser, not by reading headers
- [ ] CSP present and correct on published, embed, app, and srcdoc responses — four assertions, not one
- [ ] `frame-ancestors *` on published; `frame-ancestors 'none'` on app routes
- [ ] `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer` present
- [ ] A cache-key probe: `/p/<id>/x.css` and `/p/<id>/x.jpg` return 404 and nothing is cached. Web cache deception is mostly a v3 concern, but the probe costs one test and the answer should be "there is no router to be lenient"
- [ ] The build output contains no key-shaped strings — `sk-`, `eyJ`, long high-entropy values. Grep for shapes, not for known prefixes

**Performance — hot path 1**

- [ ] JS disabled: the published page is readable and complete. Text, images, and layout are in the HTML
- [ ] No third-party script, no analytics SDK, no tag manager. React and Motion are the entire JS budget and it is already committed
- [ ] Serving `/p/[id]` performs no database query and no render

---

## Skipped

| Not built | Trigger |
|---|---|
| S3 + CloudFront + three origins | v3. `storage.ts` already speaks S3 against MinIO, so this is a destination change ([../../techstack/infrastructure.md](../../techstack/infrastructure.md)) |
| Custom domains, ACM, dangling-DNS handling | v3, with real customers |
| The `/r/fields` and `/v/beacon` endpoints | v3. Their absence is why `connect-src 'none'` still holds |
| Publishing from the `render` service | v2, with the visual loop. In v1 a `web` route renders to local disk — one user, one experience at a time, no timeout pressure ([../../techstack/backend.md](../../techstack/backend.md)) |
| Cache invalidation on publish | No CDN to invalidate |
| PDF / PPTX export, speaker notes, presenter view | Not in v1, and asked for in week one. Have a real answer ready, not "coming soon" ([../spec.md](../spec.md), Risk 3) |

---

## Exit gate

- [ ] A hand-written scene tree can be published, viewed in a private window, presented fullscreen, and embedded — with no AI anywhere in the loop
- [ ] Published page makes zero network requests, proven in a browser
- [ ] Four CSP assertions passing
- [ ] The published page is complete without JavaScript
- [ ] Publishing and viewing share exactly one renderer, with no `mode` anywhere
