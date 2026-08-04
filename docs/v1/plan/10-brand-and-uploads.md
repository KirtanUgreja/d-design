# Phase 10 — Brand kit and uploads

> Marketers cannot ship off-brand, and they cannot ship a page showing an approximation of their product. This phase makes both possible, and it opens the only file-handling surface in v1.

**Depends on:** [09](09-editor.md), [03](03-art-direction-tokens.md) · **Blocks:** [11](11-visuals-and-slot.md) · **Spec step:** 9

The brand kit is a **v1 primitive**, not a feature ([../spec.md](../spec.md)). Uploads are where v1 stops having a purely trusted input surface — every uploaded file is hostile until proven otherwise.

---

## Search

**Read first**

- [../../security/content-and-web.md](../../security/content-and-web.md) → "Uploads", in full. Six controls, each with a named reason
- [../art-direction.md](../art-direction.md) → "Brand kit integration" — brand colours map into semantic roles, they do not replace them
- [../scene-schema.md](../scene-schema.md) → `Asset`, and why `source` is not decoration
- [../../coderules/dependencies.md](../../coderules/dependencies.md) → "Where a dependency runs is part of the decision", and the ledger entries already anticipated for `sharp` and an SVG sanitizer

**Grep for**

- `src/lib/storage.ts` — built in phase 00, already talking S3 to MinIO. Uploads use it. Do not write a second storage path
- `src/features/art-direction/resolve-brand.ts` — the contrast resolver exists. The brand UI feeds it; it does not reimplement colour maths
- `src/lib/ids.ts` — storage keys are server-generated UUIDs. `crypto.randomUUID` is already there
- `src/features/generation/tools.ts` — `get_brand_kit` and `list_assets` were written in phase 06 against a schema with no data behind it. They now have data; the tools do not change

**Verify externally**

- `sharp` current version, and its `pnpm.onlyBuiltDependencies` requirement — install-script blocking is on by default and `sharp` legitimately needs a native build. Allowlist it **by name**, never with a blanket `--ignore-scripts` reversal
- The current DOMPurify major, and specifically that no DOMPurify **2.x** is anywhere in the transitive tree. Four distinct XSS bypasses were disclosed in 2025–2026 and the 2.x branch was never patched for one of them
- Whether the platform's own image API now covers re-encode and EXIF strip. If it does, that is one fewer ledger entry — deletion is a feature

---

## Make

```
src/features/brand/
  index.ts
  brand-kit.tsx          fonts by registry id, colours, logo
  brand.data.ts          'server-only'
src/features/assets/
  index.ts
  upload.ts              the pipeline below
  sanitize-svg.ts        the one place SVG is touched
  assets.data.ts         'server-only'
  assets.test.ts
```

### Brand kit

```
BrandKit { displayFont, textFont, primary, secondary?, neutral?, logoAssetId }
```

**Fonts are chosen from the registry by id.** Never a user-supplied family string — it is the most natural-looking free-text token in the whole system and the one that most easily carries a payload ([../../security/content-and-web.md](../../security/content-and-web.md)). The registry was built in phase 03; this phase gives it a UI.

Colours run through `resolveBrand`. **The contrast correction is visible to the user**: if their primary fails 4.5:1 against the dark background, show them the corrected colour and say why. Silently deviating from a brand hex is worse than saying you did.

### The upload pipeline

```
file ──▶ quarantine prefix ──▶ verify ──▶ re-encode ──▶ public prefix ──▶ Asset row
```

Six controls, in this order, and the order matters:

| Control | Why |
|---|---|
| **Size and dimension caps *before* decode** | Decompression bombs — a 200KB PNG can decode to gigabytes. A parser that has already allocated is a parser you have already lost |
| **Magic-byte verification** | Extension and `Content-Type` are attacker-supplied |
| **Server-side re-encode** (`sharp`) | Strips EXIF, kills polyglots, normalizes format |
| **Server-generated UUID storage keys** | User filenames mean path traversal. Never use them; discard the original |
| **`Content-Type` set by the server, `nosniff`** | An image interpreted as HTML is an XSS |
| **Served from one prefix, never inline HTML** | Contains any content-type confusion |

**SVG** is accepted, sanitized, and served **only via `<img>`**. Sanitization removes `<script>`, `<foreignObject>`, event-handler attributes, external references, and `<use href>` pointing off-document. Cap entity expansion and nesting depth — the entity-expansion bomb is a distinct denial-of-service shape from the XSS case, and it is the one that reaches an image pipeline.

> **The layering is the control, not caution.** Referenced through `<img>`, an SVG cannot execute even if sanitization missed something. A design that trusted the sanitizer alone would have been exploitable four times in eighteen months. Rejecting SVG outright would hurt real users, because logos are almost always SVG.

**Each of the six gets its own sentence.** A rejected upload is a user holding their own logo, being told no by a product that has just claimed it will keep them on brand — the highest-frustration moment in the phase, and *"Invalid file"* is not an answer to any of the six questions above. Six controls means six reasons and six messages: too large, wrong contents, unreadable, unsupported format, and so on ([../../design/app.md](../../design/app.md)). None of them may expose the internal error class, which is logged and never displayed ([../../security/operations.md](../../security/operations.md)).

**The brand kit is asked for second, never first.** It arrives after the first artifact exists, framed as *make this yours* — six brand fields standing between a new user and their first generation is where a first session is lost, and the whole first run has a ninety-second budget ([08](08-intake.md)). That is a sequencing decision this phase can quietly break by building a setup wizard.

### The deliberate deviation, named

[../../techstack/backend.md](../../techstack/backend.md) puts all of this in the **fetch worker** — the container with no database, no VPC route, and nothing worth stealing. That container is v3.

So in v1 the upload pipeline runs **in-process**, next to the database credentials, which is exactly the placement the dependency ladder says should feel wrong. It is accepted for one reason: v1 is a single user uploading their own product shots on their own machine, with no other tenant to reach and no network exposure. It would not be acceptable the moment a second person has an account.

```ts
// ponytail: upload verification and re-encode run in-process. v1 is one local user,
// so there is no tenant to reach and no exposure. Move the whole pipeline to the
// fetch worker before the first outside account exists — the interface is a
// function call today and an HTTP boundary then.
```

Write that comment. It is the difference between debt and a hole, and `ponytail-debt` harvests it.

### The `assets` table

```
assets  id, owner_id, kind, storage_key, mime, width, height,
        alt, source ('upload' | 'generated'), created_at
```

RLS policy and isolation test, same pattern as every other table.

**`source` is not decoration.** Generated imagery carries different legal and brand risk than an uploaded product shot, and a marketer needs to know which is which before publishing. The editor surfaces it; do not drop the field.

Assets reach the pipeline only after verification, which is why phase 06 can treat asset metadata as trusted and why `list_assets` needed no validation of its own.

---

## Verify

**The gate** — green, and the ledger updated: `sharp` and the SVG sanitizer each get a one-line justification in [../../coderules/dependencies.md](../../coderules/dependencies.md). **A dependency added without a ledger line fails review.**

**Uploads** ([../../security/testing.md](../../security/testing.md) → "Uploads")

- [ ] Extension/content-type mismatch — a PHP file renamed `.png` — rejected by magic bytes
- [ ] Decompression bomb: small file, huge decode → rejected **before** full decode. Assert no memory spike, not just a rejection
- [ ] SVG with `<script>` and SVG with `onload` → sanitized, and served via `<img>` where neither could run anyway
- [ ] SVG entity-expansion bomb and pathological nesting → rejected with no CPU spike. Distinct test from the XSS case
- [ ] Path-traversal filename → server UUID used, original discarded entirely
- [ ] EXIF present on upload, absent after re-encode
- [ ] `Content-Type` is server-set and `nosniff` is present on every served asset
- [ ] No DOMPurify 2.x anywhere in the tree

**Brand**

- [ ] A brand primary failing 4.5:1 is corrected, and the correction is **shown to the user**
- [ ] A font can only be selected by registry id; a raw family string is rejected
- [ ] Under a pastel brand, `cinematic-dark` is still dark

**Isolation**

- [ ] `assets` and `brands` both have RLS policies and isolation tests
- [ ] Every read goes through `asUser`

**Integration**

- [ ] `list_assets()` returns real uploads with dimensions and alt text
- [ ] An `Image` block whose `assetId` does not resolve fails validation — it does not render a broken image
- [ ] Generated-vs-uploaded is visible in the editor

---

## Skipped

| Not built | Trigger |
|---|---|
| Running the pipeline in the fetch worker | The first outside account. Named in a `ponytail:` comment, not left implicit |
| Presigned direct-to-S3 uploads | v3. Presigned uploads without the quarantine step is uploading arbitrary bytes to your own CDN — the quarantine prefix is built now so the ordering is already right |
| Stock images | Not in v1 |
| Video transcoding | Uploads are accepted as-is with a size cap. Add transcoding when a real file forces it |
| Asset library UI beyond a list | Cold 90% ([../../coderules/performance.md](../../coderules/performance.md)). Assemble it, do not craft it |

---

## Exit gate

- [ ] All six upload controls implemented, in the right order, each with a test
- [ ] SVG sanitized **and** served via `<img>` — both layers, because either alone has failed in the wild
- [ ] Brand contrast correction works and is visible
- [ ] Fonts by registry id only
- [ ] `assets` and `brands` isolated and tested
- [ ] `sharp` and the sanitizer have ledger lines and `sharp` is in `onlyBuiltDependencies` by name
- [ ] The in-process `ponytail:` comment exists and names the upgrade path
