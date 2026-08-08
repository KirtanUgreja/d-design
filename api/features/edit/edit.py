"""One block, one instruction, one partial back (docs/v1/plan/09-editor.md ->
"The Edit call").

The narrowest call in the pipeline, and the only one where a user types free
text that reaches a model with scene content in context. What keeps that safe
is not the prompt: it is that `EditResult` has no field for a scene id, a block
id, or any presentational value, so "make the whole page blue" and "rewrite the
next headline" have nowhere to land even if the model wanted to comply.

No tools. The phase doc allows one tier-0 `read_block(id)` so an edit is a diff
rather than a rewrite — but the block is already in the prompt, so a tool that
fetches it would be a second way to get what the caller already sent. It stays
unbuilt until an edit needs a block it was not given, which is a different
feature (docs/coderules/patterns.md: never give the AI a tool with side
effects, and do not add one for its own sake).
"""

from ai.complete import complete
from features.edit.prompts.edit import build_edit_prompt
from lib.result import Err, Result, err, ok
from schema.no_style import assert_no_presentational_values
from schema.patch import EditDraft, EditResult
from schema.scene import Scene


async def edit_block(
    *,
    scene: Scene,
    block_id: str,
    instruction: str,
    owner_id: str,
    experience_id: str,
) -> Result[EditResult]:
    block = next((b for b in scene.blocks if b.id == block_id), None)
    if block is None:
        return err("not_found", f"no block {block_id} in scene {scene.id}")

    system, user = build_edit_prompt(
        block=block.model_dump(by_alias=True),
        scene_intent=scene.intent,
        instruction=instruction,
    )
    result = await complete(
        phase="edit",
        schema=EditDraft,
        system=system,
        user=user,
        owner_id=owner_id,
        experience_id=experience_id,
    )
    if isinstance(result, Err):
        return result

    draft = result.value.value
    before = block.model_dump(by_alias=True)["props"]
    after = draft.props.model_dump(by_alias=True)

    if after["type"] != before["type"]:
        # The discriminator is what makes the client's offline whole-tree
        # validation sound (web/src/features/editor/patch.ts): a props-only
        # patch that cannot change `type` cannot turn an Eyebrow into a second
        # Headline in a scene that already has one, and nothing on the client
        # would catch it if it could.
        return err("invalid_input", "an edit cannot change a block's type")

    styled = assert_no_presentational_values(after)
    if isinstance(styled, Err):
        # Belt and braces by design: `BlockProps` has no field for a colour or
        # a size, so this should be unreachable. It runs anyway because "the
        # schema makes it impossible" is a claim worth having a control behind
        # — the same reasoning as the post-build checks.
        return styled

    # The diff is what makes an edit a diff. The model returns the whole props
    # object because a partial is an open dict strict mode cannot express; only
    # the keys it actually moved leave this function, so a patch still touches
    # the minimum and `applyPatch`'s structural sharing still holds.
    changed = {k: v for k, v in after.items() if before.get(k) != v}
    return ok(EditResult(props=changed, refusal=draft.refusal))
