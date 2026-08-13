# Phase 19 — billing

> This phase makes true that the product has a business model: tiers, quotas, a kill switch, and the fail-closed rule on anything that grants.

**Depends on:** 18 · **Blocks:** 20 · **Spec step:** Locked decisions → billing

## Search

**Read first** — docs/design/website.md (the pricing page shape), docs/security/infrastructure.md (denial of wallet, quotas, kill switch), docs/techstack/backend.md (Postgres atomic counters, transactional quota)

**Grep for** — the quota code from v1, the kill switch, the publish path

**Verify externally** — current Stripe; the atomic quota check pattern

## Make

Billing: free = generate/edit/preview + one hosted URL with a badge; paid = more URLs, no badge, team, brand kit. Quotas are Postgres atomic counters (transactional, race-proof), and the kill switch bounds denial-of-wallet.

### Design decisions

- **The plan shape re-fits to the file artefact.** Free generation with a paid hosted URL. The trade — we pay for output that never converts — is bounded by the quota and the kill switch, exactly as before.
- **The quota is transactional.** A Postgres atomic counter, incremented in the same transaction as the action that spends it. Race-proof, and it is what makes the fail-closed rule real: a quota check that cannot run refuses.
- **The badge is ours, the AI-disclosure is the law.** One mark, two layers. The badge is removable on paid; the AI-content disclosure (EU AI Act Article 50, in force 2 Aug 2026) is not removable — the one boolean, two very different meanings, from the old design questions.
- **The editor (v2) is the retention loop.** Billing is fitted around it: a user who generates once and leaves is not a customer; a user who edits, re-skins, and publishes is.

## Verify

- [ ] Free tier: generate/edit/preview + one hosted URL with a badge
- [ ] Paid tier: more URLs, no badge, team, brand kit
- [ ] Quota is transactional and race-proof
- [ ] Kill switch bounds denial-of-wallet
- [ ] **Human:** the pricing page reads as honest; the badge/disclosure mark reads as one designed thing

## Skipped

- Invoices/receipts — Stripe handles; not a product surface
- Enterprise/SSO — not yet

## Exit gate

- [ ] Tiers, quotas, kill switch in place
- [ ] Transactional quota verified race-proof
- [ ] Badge/disclosure mark correct
