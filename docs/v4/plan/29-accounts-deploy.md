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

**Re-scoped for the submission to "release", single tenant:**
- **Build day (B12, P1):** Dockerfiles for the API and worker (with Chromium) and the web; `docker-compose.yml`; `.env.example`; an **access-token gate** — when `ACCESS_TOKEN` is set, every API route requires it and fails closed; the web keeps it in an httpOnly cookie after a one-field unlock page. A hosted instance only if the owner names a host.
- **Build day (B14, P0):** the submission README — what it is, how to run it in three commands, the architecture in one page, the evidence (walls, findings), the showcase decks.
- **After submission (unchanged scope above):** managed auth, Postgres, metering, signed links, the privacy policy, the saved brand kit. Trigger: the first outside user.
