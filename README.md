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

**[docs/README.md](docs/README.md) is the index.** It routes to every directory, and each directory's README routes to every file in it — so you can get from a question to the exact document in two hops.

| Directory | | What it covers |
|---|---|---|
| [docs/v1/](docs/v1/README.md) | versioned | Generate, edit, publish. One art direction, end to end |
| [docs/v2/](docs/v2/README.md) | versioned | Creative range — same content, radically different experiences |
| [docs/v3/](docs/v3/README.md) | versioned | The wow release: derived, personalized, live, multilingual, dimensional |
| [docs/techstack/](docs/techstack/README.md) | current | Where every piece runs, which model, what the AI may call |
| [docs/security/](docs/security/README.md) | current | Threat model and every control, gated to the version that needs it |
| [docs/coderules/](docs/coderules/README.md) | current | How the code stays consistent when an AI writes most of it |

Version directories record what was believed at the time; the cross-cutting ones are kept current. Where they disagree, the cross-cutting ones win — and [docs/techstack/decisions.md](docs/techstack/decisions.md) lists what was superseded.

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
