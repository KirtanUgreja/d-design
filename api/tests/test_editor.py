"""Phase 28: editing without a model. Every change runs QA again, re-exports,
and is a labelled version that undo restores exactly."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import worker
from app import create_app
from engine import Seam
from store.files import UNDO_STEPS, Store
from tests.test_api import _approved_deck
from tests.test_ladder import AlwaysTheSame, _no_sleep


def _work(store: Store) -> None:
    """Run the worker until the queue is empty."""
    while asyncio.run(
        worker.once(
            store,
            make_seam=lambda d: Seam(
                api_key="k", transport=AlwaysTheSame(), sleep=_no_sleep, deck_id=d
            ),
            writing="w",
            design="d",
            budget_usd=1.0,
        )
    ):
        pass


def _built(tmp_path: Path, slides: int = 4) -> tuple[TestClient, Store, str]:
    store = Store(tmp_path / "data")
    client = TestClient(create_app(store))
    deck_id = _approved_deck(store, slides=slides)
    client.post(f"/api/decks/{deck_id}/build")
    _work(store)
    assert store.read(deck_id).status == "ready"
    return client, store, deck_id


def _text(store: Store, deck_id: str, slide: str, field: str) -> str:
    story = store.read(deck_id).storyline
    assert story is not None
    plan = next(p for p in story.slides if p.id == slide)
    return next(f.text for f in plan.fields if f.name == field)


def test_a_text_edit_changes_the_plan_and_the_html_together_and_undo_restores_it(
    tmp_path: Path,
) -> None:
    client, store, deck_id = _built(tmp_path)
    before = _text(store, deck_id, "s02", "headline")
    r = client.patch(
        f"/api/decks/{deck_id}/slides/s02/fields",
        json={"field": "headline", "text": "Flaky tests cost every team a day a week"},
    )
    assert r.status_code == 200
    _work(store)
    assert _text(store, deck_id, "s02", "headline") == "Flaky tests cost every team a day a week"
    slide = next(s for s in store.read(deck_id).slides if s.id == "s02")
    assert "Flaky tests cost every team a day a week" in slide.html
    assert "a day a week" in (store.dir(deck_id) / "export-send.html").read_text()
    assert store.history(deck_id).labels == ["Generated", "Edited text"]

    assert client.post(f"/api/decks/{deck_id}/undo").status_code == 200
    assert _text(store, deck_id, "s02", "headline") == before
    assert "a day a week" not in (store.dir(deck_id) / "export-send.html").read_text()
    assert client.post(f"/api/decks/{deck_id}/undo").status_code == 409  # nothing more
    assert client.post(f"/api/decks/{deck_id}/redo").status_code == 200
    assert _text(store, deck_id, "s02", "headline") == "Flaky tests cost every team a day a week"


def test_recolour_keeps_every_layout_and_runs_qa_on_all_slides(tmp_path: Path) -> None:
    client, store, deck_id = _built(tmp_path)
    old_send = (store.dir(deck_id) / "export-send.html").read_text()
    old_html = [s.html for s in store.read(deck_id).slides]
    client.post(f"/api/decks/{deck_id}/recolour")
    _work(store)
    deck = store.read(deck_id)
    assert deck.palette_nonce == 1
    assert [s.html for s in deck.slides] == old_html  # the layouts are untouched
    assert (store.dir(deck_id) / "export-send.html").read_text() != old_send  # the colours are not
    assert all(s.qa.status == "passed" for s in deck.slides)


def test_the_cover_and_the_ask_stay_where_they_are(tmp_path: Path) -> None:
    client, store, deck_id = _built(tmp_path, slides=5)
    client.delete(f"/api/decks/{deck_id}/slides/s01")
    _work(store)
    assert next(s.id for s in store.read(deck_id).slides) == "s01"
    client.post(
        f"/api/decks/{deck_id}/reorder", json={"slides": ["s01", "s03", "s02", "s04", "s05"]}
    )
    client.delete(f"/api/decks/{deck_id}/slides/s04")
    _work(store)
    assert [s.id for s in store.read(deck_id).slides] == ["s01", "s03", "s02", "s05"]
    refused = [e for e in store.events(deck_id) if e["type"] == "edit_refused"]
    assert len(refused) == 1


def test_an_edit_that_breaks_the_slide_is_flagged_and_fit_repairs_it(tmp_path: Path) -> None:
    client, store, deck_id = _built(tmp_path)
    # Too long for this composition, not for a slide: 40 words, 229 characters.
    long = " ".join((["flaky", "tests", "cost", "teams"] * 10)[:40])
    client.patch(
        f"/api/decks/{deck_id}/slides/s02/fields", json={"field": "headline", "text": long}
    )
    _work(store)
    done = [e for e in store.events(deck_id) if e["type"] == "edit_done"][-1]
    assert done["flagged"] == ["s02"]
    client.post(f"/api/decks/{deck_id}/slides/s02/fit")
    _work(store)
    slide = next(s for s in store.read(deck_id).slides if s.id == "s02")
    assert slide.qa.status == "passed" and slide.origin == "fallback"
    assert store.history(deck_id).labels[-1] == "Fitted a slide"


def test_undo_keeps_the_last_twenty_operations(tmp_path: Path) -> None:
    _, store, deck_id = _built(tmp_path, slides=3)
    for n in range(UNDO_STEPS + 5):
        store.snapshot(deck_id, f"op {n}")
    h = store.history(deck_id)
    assert len(h.labels) == UNDO_STEPS + 1 and h.labels[-1] == f"op {UNDO_STEPS + 4}"
    assert h.at == UNDO_STEPS
