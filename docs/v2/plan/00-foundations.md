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

- [ ] `POST /screenshot` with a hand-written scene tree returns a PNG that shows the scene, at a fixed viewport, under the art direction it was given
- [ ] Two requests in a row reuse one browser process. Assert on process count, not on latency feeling fine
- [ ] `render` has no `DATABASE_URL`, no `S3_*`, and no `OPENROUTER_API_KEY` in its environment. Assert it in the compose file and in a test that reads `process.env` — this is the control, and a control nobody asserts is a comment
- [ ] It refuses a payload that is not a valid `Scene[]` — one Zod parse at entry, like every other boundary

**Migrations**

- [ ] `alembic upgrade head` then `downgrade` then `upgrade` again, clean, against a database with existing v1 rows
- [ ] Every v1 experience comes out with `{"id": "cinematic-dark", "version": 1}` or its editorial equivalent, and its `scenes` jsonb is byte-identical before and after
- [ ] `scripts/checks/invariants.sh` still passes — in particular the Alembic auth-table filter, which now has three more migrations to be wrong about

**Security** ([../../security/testing.md](../../security/testing.md))

- [ ] A second user cannot read another user's `art_directions` row, and *can* read every `owner_id is null` row. Exercised through `as_user()`, not raw SQL
- [ ] A second user cannot read another user's `snapshots`
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

- [ ] `docker compose up -d` brings up postgres, minio, and render
- [ ] `render` returns a correct screenshot of a hand-written scene tree, and holds no credential
- [ ] Four migrations up, down, and up again against v1 data with no content change
- [ ] RLS proven on both new tables, including the system-AD read path
- [ ] `@d-design/schema` is versioned and consumed by both `web` and `render`, through a workspace protocol and no registry
- [ ] The whole of v2 still runs on `docker compose up` and a dev server, with no account on any external service. If this phase acquired one, it acquired the wrong thing
- [ ] The gate is green
