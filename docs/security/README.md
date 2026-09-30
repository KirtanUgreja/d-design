# Security

> The threat model and every control, gated to the phase that introduces the threat. The core problem: untrusted input reaches an LLM whose output becomes a web page. **Updated 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)) — the model now writes that page's HTML.

**Start here:** the *Adversaries* and *Trust boundaries* sections below — they route to everything else by threat rather than by topic.

**Looking for one specific thing?** Jump to [Find it fast](#find-it-fast).

Security is cross-cutting, so it lives outside the version directories. But the threats arrive on different schedules, and that matters more than it looks.

## The unusual thing about this app

**Untrusted input reaches an LLM whose output becomes a web page.**

That sentence is the product and the threat at the same time. No framework protects against it, and it is the reason this directory leads with prompt injection rather than with the usual OWASP ordering.

v4 sharpens it. Until v3 the model filled a JSON form and a renderer escaped it. **Now the model writes each slide's HTML and CSS**, so the output is markup rather than data, and the controls moved from a schema to three layers around that markup.

The paths that carry untrusted content into generation:

| Path | Arrives in |
|---|---|
| The brief, interview answers and pasted material | Phase 22 |
| Typed brand kit | Phase 23 |
| **Web search results** | Phase 24 |
| Edit instructions | Phase 28 |
| Uploaded files, fetched URLs, integrations | Not built; each needs its own threat model first |

## Adversaries, in effort order

1. **Attacker via injected content** — plants instructions in pasted notes or on a web page the search returns. Product-specific, and nothing off the shelf helps. → [prompt-injection.md](prompt-injection.md)
2. **Attacker targeting viewers** — poisons a deck so it attacks the audience. Worst reputationally: your customer's investors get hit on your customer's pitch. → [content-and-web.md](content-and-web.md)
3. **Malicious platform user** (from phase 29) — reaches another user's decks, or burns your model budget. → [tenancy-and-data.md](tenancy-and-data.md), [infrastructure.md](infrastructure.md)
4. **Attacker targeting your infrastructure** — the model key, denial-of-wallet, and the build pipeline. → [infrastructure.md](infrastructure.md), [build-pipeline.md](build-pipeline.md)
5. **Nobody in particular** — an automated agent sweeping the internet, which in 2026 will probe this product thoroughly whether or not anyone is interested in it. → [adversarial-ai.md](adversarial-ai.md)

Adversary 5 does not introduce new controls; it changes which existing ones you can rely on. Anything that works by *recognizing* an attack degrades against something that never gets bored. Anything that works by *having nowhere for the attack to land* holds.

## Trust boundaries

```
 brief · interview · pasted material ─┐
 web search results ──────────────────┤◀── UNTRUSTED
                                      ▼
                     storyline (JSON, Pydantic-parsed) ──▶ [human approves outline]
                                      │
                     compose: the model writes slide HTML + CSS     ◀── UNTRUSTED OUTPUT
                                      │
        ┌─────────────────────────────┼──────────────────────────────┐
   1. sanitize (nh3 allowlist:   2. lint CSS (tinycss2:        3. the browser: no slide script,
      no script, a, img, svg)       no url(), no at-rules)        no request, Shadow DOM scoping
        └─────────────────────────────┼──────────────────────────────┘
                                      ▼
                 single-file .html — offline, default-src 'none', one hashed script
                                      │
                                      ▼
                               viewer's browser
```

The process topology is the second boundary ([../techstack/backend.md](../techstack/backend.md)):

```
  web (browser UI)      api (internet-facing)        worker (no inbound port)
  no data, no key       NO model key, NO browser     the model key · Chromium · the engine
```

**The process that faces the internet holds nothing worth stealing, and the process holding the key accepts no connection.** That split exists from phase 27; before it the engine runs from the CLI on a developer machine.

Three boundaries carry the weight:

**The three layers around slide markup.** A fully compromised model can only emit HTML that is sanitized, linted, rendered without scripts and exported under `default-src 'none'`. Each layer alone stops script execution and exfiltration ([content-and-web.md](content-and-web.md) → "AI-written HTML and CSS"). This replaces the v1–v3 claim that the `Deck` schema had no field for a command.

**The offline single-file artefact.** `connect-src 'none'` — it talks to nothing. No CDN to poison, no origin to route around, no beacon to misdirect. It is the product rather than a constraint.

**The API/worker split.** A bug in a request handler cannot read the model key, and a bug in the browser that renders model markup is not reachable from the internet.

## When each control is needed

Building them in the wrong order wastes effort on threats that do not exist yet — which is what v1–v3 did with RLS, quotas and teams.

| Phase | What it introduces | Controls that become necessary |
|---|---|---|
| **22 engine spike** | Model-written HTML, a browser rendering it, an export | Sanitizer · CSS lint · request-aborting render · the export CSP · the zero-request test · the hostile-slide suite · per-deck budget cap · ZDR routing |
| **23 design system** | Typed brand colours | Token validation by type |
| **24 content engine** | Web search, pasted material | Untrusted-data framing · search caps · the injection corpus · provenance |
| **25 composition + QA** | Images, the repair loop | Image cap · repair limit · IPTC tag |
| **26 player + export** | The player script, speaker notes | Script allowed by hash · the send flavour without notes · AI disclosure |
| **27 app** | An internet-facing API, a slide iframe | API/worker split · script-less iframe · human error copy only · 409 during builds |
| **28 editor** | Inline edits, AI edits | Re-sanitise on every save · plaintext-only editing |
| **29 accounts + deploy** | Users, Postgres, hosting | JWT verification failing closed · owner filtering in one data module · budget per user · kill switch · build-pipeline rules · subprocessor list |

Three controls are **phase-independent**: keeping the framework and the packages that touch hostile bytes patched ([platform-and-packages.md](platform-and-packages.md)), failing closed on anything that grants ([infrastructure.md](infrastructure.md)), and a build pipeline that cannot be used to skip both ([build-pipeline.md](build-pipeline.md)).

One is **live from the first model call**: model routing and retention ([third-parties.md](third-parties.md)). A founder's unannounced pitch reaches a third party the first time anything is generated.

## Documents

| | |
|---|---|
| [prompt-injection.md](prompt-injection.md) | The paths, including web search, and what holds the output channel now that the model writes HTML |
| [tenancy-and-data.md](tenancy-and-data.md) | The single-writer file store, then (phase 29) authentication, owner isolation, logging, retention |
| [content-and-web.md](content-and-web.md) | **AI-written HTML and CSS: the three layers.** CSP, speaker notes, AI disclosure, theme tokens |
| [infrastructure.md](infrastructure.md) | The API/worker split, the browser in the worker, failing closed, denial-of-wallet, and what returns with uploads |
| [platform-and-packages.md](platform-and-packages.md) | Framework CVEs, cache poisoning, the parsers that touch hostile bytes, version floors |
| [third-parties.md](third-parties.md) | Where customer data actually goes — model routing, subprocessors, the GDPR obligation |
| [build-pipeline.md](build-pipeline.md) | CI/CD as an attack path — OIDC trust policies, Terraform state, publishing, images |
| [ai-built-app-failures.md](ai-built-app-failures.md) | The four mistakes that account for nearly every AI-built-app breach, audited against this design |
| [adversarial-ai.md](adversarial-ai.md) | What changes when the attacker is a machine — and the OWASP mapping |
| [testing.md](testing.md) | The automated suite and the manual checklist |
| [operations.md](operations.md) | Disclosure, incident response, dependencies, release gate |

Two are worth reading even if you skip the rest. [ai-built-app-failures.md](ai-built-app-failures.md) is the measured evidence of how applications built this way actually get breached — in one sample of 1,645, **~70% shipped with row-level security disabled**, which is the context for phase 29's isolation decision. [adversarial-ai.md](adversarial-ai.md) carries the OWASP mapping (LLM Top 10 2025, Agentic Top 10 2026, Web Top 10 2025) and the honest answer to whether this can be made unhackable.

## Find it fast

| If you need… | Go to |
|---|---|
| **How AI-written HTML/CSS is made safe** | [content-and-web.md](content-and-web.md) → "AI-written HTML and CSS"; specification in [../v4/engine.md](../v4/engine.md) → "Security of AI-written HTML" |
| Why slides have no links, images or SVG of the model's own | [content-and-web.md](content-and-web.md) → "Layer 1" |
| What the CSS lint rejects | [content-and-web.md](content-and-web.md) → "Layer 2" |
| The CSP for an exported deck | [content-and-web.md](content-and-web.md) → "CSP" |
| Why an emailed deck has no speaker notes | [content-and-web.md](content-and-web.md) → "Speaker notes do not leave with the deck" |
| Whether a poisoned search result can do real damage | [prompt-injection.md](prompt-injection.md) → "What holds the output channel" |
| What tools the AI may call | [prompt-injection.md](prompt-injection.md) → "Defense 5", and [../techstack/pipeline-tools.md](../techstack/pipeline-tools.md) |
| Why the API holds no model key | [infrastructure.md](infrastructure.md) → "The API and the worker" |
| Hardening the browser that renders slides | [infrastructure.md](infrastructure.md) → "Chromium in the worker" |
| The fail-closed rule | [infrastructure.md](infrastructure.md) → "Failing closed — OWASP A10" |
| Denial of wallet, the per-deck budget, the kill switch | [infrastructure.md](infrastructure.md) → "Denial of wallet" |
| Who may write a deck | [tenancy-and-data.md](tenancy-and-data.md) → "Before accounts: one writer" |
| Auth rules at phase 29 | [tenancy-and-data.md](tenancy-and-data.md) → "Authentication (phase 29)" |
| Why RLS is deferred, and what would bring it back | [tenancy-and-data.md](tenancy-and-data.md) → "Isolation (phase 29)" |
| Package version floors, and known CVEs | [platform-and-packages.md](platform-and-packages.md) → "Version floors" |
| Where customer prompts and search queries actually go | [third-parties.md](third-parties.md) → "The model route is not one vendor" |
| The GDPR subprocessor obligation | [third-parties.md](third-parties.md) → "The full subprocessor list" |
| CI as an attack path | [build-pipeline.md](build-pipeline.md) |
| What an automated attacker changes | [adversarial-ai.md](adversarial-ai.md) → "The one thing that actually changes" |
| The OWASP mapping | [adversarial-ai.md](adversarial-ai.md) → "OWASP mapping" |
| A test to write | [testing.md](testing.md) — organized by threat, gated by phase |
| What to do during an incident | [operations.md](operations.md) → "Incident response" |
| The release gate | [operations.md](operations.md) → "Release gate" |

## Principles

**Prefer structural controls over filters.** A blocklist you must keep correct forever is worse than an architecture where the attack has nowhere to land. Network-level isolation beats URL parsing; a script-less iframe beats scanning generated markup; having no link element beats filtering link schemes.

**The AI may arrange, style, and translate what the user gave it. It may not invent the subject.** This began as a quality rule — never invent marketing claims, never generate the product — and it turns out to be a security rule too. Applied to numbers it means every figure traces to the user or a cited source. Applied to URLs it means a slide has no link at all, which makes an injected phishing link structurally impossible rather than merely unlikely.

**Assume the model is compromised.** Design so that a fully attacker-controlled model produces a deck that is ugly, not a deck that is dangerous.

## Connects to

| | |
|---|---|
| [../techstack/README.md](../techstack/README.md) | The runtime topology every control in this directory assumes |
| [../coderules/patterns.md](../coderules/patterns.md) | The rules that make these controls mechanical — the tenant wrapper, failing closed, the model seam |
| [../v4/engine.md](../v4/engine.md) | The specification of the three layers, the model seam and the job protocol |

**Fail closed on anything that grants; fail open on anything that merely displays.** A quota check that cannot run refuses. An image that cannot be generated leaves a slide without one. This is OWASP's newest category, and every budget, cap and token check here is a place it applies — see [infrastructure.md](infrastructure.md).

**Nothing here is unhackable, and the goal is not to be.** The goal is that the attacks which succeed produce outcomes you can live with, and that the ones you cannot live with have no path at all. A threat model claiming completeness is the one that gets believed and then breached.
