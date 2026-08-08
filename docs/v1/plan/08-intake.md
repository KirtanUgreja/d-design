# Phase 08 — Intake

> Conversation in, `Brief` out. The phase that captures *approved* messaging, and the one place a marketer's trust is won or lost before a single page exists.

**Depends on:** [06](06-model-seam-and-build.md) · **Blocks:** the end-to-end run · **Spec step:** 7

**Scope decision:** v1 ships **prompt and AI-led Q&A only**. The import path — PDF, deck, doc, URL — is deferred. See below; it is the plan's largest deliberate deviation from [../ai-pipeline.md](../ai-pipeline.md) and it is recorded rather than absorbed quietly.

---

## Search

**Read first**

- [../ai-pipeline.md](../ai-pipeline.md) → "Phase 1 — Intake", especially "The claims rule" and "The URL rule"
- [../../security/prompt-injection.md](../../security/prompt-injection.md) → the five paths, and which of them v1 actually opens
- [../../security/tenancy-and-data.md](../../security/tenancy-and-data.md) → what a brief is, legally and commercially, and therefore what must never be logged

**Grep for**

- `src/schema/brief.ts` — defined in phase 01, consumed here. One source
- `src/lib/ai/complete.ts` — Intake is `phase: 'intake'`. Refusal normalization already lives in the seam, and **Intake is where refusals actually fire**, because its input is arbitrary user content rather than marketing copy
- `src/features/generation/checks.ts` — the URL allowlist built in phase 06. The Brief's `cta.href` is validated by the same code, not by a second copy

**Verify externally** — nothing, given the deferred import path. That absence is most of the point.

---

## Make

```
api/features/intake/
  __init__.py           the public surface
  interview.py          the Q&A loop → Brief
  checks.py             the claims rule, as a check
  prompts/intake.py
  intake_data.py        the briefs table
  test_interview.py · test_privacy.py
api/routes/intake.py
api/migrations/versions/0004_briefs.py
```

**Paths corrected 2026-08-05.** This section was written before the Python backend move (`../../techstack/decisions.md`) and named `src/features/intake/*.ts`. Intake calls the model, so it lives in `api` beside Director and Build — there is exactly one model call site and it is `api/ai/complete.py`. The Search list above has the same drift: read `api/schema/brief.py`, `api/ai/complete.py` and `api/features/generation/checks.py`.

### Why import is deferred

[../ai-pipeline.md](../ai-pipeline.md) specifies extraction running in the **fetch worker** — the container with no database, no VPC route, and nothing worth stealing — because an uploaded PDF is the single most hostile input in the product, and PDF parsers are the richest source of parser CVEs in the dependency tree.

That container is v3 infrastructure ([../../techstack/infrastructure.md](../../techstack/infrastructure.md)). The three available options were: build it early, run the parser in the app anyway, or defer the path. Running `pdf.js` and `sharp` next to the database credentials is exactly the placement [../../coderules/dependencies.md](../../coderules/dependencies.md) says *should feel wrong* — the ladder's fifth rung is "if it touches untrusted bytes, it goes in the fetch worker", and a feature that seems to need one elsewhere is a signal the work is in the wrong process.

So it waits. Two consequences worth being explicit about:

- **The `Brief` shape does not change.** Import produces the same object by a different route, so this is purely additive when the worker exists. No downstream phase knows the difference
- **v1 has no untrusted-input path at all.** Every byte reaching the model was typed by the single user. That is why phase 06's injection corpus runs against pasted text — which is still worth running, because the corpus has to exist and be green *before* the path that needs it opens

Record it as a `ponytail:` comment at the top of `interview.py` naming the ceiling and the upgrade path.

### The three entry paths, minus one

| Path | v1 |
|---|---|
| **Prompt** — freeform description | **Yes.** Fill what is inferable, ask about the rest |
| **Q&A** — no material at all, the AI interviews | **Yes.** The default path |
| **Import** — PDF, deck, doc, URL | **Deferred.** Needs the fetch worker |

### Always ask, never assume

`goal`, `audience`, `cta`. These three determine narrative structure, and guessing them wastes the entire downstream pipeline — a wrong audience produces twelve well-built scenes aimed at the wrong person.

The interview may infer everything else. It may not infer these, even when it thinks it can.

### The claims rule — the most important constraint in the pipeline

```ts
Brief {
  goal, audience,
  keyMessages: string[],     // 3–5, APPROVED copy
  proofPoints: string[],     // stats, quotes, customer names
  tone,
  cta: { label, href },
  assets: AssetRef[],
  constraints?: string,      // legal, brand, must-not-say
}
```

`keyMessages` and `proofPoints` are **approved copy**. Downstream phases may shorten, split, and rearrange them. They may not invent new claims, new statistics, new customer names, or new capabilities.

A marketer cannot ship a page asserting something untrue about their product, and one such incident costs more trust than a hundred good generations earn ([../spec.md](../spec.md), Risk 2). Enforcement is three-layered — stated in the build prompt, visible at the outline gate, and checked after the build. **Only the third layer catches anything**, and it was built in phase 06.

The Intake UI's job here is narrow and important: make it obvious that what the user types into `keyMessages` is what will appear on the page. If the interview paraphrases the user's messaging into something smoother, it has already broken the rule the whole pipeline rests on.

### The interview is not a chat

The first screen a user touches, and one of the four that gets real design attention ([../../design/app.md](../../design/app.md)). Four decisions, each of which is cheaper to take now than to unwind:

| | |
|---|---|
| **Prompt box first, then a short structured interview** | Chat bubbles promise conversational memory, open-ended back-and-forth, and off-task requests — three things this pipeline will not do. A chat log is also not a `Brief`; a structured interview produces one directly |
| **Skipping to generate is always available** | The interview improves the output. It must never gate it |
| **The Brief stays visible and editable, permanently** | It is the approved-claims record. Burying it behind a step contradicts the rule above, which says the user's exact words are what ships |
| **No upload affordance at all** | Import is deferred, and a disabled button that explains why it is disabled is worse than no button. The `Brief` shape is unchanged when the fetch worker lands, so nothing has to move |

**No templates, no starting-point gallery.** "No templates" is the positioning ([../market.md](../market.md)); a template picker on the first screen argues against the product on the product's own front page. The equivalent affordance is example *briefs* — real launches — and every one of them should be commercial work, because generic examples recruit the cohort that killed Tome ([../../design/principles.md](../../design/principles.md), principle 2).

**The first run has a 90-second budget**, which is what makes the brand kit a second-session concern rather than a setup step. Six brand fields before anything has happened is where a first session is lost.

### The URL rule

`cta.href` comes from the user, always. The AI never composes a URL. Validate it here with the same scheme allowlist phase 06 uses — `javascript:`, `data:`, `vbscript:`, and protocol-relative all rejected — and store the full set of user-supplied URLs on the Brief, because that set is what phase 06's provenance check compares against.

### The `briefs` table

```
briefs  id, experience_id, owner_id, payload (jsonb), created_at
```

RLS policy and isolation test, same pattern as phase 00, through `as_user`.

**The brief is stored; it is never logged.** It is the customer's unreleased launch messaging, and the distinction between a row in a table the user owns and a line in an error tracker is the whole of [../../security/tenancy-and-data.md](../../security/tenancy-and-data.md).

---

## Verify

**The gate** — green.

**Brief construction**

- [x] `goal`, `audience`, and `cta` are always asked, never inferred. Enforced two ways, neither of them a prompt instruction: `interview.py`'s `next_question` decides completeness deterministically (the model is never asked whether the interview is done), and `BriefDraft` — the model's entire output shape — **has no field for any of the three**, so an inferred audience has nowhere to travel. `test_interview.py` asserts the doc's exact wording: a transcript missing the audience returns a question and never reaches the seam at all
- [x] `key_messages` capped at 3–5 by Pydantic — on `BriefDraft` and `Brief` both; rejection tested at 2 and at 6
- [x] The Brief is schema-parsed once, at entry, and trusted thereafter — the model's output is parsed as `BriefDraft` inside the seam, and the `Brief` is constructed once in `_as_brief`
- [x] A user's exact `keyMessages` text survives into the Brief unmodified. `features/intake/checks.py` is the third layer this doc says is the only one that catches anything: every key message and proof point must be a normalized substring of what the user typed. Splitting and reordering pass; a single reworded word fails. Deliberately not punctuation-insensitive, so "cuts costs, sometimes" cannot match a claim of "cuts costs"

**URLs**

- [x] `javascript:`, `data:`, `vbscript:`, `//evil.example` and `JAVASCRIPT:` in `cta.href` are all rejected — `BriefCta.href` now carries `HREF_PATTERN`, **imported from `schema/scene.py`, not restated**. Because a `pattern` is a JSON Schema keyword, it crossed into the generated Zod validator on regeneration, so `web` inherits the same allowlist
- [x] The user-supplied URL is stored on the Brief and is what phase 06's provenance check reads — `check_scene`'s `supplied_hrefs` is `{brief.cta.href}`, unchanged. v1 supplies exactly one URL

**Refusals**

- [x] A refusal reaches the user **as a refusal** — `advance` returns the seam's `Err` unflattened, so a `refused` code stays `refused` rather than collapsing into a generic validation failure. Tested

**Privacy**

- [x] `generations` rows for `phase: 'intake'` contain no brief content — the seam logs call metadata only, and the canary test greps `generations` for the canary
- [x] A canary string appears in the `briefs` table and nowhere else — `features/intake/test_privacy.py`. It also covers error output specifically: a rejected `javascript:` href produces a message carrying the field name and Pydantic's own text, never the user's value

**Isolation**

- [x] `briefs` has an RLS policy and an isolation test — policy created in the same migration as the table, verified live against Postgres. Two-owner isolation tested, plus a `with check` test proving a tenant cannot insert a row owned by someone else

---

## Skipped

| Not built | Trigger |
|---|---|
| Import — PDF, deck, doc | The fetch worker exists. Then: quarantine prefix → caps before parse (page count, byte size, decompression ratio) → magic bytes → `unpdf`/`pdf.js` → extracted text to the model |
| URL import | Same worker, plus the full SSRF suite. Network isolation, not URL filtering |
| `list_documents` / `read_document` tools | They exist to page a document safely, and there are no documents |
| Model-native PDF reading | The documented fallback for the day a parser advisory lands with no patch. Available immediately, costs tokens, needs the seam to expose native document input per provider |
| Multi-turn brief revision | Users edit the Brief directly. Add a conversational revision loop only if direct editing proves insufficient |
| The design pass on the Intake screen | It is one of the four hot screens ([../../design/app.md](../../design/app.md)) and it is currently correct rather than crafted: the layout, type and motion are unstyled defaults over Tailwind. Trigger: before the product is shown to anyone outside the build |
| A readable message for a rejected `cta.href` | The user currently sees Pydantic's raw `String should match pattern '^(https?://\|mailto:...'`. It is honest and it leaks nothing, which is why it ships; it is not something to show a marketer. Trigger: the same design pass |
| Reloading a stored Brief into the screen | `loadBrief` exists and is tested, and nothing calls it — `/new` mints a fresh `experienceId` per visit, so there is never a brief to reload. Trigger: experiences get real identity and a URL, which is phase 09's editor |

---

## Built, on the web side

`web/src/features/intake/` — the prompt box, the structured interview, and the permanently-visible editable Brief, mounted at `/new` (`web/src/app/new/`), which is also where the product path Intake → outline gate → Build is composed. Verified live in a browser, end to end, 2026-08-09.

Three things worth recording because they are decisions rather than code:

- **`InterviewStep` and `Question` moved into `api/schema/` and into `EXPORTED`.** They are the route's response shape, so they cross the language boundary, and the alternative was a hand-written Zod copy on the TypeScript side — the exact drift the codegen exists to prevent ([../../coderules/typescript.md](../../coderules/typescript.md)). `BriefDraft` stayed inside Python, which is the same rule pointing the other way: `web` never sees it
- **Two new routes, `GET`/`PUT /experiences/{id}/brief`.** Without them "the Brief stays visible and editable, permanently" is true of the screen and false of the record. `PUT` deliberately does **not** run `checks.py` — that check exists to stop the *model* rewording the user's copy, and text the user typed is approved by definition. `routes/test_intake.py` asserts this so it is not "fixed" later. The `cta.href` allowlist still applies, because a Brief parses at entry on both paths
- **`Question` carries `index`/`total`.** The "visible progress" [../../design/app.md](../../design/app.md) asks for, derived from `REQUIRED` server-side so there is one definition of how many questions there are

### The CSP break this phase found

`appHeaders()` had no `connect-src`, so it fell back to `default-src 'self'` — and `api` is a different origin. Every browser-side pipeline call from a real app route was blocked, **in production as well as in dev**. It had never shown up because until now every such call lived under `/dev/*`, where phase 07 had already hit the same wall and fixed it locally with `devToolingHeaders()` ([07-director.md](07-director.md)).

Fixed in `web/src/features/publish/csp.ts`: an explicit `connect-src 'self' <NEXT_PUBLIC_API_URL>` — one exact origin from configuration, not a wildcard — plus `'unsafe-inline'` on `script-src` (Next sets `self.__next_r` from an inline script; without it the page never hydrates and every button is silently dead) and `'unsafe-eval'` in development only, which `next dev`'s React needs and a production build does not. The correct end state for the inline-script allowance is a per-request nonce through middleware, the same deferral `publishedHeaders()` already records.

---

## Exit gate

- [x] Prompt and Q&A both produce a valid `Brief` — proven at the API, both paths, with a mocked seam (`test_interview.py`), and **verified live 2026-08-05** against `openai/gpt-5-mini` for the prompt path: the model split the user's typed sentences verbatim rather than smoothing them, so the claims check passed on the first call, and it correctly lifted a "do not describe it as…" line into `constraints`. `goal` and `audience` came back byte-identical to the answers, as they must — they are copied, not generated. **Verified again 2026-08-09 through the built UI**, in a browser: four questions with progress, a `javascript:` CTA rejected with the field name and pattern and no echo of the user's value, the same claims-faithful split, an edit saved, and the Brief handed to the Director, which produced a six-scene outline that then built
- [x] The Intake UI is built — `web/src/features/intake/`, mounted at `/new`. The screen's four decisions are its own docstring; what is *not* built is the design pass that would make it one of the four hot screens rather than a correct one. It is currently plain — see below
- [x] The three always-ask fields are enforced, not encouraged
- [x] URL scheme allowlist shared with phase 06, not duplicated
- [x] A refusal surfaces as a refusal
- [x] Canary test proves brief content lives in exactly one place
- [x] `ponytail:` comment on the deferred import path names the ceiling and the upgrade — top of `features/intake/interview.py`
