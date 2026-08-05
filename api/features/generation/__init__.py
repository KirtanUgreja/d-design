"""The quota/logging functions the model seam calls on every phase's behalf
(docs/v1/plan/06-model-seam-and-build.md).

`build_experience` is deliberately NOT re-exported here. `ai/complete.py`
imports `check_quota_and_kill_switch`/`log_generation` from this package,
and this package's own `build` submodule imports `ai.complete` — so an
eager `from features.generation.build import build_experience` at the top
of this file closes a real cycle the moment anything imports `ai.complete`
before this package (dotted-path submodule imports always run a package's
`__init__.py` first, with no way to skip it). Callers import
`build_experience` straight from `features.generation.build` instead, the
same direct-submodule pattern `build.py` itself uses for `checks`/`tools`.
"""

from features.generation.quota import check_quota_and_kill_switch, log_generation

__all__ = ["check_quota_and_kill_switch", "log_generation"]
