"""The bench's own plumbing: briefs load, the wall is blind and complete."""

from __future__ import annotations

from pathlib import Path

from benchtools import files, wall


def test_twelve_briefs_load_and_the_smoke_set_exists() -> None:
    ids = files.brief_ids()
    assert len(ids) == 12
    assert set(files.SMOKE) <= set(ids)
    for brief_id in ids:
        assert files.load(brief_id).brief.id == brief_id


def test_wall_is_blind_and_lists_every_deck(tmp_path: Path) -> None:
    for system, brief in (("engine", "a"), ("oneshot", "a"), ("oneshot", "b")):
        folder = tmp_path / system / brief
        folder.mkdir(parents=True)
        (folder / "01.png").write_bytes(b"")
    decks = wall.collect(tmp_path / "engine", "engine") + wall.collect(
        tmp_path / "oneshot", "oneshot"
    )
    out = tmp_path / "wall.html"
    assert wall.build(decks, out, "t") == 3
    page = out.read_text()
    visible = page.split("<script>")[0]
    assert "oneshot" not in visible and "engine" not in visible
    assert page.count("01.png") == 3


def test_flat_baseline_folders_are_grouped_by_deck(tmp_path: Path) -> None:
    for name in ("crm-launch-deck-01.png", "crm-launch-deck-02.png", "aurora-01.png"):
        (tmp_path / name).write_bytes(b"")
    decks = wall.collect(tmp_path, "v3")
    assert sorted(len(d.images) for d in decks) == [1, 2]
