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
| Zod (**v4**) | Schemas and validation, the source of truth. v4 also generates the model's JSON Schema — see [typescript.md](typescript.md) |
| Drizzle | Typed SQL, migrations |
| **Motion** (`motion`, import `motion/react`) | Motion, driven by the art-direction vocabulary. **Not `framer-motion`** — renamed in 2025, now maintained independently at motion.dev; the old package still installs but is no longer actively developed |
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

## Installing one safely — the part that changed

The ledger above is about *whether* to take a dependency. This section is about the install itself, which stopped being a background detail in late 2025.

**What happened:** the Shai-Hulud worm compromised **796 npm packages with 132 million monthly downloads** in November 2025, self-replicating through maintainer credentials. It ran from `preinstall` scripts — stealing credentials, installing backdoors, and in some cases wiping developer environments. Follow-on waves ran through 2026. This is now the ordinary condition of the registry, not an incident.

Two defenses matter, and both are configuration rather than code:

**1. A release-age gate.** Do not install a version published in the last day. Nearly every one of these compromises was caught within hours by the community; a delay converts "you were the first victim" into "you read about it."

| | Status |
|---|---|
| **pnpm 11** (May 2026) | `minimumReleaseAge` **on by default**, 1440 minutes |
| **Yarn 4.10** | `npmMinimalAgeGate` on by default |
| **npm 11.10** (Feb 2026) | `min-release-age` supported but **off** — you have to write it in |

**2. No lifecycle scripts on install.** This is what the worm actually used. pnpm has blocked install scripts by default since v10 (January 2025).

**Which is why the package manager is pnpm.** Both defenses are on out of the box; on npm you configure both yourself and one of them silently is not there. This is the rare case where the safe default and the lazy default are the same choice — take it.

### The one conflict this creates, and the fix

Blocking install scripts breaks packages that legitimately need them to build a native binary. **`sharp` is in the ledger below and is one of them** — as are `esbuild`, `node-gyp` consumers, Playwright, and Cypress. The failure is confusing: the install succeeds and the package is broken at runtime.

Do **not** solve this by turning scripts back on globally. Allowlist the specific packages:

```jsonc
// package.json
"pnpm": { "onlyBuiltDependencies": ["sharp", "esbuild"] }
```

A short, explicit, reviewable list. Every name on it is a package you have decided may execute code on your machine — which is a decision worth making on purpose, once, in a file, rather than implicitly for all 800 packages in the tree.

`--ignore-scripts` as a blanket flag is the wrong tool: it disables the legitimate along with the hostile, and the breakage it causes is what pushes people to disable the protection entirely.

## Removing one

A dependency used in one place, for one small thing, that the platform now covers — delete it. Deletion is a feature. Revisit the ledger when the platform baseline moves (a new stable Web API can retire a package).

## Test

CI fails on a known-critical advisory in the tree. The lockfile is committed and installs run frozen; builds are reproducible. `minimumReleaseAge` and script blocking are on — verify by checking that a freshly published package refuses to resolve, not by trusting the default stayed. `onlyBuiltDependencies` is short and every entry is deliberate.

A PR that adds a `package.json` dependency without a ledger line fails review — for AI-authored changes, this is a line in the instruction file ([tooling.md](tooling.md)). Worth stating plainly there, because reaching for a package is one of the things a model does most readily and least visibly ([ai-authorship.md](ai-authorship.md)).
