"""Phase 29 (item A1): the SQL store keeps the file store's promises, and the
one tenant wrapper keeps every user to their own decks. Runs on the file
store, SQLite, and Postgres when TEST_DATABASE_URL is set (tests/stores.py)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from engine import Brief, Composed, Kept, LedgerEntry, Question
from lib.result import Err, Ok
from store.files import UNDO_STEPS, Avatar, NoDeckError, Store
from store.models import BlobRow, LedgerRow
from store.sql import SqlStore, direct_url, driver_url
from store.tenant import AnyStore, Tenant
from tests.stores import STORES, make_store

each_store = pytest.mark.parametrize("kind", STORES)
sql_only = pytest.mark.parametrize("kind", [k for k in STORES if k != "files"])

PNG = b"\x89PNG\r\n\x1a\n-a-screenshot"


def _brief() -> Brief:
    return Brief(id="", prompt="A seed pitch for Flakeguard")


def _two_users(store: AnyStore) -> tuple[Tenant, Tenant]:
    store.upsert_user("userA", "a@example.com", "A")
    store.upsert_user("userB", "b@example.com", "B")
    return store.tenant("userA"), store.tenant("userB")


def _entry(deck_id: str, cost: float, at: datetime | None = None) -> LedgerEntry:
    return LedgerEntry(
        at=at or datetime.now(UTC), deck_id=deck_id, stage="compose", model="m", cost_usd=cost
    )


def _blobs(store: AnyStore) -> int:
    assert isinstance(store, SqlStore)
    with store.engine.connect() as conn:
        return int(conn.scalar(select(func.count()).select_from(BlobRow)) or 0)


# the tenant wrapper ----------------------------------------------------------


@each_store
def test_another_users_deck_is_a_missing_deck_on_every_method(tmp_path: Path, kind: str) -> None:
    store = make_store(kind, tmp_path)
    a, b = _two_users(store)
    deck = a.create(_brief())
    a.append_event(deck.id, {"type": "stage"})
    a.save_kept(deck.id, "s01", Kept(Composed("<p>x</p>", ""), "authored"))
    a.save_export(deck.id, "export-send.html", "<html></html>")
    a.snapshot(deck.id, "Generated")
    assert a.exists(deck.id) and a.read(deck.id).owner_id == "userA"
    assert [d.id for d in a.all()] == [deck.id]

    assert not b.exists(deck.id)
    assert b.all() == []
    assert b.slide_png(deck.id, "s01") is None
    assert b.export(deck.id, "export-send.html") is None
    assert b.history(deck.id).labels == []
    raising: list[Callable[[], object]] = [
        lambda: b.read(deck.id),
        lambda: b.write(deck, read_version=deck.version),
        lambda: b.update(deck.id, title="mine now"),
        lambda: b.questions(deck.id),
        lambda: b.save_questions(deck.id, []),
        lambda: b.append_event(deck.id, {"type": "x"}),
        lambda: b.events(deck.id),
        lambda: b.append_ledger(deck.id, [_entry(deck.id, 1.0)]),
        lambda: b.ledger(deck.id),
        lambda: b.slides_dir(deck.id),
        lambda: b.kept(deck.id),
        lambda: b.save_kept(deck.id, "s01", Kept(Composed("", ""), "authored")),
        lambda: b.drop_kept(deck.id, "s01"),
        lambda: b.save_export(deck.id, "export-send.html", "pwned"),
        lambda: b.abort(deck.id),
        lambda: b.aborted(deck.id),
        lambda: b.clear_abort(deck.id),
        lambda: b.snapshot(deck.id, "x"),
        lambda: b.restore(deck.id, 0),
        lambda: b.busy(deck.id),
        lambda: b.enqueue("build", deck.id),
    ]
    for call in raising:
        with pytest.raises(NoDeckError):
            call()
    # Nothing B tried landed, and a missing deck looks the same to B.
    assert a.read(deck.id).title == deck.title and not a.aborted(deck.id)
    assert a.export(deck.id, "export-send.html") == b"<html></html>"
    assert not a.busy(deck.id) and store._jobs("queued") == []
    assert not b.exists("nosuchdeck")
    with pytest.raises(NoDeckError):
        b.read("nosuchdeck")
    # Deleting B touches nothing of A's.
    store.delete_user("userB")
    assert a.exists(deck.id)


@each_store
def test_a_tenant_needs_a_user_and_cannot_give_its_deck_away(tmp_path: Path, kind: str) -> None:
    store = make_store(kind, tmp_path)
    a, b = _two_users(store)
    with pytest.raises(ValueError):
        store.tenant("")
    deck = a.create(_brief())
    a.update(deck.id, owner_id="userB")
    a.write(deck.model_copy(update={"owner_id": "userB"}), read_version=a.read(deck.id).version)
    assert a.exists(deck.id) and not b.exists(deck.id)
    unowned = store.create(_brief())  # a local run's deck, no account
    assert not a.exists(unowned.id) and store.exists(unowned.id)


@each_store
def test_jobs_carry_the_owner(tmp_path: Path, kind: str) -> None:
    store = make_store(kind, tmp_path)
    a, _ = _two_users(store)
    deck = a.create(_brief())
    job = a.enqueue("build", deck.id)
    assert job.user_id == "userA"
    claimed = store.claim()
    assert claimed is not None and claimed.user_id == "userA"


# users, spend, cascade --------------------------------------------------------


@each_store
def test_users_get_an_avatar_and_keep_their_name(tmp_path: Path, kind: str) -> None:
    store = make_store(kind, tmp_path)
    made = store.upsert_user("u1", "a@example.com", "Ada")
    assert made.avatar.style == "notionists" and made.avatar.seed
    again = store.upsert_user("u1", "new@example.com", "Token Name")
    assert again.name == "Ada" and again.email == "new@example.com"
    assert again.avatar == made.avatar
    face = Avatar(style="lorelei", seed="s", options={"backgroundColor": ["b6e3f4"]})
    changed = store.update_user("u1", name="Ada L", avatar=face)
    assert changed is not None and changed.name == "Ada L"
    assert store.get_user("u1") == changed
    assert store.get_user("nobody") is None
    assert store.update_user("nobody", name="x") is None


@each_store
def test_daily_spend_counts_today_and_only_this_user(tmp_path: Path, kind: str) -> None:
    store = make_store(kind, tmp_path)
    a, b = _two_users(store)
    mine, theirs = a.create(_brief()), b.create(_brief())
    yesterday = datetime.now(UTC) - timedelta(days=1, hours=1)
    a.append_ledger(mine.id, [_entry(mine.id, 0.25), _entry(mine.id, 0.5)])
    a.append_ledger(mine.id, [_entry(mine.id, 9.0, at=yesterday)])
    b.append_ledger(theirs.id, [_entry(theirs.id, 4.0)])
    assert a.daily_spend() == pytest.approx(0.75)
    assert store.daily_spend("userB") == pytest.approx(4.0)
    assert store.daily_spend("nobody") == 0.0
    assert [e.cost_usd for e in a.ledger(mine.id)] == [0.25, 0.5, 9.0]


@sql_only
def test_every_ledger_row_carries_the_owner(tmp_path: Path, kind: str) -> None:
    store = make_store(kind, tmp_path)
    assert isinstance(store, SqlStore)
    a, _ = _two_users(store)
    deck = a.create(_brief())
    a.append_ledger(deck.id, [_entry(deck.id, 0.1), _entry(deck.id, 0.2)])
    with store.engine.connect() as conn:
        owners = conn.scalars(select(LedgerRow.user_id)).all()
    assert owners == ["userA", "userA"]


@each_store
def test_deleting_a_user_removes_their_decks_and_everything_under_them(
    tmp_path: Path, kind: str
) -> None:
    store = make_store(kind, tmp_path)
    a, b = _two_users(store)
    deck, kept = a.create(_brief()), b.create(_brief())
    for t, d in ((a, deck), (b, kept)):
        t.save_questions(d.id, [Question(fills="ask", question="?", suggestions=["1", "2", "3"])])
        t.append_event(d.id, {"type": "stage"})
        t.append_ledger(d.id, [_entry(d.id, 1.0)])
        (t.slides_dir(d.id) / "s01.png").write_bytes(PNG + d.id.encode())
        t.save_kept(d.id, "s01", Kept(Composed("<p/>", ""), "authored"))
        t.save_export(d.id, "export.pdf", b"%PDF-shared")  # one blob, two decks
        t.snapshot(d.id, "Generated")
        t.enqueue("build", d.id)

    store.delete_user("userA")
    assert store.get_user("userA") is None
    assert not store.exists(deck.id) and store.all(owner_id="userA") == []
    assert [j.deck_id for j in store._jobs("queued")] == [kept.id]
    assert store.daily_spend("userA") == 0.0
    assert b.export(kept.id, "export.pdf") == b"%PDF-shared"
    assert b.slide_png(kept.id, "s01") == PNG + kept.id.encode()
    if isinstance(store, SqlStore):
        assert _blobs(store) == 2  # B's screenshot and the shared PDF; A's own is gone
        store.delete_user("userB")
        assert _blobs(store) == 0


# blobs ------------------------------------------------------------------------


@sql_only
def test_a_file_many_versions_share_is_stored_once_and_orphans_go(
    tmp_path: Path, kind: str
) -> None:
    store = make_store(kind, tmp_path)
    assert isinstance(store, SqlStore)
    a, _ = _two_users(store)
    deck = a.create(_brief())
    a.save_export(deck.id, "export-send.html", "<html>v1</html>")
    for n in range(5):
        a.snapshot(deck.id, f"op {n}")
    assert _blobs(store) == 1
    a.save_export(deck.id, "export-send.html", "<html>v2</html>")
    assert _blobs(store) == 2  # v1 is still held by the versions
    assert isinstance(a.restore(deck.id, 0), Ok)
    assert a.export(deck.id, "export-send.html") == b"<html>v1</html>"
    assert _blobs(store) == 1  # v2 was never a version: nothing links it now


@each_store
def test_a_kept_slide_keeps_its_screenshot_and_a_dropped_one_loses_it(
    tmp_path: Path, kind: str
) -> None:
    store = make_store(kind, tmp_path)
    a, _ = _two_users(store)
    deck = a.create(_brief())
    (a.slides_dir(deck.id) / "s02.png").write_bytes(PNG)
    a.save_kept(deck.id, "s02", Kept(Composed("<h1>x</h1>", "h1{}"), "authored"))
    assert a.slide_png(deck.id, "s02") == PNG
    assert a.kept(deck.id)["s02"].composed == Composed("<h1>x</h1>", "h1{}")
    assert a.slide_png(deck.id, "../s02") is None and a.export(deck.id, "../x") is None
    a.drop_kept(deck.id, "s02")
    assert a.slide_png(deck.id, "s02") is None and a.kept(deck.id) == {}


# parity with the file store ---------------------------------------------------


@each_store
def test_a_stale_write_is_refused(tmp_path: Path, kind: str) -> None:
    store = make_store(kind, tmp_path)
    deck = store.create(_brief())
    first = store.write(deck.model_copy(update={"title": "one"}), read_version=deck.version)
    assert isinstance(first, Ok) and first.value.version == deck.version + 1
    stale = store.write(deck.model_copy(update={"title": "two"}), read_version=deck.version)
    assert isinstance(stale, Err) and store.read(deck.id).title == "one"


def _undo_trace(store: AnyStore) -> list[object]:
    """One run of snapshots, undos and redos; what each step left behind."""
    deck = store.create(_brief())
    out: list[object] = []
    for n in range(3):
        store.update(deck.id, title=f"t{n}")
        store.save_export(deck.id, "export-send.html", f"v{n}")
        out.append(store.snapshot(deck.id, f"op {n}").model_dump())
    for to in (1, 0, -1, 2, 3):
        moved = store.restore(deck.id, to)
        out.append(moved.value.model_dump() if isinstance(moved, Ok) else moved.error)
        out += [store.read(deck.id).title, store.export(deck.id, "export-send.html")]
    store.restore(deck.id, 0)
    out.append(store.snapshot(deck.id, "branch").model_dump())  # drops the two ahead
    version = store.read(deck.id).version
    store.restore(deck.id, 0)
    out.append(store.read(deck.id).version == version + 1)  # a restore moves forward
    stale = store.write(store.read(deck.id), read_version=version)
    out.append(isinstance(stale, Err))
    for n in range(UNDO_STEPS + 3):
        store.snapshot(deck.id, f"more {n}")
    out.append(store.history(deck.id).model_dump())
    return out


@sql_only
def test_versions_and_undo_match_the_file_store(tmp_path: Path, kind: str) -> None:
    files = _undo_trace(Store(tmp_path / "files"))
    assert _undo_trace(make_store(kind, tmp_path)) == files
    assert files[3:6] == [{"labels": ["op 0", "op 1", "op 2"], "at": 1}, "t1", b"v1"]


@each_store
def test_events_are_numbered_and_resume_after_a_seq(tmp_path: Path, kind: str) -> None:
    store = make_store(kind, tmp_path)
    deck = store.create(_brief())
    seqs = [store.append_event(deck.id, {"type": "stage", "n": n}) for n in range(3)]
    assert seqs == [1, 2, 3]
    assert store.events(deck.id, after=1) == [
        {"seq": 2, "type": "stage", "n": 1},
        {"seq": 3, "type": "stage", "n": 2},
    ]


@each_store
def test_a_job_is_claimed_exactly_once_by_racing_workers(tmp_path: Path, kind: str) -> None:
    store = make_store(kind, tmp_path)
    decks = [store.create(_brief()) for _ in range(6)]
    for d in decks:
        store.enqueue("build", d.id)
    store.enqueue("build", decks[0].id)  # a double click is one job
    claimed: list[str] = []
    lock = threading.Lock()

    def work() -> None:
        while (job := store.claim()) is not None:
            with lock:
                claimed.append(job.id)

    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(claimed) == 6 and len(set(claimed)) == 6
    assert all(store.busy(d.id) for d in decks)
    stale = store.requeue_stale(now=10**12)
    assert len(stale) == 6 and not store._jobs("running")
    while (job := store.claim()) is not None:
        assert job.attempts == 2
        store.finish(job)
    assert not any(store.busy(d.id) for d in decks)


def test_urls_use_psycopg_and_migrations_skip_the_pooler() -> None:
    pooled = "postgresql://u:p@ep-cool-1-pooler.eu.aws.neon.tech/app?sslmode=require"
    assert driver_url(pooled).startswith("postgresql+psycopg://u:p@ep-cool-1-pooler.")
    assert direct_url(pooled) == (
        "postgresql+psycopg://u:p@ep-cool-1.eu.aws.neon.tech/app?sslmode=require"
    )
    assert driver_url("sqlite:///x.db") == "sqlite:///x.db"
