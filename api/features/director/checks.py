"""Post-generation checks on the Director's own output — the layoutHint
completeness and variety the prompt asks for but structured output alone
cannot guarantee (docs/v1/plan/07-director.md -> "Assign layoutHint here,
not in Build").

Deliberately not a `Outline` Pydantic `model_validator`: that model also
governs the outline-editor's own edits (reorder, retitle, add a scene), and
a user reordering scenes should be free to end up with two adjacent
similar-layout scenes if that is what they want. This check is specific to
what the *Director's own generation* must satisfy, not a universal
structural rule — the same reason `check_scene` lives in
`features/generation/checks.py` rather than on `Scene` itself.
"""

from lib.result import Result, err, ok
from schema.outline import Outline


def check_outline(outline: Outline) -> Result[None]:
    missing = [i for i, s in enumerate(outline.scenes) if s.layout_hint is None]
    if missing:
        return err("invalid_input", f"scenes missing a layoutHint: {missing}")

    repeats = [
        i
        for i, (a, b) in enumerate(
            zip(outline.scenes, outline.scenes[1:], strict=False)
        )
        if a.layout_hint == b.layout_hint
    ]
    if repeats:
        return err(
            "invalid_input", f"adjacent scenes repeat layoutHint at index {repeats}"
        )

    return ok(None)
