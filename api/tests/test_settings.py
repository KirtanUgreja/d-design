"""MODEL picks one model for every text role; MODEL_<ROLE> still wins."""

from __future__ import annotations

import pytest

import settings


def test_model_sets_every_text_role(monkeypatch: pytest.MonkeyPatch) -> None:
    for role in ("WRITING", "DESIGN", "CHEAP"):
        monkeypatch.delenv(f"MODEL_{role}", raising=False)
    monkeypatch.setenv("MODEL", "openai/gpt-6")
    monkeypatch.setenv("MODEL_CHEAP", "openai/gpt-6-mini")
    loaded = settings.load()
    assert (loaded.model_writing, loaded.model_design, loaded.model_cheap) == (
        "openai/gpt-6",
        "openai/gpt-6",
        "openai/gpt-6-mini",
    )


def test_unset_model_keeps_the_pins(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("MODEL", "MODEL_WRITING", "MODEL_DESIGN", "MODEL_CHEAP"):
        monkeypatch.delenv(name, raising=False)
    loaded = settings.load()
    assert loaded.model_writing == settings.Settings.model_writing
    assert loaded.model_cheap == settings.Settings.model_cheap
