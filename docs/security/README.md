# Security

> The threat model and every control, gated to the version that introduces the threat. The core problem: untrusted input reaches an LLM whose output becomes a web page.

**Start here:** the *Adversaries* and *Trust boundaries* sections below — they route to everything else by threat rather than by topic.

**Looking for one specific thing?** Jump to [Find it fast](#find-it-fast).

Security is cross-cutting, so it lives outside the version directories. But the threats arrive on different schedules, and that matters more than it looks.

## The unusual thing about this app

**Untrusted input reaches an LLM whose output becomes a web page.**

That sentence is the product and the threat at the same time. No framework protects against it, and it is the reason this directory leads with prompt injection rather than with the usual OWASP ordering.

Five distinct paths carry untrusted content into generation:

| Path | Arrives in |
|---|---|
| Uploaded documents and PDFs (intake) | v1 |
| Fetched URLs (art-direction derivation) | v3 |
| Airtable / Notion cell values (live data) | v3 |
| CSV recipient fields (personalization) | v3 |
| User-authored art-direction token values | v2 |

## Adversaries, in effort order

1. **Attacker via injected content** — plants instructions in a PDF, a page, or a spreadsheet cell that the AI obeys. Product-specific, and nothing off the shelf helps. → [prompt-injection.md](prompt-injection.md)
2. **Malicious platform user** — reaches another tenant's data, or burns your model budget. → [tenancy-and-data.md](tenancy-and-data.md), [infrastructure.md](infrastructure.md)
3. **Attacker targeting viewers** — poisons an experience so the published page attacks the audience. Worst reputationally: your customer's prospects get hit on your customer's launch page. → [content-and-web.md](content-and-web.md)
4. **Attacker targeting your infrastructure** — SSRF into cloud metadata, credential theft, denial-of-wallet, and the build pipeline that holds production credentials. → [infrastructure.md](infrastructure.md), [build-pipeline.md](build-pipeline.md)
5. **Nobody in particular** — an automated agent sweeping the internet, which in 2026 will probe this product thoroughly whether or not anyone is interested in it. It costs nothing to point at a small target now. → [adversarial-ai.md](adversarial-ai.md)

Adversary 5 does not introduce new controls; it changes which existing ones you can rely on. Anything that works by *recognizing* an attack degrades against something that never gets bored. Anything that works by *having nowhere for the attack to land* holds.

## Trust boundaries

```
 user input ─┬─ approved by a human ──▶ Brief ──▶ generation
             └─ imported / fetched ────▶ Brief ──▶ generation   ◀── UNTRUSTED
                                                      │
                                       schema-validated Scene JSON
                                                      │
                            ┌─────────────────────────┴──────────────┐
                            ▼                                        ▼
                    React renderer                          Slot (srcdoc iframe)
                    (escapes by default)              sandbox="allow-scripts" only
                            │                          no same-origin, no network
                            ▼                                        │
                    published page  ◀────────── separate origin ─────┘
                            │
                            ▼
                     viewer's browser
```

The runtime topology is a fourth boundary, and it is the newest ([../techstack/backend.md](../techstack/backend.md)):

```
  web (Vercel)   api/jobs (Fargate)   render (Fargate)   fetch worker (Fargate)
  DB · sessions         DB · renderer · models    NO db · NO vpc route
  no hostile input      no hostile input          hostile input only
                                                  Chromium · parsers
```

**The privileged processes never parse hostile bytes; the process that parses hostile bytes has nothing worth stealing.** Everything the attacker can influence — URLs, screenshots, PDFs, uploaded images — is handled in the container with no database access, no route to the VPC, and one narrowly-scoped key.

Three boundaries carry the weight:

**The `Scene` schema.** A fully compromised model can still only cause a rejected generation — nothing it emits reaches a page unless it is valid `Scene` JSON. There is no field where "run this command" fits. This is the single strongest control in the system, and it was built for design reasons rather than security ones.

**The sandbox.** `Slot` is the one field that becomes executable code. An `srcdoc` iframe with `allow-scripts` and *without* `allow-same-origin` has an opaque origin: no storage, no cookies, no parent DOM, no credentialed requests.

**Origin separation.** The app, published experiences, and uploaded assets live on three distinct origins. An XSS in published content cannot reach an app session.

## When each control is needed

Building them in the wrong order wastes effort on threats that do not exist yet.

| Version | What it introduces | Controls that become necessary |
|---|---|---|
| **v1** | Imports, AI generation, `Slot`, uploads, publishing | Prompt injection defenses · schema validation · `CTA.href` restriction · sandbox correctness · upload handling · origin separation |
| **v2** | User-authored art directions | **CSS injection via token values** — see [content-and-web.md](content-and-web.md) |
| **v3** | Accounts, URL fetching, integrations, PII, domains, billing | Authentication · RLS and tenant isolation · SSRF · credential encryption · retention · token design · cache isolation for personalized pages · custom-domain verification and dangling-DNS handling · entitlement enforcement · quotas |

Three controls are **version-independent and live from the first deploy**: keeping the framework and the untrusted-input parsers patched ([platform-and-packages.md](platform-and-packages.md)), failing closed on anything that grants access ([infrastructure.md](infrastructure.md)), and a build pipeline that cannot be used to skip both ([build-pipeline.md](build-pipeline.md)). None waits for a feature to arrive.

One control is **live from the first model call, which is v1**: model routing and retention ([third-parties.md](third-parties.md)). A customer's embargoed launch messaging reaches a third party the first time anything is generated, and that is long before accounts, RLS, or any other v3 control exists.

RLS does not exist before v3, because multi-tenancy does not exist before v3. Prompt injection is live from the first generated experience.

## Documents

| | |
|---|---|
| [prompt-injection.md](prompt-injection.md) | The five paths, and why the schema does most of the work |
| [tenancy-and-data.md](tenancy-and-data.md) | Authentication, RLS, server-mediated reads, credentials, PII, retention |
| [content-and-web.md](content-and-web.md) | Origins, CSP, sandbox, XSS, uploads, tokens, custom domains, clickjacking |
| [infrastructure.md](infrastructure.md) | SSRF, failing closed, denial-of-wallet, billing entitlements |
| [platform-and-packages.md](platform-and-packages.md) | Framework CVEs, cache poisoning, the parsers that touch hostile bytes, version floors |
| [third-parties.md](third-parties.md) | Where customer data actually goes — model routing, subprocessors, the GDPR obligation |
| [build-pipeline.md](build-pipeline.md) | CI/CD as an attack path — OIDC trust policies, Terraform state, publishing, images |
| [ai-built-app-failures.md](ai-built-app-failures.md) | The four mistakes that account for nearly every AI-built-app breach, audited against this design |
| [adversarial-ai.md](adversarial-ai.md) | What changes when the attacker is a machine — and the OWASP mapping |
| [testing.md](testing.md) | The automated suite and the manual checklist |
| [operations.md](operations.md) | Disclosure, incident response, dependencies, release gate |

Two are worth reading even if you skip the rest. [ai-built-app-failures.md](ai-built-app-failures.md) is the measured evidence of how applications built this way actually get breached — in one sample of 1,645, **~70% shipped with row-level security disabled**. [adversarial-ai.md](adversarial-ai.md) carries the OWASP mapping (LLM Top 10 2025, Agentic Top 10 2026, Web Top 10 2025) and the honest answer to whether this can be made unhackable.

## Find it fast

| If you need… | Go to |
|---|---|
| Whether a poisoned PDF can do real damage | [prompt-injection.md](prompt-injection.md) → "Why the schema does most of the work" |
| What tools the AI may call, and the tier rules | [prompt-injection.md](prompt-injection.md) → "Defense 5", and [../techstack/pipeline-tools.md](../techstack/pipeline-tools.md) |
| RLS policies, and the session-variable pattern | [tenancy-and-data.md](tenancy-and-data.md) → "RLS for authenticated users" |
| Auth rules — sessions, OAuth linking, reset tokens, enumeration | [tenancy-and-data.md](tenancy-and-data.md) → "Authentication" |
| What is stored about a recipient, and for how long | [tenancy-and-data.md](tenancy-and-data.md) → "PII and retention" |
| The CSP for a published page | [content-and-web.md](content-and-web.md) → "CSP" |
| The `/r/fields` and `/v/beacon` endpoints, and CORS | [content-and-web.md](content-and-web.md) → "The two public endpoints" |
| Sandbox flags for `Slot` | [content-and-web.md](content-and-web.md) → "The Slot sandbox" |
| Upload handling — magic bytes, SVG, decompression bombs | [content-and-web.md](content-and-web.md) → "Uploads" |
| Custom domains and dangling DNS | [content-and-web.md](content-and-web.md) → "Custom domains" |
| SSRF, and why network isolation beats URL filtering | [infrastructure.md](infrastructure.md) → "SSRF" |
| Headless Chromium hardening | [infrastructure.md](infrastructure.md) → "Headless Chromium is the most exposed component" |
| The fail-closed rule | [infrastructure.md](infrastructure.md) → "Failing closed — OWASP A10" |
| Denial of wallet, quotas, the kill switch | [infrastructure.md](infrastructure.md) → "Denial of wallet" |
| Package version floors, and known CVEs | [platform-and-packages.md](platform-and-packages.md) → "Version floors" |
| Cache poisoning and web cache deception | [platform-and-packages.md](platform-and-packages.md) → "Cache poisoning and web cache deception" |
| Where customer prompts actually go | [third-parties.md](third-parties.md) → "The model route is not one vendor" |
| The GDPR subprocessor obligation | [third-parties.md](third-parties.md) → "The full subprocessor list" |
| OIDC trust policies, Terraform state, publishing | [build-pipeline.md](build-pipeline.md) |
| What an automated attacker changes | [adversarial-ai.md](adversarial-ai.md) → "The one thing that actually changes" |
| The OWASP mapping | [adversarial-ai.md](adversarial-ai.md) → "OWASP mapping" |
| A test to write | [testing.md](testing.md) — organized by threat, gated by version |
| What to do during an incident | [operations.md](operations.md) → "Incident response" |
| The release gate | [operations.md](operations.md) → "Release gate" |

## Principles

**Prefer structural controls over filters.** A blocklist you must keep correct forever is worse than an architecture where the attack has nowhere to land. Network-level isolation beats URL parsing; an opaque-origin iframe beats scanning generated JavaScript; a schema with no dangerous field beats detecting dangerous output.

**The AI may arrange, style, and translate what the user gave it. It may not invent the subject.** This began as a quality rule — never invent marketing claims, never generate the product — and it turns out to be a security rule too. Applied to URLs it means `CTA.href` comes from the Brief, which makes an injected phishing link structurally impossible rather than merely unlikely.

**Assume the model is compromised.** Design so that a fully attacker-controlled model produces a page that is ugly, not a page that is dangerous.

## Connects to

| | |
|---|---|
| [../techstack/README.md](../techstack/README.md) | The runtime topology every control in this directory assumes |
| [../coderules/patterns.md](../coderules/patterns.md) | The rules that make these controls mechanical — the tenant wrapper, failing closed, the model seam |
| `v3/compliance.md` | Legal obligations, which are adjacent to but distinct from security |
| `v3/personalization.md` | The product side of recipient tokens and identified tracking |

**Fail closed on anything that grants; fail open on anything that merely displays.** A quota check that cannot run refuses. A 3D model that cannot load shows a poster. This is OWASP's newest category and this product has an unusual number of fallback paths — see [infrastructure.md](infrastructure.md).

**Nothing here is unhackable, and the goal is not to be.** The goal is that the attacks which succeed produce outcomes you can live with, and that the ones you cannot live with have no path at all. A threat model claiming completeness is the one that gets believed and then breached.
