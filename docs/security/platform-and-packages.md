# Platform & Packages

The framework and the dependency tree are an attack surface in their own right, and the one you control least. This is the OWASP **A03:2025 Software Supply Chain Failures** category — new in the November 2025 revision, straight in at #3, and carrying the **highest incidence rate on the whole list (5.19%) with very low CVE coverage**. That combination means these attacks are landing while scanners have no signature for them.

Companion doc: [../coderules/dependencies.md](../coderules/dependencies.md) covers *choosing* and *installing* dependencies, including the registry-compromise defenses. This doc covers *what breaks in the ones you already have*.

## Next.js is a security-relevant dependency, not just a framework

This is the most under-appreciated risk in the stack. Next.js had **13 advisories in May 2026 and 9 more in July 2026** — and several land directly on the parts of this product that matter.

### The one to understand, not just patch: CVE-2025-29927

An authorization bypass. Next.js trusted an internal header, `x-middleware-subrequest`, used to prevent infinite middleware loops. Setting it on an external request caused middleware to be **skipped entirely** — so any authorization performed in middleware simply did not run. Fixed in 12.3.5 / 13.5.9 / 14.2.25 / 15.2.3.

The patch is not the lesson. The lesson is durable and it is a design rule:

> **Middleware is not an authorization boundary. It is an optimization.**

Do the real check where the data is read — which in this codebase means inside the feature data modules ([../coderules/patterns.md](../coderules/patterns.md)), the same place the service-role filter and the RLS assumption already live. A redirect in middleware is a nicety that saves a round trip. If skipping it grants access, the access control was in the wrong place, and the next framework bug of this shape will find it again.

This rule costs nothing here because the architecture already puts data access in one module per feature — and the Python move made it structural rather than disciplinary. **`web` holds no application table at all**, so a Next.js middleware bypass has nothing to bypass: the authorization happens in `api`, in another process, behind a session lookup that fails closed ([../techstack/backend.md](../techstack/backend.md)). This is one of the few places the split is a security *gain* rather than a cost. It is worth writing down precisely because middleware is the *obvious* place to put an auth check, and the obvious thing is wrong.

### The 2026 advisories that map onto this product

| Advisory class | Why it matters here |
|---|---|
| **Cache confusion — CVE-2026-64647 / 64648** | Cached responses shared between users under specific caching conditions. This product serves **per-recipient personalized pages**. See the section below; this is the highest-severity interaction in the document |
| **Image Optimization DoS via malicious SVG** — CVE-2026-64644 | CPU exhaustion at `/_next/image` on self-hosted deployments. **This product accepts SVG uploads.** Two features that are individually fine and hostile together |
| **SSRF via `rewrites()` / `redirects()`** | A rule building its destination hostname from request-controlled input becomes SSRF (rewrites) or open redirect (redirects). Custom domains are exactly the feature that invites dynamic rewrite rules |
| **Auth bypass via App Router segment-prefetch** | Same lesson as CVE-2025-29927 — route-level access control is fragile in ways the data layer is not |
| **Unbounded Server Action payloads (Edge)** — CVE-2026-64646 | Memory exhaustion. Server Actions need explicit size limits |
| **XSS via CSP nonces and `beforeInteractive` scripts** | Interacts with the published-page CSP in [content-and-web.md](content-and-web.md) |

**Minimum versions: 15.5.21 or 16.2.11**, which cover both the May and July 2026 sets.

### Two decisions that fall out of this

**Disable remote image optimization.** All images in this product are self-hosted on `assets.<domain>` and re-encoded at upload ([content-and-web.md](content-and-web.md)). `/_next/image` fetching arbitrary remote URLs is a feature this product does not need, and it is simultaneously an SSRF surface and the SVG DoS surface above. Turning off what you do not use is the cheapest control available. `sharp`-based optimization of already-trusted, already-re-encoded local assets is fine; the remote fetch path is not.

**Never let a request-controlled value into a rewrite destination.** Custom-domain routing maps a verified hostname to an experience id via a database lookup — never by constructing a destination from the incoming `Host` header. The hostname grammar validation in [content-and-web.md](content-and-web.md) is the second layer; the lookup is the first.

## Cache poisoning and web cache deception

Serious enough to be its own section, and this is where the personalization feature and the CDN meet.

**Web cache deception** exploits a disagreement between the cache and the origin about what a URL is. The classic form: request `/r/<token>/nonexistent.css`. The origin's router ignores the trailing segment and serves the personalized page; the CDN sees a `.css` extension, decides it is a static asset, and caches it under a URL with **no session and no token binding**. The attacker then fetches the same URL and receives another recipient's page. Research has extracted account details, session tokens, private messages, and payment data this way from major platforms.

Applied here, the payload is a named prospect's personalized page and, through it, a working recipient token.

**Cache poisoning** is the mirror image: get an attacker-controlled response stored under a key that legitimate viewers will request. On a static published page served from a CDN — which is exactly this product's serving model — a poisoned entry is served to every viewer of a customer's launch page.

The controls, in dependency order:

| | |
|---|---|
| **Never cache `/r/[token]` responses** | `Cache-Control: private, no-store` on every personalized response. The cheapest and most complete control — there is nothing to poison or deceive if nothing is stored |
| **Cache key includes the full path** | No extension-based or prefix-based caching rule that treats a dynamic route as a static asset |
| **The origin rejects trailing-segment variants** | `/r/<token>/anything` is a 404, not a lenient match. The deception requires the origin to be more forgiving than the cache — so do not be forgiving |
| **No unkeyed request header changes the response** | If a header genuinely must vary the response, it goes in `Vary`. Never vary on `X-Forwarded-Host` or any other client-controlled header |
| **Static published pages are keyed by path alone** | No cookies, no auth, no per-viewer variation — which is what makes them safe to cache hard. Preserve that property deliberately; the day a published page varies by *anything*, this section applies to it too |

`Referrer-Policy: no-referrer` and `X-Robots-Tag: noindex` already protect recipient tokens from leaking outward ([content-and-web.md](content-and-web.md)). This section closes the inward path — the token leaking to someone who never received the link.

## The packages that touch untrusted input

Ordinary application dependencies are a low-grade risk. These are different: they parse hostile bytes by design, and a bug in one is directly reachable by an attacker.

| Package class | Role | What to know |
|---|---|---|
| **SVG sanitizer** (DOMPurify) | Sanitize uploaded SVG | See below — a continuous stream of bypasses |
| **`sharp`** | Image re-encode, EXIF strip | Wraps libvips, a large native C library. Decompression bombs are the primary risk, capped before decode |
| **PDF text extraction** | Intake imports | Historically the richest source of parser CVEs in this list. Run it isolated |
| **GLB / Draco / meshopt decoders** | 3D upload (v3) | Compression codecs. Same bomb shape as images, caps enforced before full decode |
| **Font parsing** | Per-script fonts (v3) | Serve from a curated registry; never parse a user-uploaded font |
| **Headless Chromium** (Playwright) | URL screenshots (v3) | The most-attacked software on the internet, pointed at pages an attacker chose. Its own section in [infrastructure.md](infrastructure.md) — and the container default is *unsandboxed*, which is the trap |

### DOMPurify is the case study for why layering is the real control

DOMPurify is the best SVG/HTML sanitizer available and it is the correct choice. It also had **at least four distinct XSS bypasses disclosed in 2025–2026**:

| | |
|---|---|
| CVE-2025-15599 | `textarea` rawtext bypass in the `SAFE_FOR_XML` regex — 3.1.3–3.2.6, fixed in **3.2.7** |
| CVE-2026-0540 | Five more missing rawtext elements (`noscript`, `xmp`, `noembed`, `noframes`, `iframe`) — through 3.3.1 |
| CVE-2026-41238 | Prototype pollution → XSS via the `CUSTOM_ELEMENT_HANDLING` fallback — 3.0.1 through 3.3.3 |
| CVE-2026-47423 | Default allowance of the `<selectedcontent>` tag — fixed in **3.4.5** |

**The 2.x branch was never patched for CVE-2025-15599.** If anything in the tree pins DOMPurify 2.x, it is permanently vulnerable — check transitive dependencies, not just the direct one.

Two conclusions:

**Track the floor, and expect it to move.** At time of writing that is **≥ 3.4.5**. It will be higher by the time this is built; the number matters less than knowing this package needs watching specifically, which is the point [operations.md](operations.md) makes about advisory-watching untrusted-input parsers by name.

**And this is the argument for the existing layering.** [content-and-web.md](content-and-web.md) already requires that SVG be served **only via `<img>`**, where script cannot execute regardless of what sanitization missed. Given four bypasses in eighteen months in the best tool available, that decision is not belt-and-braces — it is the actual control, and the sanitizer is the convenience layer. A design that relied on the sanitizer alone would have been exploitable four times in that window.

The same reasoning applies to prototype pollution generally: CVE-2026-41238 turned a *non-security* bug elsewhere in an application into an XSS in DOMPurify. Prototype pollution is a gadget, and the defense is that untrusted input is schema-parsed into known shapes at entry ([../coderules/python.md](../coderules/python.md), [../coderules/typescript.md](../coderules/typescript.md)) rather than merged into objects.

## AI frameworks are a dependency class of their own

*(researched August 2026)*

New with the Python backend, and it needs its own section because it does not behave like the classes above. The untrusted-input parsers are dangerous and **contained by placement** — they live in the fetch worker, which has nothing worth stealing ([../coderules/dependencies.md](../coderules/dependencies.md)). An agent framework would be dangerous and **uncontainable**, because its whole job is to sit in the process that orchestrates: `api`, which holds database credentials, model credentials, and from v3 decrypted integration tokens.

The class is being exploited, not theorised about:

| | |
|---|---|
| **CVE-2025-68664 "LangGrinch"** | CVSS **9.3** in `langchain-core`. Unescaped `lc` keys in `dumps()`/`dumpd()` over user-controlled dictionaries → environment-secret disclosure, API keys included |
| **CVE-2026-34070** | Arbitrary filesystem read via LangChain |
| **CVE-2025-67644** | SQL injection in LangGraph's SQLite checkpointer (CVSS 7.3) |
| **CVE-2026-28277** | Unsafe msgpack deserialization in LangGraph — object reconstruction triggered by *loading a checkpoint* (CVSS 6.8) |
| **LangGraph flaw chain**, June 2026 | Remote code execution against self-hosted agent deployments |
| **CVE-2026-25253 / ClawHavoc**, Jan 2026 | RCE in an agent *skill runtime*; within days, 1,200+ malicious skills were pushed to its marketplace |

The Cloud Security Alliance published a research note in March 2026 on agentic-framework CVEs under active exploitation.

**Read the list by shape, not by vendor.** Three patterns account for nearly all of it — **state serialization** (`dumps`/`dumpd`), **checkpoint deserialization** (msgpack, pickle, SQLite), and **plugin/skill loading**. Every framework in the category has all three, because all three are what a framework *is*. LangChain's CVEs have names because it is the most used and therefore the most audited; a less-scrutinised alternative is not a safer one.

Two conclusions, and only the first is about frameworks:

**This is a leg of the "no agent framework" decision**, not a caveat to it. [../techstack/ai-stack.md](../techstack/ai-stack.md) carries the full argument; the short version is that this pipeline is four sequential calls with a human gate, so the framework would add an actively-targeted attack surface to the most privileged process in the system in exchange for nothing.

**And the deserialization pattern generalizes past frameworks.** Two of the CVEs above are "load a stored object, get code execution." Anything in this system that deserializes something it stored earlier is the same shape — and the answer is the one already written down: **untrusted input is schema-parsed into known types at entry** ([../coderules/python.md](../coderules/python.md)), never `pickle`, never `yaml.load`, never a msgpack blob reconstructed into arbitrary classes. `pickle` should be as unwelcome in this codebase as `eval`.

## Python is a second supply chain, with worse defaults

The registry-compromise defenses in [../coderules/dependencies.md](../coderules/dependencies.md) were written for npm. PyPI has the same risk — typosquats, compromised maintainer accounts, and `setup.py` executing arbitrary code at install, which is `preinstall` under another name — and none of pnpm's protective defaults.

**The failure mode to actually worry about is asymmetry.** A hardened `pnpm` on one side and a bare `uv pip install` on the other is a project that *looks* protected, because the half anyone inspects is fine. An attacker picks the softer side. Both ecosystems get a committed lockfile, frozen installs, hash verification, and an age gate, or neither is protected.

## Version floors

Not a lockfile — a set of statements about what is known-bad, to be re-checked at build time rather than trusted from this document.

| | Floor | Why |
|---|---|---|
| **Next.js** | **15.5.21** or **16.2.11** | Covers May + July 2026 advisory sets |
| **React** | Current with the Next.js release | The May 2026 release was joint React/Next.js |
| **DOMPurify** | **≥ 3.4.5**, never 2.x | Four bypasses in 18 months; 2.x branch abandoned |
| **Node** | Current Active LTS | Runtime CVEs are patched only on supported lines |
| **Python** | Current stable, security-supported line | Same reasoning. An EOL minor gets no patches at all |
| **Agent frameworks** | **Not present.** Grepped in CI | Not a floor — an absence. See above and [../coderules/dependencies.md](../coderules/dependencies.md) |
| **`sharp` / libvips** | Latest | Native decoder against hostile input |
| **Three.js + loaders** | Latest (v3) | `WebGPURenderer` needs r171+ anyway ([../v3/dimensional.md](../v3/dimensional.md)) |

**The floors are a starting point, not the control.** The control is that CI fails on a known-critical advisory and that the four untrusted-input parsers above are watched by name. A table in a document goes stale; a failing build does not.

## The patch-speed tension, stated honestly

Two rules in this repository pull against each other, and it is better to name the conflict than to discover it during an incident.

- [../coderules/dependencies.md](../coderules/dependencies.md) sets a **24-hour minimum release age** on new package versions, so a compromised publish is caught by the community before it reaches you. This is correct and it is the single best defense against the registry-worm class.
- **28.3% of critical CVEs are weaponized within 24 hours** of disclosure ([adversarial-ai.md](adversarial-ai.md)). A quarantine that delays a malicious package equally delays the fix for an actively exploited bug.

**Resolution: the quarantine is the default; a security patch is an explicit, logged exception.** When an advisory affects something in the tree, install the fix immediately with the age gate overridden for that package, and note it. The two rules are not actually in conflict — one governs routine updates, the other governs incidents — but only if the exception path exists *before* it is needed, because the alternative under pressure is to disable the age gate globally and never turn it back on.

## What this adds to the release gate

Additions to [operations.md](operations.md):

- Framework version is at or above the floor, verified at build, not by memory
- No transitive DOMPurify 2.x anywhere in the tree
- Remote image optimization is off
- No rewrite or redirect destination is built from request-controlled input
- `/r/[token]` responses carry `Cache-Control: private, no-store`, asserted against the real CDN rather than the origin
- A lockfile diff is reviewed on every dependency update, **in both ecosystems** — the update itself is the delivery mechanism for A03
- No agent framework is in `pyproject.toml`, asserted by CI rather than by memory
- No `pickle`, `yaml.load`, or arbitrary-class deserialization anywhere in `api`
- The Python and TypeScript supply chains have the *same* hardening, verified separately — the risk is that one half is checked and the other is assumed
