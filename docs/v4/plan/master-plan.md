# Master plan — to submission (2026-10-08 → 2026-10-10)

> **What is true at submission:**
> 1. A person signs up with email and a password and types a brief.
> 2. They answer a few questions and approve an outline whose every number has a source.
> 3. They see the deck's style before it is built, then watch the deck arrive slide by slide.
> 4. The deck looks designed by a person and unlike other decks: real imagery in one style, charts drawn from the data, their logo.
> 5. They can edit it, undo, present it, and send it as one offline file. Their decks are theirs alone, kept in Postgres.

**Decided by the owner, 2026-10-08:**
- The reference library is fine ("absolutely fine").
- **Tomorrow's build includes accounts, user management and the database.**
- **Auth is Better Auth with email and password only.** No OAuth keys to set up for a one-day build.
- **The database is free hosted Postgres** (Neon or Supabase). The owner creates it and gives the connection string.
- **Parallel build agents: yes.** **Up to $0.10 for two format checks: yes.**
- Build everything on 2026-10-09; test with new credit on 2026-10-10; submit by 2026-10-10.

Evidence for the design direction: [../research-2026-10.md](../research-2026-10.md). The auth decision in the docs: [../../security/tenancy-and-data.md](../../security/tenancy-and-data.md) → Authentication.

## The three days

| Day | What happens | Credit |
|---|---|---|
| **Wed 2026-10-08** | This plan, the phase files, the recorded decisions. No build. | none |
| **Thu 2026-10-09 — build day** | Everything in "Build day" below, offline: every item ends with its tests green using fake models. Parallel agents work in their own git worktrees and the main session merges them. | **≤ $0.10** of the ~$1.80 left (two format checks) |
| **Fri 2026-10-10 — test day** | The owner tops up; the runbook below; one fix window; code freeze; the submission package. | ~$12–17 used; **top up $20** |

Rules for the sprint:
- **Nothing that needs credit or the owner blocks the build.** Paid and human steps move to test day, in order.
- **Every build item ends offline-verified.** That means unit tests with fake transports, browser QA, and a contact sheet looked at.
- **Security is not cut for time.** Every route is tested with no session and with another user's session. Anything that grants fails closed (AGENTS.md rules 9–10).
- **Cut lines are explicit.** A P1 item not done by 22:00 moves to "after submission" with its trigger written down. Nothing half-built is left on the path.
- **No overclaiming.** The submission reports what the walls measured, including what failed.

## Where we are (2026-10-08)

| Area | State |
|---|---|
| Engine: content (interview, research, storyline with sources), QA in Chromium, repair ladder, export (present, send, PDF, offline) | Built and tested; content bench passed (inverse spec 0.77, 0 banned words) |
| Look system: continuous palettes, variable fonts, textures, charts (9 forms, validated colours), logo engine | Built |
| App: API, worker, live web flow (questions → outline gate → watch → exports), editor (text, move, delete, recolour, fit, undo) | Built; proven with a fake model in a browser; data in the file store, no accounts |
| **Design quality** | **Failed the owner's walls.** First one house style (Designed 3.5, Varied 3.1), then messy with free shapes. Fix: phase 39 |
| Credit | ~$1.80 left |

## Definition of done for submission

1. **Design:**
   - The owner's 12-deck wall averages **Designed ≥ 4.0 and Varied ≥ 4.0**, and no deck is called messy.
   - **Gate 2** ("would send to an investor or customer") is yes for at least 9 of 12, rated blind against the one-shot baselines.
2. **Reliability:** ≤ 3% of slides flagged, ≤ 10% built by code, median ≤ $0.60 and p90 ≤ 5 minutes a deck.
3. **Accounts and data:**
   - Sign up, sign in, sign out, an account page and account deletion all work.
   - Each user sees only their own decks; another user's deck is a 404.
   - Data is in the hosted Postgres; a per-user spend cap is in place.
   - Every route is tested with no session and with another user's session.
4. **Product:** a typed brief builds live end to end in the app. The owner builds 3 decks there, and checks with two accounts that neither sees the other's decks.
5. **Engineering:** the gate is green (ruff, mypy --strict, pytest, eslint, tsc, OpenAPI drift, docs), and the e2e suite is green.
6. **Package:**
   - A README a reviewer can run in a few commands.
   - The evidence (walls, findings).
   - 3–5 showcase decks.

If (1) misses, the submission still ships, with the best decks as the showcase and the wall reported honestly.

## The sprint, by phase

| Phase | Sprint scope | Day | Priority |
|---|---|---|---|
| [39 — design reset](39-design-reset.md) | Visual languages, the reference library, retrieval and reference-fill, `compose.v11`, imagery, the style preview, model plumbing, the scorer | build | **P0** (scorer P1) |
| [29 — accounts and deploy](29-accounts-deploy.md) | **Better Auth** (email and password) in the web, hosted Postgres behind the one Python data module with the **tenant wrapper**, JWT verification in FastAPI, user management, a per-user cap, release packaging | build | **P0** (packaging P1) |
| [37 — beautiful data](37-beautiful-data.md) | The "pair" form for two values; the data wall | build / test | **P0** / test |
| [31 — first run](31-first-run.md) | The brief survives sign-up | build | P1 |
| [38 — brand kit](38-brand-kit.md) | Per-deck logo upload | build | P1 |
| [28 — editor](28-editor.md) | AI edit by instruction (a proposal to accept), notes editing, duplicate, the style refusal | build | P1 |
| [32 — watch and reveal](32-watch-reveal.md) | Real per-slot states; flagged slides named before download | build | P1 |
| [33 — trust and control](33-trust-control.md) | Covered by 28's proposals and the existing provenance chips | build | P1 (via 28) |
| [25 — composition and QA](25-composition-qa.md) | Images moved to 39; **gate 2 is the test-day wall** | test | gate |
| [27 — create flow](27-app-create-flow.md) | Signed-in flow; the owner's 3 live decks | test | P0 check |
| [36 — independent design](36-independent-design.md) | Kept as guards (archive, variable fonts, palettes); the exit is judged by the owner's wall | — | — |
| 21–24, 26, 30 | Built or closed; their open human checks move after submission | — | after |
| 34, 35 | After submission | — | after |

## Build day — Thursday 2026-10-09

### Before 09:00 — what the owner provides

1. **The hosted Postgres connection string** (Neon or Supabase, free tier), put in the repo's `.env` as `DATABASE_URL`. Nothing else is needed.
2. Nothing for auth. `BETTER_AUTH_SECRET` is generated locally; there are no OAuth keys.

### The work

| # | Item | Phase | Pri | Owner | Done when |
|---|---|---|---|---|---|
| B1 | **Visual languages**: 8 authored manifests; the sampler draws the language first (balanced by archive usage), then the tokens it allows | 39 | P0 | main | 1,000 seeds: every language drawn, contrast tests green |
| B2 | **Reference library**: 8 shapes × 8 languages (cut line 48, floor 40), each passing QA filled long and short under 30 looks of its language; `cli refs --wall` | 39 | P0 | **agents R1–R4** (2 languages each) | the reference QA test green; the main session reviewed every contact sheet |
| B3 | **Retrieval and reference-fill** | 39 | P0 | main | every bench slide gets a fitting reference; reference-fill passes QA for every bench slide |
| B4 | **`compose.v11`** and the new ladder (compose → 2 repairs → the alternate reference → reference-fill → code layout → flag); novelty retries only within a deck | 39 | P0 | main | ladder, prompt and resume tests green offline |
| B5 | **Imagery**: `Seam.complete_image`, `components/images.py`, `dd-image` filled after sanitizing, an image budget per language, failure → a quiet field | 39 | P0 | main | fake-transport tests; zero network in exports; image cost in the ledger |
| B6 | **Style preview**: 3 reference-filled slides with the deck's words at the outline ($0); the style card and **Another style** | 39 | P0 | main | API test; browser run with the fake worker |
| B7 | **"Pair" chart form** | 37 | P0 | main | goldens |
| B8 | **Model plumbing** and `cli bakeoff` | 39 | P0 | main | CLI test with fakes |
| A1 | **SQL store**: SQLAlchemy models (users, decks as JSONB, events, jobs, ledger, versions, kept slides, questions) and an Alembic baseline in the `app` schema. It implements the *same* Store interface with a **tenant scope** on every deck method. Jobs are claimed with `SKIP LOCKED`. Blobs (screenshots, exports, uploads) stay on disk under `data/assets/` | 29 | P0 | **agent A1** | the existing store, API and editor tests run against it (SQLite offline; the hosted Postgres when `DATABASE_URL` is set) |
| A2 | **Better Auth in the web**: email and password, sessions, the **JWT plugin** (JWKS), its tables in the `auth` schema via its CLI. Pages: sign up, sign in, account (name, email, sign out, delete account), **Your decks**. Middleware protects the app routes. Recorded demo decks stay public | 29 | P0 | **agent A2** | e2e: sign up → sign in → protected route → sign out |
| A3 | **API auth and tenancy**: a FastAPI dependency verifies the JWT with `PyJWKClient` (signature, issuer, audience, expiry, an algorithm allowlist; any failure, including an unreachable JWKS, is 401). A Python `users` row keyed by `sub` on first request. Every deck route goes through the tenant wrapper (another user's deck is 404). Jobs carry the owner. A **per-user daily spend cap** fails closed. Deleting an account cascades. The web client and the SSE reader send the token | 29 | P0 | main | security tests (A4) green |
| A4 | **Security tests**: every route with no session and with another user's session; a cap check that throws refuses; JWKS unreachable → 401; deletion removes the user's decks and files | 29 | P0 | main | green |
| A5 | **The brief survives sign-up**: typed before signing up, it starts the deck after | 31 | P1 | main | e2e |
| B9 | **Scorer and `--candidates N`** | 39 | P1 | main | unit tests |
| B10 | **Logo per deck** | 38 | P1 | main | API test; refusal path |
| B11 | **AI edit by instruction** (proposal, accept or discard), the style refusal, notes editing, duplicate | 28 | P1 | main | offline tests; browser run |
| B12 | **Release packaging**: Dockerfiles, `docker-compose.yml` (web, api, worker; Postgres external), `.env.example`, run docs | 29 | P1 | main | `docker compose up` locally |
| B13 | **Watch polish**: real states; flagged slides named before download | 32 | P1 | main | e2e |
| B14 | **Submission README**, docs, CHECKPOINT, findings | 29 | P0 | main | docs check green |

### Agents and boundaries

Each agent works in its own git worktree, owns only its files, and is merged by the main session after its tests pass. No agent edits `app.py`, `worker.py`, `engine/pipeline.py` or `web/lib/api/client.ts`; integration is the main session's.

| Agent | Owns | Brief |
|---|---|---|
| R1–R4 (references) | `api/library/references/<its two languages>/` only | The reference format and authoring rules in [39-design-reset.md](39-design-reset.md) §2. The language manifests from B1. The QA harness; it runs its own test and looks at its contact sheets |
| A1 (SQL store) | `api/store/sql.py`, `api/store/models.py`, `api/migrations/`, `api/tests/test_store_sql.py` | The Store interface as `store/files.py` defines it, plus a tenant scope. Parametrize the existing tests over both stores |
| A2 (web auth) | `web/lib/auth*`, `web/app/(auth)/`, `web/app/account/`, `web/app/decks/`, `web/middleware.ts`, auth e2e | Better Auth (current docs, checked first), email and password, the JWT plugin, the `auth` schema, the pages above; the brand and shadcn rules of the web app |

### Order and times

| Time | Main session | Agents |
|---|---|---|
| 08:00 | B1 (languages); the reference format and QA harness | — |
| ~09:00 | Spawn R1–R4, A1, A2 | Start |
| 09:00–14:00 | B3 → B4 → B7 → B5 | Working |
| 14:00–17:00 | B6, B8; merge the reference and store work; review every contact sheet; A3 | Merging |
| 17:00–20:00 | Merge A2; A4; a browser run (sign up → brief → build with the fake worker → edit → export); B14 | Fixes on request |
| 20:00–22:00 | P1 in order: B11, A5, B10, B12, B9, B13 | — |
| **22:00** | **Cut line.** Anything open moves to "after submission" with its trigger | — |

**The two format checks (≤ $0.10):** one image call to pin OpenRouter's image response, and one `compose.v11` call to confirm the new prompt parses.

### Packages arriving (each with its ledger row, in the commit that adds it)

| Where | Package | For |
|---|---|---|
| web | `better-auth`, `pg` | Auth and its Postgres pool |
| api | `sqlalchemy`, `alembic`, `psycopg[binary]` | The SQL store and its migrations |
| api | `pyjwt[crypto]` | Verifying Better Auth's JWT against its JWKS |

## Test day — Friday 2026-10-10

| # | Step | Who | Credit |
|---|---|---|---|
| T0 | Top up (recommended $20) | owner | — |
| T1 | Smoke; the image format check if skipped on Thursday | me | $0.05 |
| T2 | **Image bake-off**: `google/gemini-3.1-flash-lite-image`, `google/gemini-3.1-flash-image`, `openai/gpt-5-image-mini`; 6 prompts each from two decks | me → owner picks | $0.50–1.50 |
| T3 | **Compose bake-off**, 2 briefs each, images off. Candidates: `anthropic/claude-haiku-5.5` ($0.10/$0.50 per M), `deepseek/deepseek-v4.1-flash` (current, $0.30/$1.20), `z-ai/glm-5.3-flash`, `qwen/qwen3.8-flash` | me → owner picks | $2–3 |
| T4 | **Reference curation**: `cli refs --wall`; the owner drops any reference he would not present | owner | $0 |
| T5 | **The main wall**: the 12 outlines of 2026-10-08, with the chosen models and images on. The owner rates D/S/V/X/U and **gate 2**, blind against the one-shot baselines | me → owner | $4–6 |
| T6 | Fix window (code only), then re-run the 4 weakest decks | me | ~$2 |
| T7 | The owner signs up and builds 3 decks live in the app; **two-account isolation check** | owner | ~$2 |
| T8 | If budget remains: `--candidates 2` on 4 decks | me | ~$2 |
| T9 | **Code freeze**; showcase exports; the submission package | me + owner | $0 |

## Budget

| | |
|---|---|
| Thursday | ≤ $0.10 (format checks) |
| Friday | $12–17 (T1–T8) |
| **Recommended top-up** | **$20**, leaving a buffer for one more fix re-run |
| Per deck after the sprint (estimate) | $0.30–0.45: compose ~$0.10–0.15 with references, ~5 images, notes |
| Postgres | $0 on the free tier |

## Risks

| Risk | Mitigation |
|---|---|
| The references are not good enough | The owner curates on Friday morning. Every reference passes QA under 30 looks, and the main session reviews every contact sheet. A language with fewer than 6 good references is switched off |
| One day is not enough for design *and* accounts | Six parallel agents with strict file ownership, P0/P1 with a 22:00 cut line. If the day runs late, P1 goes first, never security |
| Auth built in a day has holes | A mature library rather than our own code; every route tested with no session and with another user's session; fail closed; no password reset or email flows to get wrong |
| Better Auth and Python on one database | Separate schemas (`auth` for Better Auth, `app` for Python). Python reads only the signed JWT, and each side runs its own migrations on its own schema |
| The free Postgres sleeps (cold starts) or caps connections | A small pool; retry once on connect; keep the free tier's limits in mind for the demo |
| The image API's response shape or cost differs | Docs read Thursday, one format call; the bake-off measures real cost from the ledger |
| A new compose model brings new failure modes | The bake-off runs before the main wall; the ladder still ends in reference-fill |
| Decks of the same language look alike | 6–8 references per language, rotated; generated tokens; one image style per deck; no repeats within a deck. Stated honestly: variety across decks is bounded by the library's size until it grows |
| Deadline | Code freeze on Friday before the package; anything open is written down with its trigger |

## After submission

| Item | Phase | Trigger or note |
|---|---|---|
| Google and GitHub sign-in, email verification, password reset, magic links, MFA | 29 | the first outside users; a managed provider reconsidered then |
| Object storage for blobs; a hosted deploy on more than one machine | 29 | the first deploy beyond one host |
| Teams, an admin panel, billing | 29 | the first paying team |
| Saved brand kit | 38 | now possible on accounts; after the submission's logo-per-deck |
| Rehearse mode | 34 | the first user who presents a generated deck |
| Funnel events and the ethics audit | 35 | weekly users |
| The 5-user sessions, the stage test, the email test, old walls | 21, 23, 26, 30–33 | after submission, in that order |
| Growing the reference library past 64 (model-drafted, owner-curated) | 39 | the owner's wall asks for more variety |
| Two candidates by default | 39 | T8 shows the ranker picks what the owner picks |
| CI replay of a recorded event log | 27 | before the first deploy |
