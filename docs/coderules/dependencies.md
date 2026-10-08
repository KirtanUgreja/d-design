# Dependencies

## The rule

**Stdlib and platform first. Every dependency past the baseline needs a one-line justification recorded here.**

Not a ban — a speed bump. The cost of a dependency is not install time; it is the security surface, the breaking changes, the transitive tree, and the fact that you now maintain a relationship with code you did not write. A few lines you own beat a package you rent, until they clearly don't.

## v4 — read this before the lists below

> **2026-09-26.** v4 ([../v4/spec.md](../v4/spec.md)) deletes `render/`, the upload worker, `web/` as it stood, and most of `api/`'s features. Phase 21 ([../v4/plan/21-reset.md](../v4/plan/21-reset.md)) removed each ledger row in the same commit that removed the package. **The baseline tables below still list the v3 stack** and are trimmed as phases 27 and 29 re-decide each row.

**Removed in phase 21 (2026-09-30):** `web/`, `render/` and `worker/` with every package they installed; and from `api`, SQLAlchemy, asyncpg, Alembic, FastAPI and uvicorn. FastAPI and uvicorn return in phase 27, the database packages in phase 29, each with a fresh row.

**Expected additions. Each needs its own ledger row in the commit that adds it; none is approved by appearing here:**

| Package | Where | For | Phase |
|---|---|---|---|
| `Pillow` | api | Re-encoding generated images to webp, and uploaded logos to a trimmed PNG with the pixel cap set before decode (phase 38) | 22–25, 38 |
| `openapi-typescript` | web (dev) | Generating `web/lib/api/schema.d.ts` from `cli openapi` | **added in phase 27** (2026-10-07): types only, so the client still parses every response once at entry |
| Tailwind + shadcn/ui (copy-in source on Radix primitives) | web | Our chrome only, never a deck | **added in phase 30** (2026-10-05), rows below |
| `better-auth` + `pg` (owner's choice 2026-10-08, replacing a managed-auth SDK); `pyjwt[crypto]`; `sqlalchemy` + `alembic` + `psycopg[binary]` | web / api | Accounts (Better Auth, email and password, its JWT verified in FastAPI) and the hosted Postgres | 29, on 2026-10-09 |

**Added in phase 27 (2026-10-07), for the API process** — `api/app.py` and nothing else imports them; the engine stays framework-free (rule 6):

| Package | Where | For | Why not something smaller |
|---|---|---|---|
| `fastapi` (+ `starlette`, its own base) | api | Thin routes, one Pydantic parse per input, OpenAPI for the web's generated types | The spec's chosen backend framework (`../v4/spec.md` → Stack); its OpenAPI is what keeps the web's types honest |
| `uvicorn` | api | The ASGI server that runs `app.py` | The reference ASGI server; nothing to configure |

**Added in phase 30 (2026-10-05), for the UI prototype** — `web/`, which pnpm 11 installs with its release-age gate and install scripts blocked:

| Package | Where | For |
|---|---|---|
| `next`, `react`, `react-dom`, `tailwindcss`, `@tailwindcss/postcss`, `typescript`, `eslint`, `eslint-config-next`, `@types/*` | web | The stack [../techstack/frontend.md](../techstack/frontend.md) names |
| `server-only` | web | Makes a client import of a server module a build error ([structure.md](structure.md)) |
| `radix-ui` | web | The primitives under shadcn/ui: focus traps, layers, keyboard navigation |
| `class-variance-authority`, `cn` | web | shadcn/ui's variant and class-merge helpers; `cn` is published by shadcn-ui itself (`github.com/shadcn-ui/cn`) |
| `tw-animate-css`, `shadcn` | web | shadcn's open/close keyframes and its base CSS, imported by `app/globals.css`; both off under reduced motion |
| `@playwright/test` | web (dev) | The app's end-to-end tests, on Chromium and WebKit locally and all three engines in CI |

shadcn's icon set (Phosphor) is **not** installed, in line with the line below: the one component that wanted an icon, the dialog's close button, uses a text glyph.

**Deliberately not added:**
- **`fonttools` + `brotli`.** Vendored Latin-subset woff2 are embedded as-is. Trigger: a non-Latin locale, or fonts exceeding 1 MB of an export.
- **An icon set.** v4 slides have no icons.
- **A chart library.** Charts are SVG built by our own code from a chart spec.
- **An agent framework.** Unchanged; see the rule below.

**Placement in v4.** Two processes matter. The **worker** (`api/worker.py`, phase 27) holds the model key and drives Chromium over model-written HTML, with all network aborted. The **API** process holds the data. Neither parses user-uploaded bytes in v4. When uploads return (the first brand-kit user), the parser goes in its own isolated process, and the old rule below applies again.

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

Installed, as of phase 22 (2026-09-30). The v3 rows left with the packages they described; their text is at the tag `v3-final`.

```
playwright (v4, phase 21) — headless Chromium, in api — screenshots for the
  bench wall now; QA measurement, thumbnails and PDF from phase 22. Writing
  our own browser is not a sentence anyone would finish. It renders
  model-written HTML, so every request is aborted and page scripts are off.
nh3 (v4, phase 22) — the HTML allowlist sanitizer for model-written slides,
  in api — a sanitizer is the one place never to write our own.
tinycss2 (v4, phase 22) — parses slide CSS so the lint walks real
  declarations, in api — a CSS tokenizer is a parser, not a regex. Lint only:
  scoping is Declarative Shadow DOM.
pydantic.mypy (v4, phase 21) — the mypy plugin that ships inside pydantic —
  not a new package. Without it `disallow_any_explicit` rejects every
  BaseModel, because the synthesized __init__ takes **Any.
better-auth (v4, phase 29) — email-and-password accounts, sessions and the
  JWT plugin (EdDSA, JWKS at /api/auth/jwks), in web — the owner's choice of
  2026-10-08 (v4/plan/master-plan.md, A2); a credential path is never ours
  to write. Its tables live in their own `auth` database through its built-in
  Kysely adapter, so no ORM is added. Its CLI runs pinned through
  `pnpm dlx auth@1.7.7 migrate` and is not installed.
pg + @types/pg (v4, phase 29) — the Postgres pool Better Auth's adapter
  takes, in web — the adapter is inert without a driver.
@dicebear/core + @dicebear/styles (v4, phase 29) — profile avatars drawn in
  the browser from {style, seed, options} (A6), in web — generative SVG art is
  not a few lines, and drawing locally keeps api.dicebear.com out of the
  request path. Core is MIT. Styles carry their own licences: only
  notionists, lorelei, open-peeps, thumbs, shapes and pixel-art are loaded,
  all CC0 1.0 (the package's LICENSE.md, checked 2026-10-08), each imported
  on demand.
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
