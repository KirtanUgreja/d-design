# d-design

An AI presentation-experience engine. Brief in, immersive scrolling experience out — published as a URL, an embed, or fullscreen.

**Status:** design complete, nothing built.

## The bet

The AI never writes styling. It emits **content + intent** — `motion: "reveal"`, `emphasis: "hero"` — and a separate art-direction layer resolves that intent into type scale, spacing, color, easing, and duration.

That single constraint buys four things at once:

| It buys | Because |
|---|---|
| Consistent design quality | The AI cannot pick a bad font size; it never sees one |
| Safe editing | Output is a typed tree, so edits patch one block instead of regenerating HTML |
| A real product boundary | Custom code runs in a sandboxed iframe with no network or storage |
| Cheap variety | Art direction #2 is a token file, not a rewrite |

Without it, this is Claude Artifacts — which already generates a beautiful HTML presentation, and already falls apart on the second edit.

## Scope

- **Wedge:** marketers building product launches
- **Delivery:** live URL, embed, fullscreen + keyboard nav
- **Builder:** solo, with AI assistance — so v1 ships *one* art direction, end to end

## Docs

Docs are versioned by release. `docs/v1/` is the current design.

**v1 — generate, edit, publish.** One art direction, end to end.

| Doc | What's in it |
|---|---|
| [v1/spec.md](docs/v1/spec.md) | Locked decisions, architecture, persistence, build order, verification, risks |
| [v1/scene-schema.md](docs/v1/scene-schema.md) | The IR — every type, all 11 blocks, every validation rule |
| [v1/art-direction.md](docs/v1/art-direction.md) | The token layer, and `cinematic-dark` defined concretely |
| [v1/ai-pipeline.md](docs/v1/ai-pipeline.md) | The four generation phases and their contracts |

**v2 — creative range.** Same content, radically different experiences, one click.

| Doc | What's in it |
|---|---|
| [v2/spec.md](docs/v2/spec.md) | Theme, commitments vs bets, what changes from v1, build order |
| [v2/art-direction-system.md](docs/v2/art-direction-system.md) | AD format, the 3 hand-authored ADs, motion axis, user controls, linter |
| [v2/transformations.md](docs/v2/transformations.md) | Reskin, overflow handling, slides mode, version history |
| [v2/primitives.md](docs/v2/primitives.md) | The 7 new primitives, and what was refused |

**v3 — the wow release.** Derived, personalized, live, multilingual, dimensional. This is what goes in front of real users.

| Doc | What's in it |
|---|---|
| [v3/spec.md](docs/v3/spec.md) | Theme, locked decisions, what changes from v2, build order, risks |
| [v3/ai-art-direction.md](docs/v3/ai-art-direction.md) | Deriving an art direction from a reference — and what it refuses to copy |
| [v3/personalization.md](docs/v3/personalization.md) | Signed per-recipient links, analytics, privacy stance |
| [v3/localization.md](docs/v3/localization.md) | Transcreation, per-script fonts, RTL, locale delivery |
| [v3/live-data.md](docs/v3/live-data.md) | Server-fetched bindings that keep the page network-free |
| [v3/dimensional.md](docs/v3/dimensional.md) | 3D scenes, the `environment` token group, performance budgets |

**Security.** Cross-cutting, versioned by when each threat arrives. The core threat: untrusted input reaches an LLM whose output becomes a web page.

| Doc | What's in it |
|---|---|
| [security/README.md](docs/security/README.md) | Threat model, trust boundaries, which control is needed when |
| [security/prompt-injection.md](docs/security/prompt-injection.md) | The five injection paths, and why the schema does most of the work |
| [security/tenancy-and-data.md](docs/security/tenancy-and-data.md) | RLS, server-mediated reads, credentials, PII, retention |
| [security/content-and-web.md](docs/security/content-and-web.md) | Origins, CSP, sandbox, XSS, uploads, CSS-token injection |
| [security/infrastructure.md](docs/security/infrastructure.md) | SSRF, denial-of-wallet, billing entitlements |
| [security/testing.md](docs/security/testing.md) | Automated suite and manual checklist |
| [security/operations.md](docs/security/operations.md) | Disclosure, incident response, dependencies, release gate |

Read `v1/scene-schema.md` first. Everything else depends on that shape.

## Roadmap

| Version | Focus | Why then |
|---|---|---|
| **v1** | One art direction, end to end | Proves the runtime, the editing model, and that output can be beautiful |
| **v2** | Creative range — 3 ADs, motion axis, one-click reskin, slides, history | The abstraction is unproven with one AD. Reskin is what makes it visible to users |
| **v3** | AI-derived ADs, personalization, analytics, localization, live data, 3D, pricing | The wow release, and the first one real users see |
| **v4** | Marketplace, CRM integrations, teams and roles | All gated on users who exist by then |
| **later** | Charts · PDF/PPTX export · speaker notes · collaboration · freeform canvas · stock images | Each is a product inside the product |

Accounts, custom domains, and the branding badge land in **v3** — it is the first version an outside person opens, and the paid tier sells two of them.

**Users arrive after v3.** That is a deliberate choice and the project's top risk — it means v1 and v2 assumptions compound unvalidated for the whole build. The bets tables in `v2/spec.md` and `v3/spec.md` are the checklist for the day the first user shows up. The natural early-exit point, if you ever want one, is after v3 step 4: derived ADs plus twelve languages is already worth showing someone.

Versioned docs exist so a decision can be revisited without rewriting history. When v2 changes something v1 locked, `docs/v2/` records what changed and why — `docs/v1/` stays as the record of what was believed at the time. See the *What v2 changes from v1* table in [v2/spec.md](docs/v2/spec.md).
