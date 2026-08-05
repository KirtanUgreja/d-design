"""The exit-gate proof docs/v1/plan/06-model-seam-and-build.md asks for
directly: "`generations` holds metadata and nothing else — proven with a
canary." A canary string travels through the real seam (mocked HTTP,
real quota check, real `generations` insert) and this greps the row back
for it — the same technique docs/security/testing.md -> "Model routing and
data flow" names: "A synthetic brief with a canary string appears in no
third-party surface you can query." Here the surface is our own table.
"""

import json
import os
from uuid import uuid4

import httpx
import pytest
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ai.complete import complete
from lib.result import Ok

_MIGRATOR = os.environ["MIGRATION_DATABASE_URL"]


class _Widget(BaseModel):
    text: str


async def test_canary_never_reaches_generations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canary = f"CANARY-{uuid4()}"
    owner_id = uuid4()
    experience_id = uuid4()

    engine = create_async_engine(_MIGRATOR)
    async with engine.begin() as conn:
        await conn.execute(
            text('insert into quotas (owner_id, used, "limit") values (:o, 0, 1000)'),
            {"o": owner_id},
        )

    def handler(request: httpx.Request) -> httpx.Response:
        # The canary lives in the outbound request — the system/user prompt
        # — which is everything `complete()` sends. `log_generation` never
        # sees the request or response body at all, only call metadata.
        assert canary in request.content.decode()
        body = json.dumps(
            {
                "model": "test/model",
                "provider": "test-provider",
                "choices": [
                    {
                        "delta": {"content": json.dumps({"text": "ok"})},
                        "finish_reason": "stop",
                    }
                ],
            }
        )
        return httpx.Response(200, content=f"data: {body}\n\ndata: [DONE]\n\n".encode())

    real_client = httpx.AsyncClient

    def fake_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)

    try:
        result = await complete(
            phase="build",
            schema=_Widget,
            system=f"You are writing scene copy. Context: {canary}",
            user=f"Write the hook scene. Reference detail: {canary}",
            owner_id=str(owner_id),
            experience_id=str(experience_id),
        )
        assert isinstance(result, Ok)

        async with engine.begin() as conn:
            row = (
                (
                    await conn.execute(
                        text("select * from generations where owner_id = :o"),
                        {"o": owner_id},
                    )
                )
                .mappings()
                .one()
            )
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("delete from generations where owner_id = :o"), {"o": owner_id}
            )
            await conn.execute(
                text("delete from quotas where owner_id = :o"), {"o": owner_id}
            )
        await engine.dispose()

    for column, value in row.items():
        assert canary not in str(value), f"canary leaked into generations.{column}"
