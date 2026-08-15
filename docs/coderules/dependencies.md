# Dependencies

## The rule

**Stdlib and platform first. Every dependency past the baseline needs a one-line justification recorded here.**

Not a ban — a speed bump. The cost of a dependency is not install time; it is the security surface, the breaking changes, the transitive tree, and the fact that you now maintain a relationship with code you did not write. A few lines you own beat a package you rent, until they clearly don't.

## The baseline

Already decided, no justification needed — these are the stack. **Two languages means two baselines**, and a package on one list is not thereby approved on the other.

### Python — `api`, `jobs`

| | For |
|---|---|
| FastAPI | The backend framework |
| **Pydantic (v2)** | Schemas and validation, **the source of truth for `Deck`**. Also produces the model's JSON Schema — see [python.md](python.md) |
| SQLAlchemy (async) + Alembic | Typed SQL and migrations, over the application tables |
| `httpx` | The model seam, and every outbound HTTP call |
| PGQueuer | Background jobs in the database you already have (v3) |
| `uv` | Resolve, lock, run. The package manager — see below |
| mypy + Ruff | The gate ([python.md](python.md)) |
| pytest | Tests |
| boto3 | S3, KMS, Secrets Manager (v3) |

### TypeScript — `web`, `render`, fetch worker

| | For |
|---|---|
| Next.js + React | App framework, one renderer, routing |
| TypeScript | The TypeScript runtimes |
| **`@d-design/schema`** | Generated types and Zod validator. **Generated — never hand-edited** ([typescript.md](typescript.md)) |
| Zod (**v4**) | The runtime the generated validator needs |
| Drizzle | Typed SQL and migrations, **auth tables only** |
| **Motion** (`motion`, import `motion/react`) | Motion, driven by the design-family vocabulary. **Not `framer-motion`** — renamed in 2025, now maintained independently at motion.dev; the old package still installs but is no longer actively developed |
| Tailwind | App chrome only — never a design family (that is CSS variables) |
| Better Auth | Accounts, sessions, OAuth, MFA (v3). Users live in your own Postgres, in `web` |
| Zustand | Editor state — one mutable document, undo/redo |
| Motion, Tailwind | See below |
| Playwright | E2E, the security assertions that need a real browser, screenshots in the fetch worker, and the visual loop in `render` |
| React Email | Auth email templates, next to the auth code that sends them (v3) |
| Sentry | Errors, **both languages** — **configure scrubbing before the first event**, see [../security/operations.md](../security/operations.md) |
| Promptfoo · Langfuse (self-hosted) | Evals and tracing ([../techstack/ai-stack.md](../techstack/ai-stack.md)) |
| **Pillow** (`api`) | Brand-kit upload re-encode (v3): strips EXIF, kills polyglots, normalizes to PNG/JPEG, and enforces the pixel cap through `MAX_IMAGE_PIXELS` before an allocator is asked for anything. Not `sharp`, which an earlier file named — that file predates the Python backend move. **Runs in the worker that handles hostile bytes** |
| **defusedxml** (`api`) | SVG entity-expansion refusal. The billion-laughs family is a denial-of-service shape distinct from SVG XSS, and it happens *in the parser*, before an allowlist has an element to inspect — so it needs a parser that refuses entity declarations rather than a sanitizer that removes them. Pure-stdlib wrapper, no transitive tree |
| **python-multipart** (`api`) | FastAPI's own requirement for `UploadFile`; a form parser is not something to write |

**Not added: DOMPurify.** `v1/plan/10-brand-and-uploads.md` anticipated it, and its Verify list asks to prove no DOMPurify **2.x** is anywhere in the tree. There is no DOMPurify at all — SVG sanitization runs in `api`, in Python, as an allowlist over a `defusedxml` parse (`api/features/assets/sanitize_svg.py`), so that check is satisfied by absence. Deletion is a feature, and this is the version of it where the dependency never arrives: DOMPurify had four distinct XSS bypasses disclosed in 2025–2026, which is precisely why the design does not rest on a sanitizer in the first place — an SVG is served only through `<img>`, where it cannot execute regardless.

shadcn/ui is deliberately absent: it is copy-in source, not a dependency. That is the point of it. Resend is absent for the same class of reason — sending mail is a POST with a JSON body, and `httpx` already does that.

Full rationale for each, and the rejected alternatives, in [../techstack/decisions.md](../techstack/decisions.md).

## Adding one

Before reaching for a package, walk the ladder:

1. Does the platform or stdlib already do this? `Intl`, `crypto.randomUUID`, `URL`, `structuredClone`, the Fullscreen and File APIs, and CSS for most animation on one side; `pathlib`, `itertools`, `functools`, `datetime`, `hashlib`, `contextlib` on the other. Reach here first.
2. Does the baseline already cover it? Pydantic validates, SQLAlchemy queries, `httpx` fetches, Motion animates. Don't add a second tool for a job one of these does.
3. Is it a few lines of our own? A debounce, a slug, a retry loop, a clamp — write it, test it, own it.
4. Only then, a dependency — and record why.

**Python makes rung 4 too easy, and that is new.** `pip install` has no friction and the ecosystem is enormous, so the ladder does more work here than it did in a TypeScript-only repo. The single most likely bad install in this project is an agent framework, which is why it has its own rule below.

### The agent-framework rule

**An agent framework is a runtime-privileged dependency and needs a ledger line naming what it does that your own code cannot.** "Everyone uses it", "it's the standard", and "it handles the tool loop" are not that — the tool loop here is a `for` with a limit of one ([patterns.md](patterns.md) rule 6).

Two facts make this a rule rather than a preference:

- **It would land in `api`** — the process with database credentials, model credentials, and decrypted integration tokens. That is the opposite end of the placement rule below from where risky dependencies belong.
- **The class is under active exploitation.** `langchain-core` CVE-2025-68664 (CVSS 9.3, secret disclosure), CVE-2026-34070 (arbitrary file read), LangGraph CVE-2025-67644 (SQLi in the checkpointer) and CVE-2026-28277 (unsafe deserialization on checkpoint load), plus a June 2026 RCE chain against self-hosted deployments. The Cloud Security Alliance's March 2026 research note covers the pattern. Full reasoning in [../techstack/ai-stack.md](../techstack/ai-stack.md).

The barrier that used to enforce this was that adding LangGraph meant adding Python. That barrier is gone, so the rule is written down instead.

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
@fontsource/* (v1, per design family) — self-hosted, open-license type for the
  design-family registry. techstack/frontend.md commits to Fontsource for a
  licensing reason that survives the vision change: these faces are embedded in
  a deck the customer redistributes, so the licence must permit bundling in a
  downloadable file. OFL-1.1 does; a webfont licence bought per-domain does not.
  The v1 registry (~10-15 families) seeds a handful of open families; the set
  grows as the family count does (v2). The constraint from docs/design/brand.md
  — our chrome's face must differ from every family's — still applies.
  **Families, not art directions.** The old registry had three fixed art
  directions each with two faces. The new registry is a combinatorial space of
  families; the type-pairing axis is where identity lives most (findings.md),
  so the face budget follows the family count, not a fixed set.
esbuild (v2, phase 00) — bundles the `render` service, JSX included — Node 26
  strips TypeScript types natively, so a plain .ts service would need no build
  at all, but it does not transform JSX and the renderer is entirely .tsx. A
  JSX/TS compiler is on the don't-write-your-own side of this file's own line.
  It also resolves `@/` against web/src, which is what lets `render` import the
  renderer rather than copy it — and one source tree is a stronger guarantee
  against drift than the version pin phase 00 originally specified.
playwright (v2, phase 00) — headless Chromium for the screenshot service —
  already a devDependency in web for the e2e suite; this makes it a runtime
  dependency of the one service whose job is driving a browser. Writing our own
  is not a sentence anyone would finish.
@fontsource/* in render (v2, phase 00) — the same families web installs —
  the screenshot document inlines the real woff2 as data URIs, because
  `setContent` gives the page no base URL and a missing face falls back
  silently to Times. A fallback face measures differently, which makes the
  vision critic review the wrong image and the PDF print measure wrong.
  `render/src/fonts.ts` throws rather than degrading, so the duplicate
  declaration cannot rot quietly.
server-only (v1, phase 05) — the marker structure.md already mandates for
  every *.data.ts and anything holding a secret ("a client component
  importing it is a build-time error"). web/src/lib/storage.ts is the first
  file that needed it; installing it is that existing rule, not a new one.
next (v2, phase 12) — the editor's app framework — the documented v2 host
  (frontend.md: "Next + the editor arrive in v2"). Baseline in the TS list;
  installed when the editor lands. The render package's esbuild bundling of
  web/src is untouched by it.
zustand (v2, phase 12) — the single mutable editor document + undo/redo —
  baseline in the TS list (frontend.md: "one mutable document, undo/redo");
  a stack of past/future deck trees with structural sharing is exactly what
  it is for. First installed when the editor lands.
tailwindcss (v2, phase 12) — app chrome only, never a design family —
  baseline in the TS list. The lint ban scoped to renderer/ (no Tailwind in
  the rendered slides) is what keeps it on the chrome side.
@radix-ui/react-select (v2, phase 12) — the accessible dropdown primitive
  the family switcher and property panel sit on — shadcn/ui is copy-in
  source on Radix primitives (frontend.md), and Radix gives the focus trap,
  dismissible layer and keyboard navigation that are genuinely easy to get
  subtly wrong. Nothing ships as a runtime dependency to the browser.
asyncpg (v3, phase 16) — the Postgres driver for api's async SQLAlchemy
  engine — baseline in the Python list; v1 had no database so it waited for
  the DB, which accounts (phase 16) brings. `pool_pre_ping`, and prepared
  statements disabled behind a transaction-mode pooler (backend.md).
better-auth (v3, phase 16) — the auth library in Node (web) — the security
  doc's own conclusion: never write your own credential path, and the
  maintained library ships OAuth, email verification, reset, MFA, passkeys,
  orgs and rate limiting that Python's options leave to you (backend.md ->
  "Auth: Better Auth"). Users live in our own Postgres, which is what makes
  the session-variable RLS work (a real FK between user and data).
drizzle-orm + drizzle-kit (v3, phase 16) — web's ORM over the auth tables
  only — baseline in the TS list. Two ORMs against one database survive only
  because the table sets are disjoint and enforced; drizzle owns auth.*,
  Alembic owns everything else (backend.md -> "Two ORMs").
pg (v3, phase 16) — the Postgres driver Drizzle's node adapter uses — the
  Drizzle baseline implies it; without a driver the adapter is inert.
fastapi + uvicorn (v3, phase 17) — api's HTTP layer, which brand kits need
  because api owns the tables and web has the UI — baseline in the Python
  list (backend.md "Python decides, TypeScript renders"). The routes are thin
  (structure.md): parse, call the feature's public function inside as_user,
  return. Uvicorn runs it in dev.
sharp (v3, phase 17) — image re-encode + EXIF strip in the worker — the
  security doc's prescribed tool (platform-and-packages.md): wraps libvips,
  caps enforced BEFORE decode, keep at latest. Lives in the worker (the
  isolated process that parses hostile bytes), never in web or api.
dompurify >=3.4.5 (v3, phase 17) — SVG sanitizer in the worker — never 2.x
  (four XSS bypasses disclosed 2025–2026, 2.x never patched for one). The
  actual SVG control is serving only via <img>; the sanitizer is the
  convenience layer. Lives in the worker, not in a privileged process.
file-type (v3, phase 17) — magic-byte detection in the worker — "extension
  and Content-Type are attacker-supplied" (content-and-web.md); the bytes
  are the authority. Worker only.
jsdom (v3, phase 17) — the DOM DOMPurify needs, worker only — the sanitizer
  runs in the isolated process; no browser context in web or api.
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

### And on the Python side, where the same problem exists with worse defaults

PyPI has the same shape of risk — typosquats, compromised maintainer accounts, and `setup.py` executing arbitrary code at install time, which is `preinstall` by another name. It has none of pnpm's defaults.

**`uv` is the package manager**, and the hardening is explicit rather than inherited:

| | |
|---|---|
| **Committed lockfile, frozen installs** | `uv.lock` in the repo; CI and Docker builds run `uv sync --frozen`. A build that can resolve differently than the last one is not reproducible |
| **Prefer wheels, avoid `setup.py`** | `--only-binary` where the dependency allows it. A wheel is data; an sdist runs code to build itself |
| **`--exclude-newer` as the age gate** | The `minimumReleaseAge` equivalent. Not on by default, so it goes in the project config where it is reviewable |
| **Hash verification** | The lockfile records hashes; installs verify them |

**The two ecosystems must not diverge in discipline.** It would be easy to run a hardened `pnpm` on one side and a bare `uv pip install` on the other and call the project protected, because the TypeScript half looks fine. The attacker picks the softer side.

The patch-speed tension in [../security/platform-and-packages.md](../security/platform-and-packages.md) applies identically to both, and so does its resolution: the age gate is the default, a security patch is an explicit logged exception, and the exception path exists before it is needed.

### The one conflict this creates, and the fix

Blocking install scripts breaks packages that legitimately need them to build a native binary. **`sharp` is in the ledger below and is one of them** — as are `esbuild`, `node-gyp` consumers, Playwright, and Cypress. The failure is confusing: the install succeeds and the package is broken at runtime.

Do **not** solve this by turning scripts back on globally. Allowlist the specific packages:

```jsonc
// package.json
"pnpm": { "onlyBuiltDependencies": ["sharp", "esbuild"] }
```

A short, explicit, reviewable list. Every name on it is a package you have decided may execute code on your machine — which is a decision worth making on purpose, once, in a file, rather than implicitly for all 800 packages in the tree.

`--ignore-scripts` as a blanket flag is the wrong tool: it disables the legitimate along with the hostile, and the breakage it causes is what pushes people to disable the protection entirely.

## You are now a publisher, not only a consumer

Everything above treats dependencies as things you take. `@d-design/schema` makes this repo a link in someone's supply chain — even if that someone is only your own fetch worker.

**Publish with npm trusted publishing (OIDC).** No long-lived npm token exists in CI, so there is no token to steal, and short-lived credentials are exactly the mitigation the registry compromises above call for. Details and the private-repo provenance caveat in [typescript.md](typescript.md).

The asymmetry to keep in mind: a compromise of your publishing pipeline is a compromise of every consumer of that package. The consumer list is short today. The discipline should not depend on it staying short.

## Where a dependency runs is part of the decision

New with the three-runtime split ([../techstack/backend.md](../techstack/backend.md)), and it changes what "risky dependency" means.

The ledger's dangerous entries — `sharp`, the PDF parser, the GLB decoders, the SVG sanitizer, headless Chromium — all live in the **fetch worker**, the container with no database access, no VPC route, and one narrowly-scoped secret. That placement is the mitigation, and it is why the fetch worker stayed TypeScript through the Python move: re-picking the highest-CVE dependency class in the tree, in a new ecosystem, buys nothing.

> **A parser CVE is a different severity depending on which container it is in.** Adding one of these to `api` or `jobs` should feel wrong, because it moves a known-hostile decoder next to the credentials.

So the ladder gains a fifth rung: *if it must be a dependency and it touches untrusted bytes, it goes in the fetch worker.* If a feature seems to need one somewhere else, that is a signal the work is in the wrong process, not that the rule needs an exception.

**The rule generalizes, and the agent-framework decision is the generalization.** Sort by what a dependency would reach if it were compromised, not by what it is for:

| Runtime | Holds | So a compromise there is |
|---|---|---|
| **`api`, `jobs`** | DB credentials, model keys, integration tokens | The worst case. **Highest bar for anything new** |
| **`web`** | Sessions, auth tables | Bad — and it also ships code to browsers |
| **`render`** | The renderer. No DB, no keys | A wrong page |
| **fetch worker** | One scoped token, no route anywhere | Contained by design. Where the dangerous parsers go |

An agent framework is a large, fast-moving dependency that would sit in the top row. That is the whole argument, and it is the same argument that puts `pdf.js` in the bottom one.

## Removing one

A dependency used in one place, for one small thing, that the platform now covers — delete it. Deletion is a feature. Revisit the ledger when the platform baseline moves (a new stable Web API can retire a package).

## Test

CI fails on a known-critical advisory in **either** tree. Both lockfiles are committed and installs run frozen; builds are reproducible. `minimumReleaseAge` and script blocking are on for pnpm, `--frozen` and `--exclude-newer` for uv — verify by checking that a freshly published package refuses to resolve, not by trusting the default stayed. `onlyBuiltDependencies` is short and every entry is deliberate.

A PR that adds a `package.json` **or `pyproject.toml`** dependency without a ledger line fails review — for AI-authored changes, this is a line in the instruction file ([tooling.md](tooling.md)). Worth stating plainly there, because reaching for a package is one of the things a model does most readily and least visibly ([ai-authorship.md](ai-authorship.md)).

**And one grep worth having in CI:** `langchain|langgraph|crewai|pydantic_ai|autogen|agno|llama_index` in `pyproject.toml`. Not because those packages are forbidden forever — the decision is falsifiable and the conditions are written down ([../techstack/ai-stack.md](../techstack/ai-stack.md)) — but because the one way this rule dies is quietly, in a dependency line nobody read, in the process that holds every credential.
