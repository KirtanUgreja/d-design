# AI Authorship

Most of this codebase will be written by Claude. That is a deliberate choice — it is the only way one person ships v1 through v3 — and it changes which mistakes are likely. This doc is about those mistakes.

Everything else in this directory would be reasonable rules for a hand-written codebase too. This one exists only because of how the code gets written.

## What actually goes wrong — measured

The 2026 industry data is consistent across independent sources, and the shape of it is not what most people assume.

| | Change |
|---|---|
| Code-block duplication | **up 81%** |
| Within-commit copy/paste | up 41% |
| Copy-pasted share of new code | 9.4% (2022) → **15.7%** (H1 2026) |
| Moved / properly refactored code | 21% (2022) → **3.8%** |
| Cross-file function calls (reuse) | **down 35%** |
| Refactoring line moves | down 70% |
| Two-week code churn | up 15% |
| Defect rate vs human-written | **1.7×** |

> **The failure mode is not bad code. It is duplicated code.**

An AI asked to add a retry does not go looking for the retry you already have three folders over — it writes a correct new one. Every individual output is defensible. The aggregate is a codebase with four retry helpers, three date formatters, and two subtly different clamps, and no single commit where that was the wrong call.

The other number worth internalizing: **about 66% of developers report AI output is "almost correct"** — close enough to merge, wrong enough to need rework. Not obviously broken. Obviously broken is cheap; it fails the typecheck and you fix it in ten seconds. *Almost* correct is the expensive class, and it is the class that gets merged.

## Why this project is unusually exposed

Three of its properties make the duplication failure worse than average:

- **Solo.** There is no second person who says "we already have that." That role has to be played by tooling or by you, deliberately.
- **Feature folders.** [structure.md](structure.md) is right for humans and slightly hostile here — a feature folder is a context boundary, and an AI working inside `editor/` has no particular reason to notice that `renderer/` already solved the same problem. The structure that keeps *you* oriented also narrows the model's field of view.
- **Nobody is watching the aggregate.** Duplication is invisible per-commit and only visible per-quarter. Solo, nobody is running the per-quarter look.

## Why it is also unusually protected

The rules in this directory were written for clarity. They happen to be exactly the right defenses:

| Rule | What it stops |
|---|---|
| Types derived from Zod ([typescript.md](typescript.md)) | The most damaging duplication of all — a second definition of a core shape — is *unrepresentable*, not merely discouraged |
| One renderer, no mode branches ([patterns.md](patterns.md)) | A second "publish-flavored" renderer, which is precisely the thing an AI would helpfully write |
| Feature public APIs (`index.ts`) | Gives the model a short, readable catalog of what already exists. A good index is a duplication defense |
| The dependency ledger ([dependencies.md](dependencies.md)) | Stops the other direction — a package added for something already in the tree |
| `Result` as the one error type | No parallel error-handling convention per feature |

The pattern: **make the canonical thing easy to find and the duplicate hard to write.** That is cheaper than review, and it is the only defense that works while you sleep.

## The four working rules

**1. Name the existing thing in the prompt.** The single highest-leverage habit. "Add retry to the build call" invites a new helper; "add retry to the build call using `lib/retry.ts`" does not. Rung 2 of the ponytail ladder — *already in this codebase?* — is the rung an AI skips by default, because it cannot see the codebase you can.

**2. Run a duplication check in CI, on changed files only.** `jscpd` or equivalent, warning-level, scoped to the diff. Not a gate — a signal. Ten seconds of CI against the one metric that degrades silently and is expensive to reverse. It fires rarely and is worth reading every time it does.

**3. `lib/` is a place to look before it is a place to add.** Before writing a helper, grep for it. If it exists, use it. If two near-identical things now exist, delete one — deletion is the refactoring move the data says has nearly stopped happening, and it is the one that matters most.

**4. Read the diff where "almost correct" is expensive.** You cannot review everything solo, and pretending otherwise means reviewing nothing. Read these properly; skim the rest:

- **the scene schema** — every downstream guarantee is a consequence of this shape
- **`*.data.ts` files** — the service-role filter and the RLS assumption are security-critical, and a missing `where` clause is textbook almost-correct ([../security/tenancy-and-data.md](../security/tenancy-and-data.md))
- **the no-styling backstop and the AD linter** — a check that is subtly too permissive still passes its own tests
- **anything touching the sandbox, the sanitizer, or a signed URL**
- **character-budget arithmetic** — an off-by-one here breaks localization in twelve languages at once
- **every `ponytail:` comment in the diff** — that is the author flagging a known ceiling; it is the cheapest signal in the codebase

Everything else — intake forms, settings UI, the outline editor — gets a skim and the gate. If it typechecks, lints, and works, it is fine.

## Review is the constraint now, not writing

CircleCI's 2026 data: feature-branch throughput up 59% year over year, while median main-branch throughput *fell*. Teams got much faster at producing code and no faster at deciding it was safe to merge.

Solo, that bottleneck is one person, and it is the actual limit on this project's speed — not typing, not model latency, not tokens ([../v1/ai-pipeline.md](../v1/ai-pipeline.md) puts a full experience at ~$0.20).

Two consequences, and they are why [tooling.md](tooling.md) exists in the form it does:

- **Every rule that a machine can check must be checked by a machine.** Each one is review capacity handed back to you. This is the whole reason the three custom lint rules are worth writing.
- **Small diffs, merged often.** A 2,000-line generated PR does not get reviewed, it gets approved. Ship the change that fits in your head, which is also the change the model edits most reliably.

## Instruction files: AGENTS.md is the source, CLAUDE.md imports it

`AGENTS.md` is now an open standard stewarded by the Agentic AI Foundation under the Linux Foundation, read natively by Codex, Cursor, Copilot, Gemini CLI, Aider, Windsurf, and Zed — 60,000+ repositories.

**Claude Code reads `CLAUDE.md`, not `AGENTS.md`.** Per Anthropic's May 2026 docs, a repo that has both should make `CLAUDE.md` import `AGENTS.md`.

So: `AGENTS.md` carries the rules, `CLAUDE.md` is three lines that import it plus anything Claude-specific. One source of truth — the same idea as everywhere else in this directory — and the project stays portable if the tool changes. See [tooling.md](tooling.md) for the content.

## Test

- CI reports duplication on changed files; the number is looked at, not gated on
- No shape in `schema/` has a hand-written type beside it
- `rg 'ponytail:'` returns a readable ledger, not a graveyard
- Every feature's `index.ts` is short enough to read in one screen — if it is not, the feature is doing too much and the model's catalog just got worse
