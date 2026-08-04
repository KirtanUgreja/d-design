# Phase 01 — Scene schema

> The IR. One Pydantic definition produces the model's JSON Schema, the validation gate, and — through the generator stood up in phase 00 — the TypeScript types and Zod validator the editor uses. Everything downstream is a consequence of this shape, which is why it is built before anything that consumes it.

**Depends on:** [00](00-foundations.md) · **Blocks:** every later phase · **Spec step:** 1

[../scene-schema.md](../scene-schema.md) is the specification. This phase does not redesign it — it types it, and resolves the handful of places the document leaves an implementation choice.

---

## Search

**Read first**

- [../scene-schema.md](../scene-schema.md) — all of it, twice. Every downstream guarantee is a consequence of this shape ([../../coderules/ai-authorship.md](../../coderules/ai-authorship.md) names it first on the read-the-diff-properly list)
- [../../coderules/python.md](../../coderules/python.md) → "The schema is the source of truth" — the three codegen rules, and the constraints that do not survive the trip
- [../../coderules/typescript.md](../../coderules/typescript.md) → "Types come from the generated schema", and why the editor still gets a validator
- [../../coderules/patterns.md](../../coderules/patterns.md) → rule 1, the no-styling invariant
- [../ai-pipeline.md](../ai-pipeline.md) → "Validation: one gate, and a decoder that only shifts the odds"

**Grep for**

- `api/lib/result.py` — validation failures on user input are `Result`, not raises. Schema violations from *inside* the system are bugs and raise. Know which you are writing before you write it
- `api/lib/ids.py` — id generation exists; do not write a second one
- **the generator from phase 00** — it is pinned and proven on a throwaway model. Do not pick a different one here

**Verify externally**

- `model_json_schema()` output for a **nested** tagged union, and that the generator turns it into a working `z.discriminatedUnion` on the other side. The known rough edge is a union at the schema *root*, which this shape avoids — `Scene` and `Experience` are objects and `Block` is nested. Confirm the whole chain rather than trusting the note: this is the single place the two languages are most likely to disagree
- That `minLength`/`maxLength` still do not survive into structured-output enforcement. They will not. Keep them anyway; they are what does the rejecting

---

## Make

```
api/schema/
  __init__.py       the public surface — package-shaped from day one
  scene.py          Block, Scene, Layout, Region, Motion, SceneIntent
  experience.py     Experience, Asset, BrandKit
  brief.py          Brief          (phase 08 consumes it; define it here, one source)
  outline.py        Outline        (phase 07 consumes it)
  patch.py          BlockPatch     (phase 09 consumes it)
  no_style.py       the presentational-value backstop
  json_schema.py    model_json_schema(), deterministically serialized
  test_scene.py

api/scripts/generate_schema.py   ← Pydantic → JSON Schema → TS types + Zod
```

### The rules Pydantic owns

Structural, on `Scene` and `Experience` ([../scene-schema.md](../scene-schema.md) → Validation rules):

- 3 ≤ scenes ≤ 12 · 1 ≤ blocks per scene ≤ 8
- max one `Headline` per scene · max one `Slot` per `Experience`
- exactly one scene with `intent: 'hook'`, and it is first
- at least one `CTA` somewhere
- every `region` exists on that scene's `layout`
- `grid`: 2–4 blocks in `cells`

Character caps go on the string fields as `.max()`. They will be violated routinely and rejected reliably — that is the design.

### The two rules Pydantic cannot own

**`assetId` resolves to a real asset** needs a database. It is a function, not a refinement:

```python
# api/schema/experience.py
def assert_assets_resolve(exp: Experience, known_ids: frozenset[str]) -> Result[None]: ...
```

Called at the pipeline boundary in phase 06, where the asset id set is available. Keeping it in `schema/` keeps the rule next to the shape it guards; keeping it out of the model keeps `schema/` free of a database import — which also keeps it cleanly generatable, since a validator that needs the database cannot cross to TypeScript.

**Claim provenance** — a `Stat.value` traceable to a `proofPoint`, a `CTA.href` traceable to a Brief URL — needs the Brief. Same treatment, same file, same reason. These are the post-build checks [../ai-pipeline.md](../ai-pipeline.md) says are "the only layer that actually catches things."

### The backstop

```python
# api/schema/no_style.py
PRESENTATIONAL = re.compile(r"#[0-9a-f]{3,8}\b|[\d.]+(px|rem|em|pt|ms|s)\b|\b(rgb|hsl|cubic-bezier)\(", re.I)
def assert_no_presentational_values(tree: object) -> Result[None]: ...
```

Walks every string value in a generated tree. **When it fires, the schema has a gap a value slipped through — add the missing concept to the art direction, never add an exception to the check.** That sentence is the rule; write it as the comment above the regex, because the next person to hit a false positive will be tempted.

### The JSON Schema

```python
SCENE_JSON_SCHEMA = Scene.model_json_schema()
```

**Serialize it with sorted keys and stable ordering.** It sits in the Build phase's cached prefix, and a re-ordered JSON dump is a different prefix — which silently costs 10× on the largest phase ([../ai-pipeline.md](../ai-pipeline.md) → prompt caching). Write the deterministic serializer here, not at the call site.

It never leaves the process. The seam is in the same codebase as the schema, so the constraint the model receives and the validator that checks the response are the same object — which is the one thing the Python move made simpler rather than harder ([../../coderules/python.md](../../coderules/python.md)).

### Fixtures

`api/schema/fixtures/` — three hand-written `Experience` trees, committed as **JSON** so both languages can load the same bytes. Phase 04 renders them, phase 06 compares against them, and the cross-language round-trip test reads them:

| | |
|---|---|
| `minimal.json` | 3 scenes, the fewest blocks that satisfy every rule |
| `full.json` | 8 scenes exercising all 11 block types, all 6 layouts, every motion intent |
| `hostile.json` | Maximum-length strings in every capped field, longest plausible `List`, a `grid` at 4 cells |

`hostile.json` is the one that matters. A design that only looks good on short copy is a design that breaks on the first real brief, and it is far cheaper to discover that in phase 04 than in phase 06.

---

## Verify

**The gate** — green.

**Schema round-trip** ([../spec.md](../spec.md) → Verification, row 1)

- [ ] Each fixture parses, serializes, and re-parses to a deep-equal tree
- [ ] **One failing fixture per validation rule.** Fourteen rules, fourteen assertions that the invalid tree is rejected. This is the table that stops a rule from being silently deleted later

**The no-styling invariant** ([../spec.md](../spec.md) → Verification, row 2)

- [ ] `assert_no_presentational_values` rejects `#fff`, `1.5rem`, `240ms`, `rgb(0,0,0)`, `cubic-bezier(...)`, `16px` in any nested string
- [ ] It accepts every fixture unchanged
- [ ] **It rejects a hex code hidden in a `Slot.css` value** — decide deliberately: `Slot` code is CSS by definition and must be exempt from the walker, so the walker skips `Slot.html`/`css`/`js` and the sandbox is what contains them instead. Write the exemption as an explicit skip with a comment, never as a loosened regex

**Type derivation** ([../../coderules/ai-authorship.md](../../coderules/ai-authorship.md) → Test)

- [ ] No shape in `api/schema/` has a hand-written duplicate beside it
- [ ] **No hand-written TypeScript describes a scene tree anywhere.** Every TS type comes from the generator, and the gate fails if regenerating produces a diff
- [ ] `SCENE_JSON_SCHEMA` serializes byte-identically across two runs in the same process and across a restart

**Cross-language agreement** ([../../coderules/python.md](../../coderules/python.md) → Test) — the check that only exists because of the split, and the only one that catches a codegen bug:

- [ ] Each fixture, loaded from the same JSON bytes, gets the **same verdict** from Pydantic and from the generated Zod validator
- [ ] Each of the fourteen invalid fixtures is rejected by **both**. A rule that survives to TypeScript but not to Python — or the reverse — is a silent hole in whichever side skipped it

---

## Skipped

| Not built | Trigger |
|---|---|
| Publishing `@d-design/schema` | A second TypeScript consumer exists — `render`, in v2. Until then the generator writes into `web` through a local file link, marked `ponytail:` ([../../coderules/typescript.md](../../coderules/typescript.md)) |
| `mode: 'slides'` rendering | v1 renders `scroll` only. The enum value exists because removing it later is a breaking schema change; the renderer simply has no slides path |
| `Scene.notes` | Speaker notes are not in v1. The field exists and is unused, for the same reason |
| Per-cell alignment in `grid` | Defer until mixed-type grids are seen in real output ([../scene-schema.md](../scene-schema.md) → Open questions) |

**One open question resolved here, ahead of phase 09:** `intent` decouples from position. A user dragging `proof` above `problem` does not make `intent` a lie, because `intent` describes what a scene *does*, not where it sits. The only positional rule is that the `hook` is first, and the editor enforces that by refusing the drag rather than by rewriting intents.

---

## Built — and the finding that reshaped "cross-language agreement"

Built 4 Aug 2026. One deviation here is bigger than the others and is worth reading before touching this schema again.

**Wire names are camelCase; the base class earns its keep.** `schema/base.py` gained `alias_generator=to_camel` and `populate_by_name=True`. Without it, `model_json_schema()` emits Python's own attribute names — `brand_id`, `art_direction` — onto the wire, and the generated Zod/TS would carry them too. `docs/v1/scene-schema.md`'s own interfaces are camelCase (`brandId`, `artDirection`, `createdAt`), and `structure.md` already says camelCase in TypeScript, snake_case in Python, "the rules are parallel, the spellings are native." Skipping the alias would have been exactly the transliteration mistake that sentence warns against, just moved to the wire instead of a filename.

**`Block.type` lives on `props`, not on `Block` itself.** The spec draws two fields — `Block.type` and `Block.props`, discriminated by the first. Pydantic discriminates a union by a field *inside* the union, and a duplicate `type` on the wrapper buys nothing a reader couldn't get from `props.type`. The patch shape (`{sceneId, blockId, props}`) is unchanged.

**The finding: nine of the fourteen validation rules cannot reach TypeScript, and this is not an emitter gap.** The cross-language fixture test was built exactly as the phase file specifies — one JSON file, both languages, one verdict per case — and it immediately found that rules like "exactly one hook, and it is first," "at least one CTA somewhere," and "ids unique within this list" have no JSON Schema representation. JSON Schema validates the shape of one node; it has no vocabulary for a predicate over a whole tree — no way to say "count the items in this nested array matching this discriminator" or "this array's items must be pairwise distinct by a key." That is a property of the format, discovered here rather than assumed away, and forcing it through by hand-authoring `if`/`then` JSON Schema branches would have violated `python.md`'s own rule that the JSON Schema is never a file someone maintains.

The honest split, once found: five of the fourteen rules are **field-level shape** (a length cap, an item count, a regex) and cross the wire cleanly — `fixtures/wire_invalid_cases.json` holds these and both `api/tests/test_schema_codegen.py` and `web/src/schema/schema.test.ts` read it. The other nine are **whole-tree structural** rules, enforced by Pydantic's `model_validator`s exactly as designed, asserted Python-only in `schema/test_scene.py` against the full `fixtures/invalid_cases.json`. This split is not a weakening of editor-side validation: `BlockPatch` — the only write path that runs entirely offline, in the property panel — can only change one block's props. It cannot delete the one CTA, retag which scene is the hook, or duplicate an id, so none of the nine whole-tree rules are reachable from the interaction the offline validator exists to protect (`typescript.md`'s "keystroke-scale interaction" case is about caps and shape, and those five are exactly what made the cut).

**One rule moved from cross-field to field-level on purpose, and got stronger for it.** `CtaProps.href`'s scheme allowlist was originally a `model_validator` calling `urlparse()` — correct, but Python-only, and the property panel patches `href` directly. Rewritten as `Field(pattern=HREF_PATTERN)`, it now generates into the Zod validator as `.regex()`, so a pasted `javascript:` URL is rejected in the browser instead of only at the next full-tree validation. The pattern itself had to drop a lookahead (`/(?!/)` → `/($|[^/])`) — Pydantic's Rust regex engine doesn't support look-around, and the same string has to parse as a JS `RegExp` on the other side of the boundary, so the portable subset both engines share is what got written, not the more expressive one.

**A second false positive, from the same test suite, for a different reason.** `hostile.json`'s `Stat.value: "<1ms"` tripped the no-styling regex — `[\d.]+(px|rem|em|pt|ms|s)\b` cannot distinguish a CSS duration from a benchmark number, and `"<50ms"` is the spec's own example of a legitimate `Stat.value`. This is not a value leaking through — `Stat` has no styling field to leak from — it is the regex matching content it was never meant to look at. Fixed the way the file's own docstring requires: an explicit named-field exemption (`STAT_CONTENT_FIELDS = {"value", "prefix", "suffix"}`), the same mechanism already used for Slot's code fields, never a loosened pattern. `Stat.label` stays covered.

**Two Python-only checks beyond the spec's two.** `assert_hrefs_are_supplied` and `assert_stats_are_supported` join `assert_assets_resolve` as pipeline-boundary functions — the first enforces the URL rule from `docs/v1/ai-pipeline.md` ("every `CTA.href` traces to a Brief-supplied URL"), the second gives `Stat.value` the same "arrange, never invent" treatment as URLs. Neither needs a Pydantic validator; both need the Brief, which is exactly the "keeps `schema/` free of a database import" reasoning the phase file already gives for `assert_assets_resolve`.

## Exit gate

- [x] Every scene-tree shape in the system traces to one Pydantic definition — TypeScript types and the Zod validator are generated, and regenerating produces no diff
- [x] The cross-language fixture agreement test passes in both directions, **for the subset JSON Schema can express** — see the finding above. Both languages read the same files; nothing is duplicated by hand
- [x] Fourteen rejection tests, one per validation rule, all passing — in Python (`schema/test_scene.py`); five of the fourteen also pass in TypeScript (`web/src/schema/schema.test.ts`)
- [x] The no-styling walker passes the fixtures and rejects six presentational patterns, with two named exemptions (Slot code, Stat content) and neither is a loosened regex
- [x] `SCENE_JSON_SCHEMA` is deterministic — same bytes across two calls in-process and across a subprocess restart
- [x] Three JSON fixtures exist, including `hostile.json` (all four caps at exactly their limit), loadable from both languages
- [x] `api/schema/__init__.py` is short enough to read in one screen
