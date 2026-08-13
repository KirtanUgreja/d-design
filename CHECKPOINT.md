# v1 checkpoint — 2026-08-13

Resume point. Working tree is clean at `cf9b680` on branch `phase-04-three-art-directions`.

## What is done

All nine v1 planes are built, committed, and the gate is green through every commit:

| Phase | Status |
|---|---|
| 00 foundations | done — three trees (api/web/render), 12 design families, 12 archetypes, gate |
| 01 schema | done — Pydantic Deck/Outline/Brief, codegen → TS+Zod, no-styling backstop |
| 02 interview | done — real seam (httpx → OpenRouter), Outline with claim provenance, CLI |
| 03 mapping | done — outline → per-slide Deck, archetype distribution check, through-line |
| 04 slide-builder | done — one model call per slide, image seam action, data-URI assets |
| 06 renderer | done — pure mode-free React renderer, family tokens, renderer-scoped lint bans |
| 05 export | done — single-file HTML, connect-src 'none', nav shell, esbuild bundling |
| 07 visual-review | done — human loop, per-slide revision with written feedback |
| 08 acceptance | done — 5 golden briefs, fingerprint variety metric, headless runner |

Then `cf9b680` — the **first live end-to-end run** with real model calls, which found and fixed two live-only defects:

- **`api/ai/complete.py` → `_strict_schema()`**: OpenRouter's strict providers (OpenAI/Azure) reject Pydantic's raw JSON Schema. The seam now adds `additionalProperties: false` and every property into `required` before sending.
- **`api/schema/deck.py` → `ChartSeries`**: chart series was `list[tuple]` (→ `prefixItems`, rejected); now a small object.

## Verified, not just built

A golden brief ran live through the whole pipeline and produced `samples/crm-launch-deck.html` (9 slides, vivid-flat family, 8 distinct archetypes, 11 KB single file). Browser verification (agent-browser, Chrome 152):

- Renders from `file://` with the family's design (cream, bold sans headline)
- Navigation works: Next button, ArrowRight, End key, counter "9 / 9"
- **Zero network requests** — the only request is the `file://` document itself
- CSP `connect-src 'none'` confirmed live in the loaded page

## The gate (must stay green)

```
./scripts/hooks/pre-commit        # api: ruff+mypy · web: prettier+eslint+tsc · render: prettier+tsc+vitest · schema no-diff · invariants
./scripts/check-docs.sh           # links resolve, every .md indexed
```

59 Python tests + 19 render tests. Schema regenerates with no diff.

## How to run the pipeline

Requires `OPENROUTER_API_KEY` in `.env` (present, gitignored). From `api/`:

```
uv run python cli.py interview --topic "..." --slides 8 ...   # → approve outline
uv run python cli.py mapping --outline outline.json          # → deck.json
uv run python cli.py build --deck deck.json                  # → built.json
uv run python cli.py review --slide 2 --feedback "..."       # per-slide revision
cd ../render && pnpm export <built.json> <out.html>          # → single-file HTML
```

## Natural next steps (not started)

- **Fontsource data-URI embedding** — the exported file uses system font stacks; the plan's follow-up is embedding the family faces as data URIs to keep the offline guarantee with real type.
- **Real-browser `connect-src` assertion in CI** — currently a static test; the plan specs a Playwright/browser check of zero requests from `file://`.
- **Images in the live run** — the golden run produced 0 images; a deck with an image block would exercise `ImageSeam.generate` live.
- **The eval harness growth** — golden briefs → Promptfoo structural evals (ai-stack.md).
- **DSPy trigger** — 50+ scored briefs and hand-tuning Build prompts.
- **The product name** — decided before phase 09 per decisions.md.

## Tooling notes

- agent-browser installed globally (Chrome 152): `agent-browser open <url>` / `snapshot` / `click @eN` / `network requests`. Use a named session: `export AGENT_BROWSER_SESSION="$(agent-browser session id --scope worktree --prefix X)"`.
- pnpm 11: build-script allowlist lives in each package's `pnpm-workspace.yaml` (`allowBuilds: { esbuild: true }`), not package.json.
- The invariants script activates when `api/` or `web/` exists — it's live now and passing.
