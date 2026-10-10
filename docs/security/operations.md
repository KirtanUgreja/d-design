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

1. **Contain.** The levers: **rotate the OpenRouter key** (the one secret, and it stops all spend), halt generation with the kill switch (phase 29), disable a compromised account at the identity provider, **revoke the deploy credential**. Know which lever fits which incident before the incident — and note that the last one is the only lever that stops an attacker who is deploying code, which is the incident where every other lever is being reverted as fast as you pull it.
2. **Assess.** What data, whose, how much, still ongoing? The cost ledger and access logs answer scope without themselves containing PII.
3. **Notify.** Personal data breach → affected publishers, within 72 hours, factually. They are the data controllers for their recipients and have their own obligations downstream — tell them in time to meet them. **A subprocessor's breach is your breach to report** ([third-parties.md](third-parties.md)): under Article 28 you remain liable for their compliance, so subscribe to the status and security notifications of every name on that list before you need them.
4. **Remediate.** Fix, add the regression test, write the retro.

Keep it to one page. A runbook nobody can read at 3am is theatre.

## Dependencies

The product is already dependency-light by design — that decision is most of the supply-chain defense.

- Automated dependency-update PRs, reviewed rather than auto-merged
- Lockfile committed; builds are reproducible
- A new dependency is a decision: is it maintained, how much does it pull in, does a few lines of our own beat it? The ponytail instinct and the security instinct agree here
- CI fails on a known-critical advisory

The most dangerous dependencies are those touching untrusted input. In v4 that is the slide sanitizer (`nh3`), the CSS parser (`tinycss2`), Chromium, and Pillow. Pin these deliberately and watch their advisories by name. [platform-and-packages.md](platform-and-packages.md) lists them — the JavaScript sanitizer in the same role had four disclosed bypasses in eighteen months.

**Watch the framework's advisories as attentively as the dependencies'.** Next.js published 13 advisories in May 2026 and 9 in July 2026, several of them auth bypasses and cache-confusion bugs that land on this product's specific features. A framework is a dependency; it is simply one nobody thinks to review.

### Patch speed, and the conflict with the quarantine

**28.3% of critical CVEs in CISA KEV are weaponized within 24 hours of disclosure.** A monthly patch cadence is not a cadence, it is a gap.

That collides with [../coderules/dependencies.md](../coderules/dependencies.md)'s 24-hour minimum release age, which exists to keep a compromised publish out of the tree and is the right default. The two rules govern different situations and the resolution has to exist *before* it is needed:

> The age gate is the default for routine updates. **A patch for an advisory affecting something in the tree is an explicit, logged exception** — install immediately, override the gate for that package only, record why.

Written down because the alternative under pressure is to disable the gate globally at 2am and never re-enable it.

Automated update PRs are reviewed rather than auto-merged — the update itself is the delivery mechanism for a supply-chain compromise (OWASP **A03:2025**, the highest-incidence category on the list). **Review the lockfile diff, in both `uv.lock` and `pnpm-lock.yaml`, not only the manifest.** A transitive change is where this arrives, and it is the line nobody reads.

## Release gate

Each version ships only after the security tests for what it introduced pass, and the manual checklist ([testing.md](testing.md)) is walked.

| Phase | Gate |
|---|---|
| **every phase exit** | Hostile-slide suite green on three engines · zero-request export test green from `file://` · fail-closed suite green · framework and the packages in [platform-and-packages.md](platform-and-packages.md) current · no key-shaped string in the build · **ZDR on, prompt logging off, model ids pinned** ([third-parties.md](third-parties.md)) |
| **22 engine spike** | Sanitizer, lint and request-aborting render in place before the first model-written slide is opened in a browser · per-deck budget cap |
| **24 content engine** | Injection corpus run, including hostile search results · search caps |
| **26 player + export** | The send flavour and the PDF contain no speaker notes · one script hash in the CSP · AI-disclosure markers present |
| **27 app** | The API holds no model key and imports no browser · slide frame has no `allow-scripts` · no exception text reaches a client |
| **29 accounts + deploy** | No-token and wrong-user on every route · isolation suite green, and failing when the owner filter is removed · JWT failures all 401 · kill switch reachable · worker not reachable from the internet · subprocessor list published · `security.txt` live |

The gate is not "we wrote the tests." It is "the tests are green and the checklist is walked." A skipped gate under deadline pressure is exactly how the control that existed stops existing.

## Ownership

Solo, so all of this is one person. State that honestly rather than pretending a team exists:

- The `security@` inbox is checked on a real cadence
- The kill switches are documented where they can be found under stress, not buried in code
- The runbook lives somewhere reachable without the production system — a breach may be the thing that took production down

When the team grows past one, the first addition is a second person who can reach the kill switches and read the runbook. Everything else can wait; a single point of failure on incident response cannot.
