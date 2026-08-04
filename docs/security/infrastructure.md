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

**There are two workers, and this is the quarantined one.** The fetch worker touches hostile input — URLs, screenshots, PDFs, uploaded images — and has no database access, no VPC route, and no secret beyond the integration token it is actively using. A separate **`jobs` worker** runs PGQueuer with full database access and never parses attacker-controlled bytes, and a **`render`** service holds the renderer but neither database credentials nor a model key. Splitting them means the process holding database credentials is never the process rendering an attacker's webpage. Topology in [../techstack/infrastructure.md](../techstack/infrastructure.md); the isolation is a subnet and a security group, so the socket-level test below asserts the network rather than the code.

### Application-level checks anyway

Cheap, and they turn a network-isolated failure into an early, loggable rejection:

- Scheme allowlist: `https` only. No `http`, `file`, `gopher`, `ftp`, `data`
- Resolve DNS, reject private, loopback, link-local, and reserved ranges — IPv4 and IPv6
- **Pin the resolved IP and connect to it**, rather than re-resolving. This is what actually stops DNS rebinding
- Maximum 3 redirects, re-validating the target at every hop
- 10-second timeout, 10MB response cap
- Log every rejection. Repeated attempts are a signal worth having

### Next.js-specific SSRF paths

Two beyond the fetch worker, both from the July 2026 advisory set ([platform-and-packages.md](platform-and-packages.md)):

- **`rewrites()` / `redirects()`** that build a destination hostname from request-controlled input become SSRF and open redirect respectively. Custom-domain routing resolves a **verified hostname to an experience id via a database lookup** — never by constructing a destination from the incoming `Host` header.
- **Remote image optimization** (`/_next/image`) fetches arbitrary remote URLs by design. This product self-hosts every image on `assets.<domain>`, so the remote path is a surface with no corresponding feature. **Turn it off.**

## Headless Chromium is the most exposed component in the product

The fetch worker runs Playwright to screenshot user-pasted URLs ([../techstack/infrastructure.md](../techstack/infrastructure.md)). That means **the most-attacked software on the internet, pointed at pages an attacker chose.**

### The trap, and it is the default

**Containers do not run Chromium in its sandbox unless you provide a seccomp profile.** Chromium fails to start, the internet says add `--no-sandbox`, it works, and the renderer process — the one parsing attacker-supplied HTML, CSS, fonts, and images — is now running with no isolation from the rest of the container.

`--no-sandbox` is acceptable in CI against pages you wrote. **It is exactly wrong here**, because here the pages are the threat.

| Control | |
|---|---|
| **Seccomp profile, sandbox on** | The documented way to run headless Chrome in a container. Not `--no-sandbox` |
| **Non-root user, and a separate user for the browser** | The recommended pattern for untrusted URLs specifically |
| **Read-only root filesystem**, writable temp only | A renderer escape lands somewhere it cannot persist |
| **One fresh browser context per fetch, always disposed** | No state carries from one target to the next |
| **Hard timeouts, and kill the process on breach** | A page that hangs the browser is the cheapest denial of service available |
| **`--disable-dev-shm-usage`, capped memory** | Chromium OOM in a container is a routine failure, not an exotic one |
| **Current Chromium** | The patch window here is days, not weeks — [adversarial-ai.md](adversarial-ai.md), and [build-pipeline.md](build-pipeline.md) on rebuilding on a schedule rather than only on code change |

### And this is what the isolation is for

Assume all of the above eventually fails. Chromium sandbox escapes are real, they are valuable, and a solo operator will not out-patch them.

**A full renderer escape lands on a container with no database access, no VPC route, no metadata endpoint, and one narrowly-scoped KMS grant.** That is the entire reason the fetch worker exists as a separate task with its own subnet ([../techstack/infrastructure.md](../techstack/infrastructure.md)), and it is why the socket-level unreachability test in [testing.md](testing.md) is the most important test in the suite — it is the one that still holds when everything above has been bypassed.

The same reasoning explains a rule from [../coderules/dependencies.md](../coderules/dependencies.md): a hostile-input parser is a different severity depending on which container it is in. Chromium is that principle at its most extreme.

## The job queue

PGQueuer runs in the privileged worker, so its inputs deserve the same scrutiny as an HTTP route.

- **Job payloads are internal but not automatically trustworthy.** A payload is JSON in a database row; treat it as a boundary and schema-parse it in the handler ([../coderules/python.md](../coderules/python.md)). It is cheap, and it means a bug in an enqueue path cannot become arbitrary behavior in a worker.
- **Payloads carry ids, never data.** No brief text, no recipient fields, no credentials in a job row — the queue is a table, it is backed up, and it outlives the work.
- **Ownership is re-checked at execution, not trusted from enqueue time.** A job enqueued before an account was deleted or downgraded must not run with the old entitlement. This is [failing closed](#failing-closed--owasp-a10) applied to time.
- **Bounded retries and a dead-letter queue.** An unbounded retry on a job that calls a model is denial of wallet with a cron attached, and it is the version of that attack that comes from your own code rather than a user.
- **Job creation is subject to the same quotas as the action that caused it.** Enqueuing is cheap; the work is not.

Enqueue in the same transaction as the data change ([../coderules/dependencies.md](../coderules/dependencies.md)) — a publish that rolls back must not leave a job that publishes.

## Failing closed — OWASP A10

New to the OWASP Top 10 in the November 2025 revision: **A10 Mishandling of Exceptional Conditions**, 24 CWEs covering uncaught exceptions, race conditions, and failing open.

It gets its own section because this product is unusually exposed to it. Graceful degradation is a *feature* here — 3D falls back to a poster, live data to its last cached value, WebGPU to WebGL2, a missing locale to the source language, a failed AD derivation to an honest error. Every one of those paths is somewhere an attacker can ask: *what if I cause the failure?*

The rule, and it applies to code that has not been written yet:

> **Availability degrades open. Authorization degrades closed.**

| Failure | Correct behavior |
|---|---|
| 3D asset unavailable | Poster frame — degrade open, nothing is protected here |
| Live-data fetch fails | Last cached value, then the honest empty state |
| Quota check throws or times out | **Refuse the generation.** Never proceed because the check was unavailable |
| Entitlement lookup fails | **Deny the paid feature** |
| Recipient token validation errors | **Reject the token** |
| Domain verification lookup fails | **Stop serving that hostname** |
| Rate limiter unreachable | **Rate-limit as if tripped** |

The distinction is whether a failure could grant something. A viewer seeing a poster instead of a 3D model has been given nothing. A generation running because the quota service was slow has.

**Test this by making the check throw**, not by reasoning about it. A dependency-injected failure on each row above, asserting refusal. Fail-open is invisible in code review — it reads as ordinary error handling, and the `catch` that returns a permissive default looks like defensive programming right up until it is the vulnerability.

Race conditions are the other half of A10, and the one that matters here is **quota checked and then consumed as two separate operations**. Concurrent requests all read the same remaining balance and all proceed. The counter increment must be atomic in the database, not a read-modify-write in application code.

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
| Database credentials | Server-only, from Secrets Manager by task role. Never in a client bundle |
| Integration KMS key | Granted to the fetch worker's task role and nothing else |
| Integration OAuth tokens | Envelope-encrypted, decrypted only in the fetch worker |
| Signing keys | Rotatable. Recipient tokens are stored-random, so rotation does not invalidate campaigns |

Nothing in the `generations` table, application logs, or error reporting carries prompt content, scene content, or recipient fields. Error trackers are the most common accidental leak, because they capture request bodies by default.

## Availability

Not a primary concern for this product — a launch page being briefly unreachable is bad, not catastrophic — but two cheap things:

**Published pages are static after render.** They do not query the database or an LLM per view, so traffic on a viral launch page costs nothing and cannot exhaust a connection pool.

**The editor degrades independently of published pages.** If generation is down, published experiences keep serving. Keep those paths separate; it costs nothing at the start and is expensive to untangle later.
