# Security

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
4. **Attacker targeting your infrastructure** — SSRF into cloud metadata, credential theft, denial-of-wallet. → [infrastructure.md](infrastructure.md)

## Trust boundaries

```
 user input ─┬─ approved by a human ──▶ Brief ──▶ generation
             └─ imported / fetched ────▶ Brief ──▶ generation   ◀── UNTRUSTED
                                                      │
                                          Zod-validated Scene JSON
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

Three boundaries carry the weight:

**The Zod schema.** A fully compromised model can still only emit valid `Scene` JSON. There is no field where "run this command" fits. This is the single strongest control in the system, and it was built for design reasons rather than security ones.

**The sandbox.** `Slot` is the one field that becomes executable code. An `srcdoc` iframe with `allow-scripts` and *without* `allow-same-origin` has an opaque origin: no storage, no cookies, no parent DOM, no credentialed requests.

**Origin separation.** The app, published experiences, and uploaded assets live on three distinct origins. An XSS in published content cannot reach an app session.

## When each control is needed

Building them in the wrong order wastes effort on threats that do not exist yet.

| Version | What it introduces | Controls that become necessary |
|---|---|---|
| **v1** | Imports, AI generation, `Slot`, uploads, publishing | Prompt injection defenses · schema validation · `CTA.href` restriction · sandbox correctness · upload handling · origin separation |
| **v2** | User-authored art directions | **CSS injection via token values** — see [content-and-web.md](content-and-web.md) |
| **v3** | Accounts, URL fetching, integrations, PII, domains, billing | RLS and tenant isolation · SSRF · credential encryption · retention · token design · custom-domain verification · entitlement enforcement · quotas |

RLS does not exist before v3, because multi-tenancy does not exist before v3. Prompt injection is live from the first generated experience.

## Documents

| | |
|---|---|
| [prompt-injection.md](prompt-injection.md) | The five paths, and why the schema does most of the work |
| [tenancy-and-data.md](tenancy-and-data.md) | RLS, server-mediated reads, credentials, PII, retention, logging |
| [content-and-web.md](content-and-web.md) | Origins, CSP, sandbox, XSS, uploads, tokens, custom domains |
| [infrastructure.md](infrastructure.md) | SSRF, denial-of-wallet, billing entitlements |
| [testing.md](testing.md) | The automated suite and the manual checklist |
| [operations.md](operations.md) | Disclosure, incident response, dependencies, release gate |

## Principles

**Prefer structural controls over filters.** A blocklist you must keep correct forever is worse than an architecture where the attack has nowhere to land. Network-level isolation beats URL parsing; an opaque-origin iframe beats scanning generated JavaScript; a schema with no dangerous field beats detecting dangerous output.

**The AI may arrange, style, and translate what the user gave it. It may not invent the subject.** This began as a quality rule — never invent marketing claims, never generate the product — and it turns out to be a security rule too. Applied to URLs it means `CTA.href` comes from the Brief, which makes an injected phishing link structurally impossible rather than merely unlikely.

**Assume the model is compromised.** Design so that a fully attacker-controlled model produces a page that is ugly, not a page that is dangerous.
