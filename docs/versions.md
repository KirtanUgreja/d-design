# How a version is documented

The rule this corpus is rebuilt on, after the first one was cleared on 2026-08-10:

> **A version directory answers what gets built and why. It is deleted and rewritten when the vision changes, and nothing outside it depends on it.**

`coderules/`, `security/`, `techstack/` and `design/` are **current**, not versioned — they survive a vision change because they are about how code is written, what the threats are, what runs where, and what our own surfaces look like. A version directory is about the product, and the product is allowed to be reborn.

---

## The directory

```
docs/vN/
  README.md          the map. What this release is, its files, where to find things
  spec.md            what gets built and why. Decisions, bets, risks
  plan/
    README.md        status table, dependency graph, build order
    NN-<slug>.md     one phase per file
  <topic>.md         a subsystem that needs more than a spec section
```

**Four required files**: `README.md`, `spec.md`, `plan/README.md`, and at least one phase. Topic docs are added only when a spec section outgrows the spec.

---

## What each file owns

### `README.md` — the map, never the content

A table of every file with one line on what is in it, and a **"find it fast"** table mapping questions people actually ask to a file *and a section*. This is the only navigation aid that survives a corpus getting large; a list of filenames does not.

**Never** put a decision here that is not also in `spec.md`. A README that argues is a second spec that will drift.

### `spec.md` — decisions and their reasons

The load-bearing file. Five sections, in this order:

| Section | Holds |
|---|---|
| **Theme** | One paragraph. What this release proves that the last one did not |
| **Commitments vs bets** | Two tables. A commitment is true regardless of user feedback; a bet has a stated thing that would disprove it. **Every bet names its falsifier** |
| **Locked decisions** | Axis · decision · why. One row per decision. The "why" is the point — a decision without one gets re-litigated every quarter |
| **What changes from the last version** | Old · new · why. The delta, not a restatement |
| **Risks** | Numbered, and each one either gets retired with evidence or stays open |

**Never** put implementation detail here. If it names a file or a function, it belongs in a phase.

### `plan/README.md` — status and order, nothing else

- **Status table**: one row per phase, `not started` · `in progress` · `done` · `blocked — <why>`
- **Dependency graph**: what blocks what, as ASCII. This is the authority on order, **not the phase numbers**
- **Recommended build order**: the graph flattened, with any non-obvious placement defended in a sentence

> **A phase number is a filename, not a position.** Renumbering to insert a phase breaks every cross-reference in the corpus and buys nothing. New phases append; the graph says where they actually go.

**Status lives in exactly two places**: this table says which phase you are in, the phase's own exit-gate checklist says how far through it you are. Never copy status between them.

### `plan/NN-<slug>.md` — one phase, one sitting

The anatomy that works, and the order matters:

```markdown
# Phase NN — <name>

> One paragraph: what this phase makes true that was not true before.

**Depends on:** [..] · **Blocks:** [..] · **Spec step:** ..

## Search
**Read first** — docs to read, with the section that matters
**Grep for** — the exact symbols and files this phase touches, and what to notice about each
**Verify externally** — platform facts to re-check, because a doc written months ago may be wrong

## Make
The files created or changed, then the design decisions with their reasons.

## Verify
Checkboxes. The gate, then the phase's own claims, then **Human** —
the checks that need a person to look at something.

## Skipped
Not built · trigger. Every deliberate omission and what would reverse it.

## Exit gate
The checklist that decides whether this phase is done.
```

**Three properties this shape has that a task list does not:**

- **Search before Make** stops the measured failure mode of AI-written code — a second copy of something that already exists.
- **Skipped with a trigger** turns "we didn't do that" into a decision with a reversal condition, instead of a gap nobody owns.
- **Human checks** exist because the automated gate verifies *structure*, and most real defects are *presentational*. A phase whose Verify section has no human check is usually a phase that has not thought about what it looks like.

---

## Conventions

**Superseding a decision.** Do not delete it. Strike it and say what replaced it and why:

```markdown
| ~~Unit~~ | ~~Scroll sections first~~ → **slides first** | ~~Matches wedge~~ **Superseded 2026-08-10.** <what it cost> |
```

The record of what was believed is worth more than a tidy table — it is how you find out *why* a wrong turn looked right at the time. **Exception:** when a whole version is being rewritten rather than corrected, delete it. Strikethrough is for corrections inside a live version; a version being reborn is not a correction.

**Every claim about the platform carries its date and status.** "Baseline since Oct 2025", "~87% support", "in force 2 August 2026". A capability claim without a date is unverifiable a year later, and platform facts are the ones most likely to be silently wrong.

**Numbers, not adjectives.** "6 font families" and "53% of an art direction is identical" are checkable. "Limited variety" is not, and cannot be argued with or fixed.

**A finding gets written where it will be read.** A lesson learned in phase 4 that binds phase 12 belongs in phase 12's file, not only in phase 4's retrospective.

---

## The invariants

Enforced by `./scripts/check-docs.sh`, which must pass before any commit touching `.md`:

1. Every relative link resolves
2. Every `.md` is listed in its directory's `README.md`
3. Every `docs/` subdirectory is listed in `docs/README.md` and has its own `README.md`

**Paths in `AGENTS.md` are pointers, not imports.** They are never prefixed with `@` — that inlines the whole corpus into every session.

---

## When to start a new version rather than extend one

Extend when the change is a feature, a fix, or a decision reversed with its reason recorded.

**Start fresh when the answer to "who is this for and what is the artefact" changes.** At that point the old directory is not a document that needs correcting — it is a record of a different product, and every strikethrough you add makes the live decisions harder to find. Delete it, write the new one, and let git hold the history.

That is what happened on 2026-08-10, and this file exists so the next one is cheaper.
