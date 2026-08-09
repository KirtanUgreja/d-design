"""Prompts are code, in the repo, reviewed in the diff
(docs/v1/plan/06-model-seam-and-build.md). Two builders: the system prefix,
byte-identical across every scene in one build (the whole point of the
caching discipline), and the per-scene instruction that varies and goes
last.

Caching discipline, all three rules from docs/v1/ai-pipeline.md:
  - No timestamp, uuid, or scene index in the system prompt — only in the
    per-scene user prompt, which is never cached
  - The brief/outline/constraints text is deterministic for a given input
  - The scene-specific instruction is the *user* message, never appended to
    system
"""

from typing import get_args

from pydantic.fields import FieldInfo

from features.generation.tools import get_constraints
from schema.brief import Brief
from schema.experience import BrandKit
from schema.outline import Outline, OutlineScene
from schema.scene import BlockProps

_PROMPT_CONTRACT = """You are the Build phase of a presentation-experience generator. \
For the one scene you are asked to write, output valid JSON conforming exactly to the \
provided schema, in this order of importance:
1. Output valid Scene JSON, nothing else.
2. Use only copy derived from the brief's key messages and proof points below. \
Invent no new claims, statistics, or customer names. The scene's beat below may describe \
a comparison or ratio in narrative terms — do not put a number into a Stat unless that \
same number independently appears in the key messages or proof points below. A number you \
compute by combining two approved figures (a ratio, a percentage difference, a multiple) \
is not itself approved, even when the arithmetic is correct.
3. Never emit colors, sizes, fonts, durations, or easing curves — your schema has no \
field for them, because the art direction supplies all of that from the intent you pick.
4. Respect every character limit in the list below. They are hard: copy over a limit \
is rejected and the scene is rebuilt, so write comfortably under each one rather than \
right up against it.
5. Prefer fewer blocks. A scene with two blocks usually beats one with six."""

# Verbatim slices of the contract above — the sentinels that say "the model
# echoed its instructions back instead of writing the brief's content". Two
# consumers: the post-build leak check (features/generation/checks.py) and the
# injection corpus's 4th assertion (evals/assertions.py,
# docs/security/testing.md). Exported from here so there is exactly one copy;
# test_checks.py asserts each one still occurs in `_PROMPT_CONTRACT`, so
# rewording the prompt fails a test rather than silently disarming the check.
PROMPT_SENTINELS = (
    "You are the Build phase",
    "Never emit colors, sizes, fonts",
    "Prefer fewer blocks",
)


def _limits_section() -> str:
    """The character caps, read off the Pydantic models rather than typed out.

    Rule 4 says "respect every character limit in the list below" and, until
    this existed, nothing was below: the caps lived only in the JSON Schema's
    `maxLength`, which `ai/complete.py` now strips before the request goes out
    (the provider enforced it by truncating copy mid-word). Stripping it without
    telling the model the numbers left it flying blind, and every remaining
    build failure was a `string_too_long` on `headline.text` or `body.text`.

    Derived, not restated, so a cap changed in `schema/scene.py` cannot drift
    out of the prompt — the same reason `PROMPT_SENTINELS` lives beside the
    contract it quotes.
    """
    lines: list[str] = []
    for props in get_args(get_args(BlockProps)[0]):
        caps = [
            f"{name} <= {cap}"
            for name, field in props.model_fields.items()
            if (cap := _max_length(field)) is not None
        ]
        if not caps:
            continue
        block = get_args(props.model_fields["type"].annotation)[0]
        lines.append(f"- {block}: {', '.join(caps)}")
    return "Character limits, counted in characters:\n" + "\n".join(lines)


def _max_length(field: FieldInfo) -> int | None:
    """Pydantic keeps `max_length` in a field's metadata, not as an attribute.

    Strings only. The same constraint also caps list lengths (`ListProps.items`
    is 2-5 *items*), and listing that under a heading about characters would
    teach the model the wrong unit for the one block where the distinction
    matters.
    """
    if str not in (field.annotation, *get_args(field.annotation)):
        return None
    for entry in field.metadata:
        length = getattr(entry, "max_length", None)
        if length is not None:
            return int(length)
    return None


def _brand_section(brand_kit: BrandKit | None) -> str:
    if brand_kit is None:
        return (
            "No brand kit is set for this experience; rely on the art direction alone."
        )
    return (
        f"Brand fonts: display={brand_kit.display_font}, text={brand_kit.text_font}. "
        f"Brand colors exist but are resolved by the renderer, not chosen by you."
    )


def _assets_section(assets: list[dict[str, str]]) -> str:
    if not assets:
        return (
            "No uploaded assets are available. Do not reference an assetId — use "
            "AbstractVisual instead wherever a scene needs imagery."
        )
    listed = "\n".join(f"- {a['id']}: {a.get('description', '')}" for a in assets)
    return f"Available assets (reference only these ids, never invent one):\n{listed}"


def build_system_prompt(
    brief: Brief,
    outline: Outline,
    brand_kit: BrandKit | None,
    assets: list[dict[str, str]],
) -> str:
    key_messages = "\n".join(f"- {m}" for m in brief.key_messages)
    proof_points = "\n".join(f"- {p}" for p in brief.proof_points) or "(none supplied)"
    outline_scenes = "\n".join(
        f"{i + 1}. intent={s.intent} beat={s.beat!r} layout_hint={s.layout_hint or 'none'}"
        for i, s in enumerate(outline.scenes)
    )
    return f"""{_PROMPT_CONTRACT}

{_limits_section()}

{get_constraints()}

{_brand_section(brand_kit)}

{_assets_section(assets)}

Brief:
Goal: {brief.goal}
Audience: {brief.audience}
Tone: {brief.tone}
Approved CTA: label={brief.cta.label!r} href={brief.cta.href!r}
Constraints: {brief.constraints or "(none)"}

Key messages (approved copy — arrange and shorten, never invent):
{key_messages}

Proof points (approved copy — arrange only):
{proof_points}

Full outline, title {outline.title!r} — you are writing ONE scene at a time; this is \
so you know your neighbors:
{outline_scenes}"""


def build_scene_user_prompt(scene: OutlineScene, index: int, total: int) -> str:
    layout = (
        f"Use layout {scene.layout_hint!r}."
        if scene.layout_hint
        else "Choose the layout that best fits this beat."
    )
    return (
        f"Write scene {index + 1} of {total}. "
        f"Intent: {scene.intent}. Beat: {scene.beat!r}. {layout} "
        f"Output only the JSON for this one scene."
    )
