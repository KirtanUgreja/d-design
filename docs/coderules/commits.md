# Commit messages

A commit message answers the one question the diff cannot: **why**. Everything else in here exists to make that answer findable six months later, by someone who does not remember the day.

## The format

```
Subject — what changed, and what it found

What was wrong, and what the project can do now that it could not before.
Two or three sentences. This is the part no tool can reconstruct.

path/to/file.ext:88-140 · symbolName()
  What was wrong in this file, and what it does instead.

path/to/other.ext:12-19 · otherSymbol()
  Same, for this one.
```

Four parts, each earning its place:

| Part | Rule |
|---|---|
| **Subject** | ≤72 characters, imperative or noun phrase, **no trailing period**. Name the change *and* what it turned up — `"the slide lint, and the three defects it found"` beats `"add linter"` |
| **Body** | Why. The problem, and the project-level consequence. Required when more than one file changed |
| **File list** | One block per file. Path, an anchor, and one or two lines on the problem and the fix **for that file** |
| **Trailers** | **None.** No `Co-Authored-By`, no `Signed-off-by`, no "Generated with" |

## Line numbers go stale; symbols do not

This is the one place the format deviates from the obvious design, and the reason matters.

A commit message is **immutable**, and line numbers are **not stable**. The moment a later commit inserts a line above, `palette.py:88-140` points at the wrong place — and unlike a stale comment, nobody will ever fix it, because rewriting history to correct a line number is absurd. A year on, the numbers in old commits are confidently wrong, which is worse than absent.

So the anchor is **both**, and they do different jobs:

```
api/engine/design/palette.py:88-140 · check_contrast()
```

- **`88-140` is for today.** It helps whoever reads this in review this week jump straight there. It is a convenience, not a record.
- **`check_contrast()` is for later.** It survives insertions, reformatting and moves, and `git log -S check_contrast` finds every commit that ever touched it.

**Trust the symbol, not the number, in any commit older than about a week.**

If a change has no symbol — a config value, a doc paragraph, a data fixture — name the key or the heading instead: `· POSTGRES_VERSION`, `· "The frame"`. Something a reader can search for.

If a change is scattered across a dozen small hunks in one file, give the symbol names and skip the ranges. A list of eleven ranges is noise pretending to be precision.

## Scale the ceremony to the change

A rule nobody can follow under pressure is a rule that gets bypassed, and a bypassed rule is worse than none.

| Change | What it needs |
|---|---|
| Typo, one line, obvious | Subject only |
| One file, non-obvious why | Subject + body |
| More than one file | Subject + body + file list. **Enforced** |
| Mechanical across many files (rename, format, codemod) | Subject + body + **name the pattern, not every file** — "all 40 call sites of `oldName`". Say it is mechanical so a reviewer knows to skim rather than read |

## No trailers, and what that does *not* mean

The message carries no `Co-Authored-By`, no `Signed-off-by`, no tool attribution.

**Git still records an author.** That is the `author` and `committer` metadata from `git config user.name` / `user.email`, and it is how git works — it is not something a message convention can remove, and it is not what this rule is about. What is dropped is **attribution inside the message body**, which is noise in a solo repository: `git log --format='%an'` already answers "who", and a trailer naming a tool answers a question nobody asked.

If this repository ever has more than one human committer, revisit this — trailers are how co-authorship is credited on a shared history, and the reason to drop them now is that there is nothing to credit.

## Branches

One branch per phase, named `phase-NN-slug` after the phase file in ../v4/plan/README.md. v4 continues the numbering (2026-09-26):

```
phase-21-reset            phase-24-content-engine     phase-27-app-create-flow
phase-22-engine-spike     phase-25-composition-qa     phase-28-editor
phase-23-design-system    phase-26-player-export      phase-29-accounts-deploy
```

A phase branch merges to `main` when the gate is green **and** the phase's exit gate is met, which in v4 includes the owner's wall score ([tooling.md](tooling.md)). Push only when asked.

## Worked example

```
Delete the CI workflow and local infrastructure

Both were built for the stack that was deleted: the workflow ran the gate
against api/ and web/, and docker-compose started a render service that
built from web/src. New ones get written for whatever the new app becomes.

scripts/setup.sh:1-27 · the whole file
  Every step pointed at something gone — uv sync, pnpm install, docker
  compose, alembic upgrade. Stripped to `git config core.hooksPath`,
  which is not stack-specific and is what makes the hooks run at all.
  A clone without it has no gate and nothing says so.

docs/coderules/tooling.md:47 · "What CI runs, across five repos"
  Read as a description of something running. Now says plainly that no
  CI exists, so the section is a specification to rebuild.
```

## What the hook enforces, and what it cannot

`scripts/hooks/commit-msg` fails a commit that breaks any of:

- Subject longer than 72 characters, or ending in a period
- A body that does not start after one blank line
- Any forbidden trailer
- More than one file staged with no body
- More than one file staged and no staged path named anywhere in the message

**It cannot check whether the *why* is any good**, which is the only part that matters. Merges, reverts, fixups and squashes are exempt — their messages are generated, and rejecting them teaches you to pass `--no-verify`, which is how a gate stops meaning anything.
