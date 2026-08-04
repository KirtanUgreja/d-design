"""The Director's output, and the thing the user approves before anything
expensive runs.

The director decides *structure and pacing*, nothing else — `beat` is one
sentence describing what a scene does in the narrative, never its copy.
"""

from pydantic import Field, model_validator

from schema.base import Schema
from schema.scene import Layout, SceneIntent


class OutlineScene(Schema):
    intent: SceneIntent
    beat: str = Field(min_length=1, max_length=200)
    layout_hint: Layout | None = None


class Outline(Schema):
    title: str = Field(min_length=1, max_length=200)
    scenes: list[OutlineScene] = Field(min_length=3, max_length=12)

    @model_validator(mode="after")
    def _pacing_rules(self) -> "Outline":
        hooks = [i for i, s in enumerate(self.scenes) if s.intent == "hook"]
        if hooks != [0]:
            raise ValueError(
                f"exactly one scene has intent 'hook' and it is first; found at {hooks}"
            )

        if not any(s.intent == "cta" for s in self.scenes):
            raise ValueError("an outline has at least one 'cta' scene")

        for i, (a, b) in enumerate(zip(self.scenes, self.scenes[1:], strict=False)):
            if a.intent == b.intent:
                raise ValueError(f"adjacent scenes repeat intent {a.intent!r} at {i}")

        return self
