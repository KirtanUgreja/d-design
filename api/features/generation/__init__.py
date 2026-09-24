"""generation — the pipeline as a service (v3).

The v1 pipeline reached the product only through `cli.py`. This feature is the
HTTP surface for it: three stages, in order, with the human approval gate
living between the first two (in the client, where the person is).

No database, no tenancy: generation writes nothing and spends no quota. The
spend it does incur is model tokens, which is why the kill switch guards it.
"""

from features.generation.generation import (
    BUILD_MODEL,
    IMAGE_MODEL,
    INTERVIEW_MODEL,
    MAPPING_MODEL,
    build,
    interview,
    mapping,
    provider_configured,
)

__all__ = [
    "BUILD_MODEL",
    "IMAGE_MODEL",
    "INTERVIEW_MODEL",
    "MAPPING_MODEL",
    "build",
    "interview",
    "mapping",
    "provider_configured",
]
