# The Machine-Speed Attacker

What changes when the thing attacking this product is not a person.

## First, the honest part

**Nothing is unhackable, and a document claiming otherwise would make this system less safe, not more.** Every real breach in history happened to someone who believed their controls were complete. The goal here is not invulnerability; it is that **the attacks which succeed produce outcomes you can live with** — a bad page, a wasted dollar, a rejected request — and that the outcomes you cannot live with have no path at all.

That is a stronger position than it sounds, and it is achievable. "Unhackable" is not.

What follows is the useful version of the question: an attacker with a frontier model is now a real adversary rather than a thought experiment, and it is worth knowing precisely which of these controls that changes and which it does not.

## What is actually happening now

This stopped being speculative during 2026.

| | |
|---|---|
| **First AI-authored zero-day in a real campaign** | Google Threat Intelligence Group, 11 May 2026 — an AI discovered *and* weaponized an unknown vulnerability, not merely automated a known one |
| **Speed of a full web-app sweep** | One agent tested a target across **47 attack vectors in under six minutes**, found a SQL injection, and exploited it |
| **Adaptation** | Agents adjust to unfamiliar environments without pre-written scripts — the reconnaissance step that used to cost an attacker hours is now nearly free |
| **Patch window** | **28.3% of critical CVEs in CISA KEV are weaponized within 24 hours** of disclosure. "Patch within 30 days" is no longer a policy, it is a hope |

The economics are what matter. Attacking a small product used to be uneconomic — a human's time was worth more than the target. That constraint is gone. **This product will be probed thoroughly whether or not anyone is specifically interested in it.**

## The one thing that actually changes

Machine-speed attackers do not have new capabilities so much as unlimited patience. That has a sharp and specific consequence:

> **Every control that works by *recognizing* an attack loses. Every control that works by *having nowhere for the attack to land* holds.**

A filter is a claim that you enumerated the bad inputs. Against a human, an incomplete enumeration is usually good enough — attackers give up. Against something that will try ten thousand encodings without getting bored, an incomplete enumeration is a **guaranteed** eventual bypass, and the only question is when.

This is not a new principle. It is [README.md](README.md)'s first principle — *prefer structural controls over filters* — and the change is only that it stopped being good taste and became the difference between working and not working.

Read down the controls in this directory and sort them:

| Structural — holds | Recognition-based — degrades |
|---|---|
| Slide markup renders where no script runs and no request leaves | The injection prompt frame ("this is data, not instructions") |
| The deck is a single offline file with `connect-src 'none'` — nothing to inject into | Pattern-matching imported text for instruction-like phrases |
| The API holds no model key and no browser | Trusting every request handler to be bug-free |
| No browser-facing database credential exists | Per-table RLS policies written by hand |
| Slides have no `<a>` element | Scheme allowlisting on link destinations |
| The model's CSS has no `url()` and no at-rules | The HTML sanitizer's allowlist staying bypass-free |
| `connect-src 'none'` — the deck cannot call out | Reviewing generated markup for network calls |
| **The pipeline has no agent framework, so there is no checkpoint to deserialize** | Patching the framework quickly |
| **The worker has no inbound port** | Trusting the markup that reaches its browser |
| **QA is a measure script, so there is no critic to talk to** | A vision model judging its own input |

**Every row's left column already exists in this design.** The right column is the second layer, and this is what it is for: it catches the ordinary and the accidental cheaply, and when it eventually fails, the left column is still there.

### v4 moved the strongest control from the left column to a stack of three

An honest amendment (2026-09-26, [../techstack/decisions.md](../techstack/decisions.md) → "The model writes markup"). Until v3 the top row read *"the `Deck` schema has no field for a command"*: the model could not express anything dangerous. v4 lets the model write HTML and CSS, so that guarantee is gone. What replaced it is a sanitizer (recognition-based, and it will have bypasses) in front of two structural controls: a document that runs no script, and one that makes no request. **The structural pair is the control; the sanitizer is the convenience layer.** If the design ever relies on the sanitizer alone — a frame that gains `allow-scripts`, a CSP that gains a source — it has moved to the wrong column.

### The Python move traded some of the left column for the right, and v4 took part of it back

An honest amendment ([../techstack/decisions.md](../techstack/decisions.md) → "The Python backend move"). Several guarantees that used to hold *structurally* now hold *procedurally*:

| Was structural | Is now |
|---|---|
| One tenant wrapper, because one language | ~~Two wrappers~~ **v4: no wrapper until RLS has a trigger, then one, in Python** |
| One schema, because `z.infer` made a second impossible | ~~A generated `Deck` tree~~ **v4: API types generated from OpenAPI**, kept in step by a no-diff gate |
| No agent framework, because it would have meant adding a language | **No agent framework**, because a rule and a CI grep say so |

Each remaining item is a build-time gate rather than a runtime hope. The mitigation is the one the table above teaches: when one fails, ask what structural control was missing — not which check to add. The first sign of trouble is any of them surviving only in prose.

The reason to write this down is that the two columns feel equally like security when you are building, and they are not. Under pressure the temptation is always to add a pattern to the right column. **The correct response to a bypass is to ask what structural control was missing, not which pattern to add** — which applies to the slide lint exactly: a bypass means a layer is missing, not that a pattern should be added.

## Where this design is genuinely strong

Worth stating plainly, because it is unusual and it was mostly not deliberate:

**The blast radius of a fully compromised model is a bad page.** The AI has one read-only tool (web search), no database writes, no shell. Its output is JSON that must pass a parse, or slide markup that is sanitized, linted and rendered where no script runs and no request leaves. An attacker who achieves total control of the model's output — the maximal win condition for prompt injection — gets to make an ugly presentation. In OWASP's agentic framing (below) this system deliberately has almost no *agency* to abuse, and that is why the agentic risk classes mostly do not apply.

**The exported deck is static and network-silent.** No database query per view, no LLM call, no outbound request — `connect-src 'none'`. Most of the web application attack surface is simply not present at the point where the most people are looking.

**The most valuable data is small.** No payment data, no passwords (the identity provider holds them, from phase 29), no uploads. What is held is the deck itself: a brief, pasted material, facts, slides and speaker notes.

The caveat: **the most confidential data does not sit still — it moves.** A founder's unannounced pitch is in flight to a model provider, and its search queries to a search engine, on every generation, which is a different threat model from data at rest and is covered separately in [third-parties.md](third-parties.md).

## Where it is genuinely weak

An honest list, because a threat model that only lists strengths is marketing.

1. **A solo operator is the real single point of failure.** Not the code — the response. An agent that finds something at 3am on a Sunday has hours before anyone reads the alert. The mitigations are the ones that work while you sleep: the per-deck budget cap, a spend limit on the key, the kill switch (phase 29), offline exported decks, and failing closed. [operations.md](operations.md) names this.
2. **Dependencies are the largest attack surface and you do not control them.** Nine Next.js advisories in July 2026 alone — and the surface is now **two** registries, npm and PyPI, with different defaults and a standing risk that only one of them gets hardened. See [platform-and-packages.md](platform-and-packages.md).
2b. **The build pipeline skips every control in this directory.** The three layers around slide markup, the API/worker split, owner isolation — all of them assume the running code is the code you wrote, and CI is where that assumption is made. It is also the surface an automated attacker reaches most cheaply, because misconfigured OIDC trust policies are enumerable from outside. See [build-pipeline.md](build-pipeline.md).
3. **Business-logic flaws have no scanner and no pattern.** An agent that reasons about *your* system finds the quota that resets on a boundary, the entitlement checked in one path and not another, the state machine that allows publish-before-payment. Nothing in the automated suite looks for these. This is the class most likely to actually get you, and the only defense is that the logic be simple enough to be obviously correct — which is an argument for [../coderules/README.md](../coderules/README.md), not for a security tool.

   **In v4 the business logic worth attacking is the budget.** A cap checked then spent in two steps, a repair loop or re-roll that is not counted, a job re-claimed after a stale heartbeat that runs its slides twice. Each is checked in one place, failing closed, and each is worth an hour of deliberately trying to break.
4. **Prompt injection is unsolved and will stay unsolved.** The posture here is containment, not prevention, and that is a deliberate bet that containment is achievable where prevention is not.

## OWASP mapping

Anchoring to a published taxonomy is how you find the thing you did not think of. Three lists apply.

### OWASP Top 10 for LLM Applications (2025)

| | Where it lands |
|---|---|
| LLM01 Prompt Injection | [prompt-injection.md](prompt-injection.md) — the central threat |
| LLM02 Sensitive Information Disclosure | [tenancy-and-data.md](tenancy-and-data.md) — no prompts or outputs logged |
| LLM03 Supply Chain | [platform-and-packages.md](platform-and-packages.md), [../coderules/dependencies.md](../coderules/dependencies.md) |
| LLM04 Data & Model Poisoning | Low — no fine-tuning, no RAG index, no memory. The nearest analogue is a poisoned search result, which produces a wrong claim with a visible source |
| LLM05 Improper Output Handling | **The most relevant entry in v4**, because the model's output is markup. Sanitizer, CSS lint, script-less render, CSP ([content-and-web.md](content-and-web.md)) |
| LLM06 Excessive Agency | Structurally absent — one read-only tool, nothing with side effects ([prompt-injection.md](prompt-injection.md), Defense 5) |
| LLM07 System Prompt Leakage | Assumed to leak. The prompt contains no secret; the controls do not depend on it staying hidden |
| LLM08 Vector & Embedding Weaknesses | Not applicable — no vector store |
| LLM09 Misinformation | The `Fact` ledger, provenance on every claim, and the outline gate ([../v4/content.md](../v4/content.md)) |
| LLM10 Unbounded Consumption | [infrastructure.md](infrastructure.md) — denial of wallet |

### OWASP Top 10 for Agentic Applications (2026)

Published 9 December 2025; it extends rather than replaces the LLM list. **Most of it does not apply, and the reason is the point:** this is a pipeline, not an agent. No memory, no inter-agent messaging, no autonomy between runs, and the only tools are read-only ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)).

**That exemption is a design decision, not a lucky property, and it is now load-bearing enough to be re-checked deliberately** — because the barrier that used to enforce it disappeared with the Python move. Adopting LangGraph used to mean adopting a second language. It now means one line in `pyproject.toml`, and most of this list would apply the same day ([../techstack/ai-stack.md](../techstack/ai-stack.md), [platform-and-packages.md](platform-and-packages.md)).

Three are worth checking anyway:

- **ASI01 Agent Goal Hijack** — the injection case, gated by the human outline approval
- **ASI05 Unexpected Code Execution** — in v4 this is model-written markup, contained by the three layers rather than by keeping untrusted input away from the model. The framework CVEs in [platform-and-packages.md](platform-and-packages.md) are the *dependency* form of this entry, and the reason `pickle` and friends are unwelcome in `api`
- **ASI06 Memory & Context Poisoning** — not applicable *today*. This is the entry to re-read the moment any feature gives the pipeline persistent memory across generations, which is exactly the kind of feature that arrives looking harmless — and it is also what an agent framework's checkpointer *is*, arriving as an implementation detail rather than a feature

### OWASP Top 10 (2025) — the web list

Refreshed in November 2025 with two new categories, and both are relevant:

**A03 Software Supply Chain Failures** — new, straight in at #3, and it has the *highest incidence rate on the list (5.19%) with very low CVE coverage*: these attacks are happening while scanners have no signature for them. Covered in [platform-and-packages.md](platform-and-packages.md).

**A10 Mishandling of Exceptional Conditions** — new, 24 CWEs, covering uncaught exceptions, race conditions, and **failing open**. This one deserves attention here specifically, because v4 has its own degradation paths — a failed image, a slide that will not repair, an unreadable ledger, an unreachable JWKS. Every one is a place where the fallback could be reached by *causing* the failure.

The rule that comes out of it, and it is now a design rule rather than a coding preference:

> **Availability degrades open. Authorization degrades closed.**
>
> A slide whose image failed ships without it. A budget check that cannot run refuses the call. A token validation that errors rejects the token.

Also note that **SSRF was absorbed into A01 Broken Access Control** in this revision — OWASP now treats it as fundamentally an access-control failure, which is why, if URL import is ever built, the control is network isolation and not URL parsing ([infrastructure.md](infrastructure.md)).

## What actually raises the bar from here

In value order, not effort order:

1. **Fail closed on every authorization path, and test it by making the check throw.** A10 is the newest category on the list for a reason, and this product's many fallback paths make it more exposed than most.
2. **Keep the kill switch reachable from a phone.** Against machine speed, mean-time-to-contain matters more than mean-time-to-fix, and solo the two are far apart.
3. **Patch the framework fast, and separate that from the dependency quarantine.** See the tension named in [platform-and-packages.md](platform-and-packages.md).
4. **Alert on the shape of automated probing** — a burst of sanitizer rejections, budget caps hit repeatedly by one user, a run of 401s. You will not out-react an agent, but you can find out on the same day.
5. **Keep the business logic simple.** The class with no scanner is the class where the only defense is that the code is obvious.
6. **Buy the pen test once there is revenue.** [testing.md](testing.md) already defers this correctly. The thing worth paying a human for is the business-logic class above — which is also the class the automated suite structurally cannot cover.

## What not to do

**Do not add an AI-powered security layer.** A model classifying inputs as malicious is a recognition-based control with a new failure mode of its own, and it would be the most complex component in a product whose entire security argument rests on there being nowhere for an attack to land. It would add attack surface in the name of removing it.

**Do not chase the news.** Most published AI-attack research targets systems with tool access, agent memory, or autonomous execution. This system has none of those, and adopting mitigations for risks it does not carry is how a threat model becomes too long to actually be read.

**Do not adopt an agent framework to "do this properly."** It is the single change that would import most of the risk classes this document currently gets to skip, into the most privileged process in the system, in exchange for orchestrating calls that are already in the right order ([../techstack/ai-stack.md](../techstack/ai-stack.md)). The decision is falsifiable and the two conditions that would reverse it are written down — neither is "it felt unprofessional not to."
