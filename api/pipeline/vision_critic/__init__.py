"""vision-critic — the automated visual defect checker (phase 13).

A screenshot of each rendered slide is shown to a vision model that answers
narrow structural questions; a defect triggers at most one corrective
revision, then stops. Bounded by a literal MAX_REVISIONS = 1 — a bounded
loop is not an agent (ai-stack.md).
"""

from pipeline.vision_critic.critic import MAX_REVISIONS, CriticOutcome, run_critic

__all__ = ["MAX_REVISIONS", "CriticOutcome", "run_critic"]
