"""The only module that reads the environment (docs/v4/engine.md -> Layout).

Everything under ``engine`` takes what it needs as arguments. Model ids are
pinned here: a change is a config change, and it re-runs the bench
(docs/v4/spec.md -> Risks, "Model drift").
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Read ``KEY=value`` lines into the environment, never overriding it.

    ponytail: eight lines instead of a dotenv dependency. Ceiling: no quoting
    or interpolation. Upgrade path: python-dotenv, with a ledger row.
    """
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key, value.strip().strip("\"'"))


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    # Candidates until the phase-22 bake-off pins the winners
    # (docs/techstack/ai-stack.md). Prices read 2026-09-30.
    model_writing: str = "anthropic/claude-sonnet-5.5"
    model_design: str = "anthropic/claude-opus-5.5"
    model_cheap: str = "anthropic/claude-haiku-4.5"
    deck_budget_usd: float = 5.0


def load() -> Settings:
    _load_dotenv(REPO_ROOT / ".env")
    return Settings(
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        model_writing=os.environ.get("MODEL_WRITING", Settings.model_writing),
        model_design=os.environ.get("MODEL_DESIGN", Settings.model_design),
        model_cheap=os.environ.get("MODEL_CHEAP", Settings.model_cheap),
    )
