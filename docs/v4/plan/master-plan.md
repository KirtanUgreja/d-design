# Master plan — to submission (2026-10-08 → 2026-10-10)

> **What is true at submission:** a person types a brief, answers a few questions, approves an outline whose every number has a source, sees the deck's style before it is built, watches the deck arrive slide by slide, and gets a deck that looks designed by a person and unlike other decks — real imagery in one style, charts drawn from the data, their logo — which they can edit, undo, present and send as one offline file.

**Decided by the owner, 2026-10-08:** the reference library is fine ("absolutely fine"); build everything on 2026-10-09; test with new credit on 2026-10-10; submit by 2026-10-10. Evidence for the design direction: [../research-2026-10.md](../research-2026-10.md).

## The three days

| Day | What happens | Credit |
|---|---|---|
| **Wed 2026-10-08** | This plan and the phase files. No build. | none |
| **Thu 2026-10-09 — build day** | Everything in "Build day" below, offline: every item ends with its tests green using fake models. | **≤ $0.10** of the ~$1.80 left, only for two format checks (one image call, one compose call) — the owner may veto |
| **Fri 2026-10-10 — test day** | The owner tops up; the runbook below; one fix window; code freeze; the submission package. | ~$12–17 used; **top up $20** |

Rules for the sprint:
- **Nothing that needs credit or the owner blocks the build.** Paid and human steps all move to test day, in order.
- **Every build item ends offline-verified**: unit tests with fake transports, browser QA, a contact sheet looked at.
- **Cut lines are explicit.** A P1 item not done by evening moves to "after submission" with its trigger written down; nothing half-built is left on the path.
- **No overclaiming.** The submission reports what the walls measured, including what failed.

## Where we are (2026-10-08)

| Area | State |
|---|---|
| Engine: content (interview, research, storyline with sources), QA in Chromium, repair ladder, export (present/send/PDF, offline) | Built and tested; content bench passed (inverse spec 0.77, 0 banned words) |
| Look system: continuous palettes, variable fonts, textures, charts (9 forms, validated colours), logo engine | Built |
| App: API, worker, live web flow (questions → outline gate → watch → exports), editor (text, move, delete, recolour, fit, undo) | Built, proven with a fake model in a browser |
| **Design quality** | **Failed the owner's walls**: one house style (Designed 3.5, Varied 3.1), then messy with free shapes. Cause and fix: [../research-2026-10.md](../research-2026-10.md) → phase 39 |
| Credit | ~$1.80 left |

## Definition of done for submission

1. **Design:** the owner's 12-deck wall on 2026-10-10 averages **Designed ≥ 4.0 and Varied ≥ 4.0**, no deck called messy, and **gate 2** ("would send to an investor or customer") is yes for at least 9 of 12, blind against the one-shot baselines.
2. **Reliability:** ≤ 3% of slides flagged, ≤ 10% built by code, median ≤ $0.60 and p90 ≤ 5 minutes a deck.
3. **Product:** a typed brief builds live end to end in the app; the owner builds 3 decks there.
4. **Engineering:** the gate green (ruff, mypy --strict, pytest, eslint, tsc, OpenAPI drift, docs); the e2e suite green.
5. **Package:** a README a reviewer can run in three commands, the evidence (walls, findings), and 3–5 showcase decks.

If (1) misses, the submission still ships the best decks as the showcase and reports the wall honestly.

## The sprint, by phase

| Phase | Sprint scope | Day | Priority |
|---|---|---|---|
| [39 — design reset](39-design-reset.md) | Visual languages, the reference library, retrieval and reference-fill, `compose.v11`, imagery, the style preview, the scorer | build | **P0** (scorer P1) |
| [37 — beautiful data](37-beautiful-data.md) | The "pair" form for two values; the data wall | build / test | **P0** / test |
| [38 — brand kit](38-brand-kit.md) | Per-deck logo upload, no accounts | build | P1 |
| [28 — editor](28-editor.md) | AI edit by instruction (a proposal to accept), notes editing, duplicate, the style refusal | build | P1 |
| [29 — accounts and deploy](29-accounts-deploy.md) | **Re-scoped to release:** single-tenant packaging (Docker, an access token, run docs) and the submission package | build | P1 (package P0) |
| [32 — watch and reveal](32-watch-reveal.md) | Real per-slot states; flagged slides named before download | build | P1 |
| [33 — trust and control](33-trust-control.md) | Covered by 28's proposals and the existing provenance chips | build | P1 (via 28) |
| [25 — composition and QA](25-composition-qa.md) | Images moved to 39; **gate 2 is the test-day wall** | test | gate |
| [27 — create flow](27-app-create-flow.md) | The owner's 3 live decks | test | P0 check |
| [36 — independent design](36-independent-design.md) | Kept as guards (archive, variable fonts, palettes); exit judged by the owner's wall | — | — |
| 21–24, 26, 30 | Built or closed; their open human checks move after submission | — | after |
| 31, 34, 35 | After submission (they need accounts or real users) | — | after |

## Build day — Thursday 2026-10-09

In order. Estimates are for one builder; the reference library (B2) is the long pole and is split across parallel build agents **if the owner agrees** (each agent authors one or two visual languages against the same format and test harness; integration stays with the main session).

| # | Item | Phase | Pri | Est | Done when |
|---|---|---|---|---|---|
| B1 | **Visual languages**: 8 authored manifests; the sampler draws the language first (balanced by archive usage), then tokens it allows | 39 | P0 | 1.5 h | 1,000 seeds: every language drawn, contrast tests green, pairings respect the language |
| B2 | **Reference library**: 8 shapes × 8 languages (cut line: 6 × 8 = 48; floor 5 × 8 = 40), each passing QA under 30 looks of its language with long and short words; `cli refs --wall` | 39 | P0 | 5–6 h (≈2 h in parallel) | the reference QA test green; the main session reviewed every contact sheet |
| B3 | **Retrieval and reference-fill**: shape from the plan, a pick with no repeat in a deck and least-used across decks, fill that drops absent fields | 39 | P0 | 1.5 h | every bench slide gets a fitting reference; reference-fill passes QA for every bench slide under 20 looks |
| B4 | **`compose.v11`**: contract + tokens + the language's brief + the reference(s) + one variation; the house style, the geometric target, the ideas block and the art-direction call removed; ladder: compose → 2 repairs → fresh with the alternate reference → reference-fill → code layout → flag; novelty retries within a deck only | 39 | P0 | 2 h | ladder, prompt and resume tests green offline |
| B5 | **Imagery**: `Seam.complete_image`, `components/images.py` (prompt, Pillow crop to the slot, webp, metadata stripped), `dd-image` filled after sanitizing, an image budget per language, failure → a quiet surface field, never a broken slide | 39 | P0 | 2.5 h | fake-transport tests: bytes → webp in the slide; the failure path; the export makes zero network requests |
| B6 | **Style preview**: the outline job also draws the look and renders 3 slides by reference-fill with the deck's real words ($0); the outline gate shows the style card (name, idea, fonts, swatches, image style, 3 thumbnails) and **Another style** | 39 | P0 | 2 h | API test; a browser run with the fake worker |
| B7 | **"Pair" chart form**: two values as two large figures and the change, replacing two-bar charts | 37 | P0 | 0.5 h | goldens; form tests |
| B8 | **Model plumbing**: compose, image and cheap models set per run and per env; `cli bakeoff` builds the same briefs with N models into one wall | 39 | P0 | 1 h | CLI test with fakes |
| B9 | **Scorer and candidates**: computed design score (balance, alignment, empty-space quality, clutter, hero ratio); `--candidates N` ranks N compositions | 39 | P1 | 1.5 h | unit tests on known slides |
| B10 | **Logo per deck** (JSON upload, ingested by the worker, refused in words) and the composer/gate control | 38 | P1 | 1 h | API test; refusal path |
| B11 | **AI edit by instruction** (a proposal rendered beside the current slide, accept or discard), the style-request refusal, notes editing, duplicate slide | 28 | P1 | 2.5 h | offline tests with a fake model; a browser run |
| B12 | **Release packaging**: Dockerfiles, `docker-compose.yml`, `.env.example`, an access-token gate that fails closed when set, run docs | 29 | P1 | 1.5 h | `docker compose up` locally; the token test |
| B13 | **Watch polish**: real states per slot; flagged slides named before download | 32 | P1 | 0.5 h | e2e green |
| B14 | **Submission README** and docs; CHECKPOINT; findings | 29 | P0 | 1 h | docs check green |

**Order of work:** B1 → B2 (agents start as soon as B1's manifests and the reference format exist) → B3 → B4 → B7 → B5 → B6 → B8 → B14, then P1 in the order B11, B10, B12, B9, B13. **Cut line at 22:00:** whatever P1 is not green moves to "after submission".

**The two optional format checks (≤ $0.10):** one image call to pin OpenRouter's image response format; one `compose.v11` call to confirm the new prompt parses. Both only if the owner does not veto.

## Test day — Friday 2026-10-10

| # | Step | Who | Credit |
|---|---|---|---|
| T0 | Top up (recommended $20) | owner | — |
| T1 | Smoke; the image format check if skipped on Thursday | me | $0.05 |
| T2 | **Image bake-off**: `google/gemini-3.1-flash-lite-image`, `google/gemini-3.1-flash-image`, `openai/gpt-5-image-mini`, 6 prompts each from two decks | me → owner picks | $0.50–1.50 |
| T3 | **Compose bake-off** (the owner's ask): `anthropic/claude-haiku-5.5` ($0.10/$0.50 per M), `deepseek/deepseek-v4.1-flash` (current, $0.30/$1.20), `z-ai/glm-5.3-flash`, `qwen/qwen3.8-flash`; 2 briefs each, images off | me → owner picks | $2–3 |
| T4 | **Reference curation**: `cli refs --wall`; the owner drops any reference he would not present | owner | $0 |
| T5 | **The main wall**: the 12 outlines of 2026-10-08, the chosen models, images on; owner rates D/S/V/X/U and **gate 2** blind against the one-shot baselines | me → owner | $4–6 |
| T6 | Fix window (code only), then re-run the 4 weakest decks | me | ~$2 |
| T7 | The owner builds 3 decks live in the app | owner | ~$2 |
| T8 | If budget remains: `--candidates 2` on 4 decks | me | ~$2 |
| T9 | **Code freeze**; showcase exports; the submission package | me + owner | $0 |

## Budget

| | |
|---|---|
| Thursday | ≤ $0.10 (format checks) |
| Friday | $12–17 (T1–T8) |
| **Recommended top-up** | **$20**, leaving a buffer for one more fix re-run |
| Per deck after the sprint (estimate) | $0.30–0.45: compose ~$0.10–0.15 with references, ~5 images, notes |

## Risks

| Risk | Mitigation |
|---|---|
| The references are not good enough | The owner curates on Friday morning; every reference must pass QA under 30 looks; the main session reviews every contact sheet on Thursday; languages with fewer than 6 good references are switched off |
| One build day is not enough | Parallel agents for B2; P0/P1 with a 22:00 cut line |
| The image API's response shape or cost is not what we expect | Read the docs on Thursday (free); one format call; the bake-off measures real cost from the ledger |
| A new compose model brings new failure modes | The bake-off runs before the main wall; the ladder still ends in reference-fill |
| Decks of the same language look alike | 6–8 references per language, rotated; generated tokens; one image style per deck; within-deck no-repeat. Stated honestly: variety across decks is bounded by the library's size until it grows |
| Deadline | Code freeze on Friday before the package; anything open is written down with its trigger |

## After submission

| Item | Phase | Trigger or note |
|---|---|---|
| Accounts, Postgres, metering, a hosted instance | 29 | the first outside user |
| Saved brand kit | 38 | accounts |
| First run with sign-up; the replay before sign-up | 31 | accounts |
| Rehearse mode | 34 | the first user who presents a generated deck |
| Funnel events and the ethics audit | 35 | weekly users |
| The 5-user sessions, the stage test, the email test, old walls | 21, 23, 26, 30–33 | after submission, in that order |
| Growing the reference library past 64 (model-drafted, owner-curated) | 39 | the owner's wall asks for more variety |
| Two candidates by default | 39 | T8 shows the ranker picks what the owner picks |
| CI replay of a recorded event log | 27 | before the first deploy |
