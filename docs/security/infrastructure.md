# Infrastructure

Threats where you are the target: your model key, your model budget, your processes.

**Rewritten 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)). v3 designed a VPC, a quarantined fetch worker and a job queue for features v4 does not have. What v4 does have is one secret, one browser and one spend surface, and this document is about those. The v3 controls return with the features that need them, and are kept at the end so they are not rebuilt from memory.

## The API and the worker

From phase 27 the backend is two processes from one codebase ([../techstack/backend.md](../techstack/backend.md)).

| | **api** | **worker** |
|---|---|---|
| Reachable from the internet | Yes | **No inbound port** |
| Holds the OpenRouter key | **No** | Yes |
| Calls a model | **Never** | Yes |
| Runs a browser | **Never** | Yes |
| Parses requests from strangers | Yes | No — it reads job files our own API wrote |

**The privileged process never parses a stranger's request, and the process that does has nothing worth stealing.** It is the same split v3 drew around its fetch worker, pointed at what v4 actually holds.

Rules that keep it real:

- **The key is in the worker's environment only.** Assert its absence in the API's environment with a test that reads it, the same control v3's `render` service carried.
- **A job file is a boundary.** The worker schema-parses it like any external input. It carries ids, never content.
- **The worker re-checks at execution**, not at enqueue: the deck still exists, the budget still has room. From phase 29, the owner still exists and is still entitled.
- **Deployed, the split must be a network rule and a secret scope**, not a convention. Phase 29's first check is that both hold ([../techstack/infrastructure.md](../techstack/infrastructure.md)).

Before phase 27 there is no API: the engine runs from the CLI on a developer machine, with the key in a local `.env`.

## Chromium in the worker

The worker renders every slide in headless Chromium to measure it. **The input is model-written markup, which is attacker-influenced**, so treat this browser as exposed — though far less than v3's fetch worker, which loaded pages an attacker chose from the live internet.

What bounds it:

| Control | |
|---|---|
| **The markup is sanitized and linted first** | No script, no `url()`, no external reference reaches the browser ([content-and-web.md](content-and-web.md)) |
| **Every request is aborted except `data:`** | A sanitizer miss still cannot fetch or exfiltrate |
| **`script-src 'none'` on the rendered page** | A sanitizer miss still cannot execute |
| **A fresh context per deck, always disposed** | No state carries between decks |
| **Hard timeouts, kill the page on breach** | A pathological layout is the cheapest denial of service available |
| **Element, depth and size limits per slide** | Enforced before render |
| **Current Chromium** | Rebuild on a schedule, not only on code change |

**The container trap still applies at phase 29.** Containers do not run Chromium in its sandbox without a seccomp profile; Chromium fails to start, the internet says add `--no-sandbox`, and it works. For a browser rendering our own sanitized markup with the network cut, running without Chromium's sandbox under Docker's default seccomp is a defensible trade — v3's `render` service made it — **but decide it deliberately at phase 29 and write the reason down**, because this process also holds the model key. Non-root user, read-only root filesystem and capped memory regardless.

**Assume it all fails.** A renderer escape lands in a process with the OpenRouter key and the deck store. That is a real loss and the reason for three things: a spend limit on the key itself, a key that can be rotated in one step, and a worker with no inbound port so the escape cannot be reached from outside in the first place.

## Failing closed — OWASP A10

**A10 Mishandling of Exceptional Conditions** (November 2025): uncaught exceptions, race conditions, and failing open.

> **Availability degrades open. Authorization degrades closed.**

| Failure | Correct behavior |
|---|---|
| An image fails to generate | The slide ships without it — degrade open, nothing is protected here |
| A slide fails QA after two repairs | A safer composition, then a visible flag |
| **The budget check throws or cannot read the ledger** | **Refuse the model call** |
| **JWT verification errors, or JWKS is unreachable** (phase 29) | **401** |
| **The owner lookup fails** (phase 29) | **Deny** |
| **The kill switch cannot be read** (phase 29) | **Treat as on** |
| **A version check cannot run on a write** | **Reject the write** |

The distinction is whether a failure could grant something. A slide without its image has been given nothing. A model call made because the ledger was unreadable has.

**Test this by making the check throw**, not by reasoning about it. Fail-open is invisible in review: the `except` that returns a permissive default looks like defensive programming right up until it is the vulnerability.

The race half of A10 has two instances here. **A budget checked and then spent as two steps** lets concurrent slide calls all pass the same check; the check reserves against the ledger under the deck's lock. **Two writers on one deck** is the other, closed by the single-writer rule ([tenancy-and-data.md](tenancy-and-data.md)).

## Denial of wallet

Generation is the expensive operation, and v4 is quality-first: an estimated $1.5–3.5 per deck. The likeliest attack needs no skill — a loop.

| Control | From |
|---|---|
| **A per-deck `budget_usd` hard cap**, checked before every model call, failing closed | Phase 22 |
| **Literal limits in code**: repair rounds ≤2, searches and images per deck | Phase 22–25 |
| **Pinned model ids** | Phase 22. An alias repointed by a provider cannot move the price of a call |
| **A spend limit on the OpenRouter key** | Phase 22. The outer ceiling under everything else |
| **Per-user daily budget, rate limits** | Phase 29 |
| **A global kill switch** | Phase 29. Reachable from a phone |
| **Email verification before first generation** | Phase 29 |

The first denial-of-wallet is not an attacker. It is our own repair loop or a retry storm, which is why the per-deck cap exists seven phases before accounts do.

A theme re-roll regenerates or re-repairs every slide. It is the most expensive single user action; **warn before it** and count it against the same budget.

## Secrets

| | |
|---|---|
| **OpenRouter key** | Worker only. Never in the API's environment, never in `web`, never in a client bundle. Asserted |
| **Auth provider secret** (phase 29) | API only. The JWKS is public; the management key is not |
| **Database credentials** (phase 29) | API and worker. Never `web` |

Nothing in the cost ledger, `events.jsonl`, logs or error reports carries prompt, brief or deck content. Error trackers capture request bodies by default, which is the most common accidental leak.

## What returns with features v4 does not have

Kept so the control arrives with the feature. The full v3 text is in git history at commit `8169fd9`.

**URL import or "paste a link" → SSRF.** A server that fetches a user-supplied URL can be pointed at `169.254.169.254`, `localhost` and the private network. **Network isolation is the control**: the fetch runs in a process that cannot route to anything worth reaching. Application checks come second — `https` only, reject private and reserved ranges in IPv4 and IPv6, **pin the resolved IP and connect to it**, re-validate every redirect hop, cap time and size. Note that `openrouter:web_search` is *not* this: OpenRouter's servers do the fetching, and ours fetch nothing the model or the user chose.

**File upload → hostile-byte parsers.** Image decoders, PDF extractors and SVG sanitizers run in an isolated process with no key and no deck store. Chromium pointed at attacker-chosen pages needs its sandbox and a seccomp profile, never `--no-sandbox`.

**A job queue → payload rules.** Payloads carry ids, never content; ownership is re-checked at execution; retries are bounded with a dead-letter path.

**Billing → entitlements.** Checked server-side at the point of action, never in the client. Stripe webhooks verified, deduplicated, and reconciled on read. Downgrade behaviour defined before the first downgrade.

**Next.js-specific:** remote image optimization stays off, and no rewrite destination is ever built from request-controlled input. The dev rewrite of `/api/*` points at one fixed host ([platform-and-packages.md](platform-and-packages.md)).
