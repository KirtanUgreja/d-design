"""Generated imagery (docs/v1/plan/11-visuals-and-slot.md -> "2. Generated
imagery"; wired in v2 phase 15, docs/v2/plan/15-images.md).

v1 left this as the cap and the storage path with no provider call, and the
`ponytail:` here named the upgrade path exactly: *set an image model, add an
image branch inside `complete` so there is still one call site, and call it
from `generate_image` below.* That is what happened, and nothing else in this
file had to change.

The provider is chosen on **reference-image support**, not fidelity, because
holding one art direction's look across a whole deck is the hard part. Imagen
shut down 2026-08-17, which took the obvious default off the table; Gemini 3
Pro Image accepts up to 14 references and is reachable through the endpoint the
seam already speaks.

The three rules, none of which is about quality:

  Never generate the product. Generated product imagery is a legal and
  credibility problem — atmosphere, texture and abstract environment only,
  never the thing being sold. Enforced by the prompt builder having no access
  to the brief's key messages.

  Prefer AbstractVisual first. It costs nothing and is always on brand. The
  five generators are the default and this is the exception.

  Mark it. `source='generated'` on the row, visible in the editor, because a
  marketer must know what is real before they publish.
"""

from uuid import UUID

from ai.complete import complete_image
from db.tenant import as_user
from features.assets import save_asset, store, verify_and_reencode
from lib.result import Err, Result, err, ok
from schema.experience import Asset

# Generated imagery is the one place v1's cost model stops being a rounding
# error: docs/v1/ai-pipeline.md is explicit that token cost is not this
# product's constraint — "generated imagery, storage, bandwidth, and human
# review time all exceed it". A per-experience cap, not a per-owner one,
# because the runaway shape is one experience regenerating in a loop.
MAX_GENERATED_PER_EXPERIENCE = 4


def build_imagery_prompt(*, scene_intent: str, scene_beat: str, tone: str) -> str:
    """The prompt, from the scene's own intent and beat and the brief's tone.

    No key messages, no proof points, no user free text beyond what the
    pipeline already checked — which is both the injection boundary and the
    "never generate the product" rule made structural: a prompt with no access
    to what the product *is* cannot be asked to depict it.
    """
    return (
        "Atmospheric background imagery for a presentation scene. "
        f"The scene's intent is {scene_intent!r} and its beat is {scene_beat!r}. "
        f"The overall tone is {tone!r}. "
        "Texture, light and abstract environment only. "
        "Do not depict any product, device, screen, logo, brand mark, or person. "
        # The house ban, in the only place it can be enforced for pixels.
        # Rules 18 and 19 are greppable because they are CSS; an image is
        # bytes, and `invariants.sh` cannot see a bloom inside a JPEG. Asked
        # only for "atmospheric background imagery", this model's first output
        # was a soft blurred colour wash — a gradient by any other name, and
        # the exact look the product bans. Verified 2026-08-09.
        "Physical, tactile surfaces with visible structure and grain: paper, "
        "ink, fibre, stone, weathered metal, fabric weave. Hard-edged forms. "
        "No smooth colour ramps, no gradients, no soft glow, no bloom, no "
        "haze, no lens flare, no neon, no out-of-focus blur across the frame."
    )


async def store_generated_image(
    *, raw: bytes, owner_id: str, alt: str
) -> Result[Asset]:
    """A generated image becomes an `Asset` through the *same* pipeline an
    upload takes — the same magic-byte check, the same re-encode, the same
    server-generated key.

    Not because a provider's bytes are hostile in the way a user's are, but
    because a second path is a second place to get it wrong, and the day this
    is fetched from a URL rather than handed over in memory the difference
    stops being theoretical.
    """
    verified = verify_and_reencode(raw)
    if isinstance(verified, Err):
        return verified

    upload = verified.value
    await store(upload)

    # Opens its own tenant-scoped session rather than taking one: SQLAlchemy
    # belongs in a `*_data.py` module and nowhere else, so this file cannot
    # name an `AsyncSession` even in an annotation (rule 8, enforced by
    # `scripts/checks/invariants.sh`).
    async with as_user(owner_id) as session:
        row = await save_asset(
            session,
            owner_id=UUID(owner_id),
            kind="image",
            storage_key=upload.storage_key,
            mime=upload.content_type,
            width=upload.width,
            height=upload.height,
            alt=alt,
            # The field the whole rule rests on.
            source="generated",
        )
        return ok(
            Asset(
                id=str(row.id),
                kind="image",
                storage_key=row.storage_key,
                mime=row.mime,
                width=row.width,
                height=row.height,
                alt=row.alt,
                source="generated",
            )
        )


def check_generation_cap(existing_generated: int) -> Result[None]:
    """Fails closed, and the signature is why: it takes a count rather than
    fetching one, so a caller that cannot produce a count cannot accidentally
    proceed with a default of zero. Same reasoning as the quota check —
    "anything that prevents the check from completing is treated exactly like
    over quota: refused, not permitted"."""
    if existing_generated >= MAX_GENERATED_PER_EXPERIENCE:
        return err(
            "quota_exceeded",
            f"this experience already has {existing_generated} generated images, "
            f"which is the limit of {MAX_GENERATED_PER_EXPERIENCE}",
        )
    return ok(None)


async def generate_image(
    *,
    owner_id: str,
    experience_id: str,
    existing_generated: int,
    scene_intent: str,
    scene_beat: str,
    tone: str,
    alt: str,
) -> Result[Asset]:
    """The whole path: cap, prompt, seam, verification, row.

    The order is the point. The cap is checked *before* the call, so a refusal
    costs nothing — and it is checked here rather than inside the seam because
    it is a per-experience count this module owns, where the seam's quota is
    per-owner. Both have to pass and both fail closed.

    No retry. A failed image returns the error and leaves the caller to decide;
    an automatic second attempt at $0.137 is the denial-of-wallet shape this
    codebase caps everywhere else.
    """
    capped = check_generation_cap(existing_generated)
    if isinstance(capped, Err):
        return capped

    generated = await complete_image(
        prompt=build_imagery_prompt(
            scene_intent=scene_intent, scene_beat=scene_beat, tone=tone
        ),
        owner_id=owner_id,
        experience_id=experience_id,
    )
    if isinstance(generated, Err):
        return generated

    # The provider's bytes go through the upload pipeline unchanged — magic
    # bytes, re-encode, server-generated key. `mime` from the response is
    # deliberately *not* trusted here; `verify_and_reencode` decides what these
    # bytes actually are, exactly as it does for a user's upload.
    return await store_generated_image(
        raw=generated.value.data, owner_id=owner_id, alt=alt
    )
