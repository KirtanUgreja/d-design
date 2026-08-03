# Tenancy & Data

Multi-tenancy arrives in v3 with accounts. Before that there is one local user and nothing to isolate.

## Authentication

Everything below concerns what a session is allowed to do. This section is about how a session comes to exist — the step before isolation, and the one where an attacker prefers to work, because a legitimate session defeats every authorization control by satisfying it.

**Use the provider's auth. Do not build it.** Supabase Auth handles password hashing, session tokens, refresh rotation, email verification, and OAuth. This is the same reasoning as the ledger rule in [../coderules/dependencies.md](../coderules/dependencies.md): never write your own for a crypto primitive or a credential path. Authentication is the canonical example.

What still has to be decided, because the provider does not decide it for you:

| | |
|---|---|
| **Where authorization is checked** | **At the data layer, never in middleware alone.** See CVE-2025-29927 in [platform-and-packages.md](platform-and-packages.md) — a framework bug made middleware skippable, and every app that authorized there was open. Middleware redirects are an optimization |
| **Email verification before anything expensive** | Already required before first generation ([infrastructure.md](infrastructure.md)). It is also the account-farming control |
| **OAuth account linking** | Linking by verified email only. Linking an unverified email from one provider to an existing account is a well-worn takeover path |
| **Session invalidation on password change** | Existing sessions end. Otherwise a stolen session survives the user's response to the theft |
| **Password reset tokens** | Single-use, short-lived, invalidated on use and on password change. Never logged, never in a URL that gets sent to an error tracker |
| **MFA** | Not v3. Offer it when accounts hold something worth stealing — note that they hold integration credentials from day one, which arguably means sooner |
| **Enumeration** | Signup, login, and reset return the same response for existing and non-existing addresses. Cheap, and `recipients` makes the address list itself interesting |

**Rate-limit the auth endpoints specifically**, separately from the generation quotas. Credential stuffing targets login, not the expensive path, and the volume that constitutes an attack there is much lower.

The account-deletion path is a security control too, not only a privacy one: it is the thing that revokes integration credentials. See retention below.

## The invariant

**The `anon` Postgres role has zero grants on every table.**

One sentence, trivially testable, and it removes an entire class of bug.

Anonymous visitors never touch the database. Published pages render server-side through a service role with explicit filters. RLS then only guards *authenticated* users, and there is no anonymous policy to get subtly wrong — which is where Supabase deployments usually fail, because every new table silently needs its anon policy considered forever.

```sql
revoke all on all tables in schema public from anon;
alter default privileges in schema public revoke all on tables from anon;
```

Run it, then assert it in the test suite against every table, including tables that do not exist yet.

## RLS for authenticated users

Every table carries RLS. Ownership is either a direct `owner_id` or a join through `experiences`.

```sql
alter table experiences enable row level security;

create policy own_experiences on experiences
  for all to authenticated
  using      (owner_id = auth.uid())
  with check (owner_id = auth.uid());
```

Child tables — `locales`, `snapshots`, `recipients`, `briefs`, `data_sources`, `domains` — scope through the parent:

```sql
create policy own_locales on locales
  for all to authenticated
  using (exists (
    select 1 from experiences e
    where e.id = locales.experience_id and e.owner_id = auth.uid()
  ));
```

`art_directions` is the exception worth care: system ADs are readable by everyone authenticated, user-authored ones only by their owner.

```sql
create policy read_art_directions on art_directions
  for select to authenticated
  using (source = 'system' or owner_id = auth.uid());
```

**`with check` is not optional.** A policy with only `using` permits an owner to insert or update a row *assigning it to someone else*. Every write policy needs both clauses, and the test suite should attempt exactly that.

**`security definer` views and functions bypass RLS entirely.** A view created that way runs with its creator's privileges, so a view over a protected table hands out exactly what the policy denies — and it does so silently, because the policy is still there and still correct. Default to `security invoker`. A definer function that is genuinely necessary carries its own filter and is reviewed as security code, not as a convenience.

These two, together, are how RLS ends up enabled and ineffective — which is a worse position than RLS being off, because it looks fine. [ai-built-app-failures.md](ai-built-app-failures.md) has the measured background: in one sample of 1,645 AI-built applications, **~70% shipped with RLS disabled outright**. The zero-grants invariant above exists because that number is what "remember to configure it per table" achieves in practice.

## The service role

Used only in server routes, never reachable from a browser. Two rules:

1. **Every service-role query carries an explicit filter.** RLS is bypassed for this role, so the filter is the only control left. `where published_at is not null` is doing security work, not just returning fewer rows.
2. **The service key never reaches the client bundle.** Assert it in the build — grep the output for the key prefix.

## Recipient tokens

`recipients` is the most sensitive table: it holds named contacts at named companies. It is never exposed to anon, and never queried by anything but a single server route that takes a token.

- **128-bit random**, stored — not HMAC-derived. A stored token can be revoked individually without rotating a signing key that would invalidate every campaign at once.
- **Indexed lookup**, so timing does not vary with position.
- **Rate-limited** per IP, even though guessing is infeasible. It catches scanners and tells you someone is trying.
- **Optional per-campaign expiry.**

See [content-and-web.md](content-and-web.md) for the referrer-leak problem, which is how tokens actually escape in practice.

## Integration credentials

Airtable and Notion OAuth tokens grant access to a customer's entire workspace. They are the highest-value secret in the system.

**Envelope encryption.** Data key encrypted by a KMS-held master key; ciphertext in `data_sources.credentials_ref`. A database dump yields nothing usable.

**Decrypted only in the fetch worker.** The app tier never holds a plaintext integration token. This composes with the SSRF isolation in [infrastructure.md](infrastructure.md) — the worker that holds credentials is also the one with no route to your internal network.

**Narrowest read-only scope the integration offers.** This product reads one value from one path. It never needs write access, and asking for it makes a compromise catastrophic instead of embarrassing.

**Revocation on disconnect.** Call the provider's revoke endpoint, do not merely delete the row.

## Logging

`generations` stores **metadata only**: phase, token counts, repair flag, error class, duration.

**No prompts. No outputs.**

Prompts contain the customer's unreleased launch messaging — plausibly the most confidential thing they will ever hand you, and often under embargo. It does not belong in a metrics table that exists to answer "what does this cost" and "which validation rules fail most." Both questions are answerable from counts.

The same rule applies to application logs and error reporting: scrub scene content, brief content, and recipient fields before anything leaves the process. Error trackers are a common accidental PII sink.

## PII and retention

| Data | Retention |
|---|---|
| `views` | 12 months, rolling deletion |
| `recipients` | Until the campaign or account is deleted |
| Integration credentials | Until disconnected, then revoked and purged |
| `generations` metadata | Indefinite — contains no personal data |

**Cascade delete works and is tested.** Deleting an experience removes its locales, snapshots, recipients, and views. Deleting an account removes everything. Write the test that asserts no orphans, because GDPR deletion requests are not the moment to discover a missing foreign key.

**Delete-recipient is a first-class action**, available from the editor, removing or anonymizing their view rows. Retrofitting deletion into an analytics table is genuinely painful — build it with the feature.

**IP addresses are not stored** in `views`. Scroll depth, CTA reach, and duration answer the marketer's questions; the signed link already says who. Anything more is surveillance the product does not need to be valuable.

## Identified tracking

`views.recipient_id` is nullable and **null unless the publisher explicitly enabled identified tracking**. That nullability is the privacy design, not an implementation detail.

Enabling it makes the publisher a data controller with consent, retention, and deletion obligations. The product surfaces that at the moment of opting in, not in a support article afterwards.

See [../v3/personalization.md](../v3/personalization.md) for the product-side treatment.
