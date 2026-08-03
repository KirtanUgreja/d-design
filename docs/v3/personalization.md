# Personalization & Analytics

One experience, one link per recipient, each carrying that account's name, logo, and industry. Then: who opened it, and how far they got.

For account-based marketing this is the pairing that matters. A PDF cannot tell you Acme opened it three times and stopped before the pricing scene.

## Signed per-recipient links

```
/e/[experienceId]/r/[token]
```

`token` is signed server-side and resolves to a `recipients` row. It cannot be edited into someone else's variant, cannot be guessed, and requires no tracking script, no IP enrichment, and no third-party cookie.

```
recipients  id, experience_id, token, company, logo_asset_id,
            industry, contact_name, custom, created_at
```

Recipients are added by CSV upload or one at a time. CRM sync is a v4 integration question, not a v3 feature — the value here is the link, not the plumbing that generates the list.

The unpersonalized URL `/e/[id]` stays live and renders clean defaults. Every personalized field has a fallback; a viewer must never see `{{company}}` or an empty gap where a logo was.

### One static artifact, fields fetched at view

**A published experience is a static object on a CDN with no origin server behind it** ([../techstack/infrastructure.md](../techstack/infrastructure.md)). That is what makes publishing cheap, unattackable, and immune to a viral launch page — and it means there is nothing to render a per-recipient variant at request time.

```
recipient link ──▶ CloudFront: the same static shell every recipient gets
                          │
                          └──▶ GET https://api.<domain>/r/fields  (five fields)
```

The alternative — pre-rendering one artifact per recipient — was rejected: a thousand recipients is a thousand publishes, and a copy edit means republishing all of them. One shell, one renderer, one publish path.

**This is the decision that ended `connect-src 'none'`**, and it is recorded as one of the two trades in the stack that cost a stated guarantee ([../techstack/decisions.md](../techstack/decisions.md)). The published page was specified to make zero outbound requests. It now makes exactly two — this fetch and the analytics beacon — named as **exact paths** in the CSP, not `'self'` and not a host:

```
connect-src https://api.<domain>/r/fields https://api.<domain>/v/beacon;
```

The guarantee degrades from *this page cannot talk to anything* to *this page talks to two endpoints you own, and a browser test proves it talks to nothing else*. Weaker, still strong, and the test in [../security/testing.md](../security/testing.md) changes from "zero requests" to "these two and no others" — asserted in a real browser, because that is the only place it is true or false.

**A token now travels in a client-side request, which raises the stakes on three things that would otherwise be hygiene:**

| | Why |
|---|---|
| `Referrer-Policy: no-referrer` | A token in a URL leaks through the `Referer` header to every third-party resource the page loads. This is how recipient links actually escape |
| `Cache-Control: private, no-store` on the fields response | A personalized response cached by a shared proxy is served to the next viewer |
| CORS validated against verified domains — **never reflect `Origin`** | The endpoint is called cross-origin from published pages on customer domains. Reflecting the requesting origin turns it into an open endpoint |

The fields endpoint is a Vercel route rather than a static object, so it is the one part of the personalized path where the cache-deception controls in [../security/platform-and-packages.md](../security/platform-and-packages.md) still apply in full.

**Restoring `connect-src 'none'` is possible and deliberately deferred.** Analytics would move to CDN access logs and personalization to per-recipient pre-rendering. Both are viable; neither is worth doing before there are users to prove the feature matters.

## What varies

Five named fields. Not arbitrary text, not whole scenes.

| Field | Example use |
|---|---|
| `company` | "Built for **Acme**" |
| `logo` | Their mark beside yours in a `LogoWall` |
| `industry` | Selects one of several pre-written proof points |
| `contactName` | "**Dana** — here's what we discussed" |
| `custom` | One free line per recipient |

**The build phase suggests insertion points; the user confirms them.** The AI proposes "this headline would personalize well" and writes both the personalized and default forms. Nothing is personalized without review.

### Why not regenerate per recipient

Deeper personalization is technically easy and strategically fatal. Regenerating scene copy per viewer means every recipient receives marketing copy no human approved — the same failure v1 designed its whole intake around avoiding.

Substitution happens at render, from reviewed templates. There is no generation call in the personalized path.

## Analytics

```
views  id, experience_id, recipient_id?, scroll_depth, reached_cta,
       duration_ms, created_at
```

Four things worth knowing, and no more: did they open it, how far did they scroll, did they reach the CTA, how long did they stay.

Scroll depth as a percentage of the experience, plus the deepest scene reached — "stopped at the pricing scene" is the sentence a marketer actually acts on, and it needs the scene, not a number.

**The beacon is an unauthenticated write endpoint**, which is a category worth naming rather than discovering. Any published page can call it, from any origin, with no session — that is what it is for. So it is designed as one: the payload is a small fixed schema Zod-parsed at entry, the experience id is validated against a real published experience, values are range-clamped, and it is rate-limited per source independently of generation quotas ([../techstack/backend.md](../techstack/backend.md)). Inflated numbers are the realistic abuse, and the honest mitigation is that analytics is a marketing signal rather than a billing input.

### Privacy: aggregate by default, identified opt-in

`views.recipient_id` is **nullable, and null unless the publisher explicitly enables identified tracking.** That nullability is the privacy design, not an implementation detail.

| | Default | Opt-in |
|---|---|---|
| Scroll depth, CTA reach, duration | ✅ anonymous | ✅ |
| Which account opened it | ❌ | ✅ |
| Consent banner required | no | yes, publisher's responsibility |
| DPA required | no | yes |

Identified tracking means tracking named people at named companies. In the EU that requires consent, a retention policy, deletion on request, and a data processing agreement. Aggregate-by-default keeps the feature shippable for everyone; opting in moves the burden to the publisher, who is the data controller and the one with the customer relationship.

Ship with retention limits and a delete-recipient action from day one. Retrofitting deletion into an analytics table is genuinely painful.

### What is deliberately not tracked

No cross-experience identity, no fingerprinting, no third-party pixels, no session recording, no IP-based company detection. The signed link already tells you who — anything more is surveillance the product does not need to be valuable.

## Verification

- Tamper with a token → rejected, not silently defaulted
- Unpersonalized link → clean defaults, no empty braces, no missing-logo gap
- Publish without opting in → every `views.recipient_id` is null
- Delete a recipient → their view rows are removed or anonymized
- Personalized fields survive reskin, mode switch, and every locale
- A published page makes **exactly two** network requests and no others, asserted in a real browser
- The fields endpoint with a forged `Origin` → rejected, not reflected
- The fields response carries `no-store`; the page carries `no-referrer`
- A recipient's token never appears in a CDN access log, a `Referer` header, or an error report
