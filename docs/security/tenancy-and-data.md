# Tenancy & Data

Who may read and write a deck, what is stored, and what never is.

**Rewritten 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)). Accounts arrive in phase 29. Before that there is one local user and nothing to isolate — but there are two processes writing the same deck, which is its own integrity problem.

## Before accounts: one writer

Decks live in a file store. **`api/store/files.py` is the only module that reads or writes deck data** ([../techstack/backend.md](../techstack/backend.md) → "Data").

| Rule | Prevents |
|---|---|
| Atomic writes (write, then rename) | Half a deck after a crash |
| A per-deck lock | Interleaved writes from the API and the worker |
| A version check on every write, failing closed | A stale tab overwriting newer work |
| **API edits return 409 while a build runs** | Two writers at once. During generation the worker is the single writer |
| Deck ids are server-generated and never built from user input | Path traversal through an id |

These are integrity controls today and the base of isolation tomorrow: one module that touches data is one place where an owner filter has to be right.

## Authentication (phase 29)

**Use a managed identity provider. Do not build it.** WorkOS AuthKit or Clerk, chosen at phase start. It handles passwords, email verification, OAuth, MFA and reset flows. v3 kept Better Auth in Node and had Python read its session table across a language boundary; that arrangement is gone ([../techstack/decisions.md](../techstack/decisions.md)).

**How FastAPI learns who you are:** it verifies the provider's JWT with PyJWT's `PyJWKClient` — signature against the JWKS, issuer, audience, expiry, and an explicit algorithm allowlist. **Every failure, including an unreachable JWKS, is a 401.** There is no permissive default.

**A Python-owned `users` row keyed by the provider's `sub`.** Decks reference `users.id`, so foreign keys and cascade deletes are real, and the provider's subject id never becomes a free-floating string in our tables.

What still has to be decided, because the provider does not decide it for you:

| | |
|---|---|
| **Where authorization is checked** | **At the data layer, never in middleware alone** — CVE-2025-29927 in [platform-and-packages.md](platform-and-packages.md). `web` holds no data, so there is nothing for a Next.js middleware bypass to reach |
| **Token lifetime** | Short. Revocation is no longer an instant session delete; it is bounded by this number. That is the cost of moving off a session table |
| **Where the token lives in the browser** | The provider's SDK decides. Never in a URL, never logged. It goes to the API as `Authorization: Bearer`, which is why SSE is read with `fetch` rather than `EventSource` |
| **Email verification before anything expensive** | Before the first generation. Also the account-farming control |
| **MFA** | Offered from phase 29; the provider ships it |
| **Rate limits on auth** | The provider's, checked rather than assumed |

Account deletion is a security control as well as a privacy one: it must delete the user's decks and assets, and it is tested.

## Isolation (phase 29)

**Every query is filtered by owner in one Python data module.** Routes never build a query. That converts "did every endpoint check?" into "did this one module check?".

**RLS is deferred.** v3 built it — a session variable per transaction, two tenant wrappers in two languages, and three migrations that existed only to fix recursion in team policies. v4 has one language, one ORM and one module touching the database, so the second layer would guard against a mistake that has exactly one place to happen.

**Trigger to add RLS: a second database client.** A second service, an admin tool, a reporting job, anything that connects without going through the data module. When it fires:

- Identity comes from `set_config('app.user_id', …, true)` inside a transaction, in **exactly one wrapper, in Python**. The `true` scopes it to the transaction; without it a pooled connection serves the next request as the previous user.
- Every write policy has `with check`, not only `using`.
- No `security definer` view or function over an owned table.
- The unset case is tested: `current_setting` on a connection where it was never set must fail, not match everything.

**What holds regardless of RLS:**

- **No anonymous database role exists. Nothing but our own server connects.** One sentence, trivially testable. In one sample of 1,645 AI-built apps, ~70% shipped with RLS disabled and a public key granting reads; having no browser-facing database credential at all is what prevents that ([ai-built-app-failures.md](ai-built-app-failures.md)).
- The application role owns no schema objects; a separate role runs migrations.
- **The isolation test is a gate on phase 29**, written before the first real account: two seeded users, every route, each unable to read, write or delete the other's decks.

Without RLS the owner filter is the only control, so the test that proves it is not optional: remove the filter in a test build and the isolation suite must fail.

## Logging

The cost ledger, `events.jsonl` and application logs store **metadata only**: stage, pinned model id, prompt version, token counts, dollars, milliseconds, repair flag, error class, slide ids.

**No prompts. No outputs. No brief, interview, fact or slide content. No generated images.**

A prompt here contains a founder's unannounced pitch — plausibly the most confidential thing they will hand a vendor. It does not belong in a table that exists to answer "what does this cost".

The same rule applies to error reporting: scrub request bodies before anything leaves the process.

**And the same fact governs marketing.** A showcase, a case study or a screenshot is publication of a customer's deck by a route that never touches a log. The rule: **explicit written release, per artifact, after that customer's launch or raise is already public** ([../design/website.md](../design/website.md)). The interview needs a separate release from the output, because it is the more sensitive of the two.

## What is stored, and for how long

| Data | Where | Retention |
|---|---|---|
| Brief, interview, facts, storyline, slides | The deck | Until the user deletes the deck or the account |
| Pasted material | The deck's brief | Same. The user can see and remove it |
| Speaker notes | The deck. **Never in the "send" export or the PDF** ([content-and-web.md](content-and-web.md)) | Same |
| Generated images | The deck's assets | Same |
| Cost ledger | Per deck, and per user from phase 29 | Indefinite — no content, no personal data beyond the owner id |
| Auth identities | The provider. We hold `sub` and an email | Until account deletion |

**Cascade delete works and is tested.** Deleting a deck removes its assets, events and ledger. Deleting an account removes everything. Write the test that asserts no orphans before the first deletion request arrives.

**The exported file is outside all of this.** Once downloaded, a deck is the user's file. It makes no requests, so there is no view tracking, no recipient data and no analytics to retain.

## What v3 had here

Integration credentials with envelope encryption, recipient tracking, hosted-URL analytics and team-scoped brand kits were specified for v3 and do not exist in v4. Each returns only with its feature, and the v3 text is in git history at commit `8169fd9`.
