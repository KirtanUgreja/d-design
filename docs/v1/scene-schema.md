# Scene Schema

The IR. The single contract between the AI, the editor, and the renderer. Read this before anything else.

## The invariant

**No block prop may contain a presentational value.** No hex codes, no pixels, no rem, no durations, no easing curves, no font names, no z-index.

A block says `emphasis: "hero"`. The art direction decides that means `clamp(3.5rem, 8vw, 8rem)`.

This is checkable, and it should be checked: a test that walks every block in a generated tree and fails on anything matching `/#[0-9a-f]{3,8}|[\d.]+(px|rem|em|ms|s)\b/i`. If that test ever needs an exception, the schema has a missing concept — add the concept, don't add the exception.

## Types

```ts
type Mode        = 'scroll' | 'slides';           // v1 renders 'scroll' only
type SceneIntent = 'hook' | 'problem' | 'reveal' | 'proof' | 'cta';
type Layout      = 'full-bleed' | 'split-left' | 'split-right'
                 | 'centered' | 'stack' | 'grid';
type Motion      = 'reveal' | 'emphasize' | 'parallax' | 'none';

interface Experience {
  id: string;
  title: string;
  mode: Mode;
  brandId: string;
  artDirection: 'cinematic-dark';                 // v1: one value
  scenes: Scene[];                                // 3–12
  meta: { createdAt: string; updatedAt: string; publishedAt?: string };
}

interface Scene {
  id: string;
  intent: SceneIntent;
  layout: Layout;
  blocks: Block[];                                // 1–8
  notes?: string;                                 // speaker notes, unused in v1
}

interface Block {
  id: string;
  type: BlockType;
  region?: Region;                                // defaults per layout
  props: BlockProps;                              // discriminated on type
  motion?: Motion;                                // default 'reveal'
}
```

### Why these enums are small

`SceneIntent` is five values because a marketing narrative has five beats. It drives outline structure, and later it will drive art directions that style a `hook` differently from a `proof`. Adding a sixth is a real decision, not a convenience.

`Motion` is four values because the art direction owns everything else — stagger, trigger point, distance, duration. The AI picks *whether* something moves and roughly *why*. Never how.

## Layouts and regions

Each layout exposes named regions. A block's `region` says where it goes; the art direction says what that means spatially.

| Layout | Regions | Use |
|---|---|---|
| `full-bleed` | `bg`, `content` | Hero moments. Visual fills viewport, content floats over |
| `split-left` | `left`, `right` | Content left, visual right |
| `split-right` | `left`, `right` | Visual left, content right |
| `centered` | `content` | Single statement. Maximum restraint |
| `stack` | `content` | Sequential text beats, vertically stacked |
| `grid` | `cells` | 2–4 parallel items (stats, features) |

Default region: `content`, or `cells` for `grid`, or `left` for splits.

**Stagger is automatic** — derived from block index within a region. The AI does not control it. This removes an entire category of bad output.

## Block types

Eleven. Each lists only props that carry meaning, never appearance.

### Text

```ts
Eyebrow  { text: string }                                    // ≤ 24 chars
Headline { text: string; emphasis?: 'hero' | 'section' }     // ≤ 60 chars
Body     { text: string; emphasis?: 'lead' | 'normal' | 'muted' }  // ≤ 240 chars
Quote    { text: string; attribution?: string; role?: string }     // ≤ 200 chars
List     { items: { text: string; detail?: string }[];       // 2–5 items
           style: 'bullets' | 'numbered' | 'checks' }
```

### Data

```ts
Stat { value: string; label: string; prefix?: string; suffix?: string }
```

`value` is a string, not a number — `"10x"`, `"2.4M"`, `"<50ms"` are all legitimate. The renderer animates a count-up when it parses as numeric and holds it static otherwise.

### Media

```ts
Image { assetId: string; alt: string;                        // alt required
        fit: 'cover' | 'contain';
        treatment?: 'plain' | 'framed' | 'bleed' }
Video { assetId: string; posterAssetId?: string;
        autoplay: boolean; loop: boolean }
```

`alt` is required by the schema, not by convention. Generated experiences are public web pages.

### Action

```ts
CTA { label: string; href: string; style: 'primary' | 'secondary' }
```

### Assets

`Image` and `Video` reference an asset, never a URL. Blocks stay portable and the
storage backend stays swappable.

```ts
Asset {
  id: string;
  kind: 'image' | 'video';
  storageKey: string;                              // resolved by storage.ts
  mime: string;
  width?: number; height?: number;
  alt?: string;                                    // default for blocks
  source: 'upload' | 'generated';
}
```

`source` is not decoration. Generated imagery carries different legal and brand
risk than an uploaded product shot, and a marketer needs to know which is which
before publishing. The editor surfaces it; do not drop the field.

### Generated visuals

```ts
AbstractVisual {
  generator: 'gradient-mesh' | 'particle-field' | 'grid-lines' | 'orb' | 'noise-veil';
  seed: number;
  intensity: 'subtle' | 'medium' | 'bold';
}
```

Rendered as code (CSS/SVG/canvas) using art-direction colors. Zero asset cost, always on-brand, infinitely tweakable. This is what makes a sparse scene look designed rather than empty.

### Escape hatch

```ts
Slot { description: string; html: string; css: string; js: string;
       height: 'viewport' | 'auto' }
```

Runs in `<iframe srcdoc sandbox="allow-scripts">` with no `allow-same-origin`. No storage, no cookies, no parent DOM, no credentialed fetch. Brand and art-direction tokens are injected as CSS variables into the srcdoc.

`description` is what the editor shows and what an AI edit operates on — the code itself is not user-editable in v1.

## Validation rules

Zod enforces all of these. Violations fail the generation and trigger one repair retry.

**Structural**
- 3 ≤ scenes ≤ 12
- 1 ≤ blocks per scene ≤ 8
- Max **one** `Headline` per scene
- Max **one** `Slot` per Experience
- Exactly one scene with `intent: 'hook'`, and it is first
- At least one `CTA` somewhere in the Experience
- Every `region` must exist on that scene's `layout`
- `grid` layout: 2–4 blocks in `cells`
- Every `assetId` resolves to a real asset

**Content**
- Character caps above are hard limits, not suggestions
- No block prop matches the presentational-value regex

### Why the length caps matter more than they look

LLMs write too much. A headline that runs to 140 characters destroys a cinematic layout no matter how good the tokens are. The caps make restraint mechanical rather than politely requested.

**But they are enforced at a different layer than the shape rules, and the difference is load-bearing.**

| | Enforced by | Can the model violate it? |
|---|---|---|
| Shape — fields, types, enums, no styling values | Structured outputs constrains generation itself | **No.** The token has nowhere to go |
| **Character caps** | Zod, after the response arrives | **Yes, routinely** |

Structured outputs does **not** support JSON Schema's `minLength` / `maxLength` — string-length constraints are among the unsupported keywords, alongside numeric bounds. The SDKs strip them from the schema before sending and validate client-side, so keeping `maxLength` in the Zod schema is harmless; it simply doesn't constrain decoding.

So a 90-character headline is a *valid generation* that fails *validation*, and the repair loop fixes it. Two practical consequences:

1. **State the character budget in the prompt as a hard number.** That is the only thing that lowers repair frequency — the schema will not do it for you.
2. **Expect the repair loop to fire on these constantly at first.** That is the system working; log the pattern, because it tells you where prompt and schema disagree.

## Editing

Edits are patches against a single block:

```ts
{ sceneId, blockId, props: Partial<BlockProps> }
```

The tree is re-validated after every patch. Property-panel edits and element-scoped AI edits produce the identical patch shape, so there is one code path and one place for validation to live.

A full regeneration is never triggered by an edit.

### What the property panel exposes

Every prop in the tables above, and nothing else. Because no prop is
presentational, the panel is structurally incapable of offering a font size or a
color picker — the thing users most expect and most reliably use to wreck a
design.

| Block | Editable |
|---|---|
| Text blocks | `text`, `emphasis`, plus `attribution`/`role`/`items`/`style` |
| `Stat` | `value`, `label`, `prefix`, `suffix` |
| `Image` / `Video` | swap asset, `alt`, `fit`, `treatment`, `autoplay`, `loop` |
| `CTA` | `label`, `href`, `style` |
| `AbstractVisual` | `generator`, `intensity`, reroll `seed` |
| `Slot` | `description` only — code is not hand-editable in v1 |
| Any block | `motion`, delete, reorder within region |
| Scene | `layout`, `intent`, delete, reorder |

"Reroll seed" is the one affordance users will reach for constantly. Make it a
button, not a number field.

## Open questions

- **Scene reordering across intents.** If a user drags `proof` above `problem`, does the `intent` field become a lie? Probably intent should decouple from position — resolve when building the editor (step 8).
- **`grid` with mixed block types.** A grid of three `Stat`s is obvious. A grid mixing `Stat` and `Image` may need a per-cell alignment concept. Defer until it's seen in real output.
