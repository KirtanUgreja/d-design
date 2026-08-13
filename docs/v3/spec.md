# v3 — spec

## Theme

**One paragraph. What this release proves that the last one did not.**

v2 proved the design engine scales and the editor retains. v3 proves the product can be a *business*: accounts and auth, a persisted brand kit that teams share, a hosted URL for a deck (with the single-file HTML still downloadable), billing and quotas, and the multi-tenant security that all of it demands. The design-diversity claim is unchanged — it is the spine, and v3 adds the shell around it that lets people pay for it.

## Commitments vs bets

### Commitments

| Commitment | Why it holds |
|---|---|
| **The single-file offline HTML remains the artefact, even with a hosted URL** | It is the product. The URL is a distribution layer, never a replacement |
| **The design engine and variety gate are unchanged** | v1/v2 spine. The business does not dilute the design claim |
| **Multi-tenancy brings RLS, quotas, fail-closed** | The old security spine survives; it is what makes accounts safe |
| **Prompt injection stays live from the first call** | The five paths from the security README, unchanged |
| **AI-disclosure obligations are designed in, not bolted on** | EU AI Act Article 50 (in force 2 Aug 2026). A machine-readable mark plus a human-visible one |

### Bets

| Bet | What would disprove it |
|---|---|
| **The hosted URL is what people pay for** (the file is the free wow, the URL is the paid convenience) | Users pay for something else, or refuse to pay for the URL |
| **Team collaboration is a paid need** | Teams share the file instead and never need shared kits |
| **Native PPTX export is worth building** (the category's worst-reviewed feature) | Users never ask; the HTML/PDF covers them |
| **A brand kit that maps to any design family is a moat** | Users keep their own brand in Canva and never import it |

## Locked decisions

| Axis | Decision | Why |
|---|---|---|
| **Accounts** | Email + OAuth, sessions, RLS, quotas. Better Auth in `web` (the old decision survives) | Multi-tenancy is a security boundary, not a feature |
| **Brand kit** | Persisted, team-shared, file-upload + extraction, mapped to semantic roles with contrast enforced | What marketers expect; the v2 extraction becomes a product surface |
| **Hosting** | A hosted URL for a deck (static, CDN-served) **plus** the downloadable single-file HTML | The file stays the artefact; the URL is the distribution/business layer |
| **Billing** | Free = generate/edit/preview + one hosted URL with a badge; paid = more URLs, no badge, team, brand kit | The old plan shape, re-fit to the file artefact |
| **PPTX export** | **Conditional** — build only if the market asks. Native OOXML generation, never lossy conversion | The category's worst-reviewed feature; native is the only version that does not lose fonts/texture/motion |
| **AI disclosure** | Machine-readable mark + human-visible line on the deck; badge removable on paid, disclosure not | EU AI Act Article 50; the badge is ours, the disclosure is the law |
| **Infrastructure** | RDS/Aurora, S3, CloudFront, Fargate workers, Terraform, CI/CD — the old stack, now serving the file artefact | The old decisions were sound; they were serving the wrong artefact |

## What changes from v2

| Old | New | Why |
|---|---|---|
| No accounts | Email + OAuth, sessions, RLS | The business requires tenants |
| Typed-text brand kit | Persisted, team-shared, file-upload + extraction | What marketers expect |
| Download-only artefact | Hosted URL + downloadable file | The business layer |
| No billing | Free tier + paid tiers, quotas, kill switch | The business |
| No PPTX | PPTX export (conditional) | Only if the market asks |
| — | AI-disclosure marks | The law (Article 50, in force 2 Aug 2026) |

## Risks

1. **The hosted URL becomes the product and the offline file is forgotten.** → The file stays the primary artefact; the URL is a distribution layer. Retired if users pay for the URL without abandoning the file.
2. **Auth/multi-tenancy slips and a tenant reads another's data.** → RLS, the session-variable pattern, the fail-closed rule. This is the old security spine, now load-bearing.
3. **PPTX export is a money pit** (the category's worst-reviewed feature). → It is conditional and native-only. Retired if users never ask.
4. **Billing churn** — users generate once and leave. → The editor (v2) is the retention loop; billing is fitted around it.
