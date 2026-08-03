# Infrastructure

Threats where you are the target: your network, your model budget, your revenue.

## SSRF

v3 lets a user paste a URL and your server fetches it, for art-direction derivation. This is textbook SSRF, and the interesting targets are internal:

```
http://169.254.169.254/latest/meta-data/     cloud instance credentials
http://metadata.google.internal/             GCP equivalent
http://localhost:5432                        your database
http://10.0.0.0/8                            your VPC
file:///etc/passwd                           local files
```

### Network isolation is the control

**URL fetching runs in a dedicated worker with egress-only networking and no route to the VPC, the database, or the metadata endpoint.**

The control is not "we reject bad URLs." It is that the process doing the fetching *cannot reach anything worth reaching*. A bypass in URL parsing then lands on a machine with nothing on it.

This matters because application-level blocking is a game you keep losing: DNS rebinding (a hostname that resolves to a public IP on validation and a private one on fetch), IPv6-mapped IPv4, decimal and octal IP encodings, redirect chains that pivot on the third hop, and `0.0.0.0`. Every one of these has broken a careful blocklist somewhere.

The same worker holds decrypted integration credentials — see [tenancy-and-data.md](tenancy-and-data.md). One isolated process for all outbound network access, and it is the only thing holding secrets.

### Application-level checks anyway

Cheap, and they turn a network-isolated failure into an early, loggable rejection:

- Scheme allowlist: `https` only. No `http`, `file`, `gopher`, `ftp`, `data`
- Resolve DNS, reject private, loopback, link-local, and reserved ranges — IPv4 and IPv6
- **Pin the resolved IP and connect to it**, rather than re-resolving. This is what actually stops DNS rebinding
- Maximum 3 redirects, re-validating the target at every hop
- 10-second timeout, 10MB response cap
- Log every rejection. Repeated attempts are a signal worth having

## Denial of wallet

Generation is the most expensive operation in the product, and the free tier gives it away. This is the likeliest real-world attack because it needs no skill — a loop and a script.

| Control | |
|---|---|
| **Per-account quotas** | Hard caps per plan, checked server-side *before* the model call. The `generations` table already records what is needed |
| **Rate limits** | Per account and per IP. Also catches runaway client retry loops, which is the more common cause |
| **Email verification before first generation** | Blocks throwaway-account farming. Friction at the wow moment, accepted deliberately |
| **Spend alerting + global kill switch** | You find out from a monitor, not an invoice |

The kill switch is the one that matters. Quotas and rate limits are bypassable in ways you have not thought of; a global spend ceiling that halts generation fails safe regardless of how it was reached. Build it early — it is a config flag and a check, not a system.

Related cost paths: the build phase runs one call per scene, so a 12-scene experience is 12 calls; transcreation multiplies by locale count; reskin re-runs transcreation for every locale. **Warn before a reskin on a multi-locale experience** — it is the single most expensive user action in the product, and a user clicking it repeatedly is indistinguishable from an attack.

Live data refreshes on a schedule rather than per view, which decouples cost from traffic entirely. Keep it that way.

## Billing and entitlements

**Entitlement checks are server-side, at the point of action.** Publishing to a custom domain, removing branding, enabling personalization or analytics — each verifies the subscription server-side when it happens. A client-side check is a UI affordance, never a control.

**Stripe webhooks:** verify the signature on every event, deduplicate by event id, and treat delivery as unreliable. Reconcile subscription state on read rather than trusting that every webhook arrived — a missed `subscription.deleted` otherwise means indefinite free access.

**Downgrade behavior is defined, not emergent.** When a subscription lapses: custom domains stop resolving, branding returns, personalized links keep working (they are already out in the world and breaking them punishes the recipient, not the customer), analytics collection stops. Decide this before the first downgrade, not during it.

## Secrets

| | |
|---|---|
| Model API keys | Server-only, never in a client bundle. Asserted in the build |
| Supabase service role key | Server-only. Grep the build output for its prefix |
| Integration OAuth tokens | Envelope-encrypted, decrypted only in the fetch worker |
| Signing keys | Rotatable. Recipient tokens are stored-random, so rotation does not invalidate campaigns |

Nothing in the `generations` table, application logs, or error reporting carries prompt content, scene content, or recipient fields. Error trackers are the most common accidental leak, because they capture request bodies by default.

## Availability

Not a primary concern for this product — a launch page being briefly unreachable is bad, not catastrophic — but two cheap things:

**Published pages are static after render.** They do not query the database or an LLM per view, so traffic on a viral launch page costs nothing and cannot exhaust a connection pool.

**The editor degrades independently of published pages.** If generation is down, published experiences keep serving. Keep those paths separate; it costs nothing at the start and is expensive to untangle later.
