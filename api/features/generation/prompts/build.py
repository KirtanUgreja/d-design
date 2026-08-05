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

from features.generation.tools import get_constraints
from schema.brief import Brief
from schema.experience import BrandKit
from schema.outline import Outline, OutlineScene

_PROMPT_CONTRACT = """You are the Build phase of a presentation-experience generator. \
For the one scene you are asked to write, output valid JSON conforming exactly to the \
provided schema, in this order of importance:
1. Output valid Scene JSON, nothing else.
2. Use only copy derived from the brief's key messages and proof points below. \
Invent no new claims, statistics, or customer names.
3. Never emit colors, sizes, fonts, durations, or easing curves — your schema has no \
field for them, because the art direction supplies all of that from the intent you pick.
4. Respect every character limit below; they are hard limits, not suggestions.
5. Prefer fewer blocks. A scene with two blocks usually beats one with six."""


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
