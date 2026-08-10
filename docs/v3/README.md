# v3 — the wow release

> Personalized, live, multilingual, dimensional. The first version a person outside this project ever opens.

> **Derivation left on 2026-08-10.** AI-derived art direction was v3's headline feature; it is now v2 phase [21](../v2/plan/21-art-direction-engine.md) and its design doc lives at [../v2/art-direction-engine.md](../v2/art-direction-engine.md). The product also became a **presentation** rather than a scrolling page ([../v2/presentation.md](../v2/presentation.md)), which changes what several features below mean — 3D is driven by slide advance rather than scroll, and the wedge is a founder or salesperson pitching rather than a marketer publishing. Rows affected are marked in place.

**Start here:** [spec.md](spec.md) → "The top risk, stated first".

That risk is worth reading before anything else here: **no real user sees this product until v3.** v1 and v2 assumptions compound unvalidated for the entire build. The bets tables in [../v2/spec.md](../v2/spec.md) and [spec.md](spec.md) are the checklist for the day the first user arrives.

v3 is also where the product stops being a private tool and becomes a thing with accounts, other people's data, legal obligations, and a bill.

## Files

| Doc | What's in it |
|---|---|
| [spec.md](spec.md) | Theme, the top risk, the feature set, 14 locked decisions, platform and regulatory reality, the deltas from v2, build order, verification, 6 risks |
| ~~ai-art-direction.md~~ → [../v2/art-direction-engine.md](../v2/art-direction-engine.md) | **Moved to v2.** Deriving an AD from a reference — the four input types, what is extracted, what is refused, and why priors matter more than the vision model. Left here as a pointer because half this corpus links to it |
| [personalization.md](personalization.md) | Signed per-recipient links, the 5 fields that vary, analytics, and why `recipient_id` is nullable |
| [localization.md](localization.md) | Transcreation within a budget, per-script fonts, RTL, locale delivery — 12 languages that never break the layout |
| [live-data.md](live-data.md) | Server-fetched bindings that keep the published page network-silent |
| [dimensional.md](dimensional.md) | 3D scenes, the `environment` token group, the WebGPU stack, performance budgets, three-tier failure |
| [compliance.md](compliance.md) | **EU AI Act Article 50** — machine-readable marking of AI-generated content. In force since 2 August 2026 |

## Find it fast

| If you need… | Go to |
|---|---|
| The legal obligation, and the penalty | [compliance.md](compliance.md) → "What changed on 2 August 2026" (€15M or 3% of global turnover) |
| Why the EXIF strip and C2PA collide | [compliance.md](compliance.md) → "What this product has to do" |
| Whether translations count as AI-generated content | [compliance.md](compliance.md) — yes, explicitly. And [localization.md](localization.md) → "The review gate is also the compliance gate" |
| How a reference becomes an art direction | [../v2/art-direction-engine.md](../v2/art-direction-engine.md) → "It is not a new system" (it fills v2's four control axes) |
| Why the tool refuses to copy fonts and colors | [../v2/art-direction-engine.md](../v2/art-direction-engine.md) → "What is extracted, and what is refused" |
| Why derivation quality comes from hand-authored ADs, not the model | [../v2/art-direction-engine.md](../v2/art-direction-engine.md) → "Priors" |
| Recipient token design, and how tokens leak in practice | [personalization.md](personalization.md) → "Signed per-recipient links", then [../security/content-and-web.md](../security/content-and-web.md) |
| Why translation is done inside a character budget | [localization.md](localization.md) → "Transcreation, not translation" |
| What RTL costs, and the `transform` exception | [localization.md](localization.md) → "RTL — mostly free, if the renderer was authored correctly" |
| Which script needs which font, and why fallbacks matter | [localization.md](localization.md) → "Per-script fonts" |
| How live data stays compatible with a near-silent page | [live-data.md](live-data.md) → "The boundary problem, solved by fetching elsewhere" |
| What a published page is actually allowed to request | [personalization.md](personalization.md) → "One static artifact, fields fetched at view" (exactly two endpoints) |
| Why URL input is the most dangerous feature in the product | [../v2/art-direction-engine.md](../v2/art-direction-engine.md) → "URL input is the product pointing a browser at an address a stranger chose" |
| Which runtime a given piece of v3 work runs in | [../techstack/backend.md](../techstack/backend.md) → "The five runtimes" |
| 3D performance budgets and the fallback chain | [dimensional.md](dimensional.md) → "Performance" (WebGPU → WebGL2 → poster) |
| Why image-to-3D of real products is refused | [dimensional.md](dimensional.md) → "Assets — never generate the product" |
| Accounts, custom domains, the branding badge | [spec.md](spec.md) → "Shipping to real people" |

## One principle, applied three times

Worth noticing across these documents, because it is the same rule each time and it was reached independently:

- **v1** refuses AI-generated imagery of the customer's product
- **v3** refuses image-to-3D of real products ([dimensional.md](dimensional.md))
- **v3** refuses to clone a reference's fonts, colors, and layouts ([../v2/art-direction-engine.md](../v2/art-direction-engine.md))

> **Arrange what the user gave you. Never invent the subject.**

It began as a quality rule — a plausible-but-wrong render of the thing being sold is a credibility problem no quality bar fixes. It turned out to be a security rule ([../security/README.md](../security/README.md)), and then a compliance one: a system that always knew what it generated versus what the user supplied is a system that can mark its output honestly under Article 50.

## Build order and the early exit

3D is last, deliberately. The build order is arranged so that stopping before it still leaves a coherent release — derived art directions, twelve languages, personalized links, analytics, and live data is a complete product.

**The natural early exit is after step 4.** Derived ADs plus twelve languages is already worth showing someone, and given the top risk above, showing someone early is worth more than finishing the list.

**Step 0 comes first and is not a feature — but it is no longer AWS.** Nearly every feature below depends on a *runtime topology* that does not exist yet: a fetch worker as its own process, a job worker, S3-shaped storage. Step 0 stands all of that up in **Docker Compose**, with the fetch worker on its own network and no route to the database. The AWS stack — VPC, ECS, RDS, CloudFront, Terraform, OIDC — is **step 11, last**, after every feature has been verified locally ([../techstack/infrastructure.md](../techstack/infrastructure.md)).

Split on 2026-08-09. The original argument for infrastructure-first was right and was about processes and boundaries, not about a hosting provider; separating the two means the entire feature build happens before an account exists. The honest cost is six security controls that only the deployed environment can prove — including the socket-level unreachability test, which **passes vacuously on a laptop** and must be marked not-covered rather than green. See [spec.md](spec.md) → "Why topology is first and deployment is last".

## Connects to

| | |
|---|---|
| [../v2/README.md](../v2/README.md) | The AD format, control axes, budgets, and linter that v3 reuses unchanged |
| [../security/README.md](../security/README.md) | Most controls in that directory are gated to v3, because v3 is when other people's data arrives |
| [../security/third-parties.md](../security/third-parties.md) | GDPR subprocessors, and where customer data actually goes |
| [../techstack/README.md](../techstack/README.md) | All of the infrastructure this release needs and v1 does not |
