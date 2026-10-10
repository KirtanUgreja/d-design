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
    # Candidates until the owner's wall ratings pin the winners
    # (docs/techstack/ai-stack.md). Cheap paid models by the owner's decision
    # of 2026-09-30; the one-shot baseline was made on claude-opus-5.5.
    model_writing: str = "anthropic/claude-sonnet-5.5"
    # The studio's art director, designer and improver (owner, 2026-10-09: "Sonnet
    # throughout"); the flash model it replaces designed every slide alike.
    model_design: str = "anthropic/claude-sonnet-5.5"
    # The interview and speaker notes (2026-10-09): Haiku 5.5 is a twentieth of
    # Sonnet's price; research and the storyline stay on model_writing.
    model_cheap: str = "anthropic/claude-haiku-5.5"
    # MODEL_PROVIDERS: "model=provider,…" pins a model to one OpenRouter provider,
    # no fallback. Haiku runs on Amazon Bedrock through the owner's own AWS key
    # (OpenRouter BYOK), so AWS bills it.
    model_providers: str = "anthropic/claude-haiku-5.5=amazon-bedrock"
    # Slide images (phase 39). Chosen on test day from three candidates; ""
    # turns images off and every image slot stays a quiet field.
    model_image: str = "google/gemini-3.1-flash-lite-image"
    deck_budget_usd: float = 5.0
    daily_cap_usd: float = 3.0  # per user per UTC day; not a credit system (2026-10-08)
    auth_url: str = ""  # BETTER_AUTH_URL: the web app; its JWKS and the JWT issuer
    auth_disabled: bool = False  # AUTH_DISABLED=1: a laptop run with no accounts
    data_dir: Path = REPO_ROOT / "data"  # the file store (store/files.py); gitignored
    # Neon `app` (pooled); set = the SQL store (store/tenant.py -> open_store).
    database_url: str = ""

    @property
    def providers(self) -> dict[str, str]:
        """MODEL_PROVIDERS parsed: model -> the one provider it may run on."""
        pairs = (part.split("=", 1) for part in self.model_providers.split(",") if "=" in part)
        return {model.strip(): provider.strip() for model, provider in pairs}


def _model(role: str, pinned: str) -> str:
    """MODEL_<ROLE> if set, else MODEL (one model for every text role), else the pin."""
    return os.environ.get(f"MODEL_{role}") or os.environ.get("MODEL") or pinned


def load() -> Settings:
    _load_dotenv(REPO_ROOT / ".env")
    return Settings(
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        model_writing=_model("WRITING", Settings.model_writing),
        model_design=_model("DESIGN", Settings.model_design),
        model_cheap=_model("CHEAP", Settings.model_cheap),
        model_providers=os.environ.get("MODEL_PROVIDERS", Settings.model_providers),
        model_image=os.environ.get("MODEL_IMAGE", Settings.model_image),
        daily_cap_usd=float(os.environ.get("DAILY_CAP_USD", str(Settings.daily_cap_usd))),
        auth_url=os.environ.get("BETTER_AUTH_URL", "").rstrip("/"),
        auth_disabled=os.environ.get("AUTH_DISABLED", "") == "1",
        data_dir=Path(os.environ.get("DATA_DIR", str(Settings.data_dir))),
        database_url=os.environ.get("APP_DATABASE_URL", ""),
    )
