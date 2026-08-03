# Security Operations

Process, not code. Cheap to write now, impossible to invent during an incident.

## Vulnerability disclosure

A `/.well-known/security.txt` on the app origin, and a monitored `security@` address.

```
Contact: mailto:security@<domain>
Preferred-Languages: en
Canonical: https://<domain>/.well-known/security.txt
```

Without a published channel, findings arrive on Twitter, or not at all. This is the cheapest security control in the entire directory — a text file and an inbox someone reads.

Acknowledge within a few days. You are solo, so do not promise a 24-hour SLA you cannot keep; promise what you can honor.

## Incident response

A one-page runbook, written before it is needed. GDPR gives 72 hours to notify a breach of personal data — not enough time to design a process from scratch.

**Contain → Assess → Notify → Remediate.**

1. **Contain.** The kill switches: halt generation, revoke the affected credential or signing key, unbind a domain, disable a compromised account. Know which lever fits which incident before the incident.
2. **Assess.** What data, whose, how much, still ongoing? The `generations` metadata and access logs answer scope without themselves containing PII.
3. **Notify.** Personal data breach → affected publishers, within 72 hours, factually. They are the data controllers for their recipients and have their own obligations downstream — tell them in time to meet them.
4. **Remediate.** Fix, add the regression test, write the retro.

Keep it to one page. A runbook nobody can read at 3am is theatre.

## Dependencies

The product is already dependency-light by design — that decision is most of the supply-chain defense.

- Automated dependency-update PRs, reviewed rather than auto-merged
- Lockfile committed; builds are reproducible
- A new dependency is a decision: is it maintained, how much does it pull in, does a few lines of our own beat it? The ponytail instinct and the security instinct agree here
- CI fails on a known-critical advisory

The most dangerous dependencies are those touching untrusted input: PDF parsing, image decoding, the 3D loader, HTML/SVG sanitization. Pin these deliberately, watch their advisories specifically, and run them in the isolated worker where their blast radius is smallest. [platform-and-packages.md](platform-and-packages.md) lists them by name with current version floors — DOMPurify alone had four disclosed bypasses in eighteen months.

**Watch the framework's advisories as attentively as the dependencies'.** Next.js published 13 advisories in May 2026 and 9 in July 2026, several of them auth bypasses and cache-confusion bugs that land on this product's specific features. A framework is a dependency; it is simply one nobody thinks to review.

### Patch speed, and the conflict with the quarantine

**28.3% of critical CVEs in CISA KEV are weaponized within 24 hours of disclosure.** A monthly patch cadence is not a cadence, it is a gap.

That collides with [../coderules/dependencies.md](../coderules/dependencies.md)'s 24-hour minimum release age, which exists to keep a compromised publish out of the tree and is the right default. The two rules govern different situations and the resolution has to exist *before* it is needed:

> The age gate is the default for routine updates. **A patch for an advisory affecting something in the tree is an explicit, logged exception** — install immediately, override the gate for that package only, record why.

Written down because the alternative under pressure is to disable the gate globally at 2am and never re-enable it.

Automated update PRs are reviewed rather than auto-merged — the update itself is the delivery mechanism for a supply-chain compromise (OWASP **A03:2025**, the highest-incidence category on the list). **Review the lockfile diff, not only `package.json`.** A transitive change is where this arrives, and it is the line nobody reads.

## Release gate

Each version ships only after the security tests for what it introduced pass, and the manual checklist ([testing.md](testing.md)) is walked.

| Version | Gate |
|---|---|
| **every release** | Framework and parsers at or above their version floors · fail-closed suite green · no key-shaped string in the build |
| **v1** | Injection corpus green · sandbox-escape tests green · upload tests green · origin separation verified |
| **v2** | CSS-token-injection tests green · AD linter rejects malformed token grammar |
| **v3** | Auth suite green (no-session and wrong-tenant on every route) · RLS isolation green · SSRF suite green (including socket-level unreachability) · **cache-isolation suite green against the real CDN** · privacy/retention green · entitlement + webhook tests green |

The gate is not "we wrote the tests." It is "the tests are green and the checklist is walked." A skipped gate under deadline pressure is exactly how the control that existed stops existing.

## Ownership

Solo, so all of this is one person. State that honestly rather than pretending a team exists:

- The `security@` inbox is checked on a real cadence
- The kill switches are documented where they can be found under stress, not buried in code
- The runbook lives somewhere reachable without the production system — a breach may be the thing that took production down

When the team grows past one, the first addition is a second person who can reach the kill switches and read the runbook. Everything else can wait; a single point of failure on incident response cannot.
