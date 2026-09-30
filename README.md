<div align="center">

# ✦ d-design

### AI presentation engine

*The model designs every slide in real HTML. One offline file comes out.*

<br/>

<img src="https://img.shields.io/badge/status-v4%20planned-F4B740?style=for-the-badge&labelColor=08090B" alt="Status: v4 planned">
<img src="https://img.shields.io/badge/deployed-no-F4B740?style=for-the-badge&labelColor=08090B" alt="Deployed: no">
<img src="https://img.shields.io/badge/phase-21%20reset-4C9AFF?style=for-the-badge&labelColor=08090B" alt="Phase: 21 reset">
<img src="https://img.shields.io/badge/builder-solo%20%2B%20AI-A78BFA?style=for-the-badge&labelColor=08090B" alt="Builder: solo + AI">

</div>

<br/>

> [!NOTE]
> **This repository was reset to zero on 2026-08-10, and rebuilt.** The product code and the `v1`/`v2`/`v3` documentation were deleted — not abandoned, deleted deliberately — because the product was being re-decided from the vision up. What replaced them is described below and in `docs/v1/`, `docs/v2/`, `docs/v3/`; it runs end to end locally.
>
> **Everything is in git history.** The two commits before the reset hold the deleted system and its full specification.


> [!NOTE]
> **Re-decided on 2026-09-26.** Three releases built a pipeline, an editor, accounts and billing, and every generated deck still came out as a bold heading and one line of text on a flat background. The cause was a rule this README used to open with: *the AI never writes styling*. It is reversed. The plan is [`docs/v4/`](docs/v4/README.md); the v3 code still in this tree is deleted by its first phase.

---

## What it is

An AI presentation maker for **founders and salespeople presenting live**. You type a brief. You get a deck that looks designed and says something, as **one `.html` file that runs offline** — no network requests, fonts and images inside.

| | |
|---|---|
| 🎨 **The model designs** | Each slide is composed in real HTML and CSS. Colour and type come only from the deck's own design system; layout is free |
| 🔍 **Every slide is checked** | Rendered in Chromium and measured — overflow, collisions, contrast, type size — then repaired or flagged. Never shipped broken |
| 📚 **Every number has a source** | Web research with citations plus what you paste. Anything unsourced is flagged for you |
| 🎲 **No two decks alike** | A seeded sampler picks type pairing, palette strategy, grid and motif from ~40 embedded open-licence fonts |
| 🚫 **No AI look** | No gradients, neon, blur, glow, icon cards or emoji. Texture carries colour |

## The flow

```
brief ─► interview (≤5 questions, skippable) ─► research (cited facts)
      ─► storyline            ⏸ you edit and approve the outline
      ─► 3 looks              ⏸ you pick one, or shuffle
      ─► slides composed in parallel ─► checked in a real browser ─► repaired
      ─► editor ─► present · download .html · PDF
```

```
api/   Python · FastAPI     the engine, the data, the export        (docs/v4/engine.md)
web/   Next.js · TypeScript the app — UI only, it never builds a slide
bench/ 12 briefs, baselines, and the wall a human scores            (docs/v4/bench.md)
```

## Where things stand

| Phase | | Status |
|---|---|---|
| 21 | Reset: delete the v3 code, new gate, the bench | in progress — docs done |
| 22 | **Engine spike — the make-or-break gate** | not started |
| 23–25 | Design system · content engine · composition and QA | not started |
| 26–28 | Player and export · the app · the editor | not started |
| 29 | Accounts and deploy — last, on purpose | not started |

Status lives in [`docs/v4/plan/README.md`](docs/v4/plan/README.md). **No phase closes until a human has scored its wall of decks.**

## Docs

<table>
<tr><th align="left">Path</th><th align="left">What it covers</th></tr>
<tr><td>🗺️ <a href="docs/v4/README.md"><b>docs/v4</b></a></td><td>The plan: spec, engine, content, design engine, bench, phases 21–29</td></tr>
<tr><td>📐 <a href="docs/coderules/README.md"><b>docs/coderules</b></a></td><td>How the code stays consistent when an AI writes most of it</td></tr>
<tr><td>🛡️ <a href="docs/security/README.md"><b>docs/security</b></a></td><td>Threat model and every control, routed by threat</td></tr>
<tr><td>🧰 <a href="docs/techstack/README.md"><b>docs/techstack</b></a></td><td>What runs where, which model, and why each was chosen</td></tr>
<tr><td>🎨 <a href="docs/design/README.md"><b>docs/design</b></a></td><td>How <b>our own</b> app and site look — never what the engine produces</td></tr>
<tr><td>🔬 <a href="docs/findings.md"><b>docs/findings.md</b></a></td><td>Evidence: what the audit measured, model behaviour, the category</td></tr>
</table>

**[`docs/README.md`](docs/README.md) is the index.** `AGENTS.md` is the contract any agent working here reads first.

## Working here today

```
./scripts/setup.sh               installs hooks and dependencies — run once per clone
./scripts/check-docs.sh          every link resolves, every file is indexed
./scripts/hooks/pre-commit       the gate, on demand
```

The v3 stack (`docker compose up -d`) still runs until phase 21 removes it. It is not a starting point.


---

<div align="center">

*Gamma reached ~$100M ARR by making presentations **faster**.*<br/>
*This bets that people will pay for presentations that are **better**.*<br/>
*Tome bet the same thing and lost — see [`docs/findings.md`](docs/findings.md) → "The category" before building.*

</div>
