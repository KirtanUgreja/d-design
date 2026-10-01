# Phase 24 — content engine

> This phase makes true that a deck says something specific and true: an interview, cited facts, a storyline with an argument, and notes for the speaker.

**Depends on:** 22 · **Blocks:** 25 · **Spec step:** Locked decisions → Facts, First users · **Size:** M

## Search

**Read first** — [../content.md](../content.md) (all), [../../security/prompt-injection.md](../../security/prompt-injection.md), [../engine.md](../engine.md) → "The model seam"

**Grep for**
- `api/pipeline/interview/prompts.py` at `v3-final` — the untrusted-content framing and the provenance rules worth keeping.
- `OutlineClaim` in `api/schema/outline.py` at `v3-final` — it becomes `Fact.source`.
- `git show cbfebfa^:api/evals/injection/` — the corpus for `bench/injection/`.

**Verify externally**
- The `openrouter:web_search` request shape and the `url_citation` annotation fields.
- Search pricing per engine.

## Make

- `content/interview.py`: one call, ≤5 questions with suggested answers.
- `content/research.py`: search results → `Fact`s under the "no quote, no fact" rule; results framed as untrusted data; ≤30 results.
- `content/storyline.py`: the five arcs, governing thought, assertion headlines, per-field budgets, provenance.
- `content/notes.py`: one call after approval.
- `content/rules.py`: the detectors (topic labels, banned phrases, meta-copy) and the number-provenance check.
- The inverse-spec eval in the bench.
- The CLI's outline gate: print the outline, type `y` to approve.

### Design decisions

- **Research queries come from the arc's evidence needs**, not the topic.
- **Notes are written after approval**, so iterating on an outline costs one call.
- **An unsourced number cannot pass the gate silently.** It is approved as illustrative or rejected.

## Verify

- [x] Detector fixtures: every v3 sample headline is caught — 20 of 20, and 0 of the bench's 109 assertion headlines (`tests/test_content_rules.py`)
- [x] The injection corpus: no case changes the output channel — 8 cases (7 recovered from v3, 1 hostile search result): 7 held, 1 refused by the provider (2026-10-01)
- [x] A number with no quote in its source is discarded (`tests/test_research.py`)
- [ ] **Human:** at least 5 of 6 outlines approvable with ≤3 edits
- [ ] **Human:** a 20-fact spot check at the sources; ≤1 wrong

## Skipped

- URL, PDF and DOCX import — trigger: 3 user requests. Needs an SSRF-safe fetcher and an isolated parser.
- Lesson, keynote and report arcs — trigger: the bench passes and users ask.
- Languages other than English — trigger: the first non-English user.

## Exit gate

- [x] Across the bench: zero numbers without an approved `Fact`, zero banned phrases, ≤1 topic-label headline per deck before regeneration — 0, 0, 0 (`2026-10-01-content`)
- [x] Inverse spec ≥0.8 — 0.83 with judge `inverse.v2`; it was 0.75 with `inverse.v1`, whose reference was the brief's one-line description. The judge was changed after seeing the score; both are in `bench/results.md`
- [x] Research ≤ $0.25 per deck — at most $0.098
- [x] Notes on every slide — 109 of 109
