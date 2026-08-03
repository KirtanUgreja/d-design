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

The most dangerous dependencies are those touching untrusted input: PDF parsing, image decoding, the 3D loader, HTML/SVG sanitization. Pin these deliberately, watch their advisories specifically, and run them in the isolated worker where their blast radius is smallest.

## Release gate

Each version ships only after the security tests for what it introduced pass, and the manual checklist ([testing.md](testing.md)) is walked.

| Version | Gate |
|---|---|
| **v1** | Injection corpus green · sandbox-escape tests green · upload tests green · origin separation verified |
| **v2** | CSS-token-injection tests green · AD linter rejects malformed token grammar |
| **v3** | RLS isolation green · SSRF suite green (including socket-level unreachability) · privacy/retention green · entitlement + webhook tests green |

The gate is not "we wrote the tests." It is "the tests are green and the checklist is walked." A skipped gate under deadline pressure is exactly how the control that existed stops existing.

## Ownership

Solo, so all of this is one person. State that honestly rather than pretending a team exists:

- The `security@` inbox is checked on a real cadence
- The kill switches are documented where they can be found under stress, not buried in code
- The runbook lives somewhere reachable without the production system — a breach may be the thing that took production down

When the team grows past one, the first addition is a second person who can reach the kill switches and read the runbook. Everything else can wait; a single point of failure on incident response cannot.
