# Third Parties

Where customer data actually goes.

[tenancy-and-data.md](tenancy-and-data.md) says **no prompts, no outputs** — and means it about *your* logs. But every prompt goes to a model provider by definition, every research query goes to a search engine, and from phase 29 every login goes through an identity provider. The rule covered the half of the problem you control and was silent on the half you do not.

This matters more here than in most products because of what the data is: **a founder's unannounced pitch, a sales team's pricing, an investor update's real numbers.** Plausibly the most confidential thing they will ever hand a vendor.

**Updated 2026-09-26 for v4** ([../v4/spec.md](../v4/spec.md)): web search and a managed identity provider are new data flows.

## The model route is not one vendor

The choice of OpenRouter ([../techstack/decisions.md](../techstack/decisions.md)) buys model flexibility and costs a clean answer to "who has seen this prompt."

```
your prompt ──▶ OpenRouter ──▶ whichever provider served the request
                    │                        │
              sees it to route          sees it to generate
              and log usage                  │
                    └────────── retention and training rules
                                are the UNION of both parties' policies
```

That last line is the finding, and it is OpenRouter's own documented behavior: **the defaults that apply to your data are the union of OpenRouter's policy and the downstream provider's.** Choosing a model does not choose a data policy — routing does, and routing changes.

### Web search adds a third party to the route (phase 24)

The research stage uses `openrouter:web_search`. OpenRouter runs the search against **Exa** or **Parallel**, so a query leaves for a search engine as well as a model provider.

- **A query is derived from the brief.** "Series A pitch for a CI tool" becomes searches that can reveal what the user is working on. The query is written by the model; keep the instruction to search for *public facts about the market*, never to paste the user's material into a query.
- **Pin the engine** in settings. `native` search hands the query to whichever model provider served the call, which makes the recipient vary by route.
- **Research is a user choice.** `Brief.research` is a flag, and a user with confidential material can turn it off and supply their own facts.
- The search engines are subprocessors and go on the list below.

### The three settings that matter

| | |
|---|---|
| **Zero Data Retention** | ZDR routes only to endpoints whose provider will not store the data, and a ZDR provider cannot train on it either. Configurable **account-wide, per model group, and per request** (`zdr`). **It is a setting, not a default** |
| **Prompt logging** | Opt-in. Enabling it grants OpenRouter an *irrevocable right to commercial use* of those inputs and outputs. **Never enable it on this account** |
| **EU in-region routing** | Available on enterprise. Prompts and completions stay inside the EU — relevant once there are EU customers |

### The rules

1. **ZDR is on account-wide, and set per request as well.** Belt and braces, because an account setting is one console click away from being off and a per-request parameter is in the diff.
2. **A model is only usable if a ZDR route exists for it.** That is a selection criterion alongside the four in [../techstack/ai-stack.md](../techstack/ai-stack.md) — and it is the one that is not negotiable, because it is the customer's data rather than your quality bar.
3. **Prompt logging stays off, permanently.** Add it to the release checklist so a future convenience does not switch it on.
4. **The eval and tracing stack does not leak around this.** v4's bench runs locally and writes to disk ([../v4/bench.md](../v4/bench.md)). A hosted eval or tracing platform ingesting full prompts would reintroduce everything this section prevents; adopting one is a subprocessor decision.
5. **Model ids are pinned**, so a provider repointing an alias cannot silently change who processes the data.

**This is a real cost of the OpenRouter decision and it belongs next to the other one.** [../techstack/decisions.md](../techstack/decisions.md) already records that OpenRouter trades away decoder-level schema enforcement. It also trades a single, auditable data-processing relationship for a routed one. Both are acceptable; neither should be discovered later.

## The full subprocessor list

Not bureaucracy — a legal obligation the moment there are EU publishers, and a question every serious customer will ask.

**Under GDPR Article 28 you are a processor** (your publishers are the controllers for their audiences — the deck they ship is their launch communication). That means: authorization before engaging a subprocessor, equivalent data-protection obligations flowed down, and **you remain liable for their compliance.**

| Subprocessor | Sees | Sensitivity |
|---|---|---|
| **OpenRouter + routed model providers** | Brief, interview answers, pasted material, slide content, image prompts | **Highest.** From phase 22 |
| **Exa / Parallel**, through OpenRouter | Research queries | High — a query can reveal the topic. From phase 24 |
| **The identity provider** — none: Better Auth is self-hosted (owner, 2026-10-08) | Email, password hash, sessions — in our own Postgres | None beyond the Postgres host. A managed provider (WorkOS, Clerk) would add one; reconsidered for OAuth or MFA |
| **The hosting provider(s) and Postgres** | Everything at rest | Highest. Postgres: a free hosted instance (Neon or Supabase), chosen by the owner 2026-10-08 |
| **An error tracker**, if adopted | Whatever is not scrubbed | **Medium, and entirely dependent on configuration** |

Before phase 29 the product runs on a developer machine, and the only third parties are the first two rows.

Three obligations follow, and all three are cheap now and expensive to retrofit:

- **Publish the list at a stable URL**, with a general-authorization clause in the DPA pointing at it and a notification procedure for additions. This is the standard mechanism and it is what customers' legal teams look for.
- **Verify the training claim per provider**, do not assume it. "Enterprise API tiers do not train on your data" is usually true and is exactly the kind of usually that a DPA negotiation exists to pin down.
- **A new subprocessor is a decision, not a config change.** Adding a hosted eval tool, an analytics vendor, or a second model gateway is the same category of act as adding a dependency ([../coderules/dependencies.md](../coderules/dependencies.md)) — and the blast radius is larger, because it is your customers' data rather than your build.

**The marketing site is where that last rule gets tested first**, because measuring a homepage is the most ordinary thing a company does and the tools for it are all hosted. It resolves the same way Langfuse did: **self-hosted, cookieless, on our own site only** ([../design/website.md](../design/website.md)). A hosted analytics vendor would add a row to the table above and a name to the page customers' legal teams read, in exchange for a dashboard. Not worth it — and the discipline is worth more than the tool, because the second exception is always easier to make than the first.

Two properties follow, and both are worth stating on the trust page rather than only here: **no cookies means no consent banner** — the requirement attaches to setting them, not to counting visits — and no analytics ever runs in a customer's deck: the exported file makes zero network requests, and a browser test proves it ([../techstack/frontend.md](../techstack/frontend.md)).

**AI inference providers are now among the most-questioned items in DPA negotiations.** Being able to answer precisely — which providers, under what retention, with ZDR enforced how — is a sales asset well before it is a compliance one.

## An error tracker is the one that will actually leak

Named separately because it is configuration rather than architecture, which means it fails silently and by default.

None is adopted in v4 yet; this is for the day one is. Error trackers capture request bodies. A request body here is a brief. Scrubbing is server-side, configured **before the first event is sent**, and verified by looking at real captured events rather than by reading the config.

The check already exists in [testing.md](testing.md): a canary string seeded in a brief must appear in no log, ledger or error report. This is the doc that says why it is on that list.

## What to do about the ones you cannot avoid

The host and the database hold data because they run the product. The controls are the ordinary ones: encryption at rest, credentials scoped per process ([infrastructure.md](infrastructure.md)), and cascade delete that works ([tenancy-and-data.md](tenancy-and-data.md)).

The one thing worth adding: **know where the data physically is.** Region choice for the database and object storage is a compliance input, not just a latency one, and it is far easier to choose than to change.
