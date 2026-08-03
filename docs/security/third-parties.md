# Third Parties

Where customer data actually goes.

[tenancy-and-data.md](tenancy-and-data.md) says **no prompts, no outputs** — and means it about *your* logs. But every prompt goes to a model provider by definition, every error goes to Sentry, every published page sits in someone's object store. The rule covered the half of the problem you control and was silent on the half you do not.

This matters more here than in most products because of what the data is: **a customer's unreleased launch messaging, frequently under embargo.** Plausibly the most confidential thing they will ever hand a vendor.

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

### The three settings that matter

| | |
|---|---|
| **Zero Data Retention** | ZDR routes only to endpoints whose provider will not store the data, and a ZDR provider cannot train on it either. Configurable **account-wide, per model group, and per request** (`zdr`). **It is a setting, not a default** |
| **Prompt logging** | Opt-in. Enabling it grants OpenRouter an *irrevocable right to commercial use* of those inputs and outputs. **Never enable it on this account** |
| **EU in-region routing** | Available on enterprise. Prompts and completions stay inside the EU — relevant given the customer base implied by [../v3/localization.md](../v3/localization.md) and the AI Act posture in [../v3/compliance.md](../v3/compliance.md) |

### The rules

1. **ZDR is on account-wide, and set per request as well.** Belt and braces, because an account setting is one console click away from being off and a per-request parameter is in the diff.
2. **A model is only usable if a ZDR route exists for it.** That is a selection criterion alongside the four in [../techstack/ai-stack.md](../techstack/ai-stack.md) — and it is the one that is not negotiable, because it is the customer's data rather than your quality bar.
3. **Prompt logging stays off, permanently.** Add it to the release checklist so a future convenience does not switch it on.
4. **The eval and tracing stack does not leak around this.** Self-hosted Langfuse was chosen precisely so traces stay on your infrastructure ([../techstack/ai-stack.md](../techstack/ai-stack.md)); a hosted eval platform ingesting full traces would reintroduce everything this section prevents.

**This is a real cost of the OpenRouter decision and it belongs next to the other one.** [../techstack/decisions.md](../techstack/decisions.md) already records that OpenRouter trades away decoder-level schema enforcement. It also trades a single, auditable data-processing relationship for a routed one. Both are acceptable; neither should be discovered later.

## The full subprocessor list

Not bureaucracy — a legal obligation the moment there are EU publishers, and a question every serious customer will ask.

**Under GDPR Article 28 you are a processor** (your publishers are the controllers for their recipients, per [../v3/personalization.md](../v3/personalization.md)). That means: authorization before engaging a subprocessor, equivalent data-protection obligations flowed down, and **you remain liable for their compliance.**

| Subprocessor | Sees | Sensitivity |
|---|---|---|
| **OpenRouter + routed providers** | Briefs, scene content, transcreation source and target | **Highest.** Embargoed customer messaging |
| **AWS** (RDS, S3, Fargate, KMS) | Everything at rest, including `recipients` | Highest, but encrypted and under your keys |
| **Vercel** | Requests to the app, including editor traffic | High |
| **Better Auth** | Self-hosted — users are in *your* Postgres | None. Not a subprocessor, which is a point in its favour |
| **Resend** | Email addresses, and recipient links if delivery is ever added | Medium |
| **Sentry** | Whatever is not scrubbed | **Medium, and entirely dependent on configuration** |
| **Langfuse** | Self-hosted. Nothing leaves | None, if it stays self-hosted |

Three obligations follow, and all three are cheap now and expensive to retrofit:

- **Publish the list at a stable URL**, with a general-authorization clause in the DPA pointing at it and a notification procedure for additions. This is the standard mechanism and it is what customers' legal teams look for.
- **Verify the training claim per provider**, do not assume it. "Enterprise API tiers do not train on your data" is usually true and is exactly the kind of usually that a DPA negotiation exists to pin down.
- **A new subprocessor is a decision, not a config change.** Adding a hosted eval tool, an analytics vendor, or a second model gateway is the same category of act as adding a dependency ([../coderules/dependencies.md](../coderules/dependencies.md)) — and the blast radius is larger, because it is your customers' data rather than your build.

**AI inference providers are now among the most-questioned items in DPA negotiations.** Being able to answer precisely — which providers, under what retention, with ZDR enforced how — is a sales asset well before it is a compliance one.

## Sentry is the one that will actually leak

Named separately because it is configuration rather than architecture, which means it fails silently and by default.

Error trackers capture request bodies. A request body here is a Brief. Scrubbing is server-side, configured **before the first event is sent**, and verified by looking at real captured events rather than by reading the config.

The check already exists in [testing.md](testing.md) — *"`generations`, app logs, and error reports contain no prompt, scene, or recipient content"*. This is the doc that says why it is on that list.

## What to do about the ones you cannot avoid

AWS and Vercel hold data because they run the product. The controls are the ordinary ones and they are already specified elsewhere: KMS with keys you control ([infrastructure.md](infrastructure.md)), envelope encryption for integration credentials, no PII in `views`, cascade delete that works ([tenancy-and-data.md](tenancy-and-data.md)).

The one thing worth adding: **know where the data physically is.** Region choice for RDS and S3 is a compliance input, not just a latency one, and it is far easier to choose than to change.
