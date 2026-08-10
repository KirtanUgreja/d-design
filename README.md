<div align="center">

# ✦ d-design

### AI presentation engine

*The AI emits content and intent. It never writes styling.*

<br/>

<img src="https://img.shields.io/badge/status-rebuilding%20from%20zero-F4B740?style=for-the-badge&labelColor=08090B" alt="Status: rebuilding from zero">
<img src="https://img.shields.io/badge/code-none%20yet-64748B?style=for-the-badge&labelColor=08090B" alt="Code: none yet">
<img src="https://img.shields.io/badge/docs-cross--cutting%20only-4C9AFF?style=for-the-badge&labelColor=08090B" alt="Docs: cross-cutting only">
<img src="https://img.shields.io/badge/builder-solo%20%2B%20AI-A78BFA?style=for-the-badge&labelColor=08090B" alt="Builder: solo + AI">

</div>

<br/>

> [!WARNING]
> **This repository was reset to zero on 2026-08-10.** The product code and the `v1`/`v2`/`v3` documentation were deleted — not abandoned, deleted deliberately — because the product is being re-decided from the vision up.
>
> **Everything is in git history.** The two commits before the reset hold the complete working system and the full specification.

---

## What was deleted, and why

A working system: a FastAPI backend, a Next.js frontend, a Pydantic-owned scene schema with TypeScript types and a Zod validator generated from it, a four-phase AI pipeline with a human approval gate, three art directions rendering the same scene tree with no branch in the renderer, and a passing end-to-end acceptance run. Roughly 316 files, plus 84 specification documents.

None of it was broken. The problem was upstream of the code: three releases of decisions had each corrected the one before, until finding a live decision meant reading the history of a dead one — and the framing underneath all of them was being changed rather than patched.

**A product whose *"who is this for, and what is the artefact"* has changed is not a document that needs correcting.** Improving it incrementally converges on a better version of the wrong thing.

---

## What survives

Everything true regardless of what the product turns out to be.

<table>
<tr><th align="left">Path</th><th align="left">What it covers</th></tr>
<tr><td>📐 <a href="docs/coderules/README.md"><b>docs/coderules</b></a></td><td>How the code stays consistent when an AI writes most of it</td></tr>
<tr><td>🛡️ <a href="docs/security/README.md"><b>docs/security</b></a></td><td>Threat model and every control, routed by threat</td></tr>
<tr><td>🧰 <a href="docs/techstack/README.md"><b>docs/techstack</b></a></td><td>What runs where, which model, and why each was chosen</td></tr>
<tr><td>🎨 <a href="docs/design/README.md"><b>docs/design</b></a></td><td>How <b>our own</b> app and site look — never what the engine produces</td></tr>
<tr><td>🧭 <a href="docs/versions.md"><b>docs/versions.md</b></a></td><td>How a version is documented — required files, phase anatomy, when to start fresh</td></tr>
<tr><td>🔬 <a href="docs/findings.md"><b>docs/findings.md</b></a></td><td>Evidence, not direction — measurements, model behaviour, the category, dated platform facts</td></tr>
</table>

**[`docs/README.md`](docs/README.md) is the index.** [`AGENTS.md`](AGENTS.md) is the contract any agent working here reads first.

---

## The one thing carried over

The constraint the project exists to test, kept because it is the reason there is a project:

> **The AI never writes styling.** It emits content and intent — `motion: "reveal"`, `emphasis: "hero"` — and a separate token layer resolves that into type scale, spacing, colour, easing and duration.

```jsonc
// ✅ what the AI emits — meaning only
{ "type": "Headline", "props": { "text": "Ship in minutes", "emphasis": "hero" }, "motion": "reveal" }

// ❌ the schema has no field for any of this
{ "fontSize": "4rem", "color": "#F4F4F5", "duration": "900ms", "ease": "expo-out" }
```

It is checkable, and in the deleted codebase it was checked — a test walked every block in a generated tree and failed on anything matching `/#[0-9a-f]{3,8}|[\d.]+(px|rem|em|ms|s)\b/i`.

**Whether it survives the new vision is a decision that has not been made yet.**

---

## Working here today

```
./scripts/setup.sh               installs the git hooks — run once per clone
./scripts/check-docs.sh          every link resolves, every file is indexed
./scripts/hooks/pre-commit       the gate, on demand
```

No local infrastructure, no CI. Both were specific to the deleted stack and get rewritten for whatever comes next.

```
d-design/
├── README.md            you are here
├── AGENTS.md            the contract — rules + a task→doc routing table
├── CLAUDE.md            one line: @AGENTS.md
├── docs/                what survives a vision change
└── scripts/             setup · check-docs · the gate · invariants · hooks
```

---

<div align="center">

*Gamma reached ~$100M ARR by making presentations **faster**.*<br/>
*This bets that people will pay for presentations that are **better**.*<br/>
*Tome bet the same thing and lost — see [`docs/findings.md`](docs/findings.md) → "The category" before building.*

</div>
