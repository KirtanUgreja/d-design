"""`cli bakeoff` (phase 39 -> 8): each model builds the same briefs under its
own label, and one wall follows. The build itself is faked: no credit."""

from __future__ import annotations

import argparse

import pytest

import cli
import settings


def test_each_model_builds_the_same_briefs_under_its_own_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[str, str, int, str]] = []

    async def fake_build(cfg: settings.Settings, args: argparse.Namespace) -> int:
        label = args.label or args.model.split("/")[-1]
        seen.append((args.model, label, args.briefs, args.image_model))
        return 0

    monkeypatch.setattr(cli, "_build", fake_build)
    monkeypatch.setattr(cli, "_wall", lambda run, seed, baselines: 0)
    code = cli.main(
        ["bakeoff", "--run", "b", "--models", "x/one, y/two", "--briefs", "2", "--image-model", "i"]
    )
    assert code == 0
    assert seen == [("x/one", "one", 2, "i"), ("y/two", "two", 2, "i")]
