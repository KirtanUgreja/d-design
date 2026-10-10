# Contributing to d-design

Thanks for helping. Bug reports, design feedback, new visual languages, fixes and docs are all welcome.

## Before you start

- **Small fix?** Open a pull request.
- **Bigger change** (a new pipeline step, a new dependency, a schema change)? Open an issue first so we can agree on the shape before you write it.
- Read [`AGENTS.md`](AGENTS.md) once. It holds the eleven rules every change follows, whether a person or an AI wrote it. The full reasons are in [`docs/coderules/`](docs/coderules/README.md).

## Set up

You need Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 22+ with pnpm, and an [OpenRouter](https://openrouter.ai/keys) key for live runs. The tests need no key.

```bash
git clone https://github.com/KirtanUgreja/d-design.git && cd d-design
./scripts/setup.sh          # git hooks, Python deps, Chromium
cp .env.example .env        # add OPENROUTER_API_KEY; MODEL is optional
./scripts/dev.sh            # api + worker + web on http://localhost:3000
```

## The gate

A commit lands only when the gate is green. The pre-commit hook runs it, and CI runs it again on every pull request.

```bash
./scripts/hooks/pre-commit     # ruff, mypy --strict, pytest, eslint, tsc, OpenAPI drift, docs
cd api && uv run pytest -q     # offline: fake models, real Chromium
cd web && pnpm e2e             # sign-up, sign-in and the token proxy
```

The rules the reviewers check most:

1. **Strict types.** Python passes `mypy --strict`; TypeScript has no `any` and no `!`.
2. **Model output is untrusted input.** Slide HTML is sanitized and linted where it enters. The model may use only theme tokens for colour and type.
3. **Expected failures return a `Result`.** Only bugs raise.
4. **No new dependency without a line in [`docs/coderules/dependencies.md`](docs/coderules/dependencies.md).** That includes agent frameworks.
5. **`api/engine/` stays pure.** No web framework, no environment reads. Settings come in as arguments from `api/settings.py`.
6. **Before writing a helper, search for one.** Duplication is the most common defect in AI-written code.

## Commits and pull requests

- Subject of 72 characters or fewer, no trailing period. The body says what was wrong and what the project can do now. The format is in [`docs/coderules/commits.md`](docs/coderules/commits.md).
- One concern per pull request. Include a screenshot when the change affects how a slide or the app looks: automated checks cannot judge design.
- Never commit `.env`, keys, real decks or prompts. Never log prompts or deck content.
- A live bench run costs model credit. Say in the PR if you ran one and what it cost.

## Reporting a security issue

Do not open a public issue. See [`SECURITY.md`](SECURITY.md).

By contributing, you agree that your work is released under the [MIT License](LICENSE).
