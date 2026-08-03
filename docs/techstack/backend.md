# Backend

Three runtimes, and the lines between them are trust boundaries rather than convenience.

## The three runtimes

| | Runs | Has | Never has |
|---|---|---|---|
| **App** (Vercel) | Editor, pipeline, publish render, API routes | DB, model access, sessions | Long-running work |
| **Job worker** (Fargate) | pg-boss — transcreation, posters, live-data refresh, scheduled work | DB, model access | Hostile input |
| **Fetch worker** (Fargate) | URL fetch, screenshots, document parsing, integration reads | Integration credentials, egress-only network | **DB access, VPC route, secrets beyond its own** |

### Why two workers

[../security/infrastructure.md](../security/infrastructure.md) called for "a dedicated worker with egress-only networking and no route to the VPC", and separately said that worker holds decrypted integration credentials. But the same document assigns it work with the opposite requirement — transcreation and poster generation need database access and never touch attacker-controlled bytes.

One process doing both is the exact combination the isolation exists to prevent: **the thing holding database credentials would also be the thing parsing an attacker's PDF and rendering an attacker's webpage.**

So they split, and the split is on trust rather than on job type:

- **The fetch worker touches hostile input and has nothing worth stealing.** A `pdf.js` CVE, a Chromium sandbox escape, or an SSRF bypass lands on a box with no database, no VPC route, and no metadata endpoint. Its one secret is the integration token it is actively using.
- **The job worker has real privileges and never touches hostile input.** Its inputs are rows from your own database, already validated.

This costs one extra task definition. It is the cheapest security control in the whole stack.

## Data

**Postgres.** Docker locally, RDS/Aurora in production — same database, no dialect differences, and the local-to-production move is a connection string. **Drizzle** for typed SQL and `drizzle-kit` for migrations, generated as SQL, committed, applied in CI.

One shared dev database. Preview-per-branch databases are genuinely useful while a schema changes constantly, and they are not worth a second database vendor yet — revisit if migrations start hurting.

### Isolation: RLS on a session variable

Supabase's `auth.uid()` is gone with Supabase. The replacement is a session variable set per transaction:

```sql
create policy own_experiences on experiences
  for all to app_user
  using      (owner_id = current_setting('app.user_id')::uuid)
  with check (owner_id = current_setting('app.user_id')::uuid);
```

```ts
// one wrapper, every authenticated query goes through it
await db.transaction(async (tx) => {
  await tx.execute(sql`set local app.user_id = ${userId}`);
  return fn(tx);
});
```

**`set local`, inside a transaction, in exactly one wrapper.** Not per query, not per route. A connection returned to the pool with a lingering `app.user_id` would serve the next request as the wrong user, and `set local` is what scopes it to the transaction. This is the single most dangerous line in the backend, which is why it exists once.

The invariants from [../security/tenancy-and-data.md](../security/tenancy-and-data.md) survive the move unchanged and one of them gets easier: **the application connects as a role with no `bypassrls`**, and a separate migration role owns DDL. The "anon has zero grants" rule becomes "there is no anonymous role at all" — nothing but your server ever connects.

RLS here is defense-in-depth rather than the primary control, because no browser talks to Postgres directly. That is not a reason to skip it. The measured failure rate of app-layer-only isolation is in [../security/ai-built-app-failures.md](../security/ai-built-app-failures.md), and one forgotten `where` clause with nothing behind it is a cross-tenant read.

### Connection pooling

Fargate tasks plus Vercel functions means many short-lived connections against a fixed Postgres limit. **RDS Proxy**, or PgBouncer in transaction mode. Note the interaction: transaction-mode pooling and `set local` are compatible — session-mode assumptions are not, and prepared statements need care with Drizzle.

## Auth: Better Auth

v1.6 as of May 2026, Drizzle adapter, and **users live in your own Postgres** — which is what makes the session-variable RLS above work cleanly, since the user id and the data it guards are in one database with a real foreign key between them.

It ships what the security doc requires rather than leaving it to you: OAuth, email verification, password reset, MFA, passkeys, organizations, and rate limiting. Auth.js has none of the last four, and every one of them is on the list in [../security/tenancy-and-data.md](../security/tenancy-and-data.md).

**The rules from that document still apply and are not Better Auth's job:**

- **Authorization is checked at the data layer, never in middleware alone** — [../security/platform-and-packages.md](../security/platform-and-packages.md), CVE-2025-29927
- Sessions invalidate on password change
- OAuth links by verified email only
- Signup, login, and reset are enumeration-safe
- Auth endpoints are rate-limited separately from generation quotas

## Jobs: pg-boss

The queue is a table in the database you already have. No Redis, no vendor, no second datastore — and jobs enqueue **in the same transaction** as the data change that caused them, so a publish that rolls back cannot leave an orphaned poster-generation job behind. That transactional property is the actual reason, more than the simplicity.

Work it runs: transcreation per locale, 3D poster generation, scheduled live-data refresh, retention deletion, custom-domain re-verification.

It will not scale past one Postgres. That is fine for years, and when it stops being fine the problem is a good one to have.

### Publishing — where the render happens

The original framing here was that the job worker cannot render, because the renderer lives in the app repo. **That premise is wrong given the repo split that was actually chosen**: only the fetch worker got its own repo, and the job worker ships from the app repo ([infrastructure.md](infrastructure.md)). It has the renderer.

So there is one renderer in one codebase ([../coderules/patterns.md](../coderules/patterns.md)) running in two places, and each does the job it fits:

| | |
|---|---|
| **Job worker** | Publishing, especially multi-locale. No function-timeout ceiling, so a 12-locale publish is one job rather than twelve chunked calls. Also where the visual verification loop runs ([pipeline-tools.md](pipeline-tools.md)), since that needs the renderer and Playwright together |
| **App (Vercel)** | Single-scene preview renders during generation, where latency matters and the work is small |

A Vercel publish route still works and was the earlier decision; it is now the fallback rather than the design, because the timeout chunking it required exists only to work around a constraint that turned out not to apply.

**The fetch worker never gets the renderer.** It is the container that handles hostile input, and giving it the component that produces pages would put page-making capability inside the quarantine. The trust split is the point.

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

OpenRouter's `strict: true` enforcement varies by provider: some guarantee schema-conforming output, some translate the schema into their own format, some treat it as a strong hint. So the claim in [../security/prompt-injection.md](../security/prompt-injection.md) — *"a fully compromised model can only emit valid Scene JSON"* — is no longer enforced by the decoder.

**What actually holds, and why the security posture survives:**

> The Zod parse was always the real gate. Decoder-level enforcement was a *cost and reliability* optimization — it lowers how often the model produces something invalid. It never was the thing that stopped invalid output from being rendered.

Output that fails Zod is rejected, repaired once, and then fails visibly. It never reaches a page. The security claim restates as *"a fully compromised model can only cause a rejected generation"*, which is the same outcome by a different route.

The residual is real but small: an attacker who fully controls model output can drive repeated repair cycles and burn tokens — denial of wallet, already covered by quotas and the kill switch.

**The metric that decides whether this was right is the repair rate**, already tracked in [../v1/ai-pipeline.md](../v1/ai-pipeline.md)'s `generations` table. Watch it from the first generation. If Build's repair rate is materially worse than a direct Anthropic call, move that one phase behind the seam — the seam exists for exactly this, and nothing else in the pipeline changes.

Two things the seam must not hide: **prompt caching** behavior and **cost per phase**. Both vary by route and both are load-bearing for the ~$0.20-per-experience figure. Log them per call.

Per-phase model selection is deliberately unresolved. Decide it with real briefs and a repair rate, not in advance.

## Email: Resend

Verification, password reset, and eventually recipient link delivery. React Email for templates, so the transactional emails are written in the same language as everything else.

Sending email is a security surface of its own once it carries recipient links: SPF, DKIM, and DMARC on the sending domain, and a subdomain separate from the app so a deliverability problem never affects auth email. Bounce and complaint handling before any bulk send.

## What never reaches a log

Restating [../security/tenancy-and-data.md](../security/tenancy-and-data.md), because this is the layer where it gets violated:

**No prompts. No outputs. No brief content. No recipient fields.** `generations` holds phase, token counts, repair flag, error class, duration — enough to answer what it costs and which rules fail most.

Sentry is the specific risk. It captures request bodies by default, and a request body here is a customer's unreleased launch messaging. Configure server-side scrubbing before the first event is sent, not after — [../security/operations.md](../security/operations.md) calls error trackers the most common accidental PII sink, and this is what that means concretely.
