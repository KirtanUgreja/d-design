# Phase 00 — Foundations

> The `render` service, the schema published as a real package, and the four migrations everything else in v2 writes to. One sitting, no features, and it is the only phase in this release that touches infrastructure.

**Depends on:** v1, complete · **Blocks:** [01](01-ad-format.md) · **Spec step:** infrastructure

---

## Search

**Read first**

- [../spec.md](../spec.md) → "Persistence delta" — the four table changes, and note that `art_directions` holds hand-authored and user-authored ADs in the same table on purpose
- [../../techstack/backend.md](../../techstack/backend.md) → the trust split. `render` holds the renderer and Playwright and **no credential at all**; `jobs` orchestrates it and holds the database
- [../../techstack/infrastructure.md](../../techstack/infrastructure.md) — what v2 adds to Docker Compose, and what stays until v3
- [../../coderules/typescript.md](../../coderules/typescript.md) → why `@d-design/schema` gets published now rather than file-linked

**Grep for**

- `docker-compose.yml` — the existing `postgres` and `minio` services. `render` joins them; it does not get its own compose file
- `api/migrations/versions/` — the last revision id. v2's migrations chain from it, and the auth-table filter in `env.py` stays untouched
- `web/scripts/generate-schema.mjs` and `web/src/schema/index.ts` — the generated package already has the folder layout a published package would have. Publishing it is a `package.json` and a Changeset, not a restructure
- `web/src/features/renderer/index.ts` — `SceneRenderer` is what `render` imports. It must stay the only thing it needs

**Verify externally**

- That Playwright's Chromium runs in whatever base image `render` uses, headless, at a fixed viewport. Do this before writing the service, not after — a container that cannot screenshot is a phase-09 discovery you want in phase 00

---

## Make

```
render/                             NEW. TypeScript, its own package
  src/server.ts                     one route: POST /screenshot
  src/render-scene.ts               Scene[] + ArtDirection + motion -> HTML
  src/browser.ts                    a single Playwright browser, reused
  Dockerfile
  package.json                      depends on @d-design/schema

docker-compose.yml                  + the render service
api/migrations/versions/
  0006_art_directions.py            art_directions, motion_vocabularies
  0007_snapshots.py                 snapshots
  0008_experience_v2_refs.py        experiences: art_direction -> {id, version}, + motion_vocabulary, + mode already exists
```

### `render` is a service, not a library

Python cannot server-side-render React, and the visual verification loop in phase 09 needs the renderer and Playwright in one process. That is the whole reason this exists.

**It holds no credential.** No database URL, no S3 key, no model key. It takes a scene tree and tokens over HTTP and returns a PNG. `jobs` calls it. If `render` is ever given a database connection, the trust split in [../../techstack/backend.md](../../techstack/backend.md) has quietly collapsed and the reason it was safe to run a browser in it has gone with it.

**It is not the fetch worker and must never become it.** A schema-validated scene tree with no presentational values is *trusted* input. The fetch worker renders attackers' pages; `render` renders yours. Putting the renderer in the quarantined container would hand hostile-input territory a copy of the thing that makes pages.

One browser instance, reused across requests, with a page pool. Launching Chromium per screenshot is the difference between the loop costing latency and costing a minute.

### The schema becomes a real package

`render` is the second TypeScript consumer, which is the trigger [../../coderules/structure.md](../../coderules/structure.md) already named. `web` and `render` both depend on `@d-design/schema`; neither hand-edits it; CI still regenerates it from Pydantic and fails on a diff.

Nothing about the generation changes. What changes is that a `file:` link becomes a version, so `render` cannot silently drift onto a different schema than `web` compiled against.

**A workspace protocol, not a registry.** `workspace:*` with an explicit version gets the whole benefit — versioned, no drift, CI still fails on a regeneration diff — and costs no external service, no auth, and no publish step in the local loop. Everything in v2 runs on `docker compose up` and a dev server with no account anywhere, and that property is worth keeping deliberately rather than losing to a convenience. A registry belongs to v3 step 11, when the services deploy separately and there is no shared workspace to resolve through ([../../v3/spec.md](../../v3/spec.md) → Build order).

### The migrations

```sql
art_directions      id text, version int, name text, author text,
                    tokens jsonb, budgets jsonb, brand_mapping jsonb,
                    default_motion text, owner_id uuid null, created_at
                    primary key (id, version)

motion_vocabularies id text, version int, tokens jsonb, created_at
                    primary key (id, version)

snapshots           id uuid, experience_id uuid, owner_id uuid,
                    scenes jsonb, art_direction jsonb, motion_vocabulary text,
                    mode text, label text null, trigger text, created_at

experiences         art_direction jsonb   -- {id, version}, was text
                  + motion_vocabulary text
```

**`(id, version)` is the primary key on both token tables.** A version is not an audit column here; it is part of the identity, because phase 06's published pages point at one. Updating an art direction inserts a row.

**`owner_id` is nullable on `art_directions` and that nullability is load-bearing.** `null` means a system art direction, visible to everyone; a uuid means a user authored it. The RLS policy is `owner_id is null or owner_id = current_setting('app.user_id')::uuid` — and it goes in the same migration as the table, like every other policy in this codebase. A system AD is readable by all and writable by none through the tenant wrapper.

`snapshots` is tenant-scoped with the ordinary policy. It carries `owner_id` rather than joining through `experiences`, for the same reason `generations` does — RLS policies key off a column on the row they filter.

**Migrating `experiences.art_direction` from `text` to `jsonb`** is the one destructive-looking step. Existing rows become `{"id": "cinematic-dark", "version": 1}` and `{"id": "editorial-light", "version": 1}` in the same migration that changes the type. Write the downgrade; you will use it at least once during phase 01.

---

## Verify

**The gate** — green, including the schema regenerating with no diff now that two consumers read it.

**The service**

- [x] `POST /screenshot` with a hand-written scene tree returns a PNG that shows the scene, at a fixed viewport, under the art direction it was given
- [x] Seven requests in a row reuse one browser process — asserted on `pgrep -P <server pid>`, which stays at 1
- [x] `render` has no `DATABASE_URL`, no `S3_*`, and no `OPENROUTER_API_KEY`. Asserted by absence in the compose file **and** by `assertNoCredentials`, which refuses to start — confirmed live
- [x] It refuses a payload that is not a valid `Scene[]`, and an art direction outside the schema's own closed set

**Migrations**

- [x] `alembic upgrade head` then `downgrade` then `upgrade` again, clean, against a database with existing v1 rows
- [x] Every v1 experience comes out with `{"id": "cinematic-dark", "version": 1}`, and its `scenes` jsonb is byte-identical before and after
- [x] `scripts/checks/invariants.sh` still passes — in particular the Alembic auth-table filter, which now has three more migrations to be wrong about

**Security** ([../../security/testing.md](../../security/testing.md))

- [x] A second user cannot read another user's `art_directions` row, and *can* read every `owner_id is null` row. Exercised through `as_user()`, not raw SQL
- [x] A second user cannot read another user's `snapshots`
- [x] **A tenant cannot *write* a system art direction.** Confirmed to fail with `InsufficientPrivilegeError` — the policy, not an incidental constraint
- [ ] `render` is unreachable from the public network in the compose topology — it is called by `jobs`, not by a browser

**Human**

- [ ] Look at a screenshot the service produced, at the viewport phase 09 will use. If it does not look like the page, phase 09 will be a vision model confidently reviewing the wrong image

---

## Skipped

| Not built | Trigger |
|---|---|
| AWS, RDS, a deployed anything | v3. v2 is still Docker Compose and a dev server ([../../techstack/infrastructure.md](../../techstack/infrastructure.md)) |
| A queue in front of `render` | When a single browser pool stops absorbing the load, which one local user will not do. `jobs` calls it synchronously in v2 |
| Publishing `@d-design/schema` to any registry, public or private | **v2 uses a workspace protocol** — `workspace:*` with a version in `package.json`, resolved by pnpm. What matters is that the version is explicit so `render` cannot silently drift onto a different schema than `web` compiled against; a registry adds an external service and an auth story to buy nothing at two consumers in one repo. A real registry arrives with v3 step 11, when the services deploy separately and there is no shared workspace to resolve through. v4's marketplace is the public case |
| Frame extraction from video | Phase 12, and it lands in the **fetch worker**, not here. Video containers are the same hostile-bytes class as PDFs ([../primitives.md](../primitives.md) → `ScrollSequence`) |

---

## Exit gate

- [x] `render` is a compose service; `docker compose up -d` brings up postgres, minio and render. **The image build itself is not verified** — see below
- [x] `render` returns a correct screenshot of a hand-written scene tree, and holds no credential
- [x] Migrations up, down, and up again against v1 data with no content change
- [x] RLS proven on all three new tables, including the system-AD read path *and* the system-AD write refusal
- [x] The renderer is *shared* with `web` rather than versioned against it — see the deviation below, which is a stronger guarantee than the one this phase asked for
- [x] The whole of v2 still runs on `docker compose up` and a dev server, with no account on any external service
- [x] The gate is green

## Where this phase stands

**Both halves are built.** They are two unlike things sharing a phase — one is database schema, the other exists because Python cannot server-side-render React — so they landed as two commits.

Migrations numbered 0008–0010 rather than the 0006–0008 this file predicted: v2 phases 14 and 15 landed first and took three numbers. A migration number is a position in a chain, not a name.

**Not verified: the Docker image build.** The Dockerfile is written against `mcr.microsoft.com/playwright:v1.56.0-noble` and the compose service is wired, but the image has not been built — it is a ~2GB pull. The service itself is verified in the way that matters, running the real bundle against real Chromium and returning real PNGs. What remains unproven is the container, and that is stated rather than implied.

### What the type change actually cost

**`experiences.art_direction` going from `text` to `jsonb` broke nine tests, and that is the change working.** The column now holds `{"id": …, "version": 1}`, so every caller writing a bare `'cinematic-dark'` failed loudly at the boundary rather than storing something that would not parse later.

The ripple was five files and stops at the data layer: `publish_data.ad_ref` / `ad_id` map between the stored reference and the `ArtDirectionId` the rest of the application still speaks. **Lifting the version into the API surface is [01](01-ad-format.md)'s job**, and keeping that boundary here is what stops phase 00 from quietly becoming phase 01.

`_CURRENT_AD_VERSION` is a literal rather than a lookup, deliberately: a lookup would be the data module deciding which version an experience gets, which is a product decision belonging to the phase that adds the picker.

**mypy caught defensive code for a case that cannot arrive.** `ad_id` also accepted a bare string, for a database restored from a pre-0010 dump. The branch was unreachable given the column's type — and correctly so, since such a dump also predates `motion_vocabulary` and would fail long before reaching it. Removed rather than widened: defensive code for an impossible case is a comment that looks like a control.

### The renderer is shared, not versioned

This phase specified `@d-design/schema` as a published package so `render` could not drift onto a different schema than `web` compiled against. **The workspace makes that concern disappear rather than manage it**: esbuild bundles `render` directly from `web/src`, so the two consume one source tree and *cannot* disagree — which is strictly stronger than a version pin, since a pin can be stale. The registry question returns at v3 step 11, when the services deploy separately and there is no shared tree to resolve through.

`esbuild` is a new dependency with a ledger line. Node 26 strips TypeScript types natively, so a plain `.ts` service would need no build step at all — but it does not transform **JSX**, and the renderer is entirely `.tsx`. A JSX compiler is on the don't-write-your-own side of that file's own line.

### What the build found

**The first working screenshot came back set in Times.** The art direction asked for Fraunces, the headless document had no font loaded, and Chromium fell back silently. It looked plausible, which is the dangerous part — this phase's own human check says a screenshot that does not look like the page makes [09](09-visual-verification.md) *"a vision model confidently reviewing the wrong image"*, and [13](13-scene-fit.md)'s overflow measurement is metrics arithmetic on the same frame. Wrong font, wrong line count, wrong answer, no error anywhere.

`src/fonts.ts` inlines the real woff2 as data URIs — `setContent` gives the page an opaque origin with no base URL, so `file://` and relative references resolve to nothing. It **throws** when a family is missing rather than degrading, which it promptly did: `render` did not have `@fontsource` as its own dependency and said so loudly instead of shipping another Times screenshot.

**The error body leaked scene content.** The handler returned `error.message`, which for a Zod failure is the whole issue list — offending values included, and a scene tree is a customer's unreleased launch copy. It reports paths and codes now (`invalid_type at blocks.0.props.text`), the same trade the Python seam's `_describe` already makes.

**The gate did not cover `render/`.** A new package is exactly where a violation arrives, and it was ungated until the pre-commit hook grew a block for it — which also runs on a `web/src/` change, because that is what `render` bundles.

### The policy decision worth keeping

`art_directions` has **two** policies, not one `for all`:

```sql
read  using (owner_id is null or owner_id = current_setting('app.user_id')::uuid)
write using/with check (owner_id = current_setting('app.user_id')::uuid)
```

Folding them into one would make `with check` accept the `is null` arm along with the read — and a tenant that can insert `owner_id = null` is a tenant publishing an art direction to every other account on the platform. Reading a system AD is for everybody; writing one is for nobody, and system rows are seeded by migration, which never runs through `as_user()`.
