# Phase 01 — Scene schema

> The IR. One Zod definition produces the TypeScript types, the model's JSON Schema, and the validation gate. Everything downstream is a consequence of this shape, which is why it is built before anything that consumes it.

**Depends on:** [00](00-foundations.md) · **Blocks:** every later phase · **Spec step:** 1

[../scene-schema.md](../scene-schema.md) is the specification. This phase does not redesign it — it types it, and resolves the handful of places the document leaves an implementation choice.

---

## Search

**Read first**

- [../scene-schema.md](../scene-schema.md) — all of it, twice. Every downstream guarantee is a consequence of this shape ([../../coderules/ai-authorship.md](../../coderules/ai-authorship.md) names it first on the read-the-diff-properly list)
- [../../coderules/typescript.md](../../coderules/typescript.md) → "Types come from schemas", "The JSON Schema is derived too"
- [../../coderules/patterns.md](../../coderules/patterns.md) → rule 1, the no-styling invariant
- [../ai-pipeline.md](../ai-pipeline.md) → "Validation: one gate, and a decoder that only shifts the odds"

**Grep for**

- `src/lib/result.ts` — validation failures on user input are `Result`, not throws. Schema violations from *inside* the system are bugs and throw. Know which you are writing before you write it
- `src/lib/ids.ts` — id generation exists; do not write a second one

**Verify externally**

- `z.toJSONSchema` behavior on a **nested** discriminated union in the Zod version you pinned. The known rough edge is a union at the schema *root*, which this shape avoids — `Scene` and `Experience` are objects and `Block` is nested. Confirm it rather than trusting the note
- That `minLength`/`maxLength` still do not survive into structured-output enforcement. They will not. Keep them anyway; they are what does the rejecting

---

## Make

```
src/schema/
  index.ts        the public surface — this folder is package-shaped from day one
  scene.ts        Block, Scene, Layout, Region, Motion, SceneIntent
  experience.ts   Experience, Asset, BrandKit
  brief.ts        Brief          (phase 08 consumes it; define it here, one source)
  outline.ts      Outline        (phase 07 consumes it)
  patch.ts        BlockPatch     (phase 09 consumes it)
  no-style.ts     the presentational-value backstop
  json-schema.ts  z.toJSONSchema, deterministically serialized
  scene.test.ts
```

### The rules that Zod owns

Structural, on `Scene` and `Experience` ([../scene-schema.md](../scene-schema.md) → Validation rules):

- 3 ≤ scenes ≤ 12 · 1 ≤ blocks per scene ≤ 8
- max one `Headline` per scene · max one `Slot` per `Experience`
- exactly one scene with `intent: 'hook'`, and it is first
- at least one `CTA` somewhere
- every `region` exists on that scene's `layout`
- `grid`: 2–4 blocks in `cells`

Character caps go on the string fields as `.max()`. They will be violated routinely and rejected reliably — that is the design.

### The two rules Zod cannot own

**`assetId` resolves to a real asset** needs a database. It is a function, not a refinement:

```ts
// schema/experience.ts
export function assertAssetsResolve(exp: Experience, knownIds: ReadonlySet<string>): Result<void>
```

Called at the pipeline boundary in phase 06, where the asset id set is available. Keeping it in `schema/` keeps the rule next to the shape it guards; keeping it out of Zod keeps `schema/` free of a database import.

**Claim provenance** — a `Stat.value` traceable to a `proofPoint`, a `CTA.href` traceable to a Brief URL — needs the Brief. Same treatment, same file, same reason. These are the post-build checks [../ai-pipeline.md](../ai-pipeline.md) says are "the only layer that actually catches things."

### The backstop

```ts
// schema/no-style.ts
const PRESENTATIONAL = /#[0-9a-f]{3,8}\b|[\d.]+(px|rem|em|pt|ms|s)\b|\b(rgb|hsl|cubic-bezier)\(/i;
export function assertNoPresentationalValues(tree: unknown): Result<void>;
```

Walks every string value in a generated tree. **When it fires, the schema has a gap a value slipped through — add the missing concept to the art direction, never add an exception to the check.** That sentence is the rule; write it as the comment above the regex, because the next person to hit a false positive will be tempted.

### The JSON Schema

```ts
export const SCENE_JSON_SCHEMA = z.toJSONSchema(Scene);
```

**Serialize it with sorted keys and stable ordering.** It sits in the Build phase's cached prefix, and a re-ordered JSON dump is a different prefix — which silently costs 10× on the largest phase ([../ai-pipeline.md](../ai-pipeline.md) → prompt caching). Write the deterministic serializer here, not at the call site.

### Fixtures

`src/schema/fixtures/` — three hand-written `Experience` trees that phase 04 renders and phase 06 compares against:

| | |
|---|---|
| `minimal.ts` | 3 scenes, the fewest blocks that satisfy every rule |
| `full.ts` | 8 scenes exercising all 11 block types, all 6 layouts, every motion intent |
| `hostile.ts` | Maximum-length strings in every capped field, longest plausible `List`, a `grid` at 4 cells |

`hostile.ts` is the one that matters. A design that only looks good on short copy is a design that breaks on the first real brief, and it is far cheaper to discover that in phase 04 than in phase 06.

---

## Verify

**The gate** — green.

**Schema round-trip** ([../spec.md](../spec.md) → Verification, row 1)

- [ ] Each fixture parses, serializes, and re-parses to a deep-equal tree
- [ ] **One failing fixture per validation rule.** Fourteen rules, fourteen assertions that the invalid tree is rejected. This is the table that stops a rule from being silently deleted later

**The no-styling invariant** ([../spec.md](../spec.md) → Verification, row 2)

- [ ] `assertNoPresentationalValues` rejects `#fff`, `1.5rem`, `240ms`, `rgb(0,0,0)`, `cubic-bezier(...)`, `16px` in any nested string
- [ ] It accepts every fixture unchanged
- [ ] **It rejects a hex code hidden in a `Slot.css` value** — decide deliberately: `Slot` code is CSS by definition and must be exempt from the walker, so the walker skips `Slot.html`/`css`/`js` and the sandbox is what contains them instead. Write the exemption as an explicit skip with a comment, never as a loosened regex

**Type derivation** ([../../coderules/ai-authorship.md](../../coderules/ai-authorship.md) → Test)

- [ ] No shape in `src/schema/` has a hand-written type beside it. Every type is `z.infer`
- [ ] `SCENE_JSON_SCHEMA` serializes byte-identically across two runs in the same process and across a restart

---

## Skipped

| Not built | Trigger |
|---|---|
| Publishing `@d-design/schema` | The fetch worker exists (v3). The folder is package-shaped, so this is a `package.json` and a Changeset |
| `mode: 'slides'` rendering | v1 renders `scroll` only. The enum value exists because removing it later is a breaking schema change; the renderer simply has no slides path |
| `Scene.notes` | Speaker notes are not in v1. The field exists and is unused, for the same reason |
| Per-cell alignment in `grid` | Defer until mixed-type grids are seen in real output ([../scene-schema.md](../scene-schema.md) → Open questions) |

**One open question resolved here, ahead of phase 09:** `intent` decouples from position. A user dragging `proof` above `problem` does not make `intent` a lie, because `intent` describes what a scene *does*, not where it sits. The only positional rule is that the `hook` is first, and the editor enforces that by refusing the drag rather than by rewriting intents.

---

## Exit gate

- [ ] Every type in the codebase that describes a scene tree comes from `z.infer`
- [ ] Fourteen rejection tests, one per validation rule, all passing
- [ ] The no-styling walker passes the fixtures and rejects six presentational patterns
- [ ] `SCENE_JSON_SCHEMA` is deterministic
- [ ] Three fixtures exist, including `hostile.ts`
- [ ] `src/schema/index.ts` is short enough to read in one screen — it is the catalog every later phase reads before writing something that already exists
