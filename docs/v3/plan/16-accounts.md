# Phase 16 — accounts

> This phase makes true that the product has tenants — auth, sessions, RLS — and that the multi-tenant boundary is a security property, not a feature.

**Depends on:** 12 · **Blocks:** 17, 18, 19 · **Spec step:** Locked decisions → accounts

## Search

**Read first** — docs/security/README.md (adversaries, trust boundaries), docs/security/tenancy-and-data.md (RLS, session-variable pattern), docs/techstack/backend.md (Better Auth in Node, `api` reads the session table read-only), docs/coderules/patterns.md (rule 9, the two tenant wrappers)

**Grep for** — the `Deck` schema, the renderer, the export path

**Verify externally** — current Better Auth; the RLS session-variable pattern; OAuth provider status

## Make

Accounts: email + OAuth signup/login, sessions, RLS on every tenant-scoped query, and the fail-closed rule on anything that grants. The old security spine, now load-bearing because there are tenants.

### Design decisions

- **Better Auth stays in Node** (`web`), sessions in your own Postgres, and `api` reads the `session` table read-only. This is the old decision, kept because it is sound.
- **RLS driven by a session variable** — `current_setting('app.user_id')` — with exactly two wrappers, one per language. A third is a bug (rule 9).
- **Anything that grants fails closed.** A quota check that cannot run refuses; a session that cannot be resolved denies. OWASP A10, non-negotiable 10.
- **The offline artefact means no new hostile surface from the URL.** A hosted deck is static HTML on a CDN — no origin server to route around. The single-file artefact's security posture carries to the hosted URL.

## Verify

- [ ] Signup/login, sessions, logout
- [ ] RLS enforced — a tenant cannot read another's data (manual checklist: call every route with no session and with another tenant's session)
- [ ] Fail-closed: a broken quota check refuses, it does not grant
- [ ] **Human:** the auth flow works end-to-end, and the security manual checklist passes

## Skipped

- MFA — deferred to the release that holds integration credentials (the old decision). Better Auth ships it when needed
- SSO/SAML — enterprise only, not yet

## Exit gate

- [ ] Auth, sessions, RLS in place
- [ ] Manual security checklist passes
- [ ] Fail-closed verified
