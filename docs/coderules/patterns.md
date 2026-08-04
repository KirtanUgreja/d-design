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

**The ORM is imported only in a feature's data module. Never in a route, never in a component, never in a handler.**

```
api/features/publish/publish_data.py   ← SQLAlchemy. The only place publish queries the DB
web/features/auth/auth.data.ts         ← Drizzle. Auth tables only
```

**Which ORM is a property of the runtime, not a choice at the call site** ([../techstack/backend.md](../techstack/backend.md) → "Two ORMs, one database"). `api` is SQLAlchemy over the application tables; `web` is Drizzle over the auth tables and nothing else. A SQLAlchemy import in `web` or a Drizzle import in `api` is not a style problem — it is a table-ownership violation, and the table-ownership rule is the only thing keeping two migration tools from destroying each other's schema.

Each table's access has one home, and that home is where two things live that must not scatter:

- the **service-role filter** — `where publishedAt is not null` is doing security work ([../security/tenancy-and-data.md](../security/tenancy-and-data.md)), and it must exist at every read. One data module per feature means one place to get it right.
- the **RLS assumption** — which role runs this query, and what it is allowed to see.

A component that needs data calls a feature function that calls the data module. Three layers, and the security-critical layer is never inlined into a fiftieth call site.

No generic repository wrapper over Drizzle. Drizzle is already the abstraction over SQL; wrapping it is speculative indirection ponytail deletes on sight.

Every TypeScript data module starts with `import 'server-only'`, which turns a client component importing it into a build error rather than a leak ([structure.md](structure.md)). Next.js's own security guidance names the Data Access Layer as the primary defense against accidental exposure — this rule predates that guidance here and agrees with it. Python has no equivalent marker and needs none: `api` has no client bundle to leak into.

## 4. Every tenant-scoped query runs inside the tenant wrapper

**Exactly two wrappers, one per language. Both are named below. A third is a bug.**

The rule used to read *"One wrapper. Not per query, not per route. One."* The Python move made that impossible ([../techstack/decisions.md](../techstack/decisions.md) → "The Python backend move"), and the honest version is the one that says how many and which.

```python
# api/db/tenant.py — the only place app.user_id is set in Python
@asynccontextmanager
async def as_user(user_id: str):
    async with session_factory() as s, s.begin():
        await s.execute(text("select set_config('app.user_id', :uid, true)"), {"uid": user_id})
        yield s
```

```ts
// web/db/tenant.ts — the only place app.user_id is set in TypeScript
import 'server-only';

export function asUser<T>(userId: string, fn: (tx: Tx) => Promise<T>) {
  return db.transaction(async (tx) => {
    await tx.execute(sql`select set_config('app.user_id', ${userId}, true)`);
    return fn(tx);
  });
}
```

Three things make this the most dangerous code in the backend, and all three are invisible in review:

- **The `true` in `set_config` is what scopes the value to the transaction.** Without it the setting persists on the connection, and a pooled connection handed to the next request serves it as the previous user. One boolean between correct and a cross-tenant read. **Two copies of that boolean now exist.**
- **The pooler must run in transaction mode.** Session mode binds a connection for a whole client session, which is the wrong lifetime for a web tier and silently breaks the scoping above.
- **A tenant-scoped query outside a transaction is unsafe by construction** on a shared pool. This is the production consensus, not a preference: the shared pool is only safe when every tenant query has its own transaction.

So the rule is not "remember to set the variable." It is **there are exactly two functions that can talk to the database as a user, they are the two files above, and everything goes through one of them.** A query in a data module that did not come from `as_user`/`asUser` is the bug, and it is greppable — the lint rule bans `set_config('app.user_id'` outside those two paths, which is what turns "two" from a claim into a fact.

**Duplicating a control is worse than having one**, and this is the clearest instance of that cost in the repo. The two implementations must be reviewed together and changed together; a fix applied to one is a latent cross-tenant read in the other. It is bounded only because the table sets are disjoint — `web`'s wrapper guards seven auth tables, `api`'s guards everything holding customer content. **If application tables ever become readable from `web`, re-read this rule as an incident report rather than a note.**

Test the unset case explicitly, **in both languages**: `current_setting('app.user_id')` on a connection where it was never set must fail, not match everything. That is rule 5 below applied to isolation.

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

Every call to a model goes through one module, in `api`. Not one per feature, not one per phase — one. **And there is no second one in TypeScript**: `web` and `render` never hold a model credential, so the "one call site" claim is a property of the architecture and not only of the code.

```python
# api/ai/complete.py
async def complete[T](
    phase: Literal["intake", "director", "build", "edit", "critic"],
    schema: type[T],                 # a Pydantic model
    system: str,                     # the stable, cacheable prefix
    user: str,                       # the only part that varies
    tools: list[Tool] | None = None, # tier 0 only
) -> Result[T]: ...
```

The seam exists because this product has **no preferred model vendor** ([../techstack/ai-stack.md](../techstack/ai-stack.md)) — only a preferred interface. That is only true if there is one place to change.

It also owns five things that must not be reimplemented per call site: `model_validate` of the response, the single repair retry, refusal normalization, the metadata log (model, route, tokens, calls, repair, latency), and the tool-call caps. Every one is a rule from somewhere else in this repo, and a second call path is a second place for each of them to be missing.

**Tool arguments are parsed at the tool boundary and ownership-checked there**, and the ownership check fails closed per rule 5. An injected *"read document 7"* must die because document 7 belongs to someone else — never because the model chose not to.

### Bounded loops live here too, and stay bounded

v2's visual verification loop ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)) renders a scene, shows it to a vision critic, and applies **at most one** revision. It belongs in this module, as a `for` loop with a literal limit — roughly forty lines.

**It is not an agent and must not be built with an agent framework** ([../techstack/ai-stack.md](../techstack/ai-stack.md)). The limit is a number in your code, not a budget the model negotiates. The test is one question: *can the model change how many times this runs?* If no, it is a loop. If yes, that is the trigger to reread the framework decision — and to reread [../security/adversarial-ai.md](../security/adversarial-ai.md)'s agentic section, which currently does not apply for exactly this reason.

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
