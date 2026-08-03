# Patterns

The domain-specific rules. These matter more here than in a generic app, because each one protects something the product cannot work without.

The first three protect the *product*: the art-direction abstraction, the edit/publish guarantee, and where data is read. The next three protect it from *failing quietly* — a cross-tenant read, a permissive default, and a second way to call a model. Every one of the second group describes a bug that looks like reasonable code in review.

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
- **Publish** renders it to static HTML in the job worker and writes the artifact to S3.
- **Present** wraps it in a fullscreen container with a keydown handler.
- **Embed** is publish with a different CSP header.

It now runs in **three** processes — the browser (editor), the app server (preview renders), and the job worker (publish, and the visual verification loop). That is three call sites for one function, which is fine, and it raises the stakes on the rule rather than complicating it: a `mode` prop would now have three values to drift between instead of two.

The practical form of the ban: **nothing in `renderer/` may read `process.env`, check `typeof window`, or branch on where it is running.** Environment differences are the wrapper's problem. A renderer that behaves differently in the worker than in the browser is a published page that differs from the edited one, which is the exact guarantee the rule exists to protect.

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

Every data module starts with `import 'server-only'`, which turns a client component importing it into a build error rather than a leak ([structure.md](structure.md)). Next.js's own security guidance names the Data Access Layer as the primary defense against accidental exposure — this rule predates that guidance here and agrees with it.

## 4. Every tenant-scoped query runs inside the tenant wrapper

**One wrapper. Not per query, not per route. One.**

```ts
// db/tenant.ts  — the only place app.user_id is ever set
import 'server-only';

export function asUser<T>(userId: string, fn: (tx: Tx) => Promise<T>) {
  return db.transaction(async (tx) => {
    await tx.execute(sql`select set_config('app.user_id', ${userId}, true)`);
    return fn(tx);
  });
}
```

Three things make this the most dangerous code in the backend, and all three are invisible in review:

- **The `true` in `set_config` is what scopes the value to the transaction.** Without it the setting persists on the connection, and a pooled connection handed to the next request serves it as the previous user. One boolean between correct and a cross-tenant read.
- **The pooler must run in transaction mode.** Session mode binds a connection for a whole client session, which is the wrong lifetime for a web tier and silently breaks the scoping above.
- **A tenant-scoped query outside a transaction is unsafe by construction** on a shared pool. This is the production consensus, not a preference: the shared pool is only safe when every tenant query has its own transaction.

So the rule is not "remember to set the variable." It is **there is exactly one function that can talk to the database as a user, and everything goes through it.** A `db.select()` in a data module that did not come from `asUser` is the bug, and it is greppable.

Test the unset case explicitly: `current_setting('app.user_id')` on a connection where it was never set must fail, not match everything. That is rule 5 below applied to isolation.

## 5. Anything that grants, fails closed

The OWASP A10 rule from [../security/infrastructure.md](../security/infrastructure.md), stated as a coding pattern because that is where it is violated.

> **Availability degrades open. Authorization degrades closed.**

```ts
// wrong — reads as defensive programming, is a vulnerability
try { return await checkQuota(id); } catch { return { allowed: true }; }

// right
try { return await checkQuota(id); } catch { return { allowed: false }; }
```

The test is one question: **could this failure grant something?** A 3D model that fails to load shows a poster and the viewer has been given nothing. A quota check that times out and returns "allowed" has.

This is why expected failures are `Result` and not exceptions ([typescript.md](typescript.md)) — a `Result` forces the caller to choose a branch, and the compiler will not let the permissive one be implicit. The dangerous shape is always a `catch` returning a default, because a default is a decision nobody reviewed.

Prove it by injection: make each check throw and assert refusal. Reasoning about this is not enough — fail-open reads as ordinary error handling right up until it is the incident.

## 6. One seam for model calls

Every call to a model goes through one module. Not one per feature, not one per phase — one.

```ts
// ai/complete.ts
export async function complete<T>(req: {
  phase: 'intake' | 'director' | 'build' | 'edit' | 'critic';
  schema: z.ZodType<T>;
  ...
}): Promise<Result<T>>
```

The seam exists because this product has **no preferred model vendor** ([../techstack/ai-stack.md](../techstack/ai-stack.md)) — only a preferred interface. That is only true if there is one place to change.

It also owns four things that must not be reimplemented per call site: Zod parsing of the response, the single repair retry, the metadata log (model, route, tokens, calls, repair, latency), and the tool-call caps. Every one of those is a rule from somewhere else in this repo, and a second call path is a second place for each of them to be missing.

**Tool arguments are parsed at the tool boundary and ownership-checked there**, and the ownership check fails closed per rule 5. An injected *"read document 7"* must die because document 7 belongs to someone else — never because the model chose not to.

## 7. Formatting is locale-aware from day one

Numbers, currency, and dates go through `Intl`, never string concatenation. A bound live-data stat must read correctly in German and Japanese ([../v3/localization.md](../v3/localization.md)), and retrofitting locale formatting into hand-built strings is worse than doing it once. This is also an XSS boundary — a formatted value is a text node, never interpolated into markup.

## 8. Comments explain why, not what

Comments capture the non-obvious decision, the tradeoff, the thing the code cannot say about itself. They never restate the code.

Deliberate shortcuts get a `ponytail:` comment naming the ceiling and the upgrade path:

```ts
// ponytail: parallel scene build, no cross-scene dedup. Add a layout-repetition
// pass in the director if outputs start looking samey.
```

That is not debt hidden in prose — it is debt made greppable. `ponytail-debt` harvests these into a ledger. A corner cut without the comment is the actual debt.
