"""Promptfoo's custom Python provider for the Build pipeline
(docs/v1/plan/06-model-seam-and-build.md -> "8. The five golden briefs").

Promptfoo is a Node CLI; its Python provider hook is the documented escape
hatch for a case its declarative HTTP provider does not fit
(docs/techstack/ai-stack.md): the pipeline's unit here is a whole SSE stream
of several events, not one request/response, so this calls
`build_experience` in-process instead of re-implementing an SSE client for
eval purposes — that client already exists, tested, in
`web/src/features/generation`.

Protocol: https://www.promptfoo.dev/docs/providers/python/ —
`call_api(prompt, options, context)` returns `{"output": ...}`.

Wired into CI (.github/workflows/gate.yml). Running this makes a real,
billed OpenRouter call per scene per test case. Needs `PYTHONPATH` set to
`api/` — this module's absolute imports (`lib.result`, `config`,
`features.generation.build`) only resolve with the project root on the
path, and Promptfoo's Python worker doesn't add it for you:

    PYTHONPATH="$PWD" PROMPTFOO_PYTHON="$PWD/.venv/bin/python3" \\
        npx promptfoo@0.122.0 eval -c promptfooconfig.yaml \\
        --no-progress-bar --max-concurrency 1
"""

import asyncio
import json
from pathlib import Path
from typing import cast

from lib.result import Err
from schema.brief import Brief
from schema.outline import Outline

_EVALS_DIR = Path(__file__).parent


def load_fixture(relative_path: str) -> dict[str, object]:
    return cast(
        dict[str, object], json.loads((_EVALS_DIR.parent / relative_path).read_text())
    )


async def run_build(fixture: dict[str, object]) -> dict[str, object]:
    # Imported lazily: this module is imported by Promptfoo's Python bridge
    # for every `--dry-run` and `-h`, and there is no reason to pay the
    # whole `api` import graph (db engine, config()) until a case actually
    # runs.
    from config import config
    from db.engine import engine, session_factory
    from features.director import approve_outline
    from features.generation.build import build_experience

    brief = Brief.model_validate(fixture["brief"])
    outline = Outline.model_validate(fixture["outline"])
    brand_id = cast(str | None, fixture.get("brandId"))
    scenes: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []

    try:
        # The fixture's outline is hand-authored, in the repo, reviewed in the
        # diff — a human already approved it the same way the outline-editor
        # gate would (docs/v1/plan/07-director.md). This eval tests Build in
        # isolation, not the Director -> approve -> Build chain end to end.
        async for event in build_experience(
            brief=brief,
            approved_outline=approve_outline(outline),
            brand_id=brand_id,
            owner_id=config().local_user_id,
            experience_id="00000000-0000-4000-8000-0000000000ee",
        ):
            if isinstance(event.result, Err):
                errors.append(
                    {
                        "index": event.index,
                        "code": event.result.error.code,
                        "message": event.result.error.message,
                    }
                )
            else:
                scenes.append(event.result.value.model_dump(by_alias=True))
    finally:
        # Promptfoo calls `call_api` once per case and `asyncio.run` closes its
        # loop each time — but `db.engine.engine()` is `@cache`d for the life
        # of the *process*, so case 2 checks out an asyncpg connection bound to
        # case 1's dead loop. `pool_pre_ping` then discards it and opens a
        # fresh one, which is why every case after the first lost exactly one
        # scene to "quota check unavailable: RuntimeError" and it was always
        # scene 0 — the hook. The quota check refusing on an unreachable DB is
        # correct (it fails closed); the pool outliving its loop is the bug.
        # Found by reading run 31024749251's uploaded eval-results.json, which
        # is the whole reason that artifact exists.
        await engine().dispose()
        engine.cache_clear()
        session_factory.cache_clear()

    return {"scenes": scenes, "errors": errors, "brief": fixture["brief"]}


def call_api(
    prompt: str, options: dict[str, object], context: dict[str, object]
) -> dict[str, object]:
    vars_ = cast(dict[str, object], context["vars"])
    fixture = load_fixture(cast(str, vars_["fixture"]))
    result = asyncio.run(run_build(fixture))
    return {"output": json.dumps(result)}
