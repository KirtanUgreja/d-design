"""The Director phase's public surface: Brief -> Outline, and the approval
gate `features.generation.build.build_experience` depends on
(docs/v1/plan/07-director.md).
"""

from features.director.approval import ApprovedOutline, approve_outline
from features.director.direct import direct_brief

__all__ = ["ApprovedOutline", "approve_outline", "direct_brief"]
