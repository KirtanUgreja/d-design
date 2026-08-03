# Dependencies

## The rule

**Stdlib and platform first. Every dependency past the baseline needs a one-line justification recorded here.**

Not a ban — a speed bump. The cost of a dependency is not install time; it is the security surface, the breaking changes, the transitive tree, and the fact that you now maintain a relationship with code you did not write. A few lines you own beat a package you rent, until they clearly don't.

## The baseline

Already decided, no justification needed — these are the stack:

| | For |
|---|---|
| Next.js + React | App framework, one renderer, routing |
| TypeScript | The whole codebase |
| Zod | Schemas and validation, the source of truth |
| Drizzle | Typed SQL, migrations |
| Framer Motion | Motion, driven by the art-direction vocabulary |
| Tailwind | App chrome only — never the art direction (that is CSS variables) |
| Supabase client | Auth, Postgres, storage (v3) |

## Adding one

Before reaching for a package, walk the ladder:

1. Does the platform already do this? `Intl` for number/date formatting, `crypto.randomUUID`, `URL`, `structuredClone`, the Fullscreen and File APIs, CSS for most animation. Reach here first.
2. Does the baseline already cover it? Zod validates, Drizzle queries, Framer animates. Don't add a second tool for a job one of these does.
3. Is it a few lines of our own? A debounce, a slug, a retry loop, a clamp — write it, test it, own it.
4. Only then, a dependency — and record why.

## The ledger

Every non-baseline dependency gets one line here: what it does, and why not a few lines of our own.

```
<package>   — <what it does> — <why not stdlib/baseline/ours>
```

Anticipated, with the reasoning already clear:

```
draco/meshopt decoder — GLB mesh decompression (v3) — a compression codec is not
  a few lines; hand-rolling it is absurd. Runs in the isolated worker.
sharp (or platform image API) — server-side image re-encode/EXIF strip (v1) —
  security-critical, must be a hardened, maintained decoder, not homemade.
a DOM sanitizer for SVG (v1) — SVG sanitization is a moving target against a
  motivated attacker; this is the one place NOT to write our own.
stripe — billing (v3) — never hand-roll payments.
```

The pattern in that list is the actual rule: **write your own for convenience code; never write your own for a codec, a crypto primitive, a sanitizer, or a payment path.** The line is not "hard" versus "easy" — it is "who gets hurt if I get it subtly wrong."

## Removing one

A dependency used in one place, for one small thing, that the platform now covers — delete it. Deletion is a feature. Revisit the ledger when the platform baseline moves (a new stable Web API can retire a package).

## Test

CI fails on a known-critical advisory in the tree. The lockfile is committed; builds are reproducible. A PR that adds a `package.json` dependency without a ledger line fails review — for AI-authored changes, this is a line in CLAUDE.md ([tooling.md](tooling.md)).
