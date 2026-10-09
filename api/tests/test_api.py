"""Phase 27: the API, the store and the worker, offline. The model is faked;
no credit is spent (docs/v4/plan/27-app-create-flow.md -> Verify)."""

from __future__ import annotations

import asyncio
import base64
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import looks
import worker
from app import LOCAL_USER, create_app
from benchtools import files
from engine import Fact, Kept, Seam
from engine.content.interview import Question
from store.tenant import AnyStore
from tests.fakes import Studio, _no_sleep
from tests.stores import STORES, make_store

each_store = pytest.mark.parametrize("kind", STORES)


def _client(tmp_path: Path, kind: str = "files") -> tuple[TestClient, AnyStore]:
    store = make_store(kind, tmp_path)
    return TestClient(create_app(store)), store


def _approved_deck(store: AnyStore, slides: int = 3) -> str:
    """A deck as the outline job leaves it: an outline, waiting for approval."""
    item = files.load("pitch-devtools")
    assert item.outline is not None
    store.upsert_user(LOCAL_USER, "", "You")  # the local run's one user owns it
    deck = store.create(item.brief, owner_id=LOCAL_USER)
    story = item.outline.model_copy(update={"slides": item.outline.slides[:slides]})
    store.update(deck.id, storyline=story, status="approve")
    return deck.id


@each_store
def test_create_reads_and_a_missing_deck_is_human(tmp_path: Path, kind: str) -> None:
    client, store = _client(tmp_path, kind)
    made = client.post("/api/decks", json={"prompt": "A seed pitch for Flakeguard"})
    assert made.status_code == 201
    deck_id = made.json()["deck"]["id"]
    assert client.get(f"/api/decks/{deck_id}").json()["deck"]["status"] == "brief"
    assert [j.kind for j in store._jobs("queued")] == ["interview"]
    missing = client.get("/api/decks/nope")
    assert missing.status_code == 404 and "deck" in missing.json()["error"]
    assert client.post("/api/decks", json={"prompt": ""}).status_code == 422


@each_store
def test_a_double_click_on_build_enqueues_one_job(tmp_path: Path, kind: str) -> None:
    client, store = _client(tmp_path, kind)
    deck_id = _approved_deck(store)
    assert client.post(f"/api/decks/{deck_id}/build").status_code == 200
    assert client.post(f"/api/decks/{deck_id}/build").status_code == 200
    assert [j.kind for j in store._jobs("queued")] == ["build"]


@each_store
def test_unsourced_numbers_block_the_build_until_decided(tmp_path: Path, kind: str) -> None:
    client, store = _client(tmp_path, kind)
    deck_id = _approved_deck(store)
    deck = store.read(deck_id)
    assert deck.storyline is not None
    used = deck.storyline.slides[1].fields[0]
    fact = Fact(id="i1", text="40% faster", value="40%", source="illustrative")
    slides = list(deck.storyline.slides)
    slides[1] = slides[1].model_copy(
        update={"fields": [used.model_copy(update={"fact_ids": ["i1"]}), *slides[1].fields[1:]]}
    )
    store.update(
        deck_id, facts=[fact], storyline=deck.storyline.model_copy(update={"slides": slides})
    )
    blocked = client.post(f"/api/decks/{deck_id}/build")
    assert blocked.status_code == 409 and "source" in blocked.json()["error"]
    version = store.read(deck_id).version
    stale = client.patch(
        f"/api/decks/{deck_id}/outline", json={"version": version - 1, "decisions": {}}
    )
    assert stale.status_code == 409
    ok = client.patch(
        f"/api/decks/{deck_id}/outline",
        json={"version": version, "decisions": {"i1": "approved"}},
    )
    assert ok.status_code == 200 and ok.json()["pending"] == []
    assert client.post(f"/api/decks/{deck_id}/build").status_code == 200


@each_store
def test_sse_resumes_from_last_event_id_without_a_gap(tmp_path: Path, kind: str) -> None:
    client, store = _client(tmp_path, kind)
    deck_id = _approved_deck(store)
    for n in range(1, 4):
        store.append_event(deck_id, {"type": "stage", "n": n})
    store.update(deck_id, status="ready")
    body = client.get(f"/api/decks/{deck_id}/events", headers={"Last-Event-ID": "1"}).text
    ids = [int(line[4:]) for line in body.splitlines() if line.startswith("id: ")]
    assert ids == [2, 3]
    data = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
    assert [d["n"] for d in data] == [2, 3]


@each_store
def test_a_job_is_claimed_once_and_a_dead_worker_is_replaced(tmp_path: Path, kind: str) -> None:
    store = make_store(kind, tmp_path)
    deck_id = _approved_deck(store)
    store.enqueue("build", deck_id)
    first = store.claim()
    assert first is not None and store.claim() is None
    assert store.requeue_stale() == []  # it is still beating
    assert [j.id for j in store.requeue_stale(now=10**12)] == [first.id]
    again = store.claim()
    assert again is not None and again.id == first.id and again.attempts == 2


def _run_worker(store: AnyStore, transport: Studio) -> bool:
    return asyncio.run(
        worker.once(
            store,
            make_seam=lambda deck_id: Seam(
                api_key="k", transport=transport, sleep=_no_sleep, deck_id=deck_id
            ),
            writing="w",
            design="d",
            budget_usd=1.0,
        )
    )


@each_store
def test_the_worker_builds_a_deck_end_to_end(tmp_path: Path, kind: str) -> None:
    client, store = _client(tmp_path, kind)
    deck_id = _approved_deck(store)
    client.post(f"/api/decks/{deck_id}/build")
    assert _run_worker(store, Studio())
    deck = client.get(f"/api/decks/{deck_id}").json()["deck"]
    assert deck["status"] == "ready" and len(deck["slides"]) == 3
    kinds = [e["type"] for e in store.events(deck_id)]
    assert kinds.count("slide_ready") == 3 and kinds[-1] == "done"
    first = deck["slides"][0]["id"]
    assert (store.slide_png(deck_id, first) or b"").startswith(b"\x89PNG")
    assert b"Content-Security-Policy" in (store.export(deck_id, "export-send.html") or b"")
    assert (store.export(deck_id, "export.pdf") or b"").startswith(b"%PDF")
    assert client.get(f"/api/decks/{deck_id}/slides/{first}/thumb.png").status_code == 200
    page = client.get(f"/api/decks/{deck_id}/export.html?flavour=send")
    assert page.status_code == 200 and "Content-Security-Policy" in page.text
    assert client.get(f"/api/decks/{deck_id}/export.pdf").content.startswith(b"%PDF")
    assert not _run_worker(store, Studio())  # the queue is empty


@each_store
def test_an_aborted_build_resumes_without_paying_twice(
    tmp_path: Path, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store = _client(tmp_path, kind)
    deck_id = _approved_deck(store, slides=4)
    client.post(f"/api/decks/{deck_id}/build")
    keep = store.save_kept

    def abort_after_cover(deck_id: str, slide_id: str, kept: Kept) -> None:
        keep(deck_id, slide_id, kept)
        store.abort(deck_id)  # the user stops it once the cover is in

    monkeypatch.setattr(store, "save_kept", abort_after_cover)
    _run_worker(store, Studio())
    monkeypatch.undo()
    assert store.read(deck_id).status == "aborted" and len(store.kept(deck_id)) == 1
    cover = next(iter(store.kept(deck_id)))

    client.post(f"/api/decks/{deck_id}/build")
    _run_worker(store, Studio())
    deck = store.read(deck_id)
    assert deck.status == "ready" and len(deck.slides) == 4
    # The ledger over both runs: the cover was composed once, never again.
    covers = [e for e in store.ledger(deck_id) if e.stage == "compose" and e.slide_id == cover]
    assert len(covers) == 1


def test_the_style_card_and_another_style(tmp_path: Path) -> None:
    client, store = _client(tmp_path)
    deck_id = _approved_deck(store, slides=5)
    assert client.get(f"/api/decks/{deck_id}/style").status_code == 404  # not drawn yet
    deck = looks.with_language(store, store.read(deck_id))
    asyncio.run(worker._previews(store, deck))
    card = client.get(f"/api/decks/{deck_id}/style").json()
    assert card["language"] == deck.language and card["name"] and card["previews"]
    first = card["previews"][0]
    shot = client.get(f"/api/decks/{deck_id}/style/{first}")
    assert shot.status_code == 200 and shot.headers["content-type"] == "image/png"
    assert client.get(f"/api/decks/{deck_id}/style/..%2Fdeck.json").status_code == 404
    again = client.post(f"/api/decks/{deck_id}/style")
    assert again.status_code == 200
    assert again.json()["deck"]["language"] != deck.language  # never the style just shown
    assert [j.kind for j in store._jobs("queued")] == ["style"]
    assert client.get(f"/api/decks/{deck_id}/style").json()["previews"] == []
    assert client.post(f"/api/decks/{deck_id}/style").status_code == 409  # still drawing


def test_brand_colours_build_the_palette_around_the_users_colour(tmp_path: Path) -> None:
    from engine.design.color import from_hex

    client, store = _client(tmp_path)
    deck_id = _approved_deck(store, slides=5)
    looks.with_language(store, store.read(deck_id))
    assert client.put(f"/api/decks/{deck_id}/brand", json={"colors": ["red"]}).status_code == 422
    put = client.put(f"/api/decks/{deck_id}/brand", json={"colors": ["#E8541C"]})
    assert put.status_code == 200 and put.json()["deck"]["brief"]["brand"]["colors"] == ["#e8541c"]
    assert [j.kind for j in store._jobs("queued")] == ["style"]  # the thumbnails are redrawn
    accent = from_hex(looks.theme_of(store.read(deck_id)).colors["accent"])
    assert abs(accent.h - from_hex("#e8541c").h) < 2  # the brand's hue, lightness fitted
    again = looks.theme_of(store.read(deck_id).model_copy(update={"palette_nonce": 2}))
    assert abs(from_hex(again.colors["accent"]).h - accent.h) < 2  # new colours keep it


def _png_logo() -> str:
    from PIL import Image, ImageDraw

    out = io.BytesIO()
    img = Image.new("RGBA", (400, 160), (0, 0, 0, 0))
    ImageDraw.Draw(img).rectangle((20, 20, 380, 140), fill=(200, 40, 40, 255))
    img.save(out, "PNG")
    return base64.b64encode(out.getvalue()).decode()


@each_store
def test_a_logo_is_checked_by_the_worker_then_placed_on_the_ends(tmp_path: Path, kind: str) -> None:
    client, store = _client(tmp_path, kind)
    deck_id = _approved_deck(store, slides=3)
    put = client.put(f"/api/decks/{deck_id}/logo", json={"data": _png_logo()})
    assert put.status_code == 200 and put.json()["deck"]["logo"] == "ends"
    assert client.get(f"/api/decks/{deck_id}/logo.png").status_code == 404  # not checked yet
    assert _run_worker(store, Studio())  # the logo job
    assert client.get(f"/api/decks/{deck_id}/logo.png").content.startswith(b"\x89PNG")
    client.post(f"/api/decks/{deck_id}/build")
    assert _run_worker(store, Studio())
    slides = store.read(deck_id).slides
    assert "<dd-logo" in slides[0].html and "<dd-logo" in slides[-1].html
    assert "<dd-logo" not in slides[1].html


@each_store
def test_a_file_that_is_not_a_logo_is_refused_in_words(tmp_path: Path, kind: str) -> None:
    client, store = _client(tmp_path, kind)
    deck_id = _approved_deck(store)
    bad = base64.b64encode(b"<html><script>alert(1)</script></html>").decode()
    assert client.put(f"/api/decks/{deck_id}/logo", json={"data": bad}).status_code == 200
    assert _run_worker(store, Studio())
    deck = store.read(deck_id)
    assert deck.logo == "none" and "can't be used as a logo" in deck.logo_note
    assert (
        client.put(f"/api/decks/{deck_id}/logo", json={"data": "not base64!!"}).status_code == 422
    )


@each_store
def test_a_stopped_deck_is_tried_again_from_the_step_that_failed(tmp_path: Path, kind: str) -> None:
    client, store = _client(tmp_path, kind)
    deck_id = _approved_deck(store)
    store.update(deck_id, status="approve")
    assert client.post(f"/api/decks/{deck_id}/retry").status_code == 409  # not stopped
    # stopped with an outline: the build runs again
    store.update(
        deck_id, status="error", error="The writing service cut its answer short. Try again."
    )
    again = client.post(f"/api/decks/{deck_id}/retry")
    assert again.status_code == 200 and again.json()["deck"]["status"] == "building"
    assert again.json()["deck"]["error"] == ""
    assert [j.kind for j in store._jobs("queued")] == ["build"]
    assert client.post(f"/api/decks/{deck_id}/retry").status_code == 409  # already queued
    # stopped while writing the outline, after the questions: the outline again
    other = store.create(files.load("pitch-devtools").brief, owner_id=LOCAL_USER)
    store.save_questions(
        other.id, [Question(fills="ask", question="What then?", suggestions=["a", "b", "c"])]
    )
    store.update(other.id, status="error", error="x")
    assert client.post(f"/api/decks/{other.id}/retry").json()["deck"]["status"] == "outline"
    # stopped before any question: the interview again
    first = store.create(files.load("pitch-devtools").brief, owner_id=LOCAL_USER)
    store.update(first.id, status="error", error="x")
    assert client.post(f"/api/decks/{first.id}/retry").json()["deck"]["status"] == "brief"
