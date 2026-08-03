# Patterns

The domain-specific rules. These matter more here than in a generic app, because they protect the three things that make the product work.

## 1. The no-styling invariant

**AI output carries no presentational values — enforced structurally first, by a runtime check second.**

Structural: block props are typed so a hex code, a pixel value, a font name, or a duration has nowhere to live. The `Scene` schema simply has no field that accepts one. A model that tries to emit `color: '#fff'` produces invalid JSON.

Backstop: a runtime walk over every generated tree rejects any string value matching a presentational pattern, before the tree is stored or rendered.

```ts
// schema/no-style.ts
const PRESENTATIONAL = /#[0-9a-f]{3,8}\b|[\d.]+(px|rem|em|pt|ms|s)\b|\b(rgb|hsl|cubic-bezier)\(/i;
```

**The rule for when the backstop fires:** it means the schema has a gap a value slipped through — add the missing concept to the art direction, never add an exception to the check. The check is allowed to be strict because there is never a legitimate reason for AI output to contain these tokens. See [../v1/scene-schema.md](../v1/scene-schema.md).

This is the product's spine. It does not get loosened for a convenient feature. A `styleOverride` field is the single change that would unravel editing, reskin, and the whole art-direction abstraction at once.

## 2. The renderer core is pure and mode-free

**`SceneRenderer` is a pure function of `(tree, artDirection, motion)`. It contains no knowledge of editor, publish, embed, or fullscreen.**

```ts
function SceneRenderer(props: {
  scenes: Scene[];
  artDirection: ArtDirection;
  motion: MotionVocabulary;
}): ReactNode
```

Modes wrap it and inject behavior from outside:

- The **editor** overlays selection, the property panel, and drag handles *around* the rendered output — never by passing `mode="editor"` into the core.
- **Publish** renders it server-side and ships static HTML.
- **Present** wraps it in a fullscreen container with a keydown handler.
- **Embed** is publish with a different CSP header.

A lint rule bans any `mode` prop or mode conditional inside `renderer/`. That ban is what guarantees the promise made across all three specs: what you edit is byte-for-byte what you publish. The moment a branch says `if (mode === 'editor')` inside a block component, edit and publish begin to drift, and the guarantee is gone.

Interaction lives in the wrappers. Rendering lives in the core. They do not mix.

## 3. Data access lives in feature data modules

**Drizzle is imported only in `*.data.ts` files inside features. Never in a route, never in a component.**

```
features/publish/publish.data.ts   ← the only place publish queries the DB
```

Each table's access has one home, and that home is where two things live that must not scatter:

- the **service-role filter** — `where publishedAt is not null` is doing security work ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)), and it must exist at every read. One data module per feature means one place to get it right.
- the **RLS assumption** — which role runs this query, and what it is allowed to see.

A component that needs data calls a feature function that calls the data module. Three layers, and the security-critical layer is never inlined into a fiftieth call site.

No generic repository wrapper over Drizzle. Drizzle is already the abstraction over SQL; wrapping it is speculative indirection ponytail deletes on sight.

## 4. Formatting is locale-aware from day one

Numbers, currency, and dates go through `Intl`, never string concatenation. A bound live-data stat must read correctly in German and Japanese ([../v3/localization.md](../v3/localization.md)), and retrofitting locale formatting into hand-built strings is worse than doing it once. This is also an XSS boundary — a formatted value is a text node, never interpolated into markup.

## 5. Comments explain why, not what

Comments capture the non-obvious decision, the tradeoff, the thing the code cannot say about itself. They never restate the code.

Deliberate shortcuts get a `ponytail:` comment naming the ceiling and the upgrade path:

```ts
// ponytail: parallel scene build, no cross-scene dedup. Add a layout-repetition
// pass in the director if outputs start looking samey.
```

That is not debt hidden in prose — it is debt made greppable. `ponytail-debt` harvests these into a ledger. A corner cut without the comment is the actual debt.
