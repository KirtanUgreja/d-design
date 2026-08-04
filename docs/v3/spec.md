# v3 Spec — The Wow Release

## Theme

v1 makes an experience. v2 makes it anything. **v3 makes it alive** — derived from a reference, personalized per viewer, current with real data, fluent in twelve languages, and dimensional.

This is the release that goes in front of real users.

## The top risk, stated first

**No external user will have touched this product before v3 ships.**

That decision was raised twice and confirmed twice, so it is the plan. But it means every assumption in v1, v2, and v3 compounds unvalidated for the entire build. If the wedge is wrong, or the editing model is wrong, or marketers don't want any of this, you find out at the end.

Two mitigations, both cheap, neither requiring a schedule change:

- **The bets tables stay live.** v2's bets table and this document's are the list of things to check the day the first user arrives. Re-read them before building anything that depends on them.
- **v3 is ordered so the earliest features are the most reversible.** AI-derived ADs and localization ride on systems that already exist. 3D and analytics — the two hardest to unwind — come last, so a change of mind at any point costs the least.

If you ever want to shorten the loop, the natural cut point is after localization: derived ADs, reskin, and twelve languages is already a product worth showing someone.

## The features

| | What it is |
|---|---|
| **AI-derived art direction** | Drop a screenshot, URL, moodboard, or description → a full art direction. [ai-art-direction.md](ai-art-direction.md) |
| **Personalization** | Signed per-recipient links; company, logo, industry woven in. [personalization.md](personalization.md) |
| **Analytics** | Who opened, how far they got, whether they reached the CTA. [personalization.md](personalization.md) |
| **Instant localization** | One experience, twelve languages, transcreated to fit the design. [localization.md](localization.md) |
| **Live data** | Stats bound to Airtable/Notion, server-fetched and cached. [live-data.md](live-data.md) |
| **3D scenes** | Scroll-driven WebGL, styled by the art direction. [dimensional.md](dimensional.md) |
| **Pricing** | Free to generate, pay to publish |
| **AI transparency compliance** | Machine-readable marking of generated content — legally required, in force since 2 Aug 2026. [compliance.md](compliance.md) |

Marketplace moves to **v4**. Its gate was real users, and by this timeline there still aren't any when v3 ships. What v2 and v3 contribute is the AD format and the linter that make it possible later.

## Locked decisions

| Axis | Decision | Why |
|---|---|---|
| AD derivation | Abstract qualities only — never fonts, exact colors, or layouts | A cloning tool is a plagiarism machine with your name on it |
| AD inputs | Screenshot · URL · moodboard · description | All four fill the same four control axes from v2 |
| Personalization | Signed per-recipient links | No tracking scripts, no URL tampering, matches how ABM already works |
| Personalized fields | Named fields, AI-suggested at build | Bounded and reviewable; never regenerate scenes per viewer |
| Analytics | Aggregate by default, identified opt-in | Keeps the wow, puts the compliance burden on the publisher |
| Live data | Server-side, cached, read-only | Values are baked in at publish, so live data adds **zero** requests to the page |
| Data sources | Airtable / Notion | Where marketing teams actually track work |
| Localization | Transcreate to fit the budget | Only possible because budgets exist. The design never breaks |
| Locale delivery | Locale-prefixed URLs, auto-detect on top | Auto-detect needs somewhere to redirect *to* |
| Locale support | Per-script fonts + RTL mirroring | Without both, everything outside Latin looks broken |
| 3D styling | New `environment` token group | ADs style 3D like everything else; reskin guarantee holds |
| 3D assets | Stock primitives · abstract 3D · uploads | **Never generate the product** — carried from v1 |
| Pricing | Free to generate, pay to publish | No friction at the wow moment; every v3 feature sits on the paid side |
| Marketplace | v4 | Still no designers to fill it |

### One principle, applied three times

**Never generate the product.** v1 refused AI-generated product imagery. v3 refuses AI image-to-3D of real products for the same reason: a plausible-but-wrong render of the thing being sold is a credibility problem no quality bar fixes. Stock primitives, abstract forms, and real uploads only.

The same instinct rules out cloning a reference site's design, and rules out regenerating scene copy per recipient. When in doubt: the system may arrange, style, and translate what the user gave it. It may not invent the subject.

## Platform & regulatory reality (researched August 2026)

Three capabilities matured and one legal obligation came into force. The obligation is not optional and is the only item here that adds work.

| | Status | What it changes |
|---|---|---|
| **EU AI Act Article 50** | **In force 2 August 2026.** Penalties to €15M / 3% of global turnover | Generated text, images, **and translations** must be marked machine-readably as artificially generated. C2PA is the mechanism the Commission's draft Code of Practice names. See [compliance.md](compliance.md) |
| **WebGPU** | **Baseline January 2026**, ~82% support. Three.js `WebGPURenderer` zero-config since r171 | 3D renderer choice is a non-decision: WebGPU primary, WebGL2 fallback, Three.js handles it |
| **CSS logical properties** | Long stable, universally recommended for i18n | RTL is nearly free — *if the renderer was authored logically in v1*. `transform` is the one documented exception, and it's where motion lives |
| **Vision is no longer scarce** | ~67 models have it, **28 of them open-weight and self-hostable** | AD derivation is not gated on one vendor. Give the model crop-and-verify tools rather than raising effort — a more cost-effective lever than a bigger single look ([../techstack/ai-stack.md](../techstack/ai-stack.md)) |

The RTL entry is the one to act on earliest: it is a **v1 authoring decision with a v3 payoff**, and retrofitting it means auditing 19 primitives across 3 art directions.

## Shipping to real people: the things v1 and v2 could skip

v1 was explicitly single-user and local. v2 never revisited it. v3 is the first version an outside person opens, so three things that were legitimately deferred now have to exist — and the pricing model above already sells two of them.

**Accounts and auth.** v1 said *"auth arrives with Supabase"* without naming a version. This is that version. **Better Auth** ([../techstack/backend.md](../techstack/backend.md)), email + Google. No teams, no roles, no sharing — one owner per experience. Teams land in v4 alongside the marketplace, since both need users who exist.

**Custom domains.** Sold on the paid tier, listed in v1 as *not in v1*, and never picked up since. `CNAME` to your host, automated certificate issuance, one domain per experience. Without this the paid tier has no headline benefit.

**The branding badge.** The free tier's constraint is a "made with" mark on published pages, and no document has ever mentioned it. It needs to be a real render decision — styled per art direction so it does not look bolted on, and removable on the paid tier.

**And it is not the only mark that page owes its viewer.** Article 50 expects a human-visible AI-content disclosure alongside the machine-readable marking ([compliance.md](compliance.md)). Two separate small marks in the corner of a customer's launch page is a bad outcome twice over, so **badge and disclosure are designed as one provenance line** ([../design/website.md](../design/website.md)). The trap is in the toggle: the badge is removable on the paid tier and **the disclosure is not**, and those two facts are one boolean apart in the render path.

**A front door.** v3 is the first release with a URL worth giving someone, which makes it the first release that needs a marketing site, a pricing page, and a signup flow. All three are already designed ([../design/website.md](../design/website.md), [../design/app.md](../design/app.md)); this is where they get built. It is not a large build — eight pages, no third-party scripts, and its most convincing asset is an embedded real published artifact, which costs approximately nothing because published artifacts are static.

Free: generate, edit, preview, publish one experience on a subdomain with branding.
Paid: custom domain, no branding, embed, unlimited published, personalization, analytics, localization, live data.

Every v3 feature lands on the paid side. That is not a coincidence — it is why this pricing shape was chosen.

Four presentation decisions ride on top of that shape without changing it, and they are argued in [../design/website.md](../design/website.md): the **card is taken at publish rather than at signup**, the trial is a **reverse trial** (full product, no card, then the restricted plan), plans are **seats with a generous allowance rather than credits**, and **a published page never dies when a plan lapses** — it reverts to carrying the badge. That last one is not generosity. Killing a customer's live launch page is a lawsuit and a thread.

**The business-logic exposure this creates is named rather than discovered:** free-to-generate with a paid publish gate is precisely the "publish-before-payment state machine" that [../security/adversarial-ai.md](../security/adversarial-ai.md) lists as the attack class with no scanner and no pattern. The entitlement check belongs in one place, at the data layer, failing closed.

## What v3 changes from v2

| v2 said | v3 says | Why |
|---|---|---|
| ADs are hand-authored or control-authored | Also AI-derived | Derivation fills the same four axes |
| 4 token groups | 5 — adds `environment` | 3D needs styling or it looks pasted in |
| `type` has one font stack | Per-script font stacks | Your display font has no Japanese |
| 18 primitives | 19 — adds `Model3D` | Live data and personalization are *props*, not primitives |
| `Stat.value` is a string | `string \| DataBinding` | Binding is a property of existing blocks |
| One scene tree per experience | One per locale | Transcreation produces real per-locale trees |
| Layout direction is LTR | LTR or RTL | Mirrors layouts, motion, and marquees |
| Pricing deferred | Free to generate, pay to publish | Third deferral would be permanent |
| Docker Compose and a dev server | **The whole AWS stack** — two workers, RDS, S3/CloudFront, Terraform, CI/CD | v3 is the first release with users, other people's data, and hostile input from strangers |
| One runtime | **Three**, split on trust | The process holding database credentials must not be the one rendering an attacker's webpage |
| A published page makes zero requests | **Exactly two**, by exact path | The cost of client-side personalization and the analytics beacon |

**Migration:** existing experiences get `locale: 'en'`, `direction: 'ltr'`, and an `environment` group defaulted per AD. No content changes.

## Pipeline delta

**Transcreation** is a fifth phase, running at publish: source tree + target locale + target AD budgets → per-locale tree. Not a translation call — a rewrite-to-fit call. It runs **in the `jobs` worker** as a PGQueuer job, because twelve locales is minutes of work and it must enqueue in the same transaction as the publish that triggered it ([../techstack/backend.md](../techstack/backend.md)).

**Derivation** is its own phase: reference input → the four control-axis values → `ArtDirection` → linter. If the linter rejects it, the derivation retries once with the failures as context, exactly like scene repair. When the input is a URL, the capture runs **in the fetch worker** — the quarantined container — because it is the product pointing a browser at an address a stranger chose ([ai-art-direction.md](ai-art-direction.md)).

**Personalization** is not a generation phase. Fields are substituted at render, never generated per viewer.

**The visual verification loop from v2 runs against everything above**, still bounded at one revision and still a plain loop in the seam rather than an agent ([../techstack/ai-stack.md](../techstack/ai-stack.md)) — twelve locales × three ADs multiplies the work, not the autonomy. Derived ADs get rendered and inspected rather than only linted, and twelve locales multiply the ways a layout breaks — a budget-fitting German headline can still collide with a stat block ([../techstack/pipeline-tools.md](../techstack/pipeline-tools.md)). This is the release where the loop stops being a nicety: reviewing 12 locales × 3 ADs by eye is not a thing one person does.

## Persistence delta

```
users          id, email, created_at                    -- Better Auth
locales        experience_id, locale, direction, scenes (jsonb), published_at, status
recipients     id, experience_id, token, company, logo_asset_id, industry,
               contact_name, custom, created_at
views          id, experience_id, recipient_id?, scroll_depth, reached_cta,
               duration_ms, created_at
data_sources   id, kind, credentials_ref, config (jsonb),
               last_fetched_at, last_value (jsonb), last_error
domains        id, experience_id, hostname, cert_status, verified_at
subscriptions  id, user_id, plan, status, current_period_end
art_directions + source: 'system' | 'user' | 'derived', + reference_ref
experiences    + owner_id
```

`views.recipient_id` is nullable and null unless the publisher enabled identified tracking. That nullability is the privacy design, not an implementation detail.

## Build order

Ordered by reversibility — cheapest to unwind first, with one unavoidable exception at the front.

0. **Infrastructure.** v1 and v2 ran on Docker Compose and a dev server. **v3 is where the entire operational stack stands up** ([../techstack/infrastructure.md](../techstack/infrastructure.md)): AWS account, VPC with the quarantine subnet, both ECS workers, RDS/Aurora, S3 + CloudFront + ACM, Secrets Manager and KMS, Terraform, GitHub Actions with OIDC, and the second repo for the fetch worker
1. AD format v3: `environment` group, per-script fonts. Migrate the 3 ADs
2. **AI-derived AD** — the biggest wow, and it rides entirely on v2's control axes
3. Localization: transcreation + locale URLs + per-script fonts
4. RTL mirroring
5. Live data: Airtable/Notion + bindings + failure states
6. Personalization: recipients, signed links, field substitution
7. Analytics + consent + privacy controls
8. 3D: `environment` rendering, `Model3D`, stock library, abstract generators
9. Accounts, custom domains, branding badge, billing, publish gate — **and the marketing site, pricing page, and signup**, which are the same release's work and are already designed ([../design/website.md](../design/website.md))
10. **AI transparency marking** — C2PA on generated imagery, machine-readable declaration on published pages, per-locale marking. Not last because it is least important; last because it needs every generating surface to exist first. **It gates launch, not v3 feature-completeness**

**Step 0 is not optional and it is not reversible-ordered, which is why it breaks the rule the rest of the list follows.** Almost everything after it depends on infrastructure that does not exist yet: derivation fetches attacker-supplied URLs (fetch worker), transcreation is long-running work per locale (job worker), live data holds integration credentials (fetch worker), 3D posters are generated at publish (job worker), and every one of those writes to S3. Attempting step 2 first means building it twice.

The cost is real and it belongs in the estimate rather than in a surprise: this is the release where a solo build acquires an AWS topology, an IaC codebase, and a second repository, none of which move Risk 1.

**The one thing v1 should already have done is `storage.ts`** — pointed at the S3 API from day one with MinIO locally, so this step is a credential change rather than a rewrite.

Steps 1–4 are a shippable product on their own. If you ever decide to meet users earlier, stop here.

## Verification

| What | How |
|---|---|
| **Derived ADs pass the linter** | 20 references → 20 ADs. 100% pass after at most one repair. Manually judge 20/20 for *beauty* — the linter catches unreadable, never ugly |
| **Derivation is not cloning** | Feed a well-known site. Assert output shares none of its fonts and no color within ΔE 10 |
| **Transcreation fits** | 5 experiences × 12 locales × 3 ADs. Zero budget overflows. Native-speaker review on at least 3 locales |
| **RTL** | Arabic renders mirrored: splits swapped, motion reversed, marquees reversed |
| **Live data boundary** | A published page makes **exactly two** outbound requests and no others — the personalization fields endpoint and the analytics beacon, both by exact path. **Live data adds none.** Asserted in a real browser, not by reading code ([../techstack/frontend.md](../techstack/frontend.md)) |
| **Data failure** | Kill the source. Page shows last good value, then fallback. Never blank, never an error |
| **Personalization** | Tamper with a signed token → rejected. Unpersonalized link → clean defaults, no empty braces |
| **Privacy default** | Publish without opting in → `views.recipient_id` is null for every row |
| **3D** | Mid-range phone: interactive, under budget, degrades to a static render on failure |
| **C2PA survives the pipeline** | Generated image → manifest present after upload, **server-side re-encode**, storage, and serving. The security re-encode strips metadata by design; this is the test most likely to fail |
| **Content marking** | Published page and every locale page carry a machine-readable AI-content declaration, derived from per-block provenance. Human-authored copy is *not* marked synthetic |
| **RTL exception list** | Arabic renders mirrored via `dir` alone, except `translateX` motion, `Marquee`, and horizontal `Timeline` — assert each inverts |
| **Reskin still holds** | 3 ADs + derived ADs × 4 motion × 2 modes × 12 locales. The v2 guarantee must survive everything above |

That last row matters most. Every v3 feature is a chance to break the one thing v2 promised.

## Risks

**1. No user contact until now.** Stated at the top. Everything else on this list is second.

**2. Transcreation quality in languages you cannot read.** The AI will produce confident, budget-fitting, subtly wrong German. You will not catch it. Ship with a per-locale "needs review" state and a native-review path before any locale is published, or the feature quietly damages the brands it serves.

**3. Derived ADs will be valid and ugly.** The linter enforces contrast, scale, and motion bounds — it cannot enforce taste. Expect to hand-curate a set of derivation *priors* pulled from the 3 hand-authored ADs, and expect that to be the real work.

**4. 3D is a specialty, not a feature.** Asset pipelines, draw-call budgets, mobile GPUs, memory ceilings, and a graceful fallback for every failure. It is last in the build order for that reason. Be willing to ship v3 without it.

**4b. AI transparency is a launch gate, not a feature.** Article 50 has been in force since 2 August 2026, penalties reach €15M or 3% of global turnover, and the wedge is marketers — many EU-based or serving EU audiences. The architecture already tracks what it generated versus what the user supplied, which is most of the work. What remains is marking, and one collision worth knowing about now: the security re-encode that strips EXIF will also strip a C2PA manifest unless it is written to preserve it. See [compliance.md](compliance.md), and get counsel.

**5. Analytics is a compliance surface.** Identified tracking means consent, retention policy, deletion requests, and a DPA. Aggregate-by-default contains it, but the moment a customer opts in, that surface is yours too.

**6. This is the largest version by far, built solo.** v2 was 54 design surfaces. v3 is five subsystems, three of which (3D, analytics, billing) are new competencies. The build order exists so that stopping early still leaves a coherent product.

**6b. And it is also the release that acquires an infrastructure estate.** Step 0 is an AWS topology, a Terraform codebase, two container services, a CDN, a secrets story, and a second repo — none of it visible to a user, all of it prerequisite. It is genuinely satisfying work, which is the danger: it feels like progress and does not move Risk 1 or Risk 3 at all. Time-box it, keep it in Terraform so it is reviewable rather than remembered ([../techstack/infrastructure.md](../techstack/infrastructure.md)), and get back to the features.
