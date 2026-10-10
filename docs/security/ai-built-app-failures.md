# How AI-Built Apps Actually Get Breached

There is now a large, measured body of evidence about what goes wrong in applications built quickly with AI assistance. It is worth reading as a checklist, because the failures are strikingly uniform — and because this project is built the same way.

The useful finding is not "AI writes insecure code." It is that **the same four mistakes account for nearly all of it**, they are all configuration rather than code, and every one of them is invisible until someone looks.

**Status, 2026-09-26 (v4):** v4 has no accounts and no database until phase 29, so failures 1 and 3 are not reachable yet. That is the correct order and also exactly the sequence that produced the numbers below, which is why phase 29's exit gate is the isolation suite. The answers below are updated to v4's design ([tenancy-and-data.md](tenancy-and-data.md)).

## The evidence

| | |
|---|---|
| **1,645 Lovable apps sampled** | **~70% shipped with Supabase Row Level Security disabled.** The public `anon` key then granted anyone unrestricted read of user tables — home addresses, financial data, API keys. CVSS 9.3 |
| **5,600+ public AI-built apps scanned** (Escape) | **2,000+ vulnerabilities, 400+ exposed secrets, 175 instances of PII** including medical records, IBANs, phone numbers |
| **Base44** (Wiz) | Publicly accessible endpoints allowed **authentication bypass** — the app's `app_id`, hardcoded into URI paths and readable in public files, was enough to register as a user of an application you did not own |
| **Client bundles** | Anonymous JWTs shipped in front-end JavaScript, wired to PostgREST endpoints with no row-level protection behind them |

## The four failures, and where this design stands

### 1. RLS off, or on but ineffective

The dominant failure by a wide margin. It happens because Supabase is usable the moment the tables exist and RLS is the step that comes later, so "later" arrives after launch.

**This design's answer is not "remember to enable RLS."** It is the invariant in [tenancy-and-data.md](tenancy-and-data.md):

> **No anonymous database role exists. Nothing but our own server connects.**

v4 goes one step further and defers RLS itself until a second database client exists: with one Python data module as the only thing that queries, the owner filter has one home, and a test removes it to prove the isolation suite notices. The Supabase-shaped version of the invariant, for a stack that does have an `anon` role, is below, and it is a strictly stronger position than correct RLS policies for a reason worth internalizing. Correct RLS is a per-table, per-operation obligation that recurs forever — every new table needs its anon policy considered, and one omission is a full read of that table. Zero grants is **one statement, asserted once, that cannot be forgotten for a table nobody thought about**, including tables that do not exist yet:

```sql
revoke all on all tables in schema public from anon;
alter default privileges in schema public revoke all on tables from anon;
```

The 70% number is the strongest available argument for this invariant, and it is why the test suite iterates the live schema rather than a fixed table list. A new table with a forgotten policy must fail the suite the day it is created.

**Two Postgres traps that survive correct RLS** — they are not Supabase-specific and apply just as much on RDS. Both are worth knowing before writing the first policy:

- **`security definer` views and functions bypass RLS entirely.** A view created this way runs with its creator's privileges, so a view over a protected table hands out everything the policy denies. Prefer `security invoker`; if a definer function is genuinely needed, it carries its own filter and is reviewed as security code.
- **`using` without `with check`** lets an owner write a row *assigning it to someone else* — already covered in [tenancy-and-data.md](tenancy-and-data.md), and it is the single most common way RLS is enabled but ineffective.

### 2. Secrets in the client bundle

Also uniform, and in the corpus it has a nasty wrinkle: **the Supabase `anon` key is *supposed* to be public.** It ships to browsers by design. That is only safe if RLS is doing its job — so failure 2 is not really a second failure, it is failure 1 becoming exploitable. An anon key in a bundle is either harmless or catastrophic depending entirely on a database setting nobody can see from outside.

**That specific wrinkle no longer applies here**, and the reason is worth naming: there is no browser-facing database key at all ([../techstack/backend.md](../techstack/backend.md)), because no browser talks to the database. The general lesson survives intact, and it is the more useful one — **a credential that is "public by design" is only safe while an invisible setting stays correct.** Prefer designs with no such credential over designs where you have to keep one honest.

Controls already specified in [infrastructure.md](infrastructure.md): the model key lives in the worker only, and the build output is grepped for key shapes. Two additions the research argues for:

- **Grep for the shape, not just the known prefixes.** Long high-entropy strings, `sk-`, `eyJ` (JWT), and provider-specific patterns. A leaked key you did not think to search for is the normal case.
- **Assume every value in the client bundle is public, including ones that "aren't really secret."** Endpoint URLs, internal ids, feature flags, project references. Base44's breach ran entirely on an id that was never treated as a credential and turned out to be one.

### 3. Endpoints with no authorization

Base44's exact failure: endpoints reachable without authentication because the front end never called them that way, so nobody checked what happened if someone did.

The structural defense in this codebase is [../coderules/patterns.md](../coderules/patterns.md)'s rule that **data access lives in one data module** — the owner filter has one home rather than being reimplemented at each call site. That converts "did every endpoint check?" into "did this one module check?", which is a question you can actually answer.

Two things to add to the manual checklist in [testing.md](testing.md):

- **Every route, called directly with no session.** Not through the UI. `curl` it. The UI is not a security control and it is the only thing that ever tested these paths.
- **Every route, called with a *valid session belonging to someone else*.** Authentication present, authorization absent — a genuinely distinct bug, and the one an automated scanner misses because it looks like a successful request.

### 4. PII where nobody expected it

175 instances of exposed PII across the scanned corpus, most of it in tables that existed for a legitimate reason and were never classified as sensitive.

v4 stores no recipient data at all: the exported deck makes no requests, so there are no views to record. The personal data it does hold is an email and whatever a user pastes into a brief — which can include customer names and figures, and is why brief content never reaches a log ([tenancy-and-data.md](tenancy-and-data.md)).

The habit worth keeping from the research: **when a new field is added, decide whether it is personal data at the moment the column is created.** Retrofitting that classification is how the 175 happened.

## Why this project is better positioned than the corpus — and where it is not

The four failures above are all **absent by construction** here, and mostly not because anyone was being careful about security. They are absent because the product's shape happens to exclude them:

- The artefact is an offline file, so there is no client-side data-fetching layer to under-protect
- Anonymous visitors never touch the database at all
- `web` holds no data and no credential
- Multi-tenancy does not exist until phase 29, so there is a long runway before the failure mode is even reachable

**The place to stay honest is that last point.** The corpus is full of applications where isolation was added after the feature worked, and this project's own plan defers accounts and isolation to phase 29 while phases 21–28 are built single-user. That is the correct build order and it is also exactly the sequence that produced the 70%.

The mitigation is in [README.md](README.md)'s phase table and the phase-29 release gate: **isolation tests are a gate on phase 29 shipping, not a task inside it.** Write the isolation suite before the first real account exists, not after.

## The one-page audit

Run this before the first outside user, and again whenever a table or route is added. It is the entire corpus of findings above, compressed:

- [ ] Nothing but the server holds a database credential
- [ ] The owner filter lives in one module, and removing it fails a test
- [ ] If RLS exists: every write policy has `with check`, and no `security definer` view or function sits over an owned table
- [ ] Build output contains no key-shaped string
- [ ] Every route called with no session → rejected
- [ ] Every route called with another tenant's session → rejected
- [ ] Every new column classified as personal data or not, at creation
