"""The report's judgement, tested without a browser.

Whether 1,565px of copy fits a 600px frame is a question only a layout engine
answers, and that half is verified against a real `render` (docs/v2/plan/
13-scene-fit.md). What is tested here is everything this module decides *given*
a measurement: which scenes count, which blocks are worth naming, and — the one
that matters — that a failure to measure is never a clean report.
"""

from typing import Protocol

import httpx
import pytest

from features.overflow.measure import measure_overflow
from lib.result import Err, Ok, Result
from schema.overflow import OverflowReport
from schema.scene import Scene

SCENE = Scene.model_validate(
    {
        "id": "one",
        "intent": "hook",
        "layout": "centered",
        "blocks": [{"id": "h", "props": {"type": "headline", "text": "Hello"}}],
    }
)


def _extent(scene_id: str, content: int, frame: int = 600) -> dict[str, object]:
    return {
        "sceneId": scene_id,
        "frameBlockSize": frame,
        "contentBlockSize": content,
        "blocks": [{"blockId": "h", "blockSize": content}],
    }


class RenderReturns(Protocol):
    """`Callable[..., None]` would be an implicit `Any` in the argument
    position, which this project's mypy settings refuse — and rightly, since
    the whole value of a typed fixture is that a wrong call site fails here
    rather than at runtime."""

    def __call__(self, payload: object, status: int = 200) -> None: ...


@pytest.fixture
def render_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> RenderReturns:
    """Swaps the *transport*, not the function under test.

    Stubbing `measure_overflow`'s own call out of the picture would leave the
    request shape — the thing most likely to be wrong — untested. A
    `MockTransport` keeps the real client, the real URL construction and the
    real serialization, and only replaces the socket.
    """

    def install(payload: object, status: int = 200) -> None:
        transport = httpx.MockTransport(lambda _: httpx.Response(status, json=payload))
        real = httpx.AsyncClient

        def factory(**kwargs: object) -> httpx.AsyncClient:
            kwargs.pop("transport", None)
            return real(transport=transport, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(httpx, "AsyncClient", factory)

    return install


async def _measure() -> Result[OverflowReport]:
    return await measure_overflow(
        scenes=[SCENE], art_direction="cinematic-dark", viewport_height=600
    )


async def test_only_scenes_that_exceed_their_frame_are_reported(
    render_returns: RenderReturns,
) -> None:
    """An empty list is the ordinary case and is what the banner checks. A
    report listing every scene would make "does anything overflow" a filter
    rather than a truth value."""
    render_returns([_extent("fits", 400), _extent("does-not", 900)])
    result = await _measure()
    assert isinstance(result, Ok)
    assert [s.scene_id for s in result.value.scenes] == ["does-not"]
    assert result.value.any_overflow


async def test_content_exactly_at_the_frame_is_not_overflow(
    render_returns: RenderReturns,
) -> None:
    render_returns([_extent("exact", 600)])
    result = await _measure()
    assert isinstance(result, Ok)
    assert result.value.scenes == []
    assert not result.value.any_overflow


async def test_the_report_carries_both_sizes_not_just_the_difference(
    render_returns: RenderReturns,
) -> None:
    """ "Over by 40px" and "over by 40px in a 760px frame" are different
    problems, and only the second is one a user can act on."""
    render_returns([_extent("tall", 900, frame=600)])
    result = await _measure()
    assert isinstance(result, Ok)
    scene = result.value.scenes[0]
    assert (scene.content_block_size, scene.frame_block_size) == (900, 600)
    assert scene.overflow_by == 300


async def test_at_most_three_culprit_blocks_and_the_tallest_first(
    render_returns: RenderReturns,
) -> None:
    """Every block in an overflowing scene is technically implicated. A banner
    naming eight is a banner nobody reads."""
    payload = [
        {
            "sceneId": "tall",
            "frameBlockSize": 600,
            "contentBlockSize": 2000,
            "blocks": [{"blockId": f"b{i}", "blockSize": i * 100} for i in range(1, 6)],
        }
    ]
    render_returns(payload)
    result = await _measure()
    assert isinstance(result, Ok)
    assert [b.block_id for b in result.value.scenes[0].blocks] == ["b5", "b4", "b3"]


@pytest.mark.parametrize("status", [400, 500, 503])
async def test_a_render_failure_is_an_error_never_a_clean_report(
    status: int, render_returns: RenderReturns
) -> None:
    """The one that matters. "We could not check" and "nothing overflows" must
    not be the same value — the second draws a green banner over an unmeasured
    page, which is rule 10's reasoning applied to a check that grants
    permission to publish without a warning."""
    render_returns({"error": "no"}, status=status)
    result = await _measure()
    assert isinstance(result, Err)
    assert result.error.code == "upstream_unavailable"


async def test_an_unreadable_body_is_also_an_error(
    render_returns: RenderReturns,
) -> None:
    """`render` is another process, so its output is external input and gets a
    parse at the boundary like everything else — being written by us is not a
    reason to trust its shape."""
    render_returns([{"sceneId": "x"}])
    result = await _measure()
    assert isinstance(result, Err)
    assert result.error.code == "upstream_unavailable"
