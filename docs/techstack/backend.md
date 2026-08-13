# Backend

Five runtimes and two languages. The lines between them are trust boundaries rather than convenience — except one, which is a language boundary, and that one is the price of the Python move ([decisions.md](decisions.md) → "The Python backend move").

## The five runtimes

| | Language | Runs | Has | Never has |
|---|---|---|---|---|
| **web** (Vercel) | TypeScript | Editor UI, renderer, **Better Auth**, marketing site | Sessions, **auth tables only** | App-table access, model access, long-running work |
| **api** (Fargate) | **Python** | The four pipeline phases, the model seam, quotas, enqueue | DB (all app tables), model access | Hostile input, session issuance |
| **jobs** (Fargate) | **Python** | PGQueuer — deck regeneration, retention, scheduled work | DB, model access | Hostile input |
| **render** (Fargate) | TypeScript | Deck tree → HTML, Playwright, the visual verification loop | The renderer | **DB access, model credentials** |
| **fetch worker** (Fargate) | TypeScript | URL fetch, screenshots, document parsing, integration reads | Integration credentials, egress-only network | **DB access, VPC route, the renderer, secrets beyond its own** |

`api` and `jobs` are **one Python codebase with two entry points** — same models, same data modules, same seam — exactly as the app and job worker were before. Only their process boundary differs.

**That is two more runtimes than the previous design, and the honest accounting is that one is a real trust boundary and one is not.** `render` exists because Python cannot server-side-render React and the renderer must have exactly one implementation ([../coderules/patterns.md](../coderules/patterns.md) rule 2). It is a language boundary wearing a service's clothes. It is not free, and pretending otherwise is how five runtimes become eight.

### Why the render service is separate from the fetch worker

Both are Node and both drive Playwright, so merging them is the obvious saving. **Do not.** The fetch worker is the container that handles attackers' input; giving it the renderer would put page-making capability inside the quarantine. The trust split is the entire point, and "they share a dependency" is not a reason to collapse it.

`render` receives a **schema-validated deck tree with no presentational values** — trusted input by construction — and holds no database credentials and no model key. Its worst case is producing a wrong deck.

### Why two workers

[../security/infrastructure.md](../security/infrastructure.md) called for "a dedicated worker with egress-only networking and no route to the VPC", and separately said that worker holds decrypted integration credentials. But the same document assigns it work with the opposite requirement — deck regeneration and scheduled work need database access and never touch attacker-controlled bytes.

One process doing both is the exact combination the isolation exists to prevent: **the thing holding database credentials would also be the thing parsing an attacker's PDF and rendering an attacker's webpage.**

So they split, and the split is on trust rather than on job type:

- **The fetch worker touches hostile input and has nothing worth stealing.** A `pdf.js` CVE, a Chromium sandbox escape, or an SSRF bypass lands on a box with no database, no VPC route, and no metadata endpoint. Its one secret is the integration token it is actively using.
- **The job worker has real privileges and never touches hostile input.** Its inputs are rows from your own database, already validated.

This costs one extra task definition. It is the cheapest security control in the whole stack.

## Data

**Postgres.** Docker locally, RDS/Aurora in production — same database, no dialect differences, and the local-to-production move is a connection string.

One shared dev database. Preview-per-branch databases are genuinely useful while a schema changes constantly, and they are not worth a second database vendor yet — revisit if migrations start hurting.

### Two ORMs, one database — and the rule that keeps it survivable

This is the sharpest edge of the Python move and it needs stating before anything else in this section.

| | Owns | Migrates with |
|---|---|---|
| **`web`** — Drizzle | **Auth tables only**: `user`, `session`, `account`, `verification`, `organization`, `member`, `invitation` | `drizzle-kit` |
| **`api`** — SQLAlchemy | **Everything else**: `experiences`, `briefs`, `assets`, `brands`, `generations`, `quotas`, `recipients` | Alembic |

**Neither migrates the other's tables. Ever.** Two migration tools against one database is a corruption waiting for a race, and the only thing preventing it is that each has a disjoint table set. That is enforced, not remembered:

- Alembic's `include_object` filter **excludes** the auth tables, so an autogenerate run cannot propose dropping them. Without this, Alembic sees seven tables it does not know about and helpfully writes a migration to delete them. **This is the single most destructive failure mode in the new architecture** and it is one config block away.
- `drizzle-kit` is scoped to the auth schema for the same reason, in the same direction.
- Application tables may hold a **foreign key to `user.id`** — that reference is what makes the RLS below work. `api` reads `user` and `session`; it never writes them.

**Prefer a separate Postgres schema over a naming convention.** `auth.*` versus `public.*` turns "which tool owns this table" from a rule someone follows into a grant someone cannot bypass — the same structural-over-recognition preference as everywhere else in this repo ([../security/adversarial-ai.md](../security/adversarial-ai.md)).

### Isolation: RLS on a session variable, in two places

Supabase's `auth.uid()` is gone with Supabase. The replacement is a session variable set per transaction:

```sql
create policy own_experiences on experiences
  for all to app_user
  using      (owner_id = current_setting('app.user_id')::uuid)
  with check (owner_id = current_setting('app.user_id')::uuid);
```

```python
# api/db/tenant.py — the only place app.user_id is ever set in Python
@asynccontextmanager
async def as_user(user_id: str):
    async with session_factory() as s, s.begin():
        await s.execute(text("select set_config('app.user_id', :uid, true)"), {"uid": user_id})
        yield s
```

**`set_config(..., true)`, inside a transaction, in exactly one wrapper per runtime.** The `true` is what scopes the value to the transaction; without it the setting persists on the connection, and a pooled connection handed to the next request serves it as the previous user. One boolean between correct and a cross-tenant read.

> **The rule used to be "one wrapper." It is now "exactly two, one per language."** That is a real weakening and it is the cost of the split, not a detail. [../coderules/patterns.md](../coderules/patterns.md) rule 4 carries the enforced version: two files may contain `set_config('app.user_id', ...)`, they are named, and a third is a bug the linter fails on.
>
> The weakening is smaller than it looks only because of the table-ownership rule above: `web`'s Drizzle wrapper guards seven auth tables that Better Auth already scopes by session, and `api`'s wrapper guards everything that actually holds customer content. If application tables ever become readable from `web`, this stops being a footnote.

The invariants from [../security/tenancy-and-data.md](../security/tenancy-and-data.md) survive the move unchanged and one of them gets easier: **the application connects as a role with no `bypassrls`**, and a separate migration role owns DDL. The "anon has zero grants" rule becomes "there is no anonymous role at all" — nothing but your servers ever connect.

RLS here is defense-in-depth rather than the primary control, because no browser talks to Postgres directly. That is not a reason to skip it — and with two ORMs it matters *more* than it did with one, because there are now two codebases in which a `where` clause can be forgotten. The measured failure rate of app-layer-only isolation is in [../security/ai-built-app-failures.md](../security/ai-built-app-failures.md).

### Connection pooling

Fargate tasks plus Vercel functions means many short-lived connections against a fixed Postgres limit. **RDS Proxy**, or PgBouncer in transaction mode. Note the interaction: transaction-mode pooling and `set_config(..., true)` are compatible — session-mode assumptions are not, and prepared statements need care with both Drizzle and SQLAlchemy (`asyncpg` in particular caches them; disable the cache behind a transaction pooler or you will get errors that look like nothing else).

## Auth: Better Auth, in Node, and how Python learns who you are

Better Auth stays. v1.6 as of May 2026, Drizzle adapter, and **users live in your own Postgres** — which is what makes the session-variable RLS above work cleanly, since the user id and the data it guards are in one database with a real foreign key between them.

**It stayed because Python has no equivalent, and this was checked rather than assumed** *(researched August 2026)*. It ships what the security doc requires rather than leaving it to you: OAuth, email verification, password reset, MFA, passkeys, organizations, and rate limiting. The Python options each miss most of that list — `fastapi-users` covers registration, verification, reset, OAuth and sessions but leaves MFA, passkeys, and organizations to you; Authlib is a protocol library with no user management at all; the platforms that do ship all of it (WorkOS, PropelAuth, Kinde, Auth0) move your users out of your Postgres, which breaks the foreign key the RLS design rests on and adds a subprocessor ([../security/third-parties.md](../security/third-parties.md)).

> Keeping one Node service for auth is the smaller cost. It is also the reason this is a *Python backend* rather than a *pure Python backend*, and the asterisk belongs in the open rather than in a footnote nobody reads.

### Session resolution — the one documented exception to table ownership

`web` issues the session. `api` has to resolve it. It does so by **reading Better Auth's `session` table directly, read-only**:

```python
# api/auth/session.py — the only place api touches an auth table
async def resolve_session(token: str) -> Result[str]:      # -> user_id
    row = await db.fetch_one(SELECT_SESSION, {"t": token})  # token, expires_at
    if row is None or row.expires_at <= now():
        return err(Unauthorized)                            # fails closed
    return ok(row.user_id)
```

The browser sends the Better Auth cookie to `api`; `api` resolves it to a `user_id` and hands that to `as_user()`. Three properties make this the right choice over the alternatives:

- **Revocation still works instantly.** Sessions invalidate on password change — a requirement in [../security/tenancy-and-data.md](../security/tenancy-and-data.md). A short-lived JWT minted by `web` would have kept ownership cleaner and introduced a revocation window, which is the wrong trade for a security requirement that is already written down.
- **No new secret.** A shared signing key would need to live in two secret stores and be rotated in both.
- **It fails closed by construction.** No row, expired row, or unreadable database all return `Unauthorized`. There is no permissive default to get wrong ([../coderules/patterns.md](../coderules/patterns.md) rule 5).

**The cost, stated plainly:** `api` now depends on Better Auth's session-table shape, which is a third-party schema it does not own. Pin the Better Auth version, and treat a major upgrade as a change that touches both repos in one session — the same discipline `@d-design/schema` already has.

**The rules from the security docs still apply and are not Better Auth's job:**

- **Authorization is checked at the data layer, never in middleware alone** — [../security/platform-and-packages.md](../security/platform-and-packages.md), CVE-2025-29927. With the split this gets *easier* to hold: `web` has no application data to authorize access to, so there is no temptation to check there
- Sessions invalidate on password change
- OAuth links by verified email only
- Signup, login, and reset are enumeration-safe
- Auth endpoints are rate-limited separately from generation quotas

## Jobs: PGQueuer

The queue is a table in the database you already have. No Redis, no vendor, no second datastore — and jobs enqueue **in the same transaction** as the data change that caused them, so a publish that rolls back cannot leave an orphaned poster-generation job behind. That transactional property is the actual reason, more than the simplicity, and PGQueuer names it as a headline feature rather than leaving you to hand-roll an outbox.

It replaces pg-boss, which was the same idea in Node and is not reachable from Python. Procrastinate was the other candidate and has more features — periodic tasks, task locks, richer retries. **PGQueuer won on surface area:** the one property that made pg-boss the choice is the one property PGQueuer is built around, and this project does not yet need the rest. If scheduled work outgrows it, Procrastinate is a migration within the same datastore, which is the cheap kind.

Work it runs: deck regeneration jobs, scheduled work, retention deletion, custom-domain re-verification (v3).

It will not scale past one Postgres. That is fine for years, and when it stops being fine the problem is a good one to have.

### Publishing — where the render happens

**Superseded twice, so the history is worth one line.** It was originally a Vercel route; it then moved to the job worker on the grounds that the job worker ships from the app repo and therefore has the renderer. The Python move invalidates that second premise — the job worker is Python and cannot render React.

So publishing moves to the **`render` service**, and there is still exactly one renderer in one codebase ([../coderules/patterns.md](../coderules/patterns.md) rule 2) running in three processes:

| | |
|---|---|
| **`render`** | Publishing, especially multi-locale — no function-timeout ceiling, so a 12-locale publish is one request rather than twelve chunked calls. Also where the visual verification loop runs ([pipeline-tools.md](pipeline-tools.md)), since that needs the renderer and Playwright together |
| **`web`** (Vercel) | The editor canvas (v2), and single-slide preview renders during generation where latency matters and the work is small |
| **`jobs`** (Python) | **Orchestrates** a publish; it does not render one. It calls `render` and writes the returned artifact to S3 |

That last row is the shape of the whole architecture in miniature: **Python decides, TypeScript renders.**

`render`'s contract is deliberately tiny — one endpoint, in a validated `Deck` plus a `DesignFamily`, out HTML. No database, no model credentials, no auth. A service with one function and no secrets is a service you never have to think about again.

**The fetch worker never gets the renderer.** It is the container that handles hostile input, and giving it the component that produces pages would put page-making capability inside the quarantine. `render` and the fetch worker are both Node and both run Playwright, which makes merging them look like a saving; it is the one merge the trust split forbids.

## Rate limits and quotas

Postgres, atomic counters. No Redis.

The quota check must be **atomic increment, not read-then-write** — concurrent requests reading the same remaining balance and all proceeding is the A10 race named in [../security/infrastructure.md](../security/infrastructure.md). One statement:

```sql
update quotas set used = used + 1
where account_id = $1 and used < limit
returning used;
```

No row returned means refused. The check and the consumption are the same operation, so there is no window between them.

Volumetric abuse is a different problem from per-account quota, and the cheapest place to stop a flood is the platform edge before it reaches your code. Configure that when there is traffic worth flooding.

## Model access: OpenRouter behind a seam

One provider interface, one call site, OpenRouter behind it. This buys cheap experimentation across models — a fast, cheap model for Director and Edit, a strong one for Build — without a second vendor relationship.

Model selection, evals, and what the pipeline may call are their own subject: **[ai-stack.md](ai-stack.md)** and **[pipeline-tools.md](pipeline-tools.md)**. The short version is that this product has no preferred vendor, only a preferred interface, and the eval harness is what makes that a strategy rather than a slogan.

**It costs a guarantee, and the trade should be understood rather than discovered.**

OpenRouter's `strict: true` enforcement varies by provider: some guarantee schema-conforming output, some translate the schema into their own format, some treat it as a strong hint. So the claim in [../security/prompt-injection.md](../security/prompt-injection.md) — *"a fully compromised model can only emit valid Deck JSON"* — is no longer enforced by the decoder.

**What actually holds, and why the security posture survives:**

> The schema parse was always the real gate — Pydantic now, Zod before, and the argument is identical either way. Decoder-level enforcement was a *cost and reliability* optimization: it lowers how often the model produces something invalid. It never was the thing that stopped invalid output from being rendered.

Output that fails the parse is rejected, repaired once, and then fails visibly. It never reaches a page. The security claim restates as *"a fully compromised model can only cause a rejected generation"*, which is the same outcome by a different route.

The residual is real but small: an attacker who fully controls model output can drive repeated repair cycles and burn tokens — denial of wallet, already covered by quotas and the kill switch.

**The metric that decides whether this was right is the repair rate**, tracked in the generation records. Watch it from the first generation. If the slide builder's repair rate is materially worse than a direct Anthropic call, move that one phase behind the seam — the seam exists for exactly this, and nothing else in the pipeline changes.

Two things the seam must not hide: **prompt caching** behavior and **cost per phase**. Both vary by route and both are load-bearing for the cost-per-deck figure. Log them per call.

Per-phase model selection is deliberately unresolved. Decide it with real briefs and a repair rate, not in advance.

## Email: Resend

Verification, password reset, and eventually recipient link delivery.

**Auth email is sent by `web`**, because Better Auth owns verification and reset and already has the hooks. React Email for those templates — they live next to the auth code that triggers them.

**Product email is sent by `jobs`** (recipient links, publish notifications) via Resend's HTTP API, which is a POST with a JSON body and needs no SDK. Two senders, one domain, and the split follows the same line as everything else: whoever owns the event owns the message.

Sending email is a security surface of its own once it carries recipient links: SPF, DKIM, and DMARC on the sending domain, and a subdomain separate from the app so a deliverability problem never affects auth email. Bounce and complaint handling before any bulk send.

## What never reaches a log

Restating [../security/tenancy-and-data.md](../security/tenancy-and-data.md), because this is the layer where it gets violated:

**No prompts. No outputs. No brief content. No recipient fields.** `generations` holds phase, token counts, repair flag, error class, duration — enough to answer what it costs and which rules fail most.

Sentry is the specific risk. It captures request bodies by default, and a request body here is a customer's unreleased launch messaging. Configure server-side scrubbing before the first event is sent, not after — [../security/operations.md](../security/operations.md) calls error trackers the most common accidental PII sink, and this is what that means concretely.
