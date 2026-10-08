"""Accounts, tenancy and the cap (phase 29 -> A4): every route refuses a
request with no session, another user's deck is a 404 on every deck route,
the cap fails closed, and deleting an account removes its decks."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app import create_app
from auth import Verifier
from benchtools import files
from engine import LedgerEntry
from store.tenant import AnyStore
from tests.stores import make_store
from tests.test_auth import ISSUER, PUBLIC, _token

VERIFIER = Verifier(lambda _: PUBLIC, issuer=ISSUER)


def _as(user: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(sub=user, email=f'{user}@x.co')}"}


def _setup(tmp_path: Path, cap: float = 3.0) -> tuple[TestClient, AnyStore, str]:
    store = make_store("sql", tmp_path)
    client = TestClient(create_app(store, VERIFIER, daily_cap_usd=cap))
    made = client.post("/api/decks", json={"prompt": "A seed pitch"}, headers=_as("alice"))
    assert made.status_code == 201
    deck_id = str(made.json()["deck"]["id"])
    item = files.load("pitch-devtools")
    assert item.outline is not None
    store.update(deck_id, storyline=item.outline, status="approve")
    return client, store, deck_id


def _routes(client: TestClient) -> list[tuple[str, str]]:
    app = client.app
    out = []
    for route in app.routes:  # type: ignore[attr-defined]
        if isinstance(route, APIRoute) and route.path.startswith("/api/"):
            out += [(m, route.path) for m in sorted(route.methods or ())]
    return out


def _fill(path: str, deck_id: str) -> str:
    path = path.replace("{deck_id}", deck_id).replace("{slide_id}", "s1")
    return re.sub(r"\{name\}", "preview-0-1.png", path)


def test_every_route_refuses_a_request_with_no_session(tmp_path: Path) -> None:
    client, _, deck_id = _setup(tmp_path)
    routes = _routes(client)
    assert len(routes) > 20
    for method, path in routes:
        got = client.request(method, _fill(path, deck_id), json={})
        assert got.status_code == 401, (method, path, got.status_code)
        bad = client.request(
            method, _fill(path, deck_id), json={}, headers={"Authorization": "Bearer forged"}
        )
        assert bad.status_code == 401, (method, path)


def test_another_users_deck_is_missing_on_every_deck_route(tmp_path: Path) -> None:
    client, store, deck_id = _setup(tmp_path)
    before = store.read(deck_id)
    jobs = len(store._jobs("queued"))
    for method, path in _routes(client):
        if "{deck_id}" not in path:
            continue
        got = client.request(method, _fill(path, deck_id), json={}, headers=_as("mallory"))
        # 404 for every route; 422 only where the body is checked before the deck
        assert got.status_code in (404, 422), (method, path, got.status_code)
        assert got.status_code != 200
    after = store.read(deck_id)
    assert after.version == before.version and after.status == before.status
    assert len(store._jobs("queued")) == jobs  # nothing was queued for alice's deck
    listing = client.get("/api/decks", headers=_as("mallory")).json()
    assert listing == []
    assert [d["id"] for d in client.get("/api/decks", headers=_as("alice")).json()] == [deck_id]


def test_the_owner_still_reaches_the_deck(tmp_path: Path) -> None:
    client, _, deck_id = _setup(tmp_path)
    assert client.get(f"/api/decks/{deck_id}", headers=_as("alice")).status_code == 200


def test_the_daily_cap_refuses_and_a_failed_check_refuses_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, deck_id = _setup(tmp_path, cap=0.5)
    spent = LedgerEntry(at=datetime.now(UTC), stage="compose", model="m", cost_usd=0.6)
    store.append_ledger(deck_id, [spent])
    over = client.post("/api/decks", json={"prompt": "Another pitch"}, headers=_as("alice"))
    assert over.status_code == 429
    assert client.post(f"/api/decks/{deck_id}/build", headers=_as("alice")).status_code == 429
    # someone else is not capped by alice's spend
    assert (
        client.post("/api/decks", json={"prompt": "Bob's pitch"}, headers=_as("bob")).status_code
        == 201
    )

    def broken(self: object) -> float:
        raise RuntimeError("database down")

    from store.tenant import Tenant

    monkeypatch.setattr(Tenant, "daily_spend", broken)
    assert (
        client.post("/api/decks", json={"prompt": "Bob again"}, headers=_as("bob")).status_code
        == 503
    )


def test_an_unreachable_jwks_is_a_401(tmp_path: Path) -> None:
    def down(_: str) -> object:
        raise ConnectionError("no route")

    store = make_store("sql", tmp_path)
    client = TestClient(create_app(store, Verifier(down, issuer=ISSUER)))  # type: ignore[arg-type]
    assert client.get("/api/decks", headers=_as("alice")).status_code == 401


def test_deleting_an_account_removes_its_decks(tmp_path: Path) -> None:
    client, store, deck_id = _setup(tmp_path)
    me = client.get("/api/me", headers=_as("alice")).json()
    assert me["email"] == "alice@x.co" and me["avatar"]["seed"]
    assert client.delete("/api/me", headers=_as("alice")).status_code == 204
    assert not store.exists(deck_id)
    assert store.get_user("alice") is None
