"""The image seam action — the only place an image model is called.

pipeline-tools.md: image generation is a seam action, not a tier-2 tool. The
model never reaches the network; the seam does, on the model's behalf, within
the design family's visual rules and a dimension cap. The result is a data-URI
asset embedded at export, which is what keeps `connect-src 'none'` honest.

This is the most expensive call per deck (spec.md Risk 6): a dimension cap and
a per-deck cap are enforced here and by the caller, and an injected
"generate 50 images" gets the same quota answer as unbounded repair.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from lib.result import Result, err, ok

# Dimension cap: keeps the embedded file lean and bounds the cost. The size is
# one of the modern OpenRouter image models' supported set (1024x1024 /
# 1024x1536 / 1536x1024 / auto) — the old 1280x720 was rejected with a 400 by
# gpt-image-* (live-run finding, phase 20-era).
MAX_WIDTH = 1024
MAX_HEIGHT = 1024

# Hard per-deck image cap (pipeline-tools.md -> denial-of-wallet discipline).
MAX_IMAGES_PER_DECK = 4

OPENROUTER_IMAGES_URL = "https://openrouter.ai/api/v1/images/generations"


class ImageTransport(Protocol):
    """The image seam's network boundary. httpx.Client satisfies it; tests
    inject a stub."""

    def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response: ...


@dataclass(frozen=True)
class ImageError:
    kind: str
    detail: str


@dataclass
class ImageSeam:
    """One image call site. Injected transport so tests never hit the network."""

    transport: ImageTransport = field(default_factory=lambda: httpx.Client(timeout=180.0))
    api_key: str = ""
    base_url: str = OPENROUTER_IMAGES_URL
    images_generated: int = 0

    def generate(
        self,
        subject: str,
        visual_rules: str,
        model: str = "openai/gpt-5-image-mini",
    ) -> Result[str, ImageError]:
        """Generate one image and return it as a data URI.

        ``visual_rules`` is the design family's prose description (its axis
        tags), assembled by the caller — never by the model.
        """
        if not self.api_key:
            return err(ImageError("transport", "OPENROUTER_API_KEY is not set"))
        if self.images_generated >= MAX_IMAGES_PER_DECK:
            return err(ImageError("cap", f"max {MAX_IMAGES_PER_DECK} images per deck"))

        prompt = (
            f"{subject}. "
            f"Visual style: {visual_rules}. "
            f"Max dimensions {MAX_WIDTH}x{MAX_HEIGHT}. "
            "No text, no logos, no watermarks."
        )

        response = self.transport.post(
            self.base_url,
            json={
                "model": model,
                "prompt": prompt,
                "n": 1,
                "size": f"{MAX_WIDTH}x{MAX_HEIGHT}",
                "response_format": "b64_json",
            },
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        if response.status_code != 200:
            return err(ImageError("transport", f"image endpoint returned {response.status_code}"))

        try:
            data = response.json()
            b64 = data["data"][0]["b64_json"]
        except (KeyError, IndexError, TypeError) as exc:
            return err(ImageError("invalid", f"unexpected image response: {exc}"))

        self.images_generated += 1
        uri = f"data:image/png;base64,{b64}"
        return ok(uri)


def make_image_seam() -> ImageSeam:
    return ImageSeam(
        transport=httpx.Client(timeout=180.0),
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    )
