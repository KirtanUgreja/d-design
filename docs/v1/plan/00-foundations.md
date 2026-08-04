# Phase 00 — Foundations

> The repo, the gate, and the two rules that must be habits before the first query is written. Nothing in this phase is a feature; everything in it is what stops later phases from needing a rewrite.

**Depends on:** nothing · **Blocks:** everything · **Spec step:** — (precedes step 1)

[../../coderules/tooling.md](../../coderules/tooling.md) puts this at "a few hours, once." Take the day. The custom lint rules here are the only thing standing between a solo AI-assisted build and the duplication numbers in [../../coderules/ai-authorship.md](../../coderules/ai-authorship.md).

---

## Search

**Read first**

- [../../coderules/structure.md](../../coderules/structure.md) — the whole folder layout, and the server/client boundary
- [../../coderules/tooling.md](../../coderules/tooling.md) — the gate, the lint table, the hook mechanics
- [../../coderules/typescript.md](../../coderules/typescript.md) — `tsconfig` flags, and the TS 7 caveat
- [../../coderules/dependencies.md](../../coderules/dependencies.md) — why pnpm, and the ledger format
- [../../techstack/backend.md](../../techstack/backend.md) → "Isolation: RLS on a session variable"
- [../../coderules/patterns.md](../../coderules/patterns.md) → rules 3, 4, 5

**Grep for** — nothing yet. This is the one phase with an empty codebase, which is exactly why the conventions set here have to be right.

**Verify externally before pinning**

| | What to check |
|---|---|
| Next.js | 16.3 is current as of 3 Aug 2026. Confirm the minor, and that `reactCompiler` and `cacheComponents` are still the flag names |
| TypeScript | **Stay on 6.** TS 7.0 shipped 8 July 2026 without a public compiler API, and `typescript-eslint` type-aware rules cannot run on it until 7.1 (~Oct 2026). The two-compiler workaround in [../../coderules/typescript.md](../../coderules/typescript.md) is real and is *not worth taking on day one* — a codebase this size typechecks fast on 6. Revisit at 7.1 |
| pnpm | 11+, so `minimumReleaseAge` and install-script blocking are on by default. Verify rather than assume — check that a package published in the last hour refuses to resolve |
| Zod | 4.2+ — `z.toJSONSchema` is needed in phase 01 |
| Drizzle | current `drizzle-orm` + `drizzle-kit`; confirm the Postgres session-variable pattern still works through the driver you pick |
| `eslint-plugin-import-boundaries` | Does it express "a folder's `index.ts` is its public surface"? If yes, the feature-boundary rule is config, not code. If no, write the custom rule — do not adopt `eslint-plugin-boundaries` for it, which is more configuration than this project needs |

---

## Make

### 1. Repo and package manager

```
pnpm create next-app@latest    # App Router, TypeScript, Tailwind, ESLint, src/
```

`package.json`: leave `pnpm.onlyBuiltDependencies` **absent**. Nothing here needs a native build yet. `sharp` adds itself to that list in phase 10, and the list is more meaningful when every entry arrived for a reason.

### 2. `tsconfig.json`

```jsonc
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "erasableSyntaxOnly": true
  }
}
```

`erasableSyntaxOnly` is what retires the `enum` lint rule — a compiler flag beats a lint rule.

### 3. The gate

`husky` + `lint-staged`, three steps, in order: Prettier → ESLint (no warnings on changed files) → `tsc --noEmit`.

**Keep it under two seconds.** A gate that is fast is a gate nobody routes around, and every rule below is only as real as the hook that runs it.

### 4. Lint rules — the ones that are the point

Stock: `@typescript-eslint/no-explicit-any`, `no-non-null-assertion`, `import/no-cycle`, `react-hooks` including the compiler rules.

Custom, in write-first order:

| Rule | Enforces | Note |
|---|---|---|
| no `db.` call outside the `asUser` wrapper | Rule 9 | **Write this one first.** It is the only rule on the list whose violation is a cross-tenant read rather than a design regression |
| no Drizzle import outside `*.data.ts` | Rule 8 | |
| no `process.env` / `typeof window` / `mode` prop under `renderer/` | Rule 6 | Dormant until phase 04, so write it now while it costs nothing to be strict |
| no Tailwind class under `renderer/` | The no-styling invariant, seen from the app side ([../../techstack/frontend.md](../../techstack/frontend.md)) | |
| no `dangerouslySetInnerHTML` outside the Slot path | [../../security/content-and-web.md](../../security/content-and-web.md) | |
| feature public API boundary | Rule 4 | Plugin if one fits, custom if not |

### 5. The post-edit hook

`scripts/hooks/post-edit.sh` already enforces `check-docs.sh` on `.md` edits. Add the `*.ts` branch now: run `tsc --noEmit` and `eslint` on the written file, exit 2 on failure so the agent fixes the file while it still remembers why it wrote the line.

### 6. `docker-compose.yml`

```yaml
postgres    # the real database, same one as production
minio       # S3-compatible object storage
```

**MinIO from day one** is deliberate. `storage.ts` is the only abstraction in the project with a planned second implementation ([../spec.md](../spec.md)), and pointing it at the S3 API locally means it ends up with one implementation after all. MinIO is not a mock; it speaks the same protocol. LocalStack waits for v3 — there are no integration credentials to encrypt yet.

### 7. `src/lib/` — three files, and no more

```
src/lib/result.ts     Result<T, E> — the one error type (coderules/typescript.md)
src/lib/ids.ts        crypto.randomUUID, platform, no dependency
src/lib/storage.ts    S3 client → MinIO locally. One implementation
```

`lib/` is what every feature uses and no feature owns. If something here ends up used by one feature, move it into that feature.

### 8. `src/db/` — the dangerous part

```ts
// src/db/tenant.ts — the only place app.user_id is ever set
import 'server-only';

export function asUser<T>(userId: string, fn: (tx: Tx) => Promise<T>) {
  return db.transaction(async (tx) => {
    await tx.execute(sql`select set_config('app.user_id', ${userId}, true)`);
    return fn(tx);
  });
}
```

Three things that are invisible in review and all three are load-bearing ([../../coderules/patterns.md](../../coderules/patterns.md), rule 4): the `true` scopes the setting to the transaction; the pooler must run in **transaction mode**; and a tenant-scoped query outside a transaction is unsafe by construction on a shared pool.

**v1 has one user.** Seed a fixed uuid, read it from env as `LOCAL_USER_ID`, and pass it to `asUser` exactly as v3 will pass a session's user id. The wrapper does not know the difference, which is the entire reason for building it now.

Roles: the app connects as `app_user`, which has **no `bypassrls`**. A separate migration role owns DDL. There is no anonymous role at all — nothing but the server ever connects ([../../techstack/decisions.md](../../techstack/decisions.md)).

### 9. First migration — two tables and their policies

```
experiences  id, owner_id, title, mode, brand_id, art_direction,
             scenes (jsonb), published_at, created_at, updated_at
brands       id, owner_id, display_font, text_font, primary,
             secondary, neutral, logo_asset_id
```

```sql
create policy own_experiences on experiences
  for all to app_user
  using      (owner_id = current_setting('app.user_id')::uuid)
  with check (owner_id = current_setting('app.user_id')::uuid);
```

The other three tables (`assets`, `briefs`, `generations`) arrive in the phases that need them, each with its own policy and its own isolation test. That keeps the migration story honest — a table exists because something reads it.

The scene tree is one `jsonb` column, never normalized. It is always read and written whole, Zod validates it rather than SQL, and normalizing would buy queries nobody runs.

### 10. Next config

```ts
reactCompiler: true      // stable in 16, and hot path #3 is the editor canvas
cacheComponents: true    // author against `use cache` from the start, not later
```

### 11. CI

GitHub Actions, one workflow: the gate · Vitest · dependency advisory check · `jscpd` on changed files (**warning, never a gate** — it is a signal about the one metric that degrades silently) · `scripts/check-docs.sh`.

---

## Verify

**The gate**

- [ ] `pnpm lint && pnpm typecheck && pnpm format:check` green on the empty repo
- [ ] A commit that fails any step does not land. Test it by breaking one on purpose

**Rule 9, proven rather than assumed** — this is the phase's most important test:

- [ ] `current_setting('app.user_id')` on a connection where it was never set **fails**, and does not match everything. That is [../../coderules/patterns.md](../../coderules/patterns.md) rule 5 applied to isolation
- [ ] A `db.select()` written outside `asUser` **fails lint**. Write the violation, watch it fail, delete it
- [ ] Two rows owned by two different uuids: `asUser(a)` sees exactly one

**Fail-closed, seeded early** ([../../security/testing.md](../../security/testing.md) → "Failing closed")

- [ ] `Result` is the only error type in `lib/`. No `catch` returning a permissive default exists yet — and now there is a rule and a habit before there is a `catch` to get wrong

**Supply chain** ([../../coderules/dependencies.md](../../coderules/dependencies.md) → "Test")

- [ ] A package published within the last day refuses to resolve — verify the default, do not trust it
- [ ] Lockfile committed, installs run frozen
- [ ] CI fails on a known-critical advisory

---

## Skipped

| Not built | Trigger to build it |
|---|---|
| TypeScript 7 | 7.1 ships the stable compiler API and `typescript-eslint` supports it. Until then it is two compilers on disk for a typecheck that is already fast |
| Biome | The custom rules above can be expressed in it. Speed is not the reason; one binary instead of two is |
| LocalStack | Integration credentials exist (v3) |
| `@d-design/schema` published | The fetch worker exists and needs it (v3). Layout is package-shaped already |
| Auth, sessions, Better Auth | v3. `asUser` takes a user id from env instead of a session, and that is the only difference |
| Branch-per-preview databases | Migrations against one shared dev DB start hurting |
| Terraform, AWS, CloudFront, ECS | v3. A perfect VPC does not move Risk 1 at all ([../../techstack/infrastructure.md](../../techstack/infrastructure.md)) |

---

## Exit gate

- [ ] Gate green, CI green, hook fires on a bad `.ts` write
- [ ] `asUser` exists, is the only place `set_config` appears, and the lint rule blocks bypassing it
- [ ] Unset-`app.user_id` fails rather than matching all rows
- [ ] RLS policies on both tables, isolation test passing
- [ ] `docker compose up` gives Postgres and MinIO, offline
- [ ] `storage.ts` reads and writes an object through the S3 API against MinIO
- [ ] `AGENTS.md` reviewed against what actually got built — it is the file every later session inherits
