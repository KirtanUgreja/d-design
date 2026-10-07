# Phase 29 — accounts and deploy

> This phase makes the product something other people can use: sign-in, decks that belong to someone, spend that is measured and capped, and a deployed instance. It is last on purpose.

**Depends on:** 28 · **Blocks:** — · **Spec step:** Locked decisions → Storage, Auth · **Size:** M/L

## Search

**Read first** — [../../security/README.md](../../security/README.md), [../../security/tenancy-and-data.md](../../security/tenancy-and-data.md), [../../techstack/infrastructure.md](../../techstack/infrastructure.md), [../../coderules/patterns.md](../../coderules/patterns.md) → the tenant wrapper, fail closed

**Grep for**
- Every function in `api/store/files.py` — this interface is what gets re-implemented.
- `owner_id` — it exists on `Deck` from phase 21 and is unused until now.

**Verify externally**
- Pricing and token format of the managed identity providers (WorkOS AuthKit, Clerk).
- A container host that runs Chromium, and its cold-start behaviour.
- Privacy-policy and AI-disclosure duties for the launch markets.

## Make

- **Auth:** a managed provider. FastAPI verifies the token with PyJWT's `PyJWKClient`. A Python-owned `users` row, keyed by the provider's `sub`, is created on first request.
- **Data:** Postgres + SQLAlchemy + Alembic, Python only, behind **one** owner-scoped data module. Decks as `jsonb`, assets in object storage. Jobs claimed with `SKIP LOCKED`.
- **Metering:** per-deck and per-user cost from the ledger; per-user budgets and rate limits.
- Signed, short-lived URLs for the present view.
- A privacy policy; logo upload with isolated re-encoding, if the brand kit needs it.
- Deploy: one container host with Chromium; CI running the gate.

### Design decisions

- **No table is shared across languages.** Next has no database. This ends v3's split auth.
- **Anything that grants, fails closed.** A budget or session check that throws refuses.
- **Row-level security is deferred.** One Python module owns every query. Trigger: a second database client.

## Verify

- [ ] Every route with no session, and with another user's session
- [ ] A budget check that throws refuses
- [ ] Three concurrent generations complete
- [ ] Migrating a file-store deck into Postgres round-trips byte for byte
- [ ] **Human:** the security checklist in [../../security/testing.md](../../security/testing.md)
- [ ] **Human:** the owner signs up on the deployed instance and builds a deck

## Skipped

- Billing — trigger: the first user asks to pay.
- Teams — trigger: a paying team.
- Hosted share links — trigger: "send a link" outnumbers "send the file".
- Row-level security — trigger above.

## Exit gate

- [ ] All checks green on the deployed instance
- [ ] Cost per deck and per user visible from the ledger

## Sprint status (2026-10-08) → [master-plan.md](master-plan.md)

**In the submission, decided by the owner on 2026-10-08:** accounts, user management and the database are built on 2026-10-09.

- **Auth: Better Auth** (owner's choice), self-hosted in the web app, **email and password only**, so there are no OAuth keys to set up.
  - Its tables live in the **`auth` database** (Neon), managed by its CLI. Python never reads them.
  - Its **JWT plugin** issues the token FastAPI verifies with `PyJWKClient` against its JWKS: signature, issuer, audience, expiry and an algorithm allowlist. **Any failure, including an unreachable JWKS, is a 401.**
  - The decision is recorded in [../../security/tenancy-and-data.md](../../security/tenancy-and-data.md) and [../../techstack/decisions.md](../../techstack/decisions.md).
- **Data: Neon** (free tier; the owner confirmed Neon, not Supabase). One project, **two databases**: `app` for Python and `auth` for Better Auth. Pooled connections serve the running app; direct ones run migrations.
  - SQLAlchemy and Alembic manage the **`app` database** (Neon): users keyed by the token's `sub`, decks as JSONB, events, jobs claimed with `SKIP LOCKED`, the ledger, versions, finished slides, questions.
  - This is the *same* Store interface as `store/files.py`, now behind **the one tenant wrapper**. Another user's deck is a 404.
  - **Blobs** (screenshots, exports, PDFs, uploads) are stored **in Neon by content hash**, so a file shared by many versions is stored once. The API and worker run as separate services and cannot share a disk. Object storage replaces this when Neon storage nears its cap.
- **User management:** sign up, sign in, sign out, an account page (name, email), account deletion (cascading to decks and files), and **Your decks**.
- **A generated avatar** ([DiceBear](https://github.com/dicebear/dicebear), P1): made at sign-up from a random seed. The user can change the style, shuffle it, or pick a background from the brand colours; the choice is saved as `avatar` JSON on their row. It is drawn in the browser by the library, **never via api.dicebear.com**, and only from styles whose licences allow it (CC BY styles are credited).
- **A per-user daily spend cap** that fails closed. This is a safety limit (rule 10), **not a credit system**.
- **Ready for credits later, built now:** every ledger row (tokens, cost, model, stage) carries the user. Plans, balances and usage views come after submission (owner, 2026-10-08).
- **Deploy — the live link (P0; the owner needs a live link):** Railway, as three services from this repo.
  - **web:** public, Next.js and Better Auth, connected to Neon `auth`.
  - **api:** private, reached only by the web over Railway's private network; no model key, no Chromium.
  - **worker:** private, no inbound port; the OpenRouter key and Playwright's Chromium image.
  - This keeps [../../techstack/infrastructure.md](../../techstack/infrastructure.md)'s rule: the worker is unreachable and the API cannot read the model key.
  - The first deploy is Thursday evening, with the fake model; Friday only re-deploys.
- **Sign-up open only to `ALLOWED_EMAILS`:** the link is public; the owner expects one or two users.
- **Declined for the submission (owner, 2026-10-08):** several workers and a queue position, a global abuse guard, privacy and terms pages, an admin page. Needed before the link is shared widely.
- **Verify (P0):** every route with no session and with another user's session; a cap check that throws refuses; deletion removes data; the owner's two-account check on test day.
- **After submission:** **the credit system** (plans, balances, per-user usage and token consumption, on the ledger); Google and GitHub sign-in, email verification, password reset, magic links, MFA, object storage, teams, admin, billing, metering dashboards, signed share links, the privacy policy.
