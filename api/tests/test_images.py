"""Image seam tests.

The image seam is a seam action (pipeline-tools.md): the model never reaches
the network, the seam does. Tests cover the per-deck cap, the data-URI
result, and the fail-closed paths (no key, transport error, bad response).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from ai.images import MAX_IMAGES_PER_DECK, ImageSeam
from lib.result import Err, Ok


@dataclass
class StubTransport:
    responses: list[httpx.Response] = field(default_factory=list)

    def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response:
        del url, json, headers
        return self.responses.pop(0)


def _ok_image() -> httpx.Response:
    return httpx.Response(200, json={"data": [{"b64_json": "QUJD"}]})


def test_generate_returns_data_uri() -> None:
    seam = ImageSeam(transport=StubTransport([_ok_image()]), api_key="k")
    result = seam.generate("A forest at dawn", "serif, paper")
    assert isinstance(result, Ok)
    assert result.value == "data:image/png;base64,QUJD"
    assert seam.images_generated == 1


def test_missing_key_fails_closed() -> None:
    seam = ImageSeam(transport=StubTransport([]), api_key="")
    result = seam.generate("A forest", "serif")
    assert isinstance(result, Err)
    assert result.error.kind == "transport"
    assert seam.images_generated == 0


def test_transport_error_returns_err() -> None:
    seam = ImageSeam(transport=StubTransport([httpx.Response(500, json={})]), api_key="k")
    result = seam.generate("A forest", "serif")
    assert isinstance(result, Err)
    assert result.error.kind == "transport"


def test_malformed_response_returns_err() -> None:
    seam = ImageSeam(transport=StubTransport([httpx.Response(200, json={"data": []})]), api_key="k")
    result = seam.generate("A forest", "serif")
    assert isinstance(result, Err)
    assert result.error.kind == "invalid"


def test_per_deck_cap_is_enforced() -> None:
    seam = ImageSeam(transport=StubTransport([_ok_image()] * MAX_IMAGES_PER_DECK), api_key="k")
    for _ in range(MAX_IMAGES_PER_DECK):
        assert isinstance(seam.generate("x", "y"), Ok)
    # The next call refuses: hard cap, the same shape as unbounded-repair
    # quota (pipeline-tools.md -> denial-of-wallet discipline).
    result = seam.generate("x", "y")
    assert isinstance(result, Err)
    assert result.error.kind == "cap"
