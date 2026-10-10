# db — the two databases, written out as SQL

Both files here are **generated, for reading**. Never run them by hand and never edit them:

- **Alembic** owns the `app` tables. The source is `api/store/models.py`, and the migrations are in `api/migrations/`.
- **Better Auth's CLI** owns the `auth` tables.

Regenerate both after any change to the tables:

```
cd api
uv run python -m cli schema
```

`app.sql` is the Alembic migration rendered offline, so no database is touched. `auth.sql` is read from the live auth database: table structure only, never rows. It needs `AUTH_DATABASE_URL` in `.env`.

Both databases are Postgres on Neon. They are **two separate databases that share nothing**. Python reads only `app`; the web app's Better Auth reads only `auth`. Python learns who the user is from a signed token, never from the `auth` tables.

## app.sql — the `app` database (Python)

| Table | One row is | Notes |
|---|---|---|
| `users` | a person | `id` is Better Auth's user id (the token's `sub`). Name and avatar. Deleting a user deletes everything below that is theirs |
| `decks` | a deck | The whole `Deck` as JSON in `data` (brief, outline, facts, slides' QA, look). `version` stops two writers overwriting each other; `aborted` is the Stop button |
| `questions` | a deck's interview questions | Written by the interview job |
| `events` | one thing that happened to a deck | Numbered per deck (`seq`). The page follows them live: a slide ready, a stage started, an edit done |
| `jobs` | one piece of work for the worker | `kind` (interview, outline, build, edit, style, logo, screens), `state` (queued, running, done), a heartbeat. At most one waiting job per deck and kind |
| `kept` | a finished slide | Its HTML and CSS, and how it was made (`origin`: authored, improved, repaired, fallback, edited) |
| `versions` | a labelled snapshot for undo | The deck, its kept slides and the files it linked. Up to 20 per deck |
| `version_files` | a file that a snapshot linked | So an undo restores screenshots and exports exactly |
| `blobs` | file bytes, stored once | Screenshots, exports, PDFs, uploads, keyed by their sha256. Shared between decks and versions; swept when nothing links them |
| `deck_files` | a deck's current file | A name (`slides/s03.png`, `export-present.html`, `screen-1.webp`) pointing at a blob |
| `ledger` | one model call | Model, tokens, time and cost, **never prompts or deck content**. `deck_id` becomes empty when a deck is deleted, so spending still counts toward the daily cap |
| `alembic_version` | — | Alembic's own note of which migration ran |

## auth.sql — the `auth` database (web, Better Auth)

| Table | One row is |
|---|---|
| `user` | an account: name, email |
| `account` | how that account signs in. For us, email and password (`password` is a hash, never the password) |
| `session` | a signed-in browser: a token, expiry, IP and browser |
| `verification` | a short-lived code Better Auth may issue |
| `jwks` | the key pair that signs the token the web app sends to the Python API. Python checks it with the public key only |
