# AI Transparency Compliance

**This is not legal advice.** It is a summary of a regulation that came into force two days before this document was written, affecting a product whose entire output is AI-generated. Get counsel before v3 ships to EU users. The purpose here is to make sure the *architecture* can satisfy the obligation, because retrofitting content marking into a publishing pipeline is far worse than designing for it.

## What changed on 2 August 2026

**EU AI Act Article 50 transparency obligations are now in force.**

The provision most relevant to this product:

> Providers of AI systems, including general-purpose AI systems, generating **synthetic audio, image, video or text content**, shall ensure that the outputs of the AI system are **marked in a machine-readable format and detectable as artificially generated or manipulated**.

Three details that matter here specifically:

| Detail | Why it lands on this product |
|---|---|
| **Text is explicitly in scope** | Not just images. Every scene's copy is generated text |
| **Translations and summaries are named** | Guidance calls out "AI-generated or AI-manipulated translations, summaries, image alterations and other modifications that materially affect the meaning or appearance of content." **v3's transcreation is precisely an AI-manipulated translation** |
| **Not limited to high-risk systems** | Article 50 applies to any AI system used in the covered situations. In practice it is relevant to every business using generative AI to produce content |

**Penalties** run up to **€15 million or 3% of global annual turnover.**

**Timing:** obligations apply from 2 August 2026. The AI Omnibus provisional agreement of May 2026 gives generative systems already on the market before that date until **2 December 2026** to meet the machine-readable marking requirement under Article 50(2). A product that has not launched does not benefit from that grace period in the same way — build it in.

## The mechanism: C2PA Content Credentials

The European Commission's **draft Code of Practice on Transparency names C2PA Content Credentials by example** as the technical mechanism for machine-readable marking.

C2PA is where the industry has converged. Current spec is **version 2.3 (February 2026)**. OpenAI's DALL·E, Adobe Firefly, Google Gemini, and Stability AI all sign outputs with Content Credentials; TikTok has labelled over 1.3 billion videos with provenance data; Google's Pixel 10 was the first phone to earn C2PA Conformance certification.

A C2PA manifest declares which AI system generated or modified the content, when it was produced, and which organisation signed the claim.

## What this product has to do

Three surfaces, three different answers.

### 1. Generated imagery — the solved case

AI-generated images get a **C2PA manifest attached at generation time**, preserved through storage and serving. This is the well-trodden path: the major image models already emit Content Credentials, and the tooling exists.

The catch is the pipeline: re-encoding an image to strip EXIF (a security control from [../security/content-and-web.md](../security/content-and-web.md)) will destroy a C2PA manifest unless the re-encoder preserves it. **These two requirements collide, and security wins by default unless someone notices.**

Concretely, the collision has an address: the re-encode runs in the **fetch worker**, via `sharp`, on every upload before the object becomes servable ([../techstack/infrastructure.md](../techstack/infrastructure.md)). That is one function in one container, which is the good news — the fix is local, and preserving a signed manifest while stripping location EXIF is a configuration of that one step rather than a pipeline redesign.

Verify manifests survive upload, re-encode, storage, and serving. **That is the specific test to write, and the one most likely to fail**, because nothing about a stripped manifest is visible in the rendered image.

### 2. Generated text — the harder case

C2PA is built primarily for images, video, and audio. Text provenance is less settled, and a published experience is HTML.

The workable approach for v3:

- **A machine-readable declaration on the published page** — structured metadata stating that the copy is AI-generated, which system produced it, and when. This is what "machine-readable and detectable" asks for, in the medium the content actually ships in.
- **Provenance recorded per block in the scene tree**, so the page-level declaration is derived from real data rather than asserted blanketly. The schema already tracks `source: 'upload' | 'generated'` on assets ([../v1/scene-schema.md](../v1/scene-schema.md)) — extend the same idea to text.
- **Human-authored copy is not synthetic content.** This is why the distinction is worth tracking: `keyMessages` come from the user and are only *arranged* by the model, while a transcreated German headline is genuinely AI-produced. Marking everything identically overstates the case and loses the signal.

The nuance to take to counsel: the pipeline's core rule is that the AI *arranges approved copy* rather than inventing claims. Whether arrangement constitutes "generating synthetic text content" is exactly the kind of question that needs a lawyer, not a confident guess in a design doc.

### 3. Transcreation — explicitly named, and the sharpest exposure

Guidance names AI-manipulated translations directly. A transcreated locale is not a mechanical translation — it is a rewrite to fit a character budget, which "materially affects the meaning or appearance of content" by the guidance's own wording.

Two consequences for [localization.md](localization.md):

- **Each locale page carries its own marking**, independent of the source locale.
- **The `needs-review` → human-approved workflow already in that design is doing double duty.** It was specified so a native speaker catches subtly wrong German. It is also the human oversight step that makes the AI-generated status of that copy a reviewed fact rather than an unexamined one.

## The second layer: a disclosure a human can see

Everything above is about machine-readable marking, which is Article 50(2). There is a second layer, and this document originally treated it as the same requirement.

**Article 50(4) is about people.** Deployers generating or manipulating published text must disclose that it was artificially generated, and the information has to reach a natural person **in a clear and distinguishable manner, at the latest at the time of first exposure**. A C2PA manifest satisfies neither adverb — it is invisible by design. So the obligation splits: a manifest in the file, and a mark on the page.

Two consequences, and both are design decisions rather than pipeline ones:

- **The visible mark and the "made with" badge are the same object.** A free-tier page would otherwise carry two small pieces of furniture in its corner saying adjacent things. One provenance line does both jobs, styled per art direction, and it is the only version of this obligation a customer would willingly leave switched on ([../design/website.md](../design/website.md)). **The badge is removable on the paid tier; the disclosure is not** — which is one boolean apart in the render path, and is the shape of defect an audit finds rather than a review
- **"At first exposure" is a placement requirement.** A mark in the footer of a twelve-scene scroll experience is not disclosure at first exposure, and this is the point where the compliance answer and the design instinct pull in opposite directions

**One exemption is worth taking to counsel rather than assuming**, because it may apply to most of what this product makes: AI-generated text that has undergone human review and editorial responsibility is outside the deployer's labelling obligation. This pipeline has a human approval gate before anything is built ([../v1/plan/07-director.md](../v1/plan/07-director.md)) and a marketer who reviews and publishes deliberately. Whether that constitutes editorial responsibility is exactly the question a lawyer answers and a design doc should not.

Note also that 50(4)'s text limb is scoped to text *published to inform the public on matters of public interest*. A product launch page is probably not that. The safe posture is to build the mark anyway and let counsel narrow it, because adding a disclosure later is a render change and retrofitting provenance data is not.

## Who is the provider, and who is the deployer

Article 50 splits obligations between providers and deployers, and this product sits awkwardly across the line:

- **The model provider** — whichever one served the call. This product routes through a seam with no preferred vendor ([../techstack/ai-stack.md](../techstack/ai-stack.md)), so the answer is per-request rather than fixed, and the router is itself a party in the chain ([../security/third-parties.md](../security/third-parties.md)).
- **This product** puts an AI system on the market under its own name — likely a provider obligation of its own.
- **The marketer publishing an experience** is a deployer with obligations toward their audience.

**Model neutrality has a compliance consequence that is easy to miss.** Retention and training terms are the union of the router's policy and the downstream provider's, they differ per route, and a route can change without the product changing. Two things follow, and both are cheap now and expensive later:

- **Record which model and which provider served every generation.** `generations` already carries model id and provider route ([../v1/spec.md](../v1/spec.md)) — that column is the audit trail for "which system produced this content", which is exactly what a machine-readable declaration has to assert.
- **Pin the acceptable routes deliberately** rather than letting a router pick freely. A provider whose terms permit training on prompts is a provider that cannot be in the path for a customer's embargoed launch messaging, regardless of how well it scores.

Getting the provider/deployer split right is a legal question with real money attached. What the *architecture* must do regardless: record provenance accurately, mark it machine-readably, and give the publishing customer the controls and information they need to meet their own obligations. Every one of those is a product decision that has to be made before launch, not after.

## The design principle this reinforces

The product already refuses to invent claims, refuses to generate the product being sold, and marks generated assets `source: 'generated'` in the editor.

Those were quality and credibility decisions. **They turn out to be the compliance posture too** — a system that already knows exactly what it generated versus what the user supplied is a system that can mark its output honestly. A system that blurred the two would now be facing a rebuild.

That is the second time this repo's quality instincts have landed on the legally-correct answer by accident. Worth noticing, and worth not undoing for convenience.

## Verification

- Generated image → C2PA manifest present after upload, re-encode, storage, and serving. **This is the test most likely to fail**, because the security re-encode strips metadata by design
- Published page → machine-readable AI-content declaration present, derived from per-block provenance rather than hardcoded
- Every locale page → carries its own marking
- Human-authored copy → not marked as synthetic (the signal has to mean something)
- A locale cannot publish without a human review step
- Published page → carries a **human-visible** provenance mark as well as the machine-readable one, and it is reachable at first exposure rather than only in the footer
- **Removing the badge on a paid plan does not remove the disclosure.** Assert it: flip the paid-tier flag on a published page and confirm the disclosure survives

## Sources

- [Article 50: Transparency Obligations](https://artificialintelligenceact.eu/article/50/) · [Practical guide](https://artificialintelligenceact.eu/transparency-rules-article-50/)
- [European Commission FAQ on Article 50](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act)
- [Preparing for compliance by 2 August 2026 — Sidley](https://datamatters.sidley.com/2026/06/24/eu-ai-act-transparency-obligations-preparing-for-compliance-by-2-august-2026/)
- [Transparency obligations for AI-generated content — HSF Kramer](https://www.hsfkramer.com/notes/ip/2026-03/transparency-obligations-for-ai-generated-content-under-the-eu-ai-act-from-principle-to-practice)
- [EU AI Act and C2PA: what Article 50 requires](https://c2paviewer.com/articles/eu-ai-act-content-credentials)
- [C2PA adoption status 2026](https://www.eyesift.com/faq/c2pa-content-credentials-2026-cryptographic-provenance-adoption/)
- [Draft Code of Practice on AI labelling — Jones Day](https://www.jonesday.com/en/insights/2026/01/european-commission-publishes-draft-code-of-practice-on-ai-labelling-and-transparency) · [The two labelling layers, and the human-review exemption](https://blog.pebblous.ai/blog/eu-ai-content-labeling-article-50-provenance/en/)
