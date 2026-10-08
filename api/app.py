"""The API (docs/v4/engine.md -> API surface): thin routes that enqueue and
read. It never calls a model or a browser — the worker does (worker.py). Each
route parses its input once, at entry; every error the UI can show is human
copy, never an exception string.

    cd api && uv run uvicorn app:app --port 8000

Who is calling comes from Better Auth's JWT, which the web proxy adds to
every request (auth.py); every deck route goes through the caller's tenant
(store/tenant.py), so another user's deck is a 404. Without a verifier (tests
and local runs only) every request is the one local user.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

import ops
import settings
from auth import Verifier
from engine import Brief, Deck, Question, interview
from engine.compose import preview
from lib.result import Ok
from looks import preview_names, theme_of, with_language
from store.files import Avatar, History, User
from store.tenant import AnyStore, Tenant, open_store

FINAL = {"ready", "error", "aborted"}
POLL_S = 0.4


class CreateDeck(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    deck_type: Literal["pitch", "sales", "launch", "investor_update", "partnership", "auto"] = (
        "auto"
    )
    tone: Literal["plain", "confident", "warm", "bold"] = "confident"
    audience: str = Field(default="", max_length=300)
    ask: str = Field(default="", max_length=300)
    slide_count: int = Field(default=10, ge=3, le=25)


class Answers(BaseModel):
    answers: list[str] = Field(default_factory=list, max_length=10)  # by question order; "" skips
    skip: bool = False


class OutlineEdit(BaseModel):
    version: int
    order: list[str] | None = None  # slide ids, the cover and the ask stay at the ends
    decisions: dict[str, Literal["approved", "rejected"]] = Field(default_factory=dict)


class FieldText(BaseModel):
    field: str = Field(pattern=r"^[\w-]+$")
    text: str = Field(min_length=1, max_length=600)


class Order(BaseModel):
    slides: list[str] = Field(min_length=3, max_length=40)


class DeckOut(BaseModel):
    deck: Deck
    questions: list[Question]
    pending: list[str]  # proposed numbers that need a keep-or-cut before the build


class Problem(BaseModel):
    error: str


class MeOut(BaseModel):
    id: str
    email: str
    name: str
    avatar: Avatar


class MeEdit(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    avatar: Avatar | None = None


class StyleCard(BaseModel):
    """The deck's one generated style, shown at the outline gate (phase 39 -> 6)."""

    language: str
    name: str
    idea: str
    display: str
    text: str
    colors: dict[str, str]
    image_style: str
    previews: list[str]  # thumbnail names, in order; empty while being drawn


def _problem(status: int, message: str) -> JSONResponse:
    return JSONResponse(Problem(error=message).model_dump(), status_code=status)


def _pending(deck: Deck) -> list[str]:
    used = {
        i
        for s in (deck.storyline.slides if deck.storyline else [])
        for f in s.fields
        for i in f.fact_ids
    }
    return [f.id for f in deck.facts if f.status == "proposed" and f.id in used]


LOCAL_USER = "local"  # the one user of a run without accounts (tests, a laptop)


def _caller(request: Request, authorization: str | None = Header(default=None)) -> Tenant:
    """The signed-in user's tenant. Fails closed: no verifier only in a local
    run; any failed check is 401 and no route body runs."""
    store: AnyStore = request.app.state.store
    verifier: Verifier | None = request.app.state.verifier
    if verifier is None:
        if store.get_user(LOCAL_USER) is None:
            store.upsert_user(LOCAL_USER, "", "You")
        return store.tenant(LOCAL_USER)
    got = verifier.verify(authorization)
    if not isinstance(got, Ok):
        raise HTTPException(401, "Sign in to continue.")
    who = got.value
    store.upsert_user(who.id, who.email, who.name)
    return store.tenant(who.id)


Me = Annotated[Tenant, Depends(_caller)]


def create_app(
    store: AnyStore, verifier: Verifier | None = None, *, daily_cap_usd: float = 3.0
) -> FastAPI:
    api = FastAPI(title="d-design", version="0.4.0")
    missing = "There's no deck here. It may have been deleted."

    api.state.store = store
    api.state.verifier = verifier

    def capped(t: Tenant) -> JSONResponse | None:
        """The per-user daily cap. A check that fails refuses (rule 10)."""
        try:
            spent = t.daily_spend()
        except Exception:
            return _problem(503, "We couldn't check today's usage. Try again in a minute.")
        if spent >= daily_cap_usd:
            return _problem(429, "You've reached today's limit. It resets at midnight UTC.")
        return None

    def me_out(user: User) -> MeOut:
        return MeOut(id=user.id, email=user.email, name=user.name, avatar=user.avatar)

    @api.get("/api/me", response_model=None)
    def me(t: Me) -> MeOut | JSONResponse:
        user = store.get_user(t.user_id)
        return me_out(user) if user else _problem(404, "No account here.")

    @api.patch("/api/me", response_model=None)
    def edit_me(t: Me, body: MeEdit) -> MeOut | JSONResponse:
        user = store.update_user(t.user_id, name=body.name, avatar=body.avatar)
        return me_out(user) if user else _problem(404, "No account here.")

    @api.delete("/api/me", status_code=204, response_model=None)
    def delete_me(t: Me) -> Response:
        """Deletes the user's decks, files and history; the web then deletes
        the account itself."""
        store.delete_user(t.user_id)
        return Response(status_code=204)

    def out(t: Tenant, deck: Deck) -> DeckOut:
        return DeckOut(deck=deck, questions=t.questions(deck.id), pending=_pending(deck))

    @api.post("/api/decks", status_code=201, response_model=DeckOut)
    def create(t: Me, body: CreateDeck) -> DeckOut | JSONResponse:
        if no := capped(t):
            return no
        brief = Brief(
            id="new",
            prompt=body.prompt.strip(),
            deck_type=body.deck_type,
            tone=body.tone,
            audience=body.audience,
            ask=body.ask,
            slide_count=body.slide_count,
        )
        deck = t.create(brief)
        t.enqueue("interview", deck.id)
        return out(t, deck)

    @api.get("/api/decks")
    def listing(t: Me) -> list[Deck]:
        return [d.model_copy(update={"slides": []}) for d in t.all()]  # thumbnails, not payloads

    @api.get("/api/decks/{deck_id}", response_model=None)
    def read(t: Me, deck_id: str) -> DeckOut | JSONResponse:
        if not t.exists(deck_id):
            return _problem(404, missing)
        return out(t, t.read(deck_id))

    @api.post("/api/decks/{deck_id}/interview", response_model=None)
    def answer(t: Me, deck_id: str, body: Answers) -> DeckOut | JSONResponse:
        if not t.exists(deck_id):
            return _problem(404, missing)
        if no := capped(t):
            return no
        deck = t.read(deck_id)
        if deck.status not in ("brief", "interview"):
            return _problem(409, "The interview is already done for this deck.")
        qs = t.questions(deck_id)
        given = [] if body.skip else list(zip(qs, body.answers, strict=False))
        brief = interview.apply(deck.brief, given)
        t.update(deck_id, brief=brief, status="outline")
        t.enqueue("outline", deck_id)
        return out(t, t.read(deck_id))

    @api.patch("/api/decks/{deck_id}/outline", response_model=None)
    def edit(t: Me, deck_id: str, body: OutlineEdit) -> DeckOut | JSONResponse:
        if not t.exists(deck_id):
            return _problem(404, missing)
        deck = t.read(deck_id)
        if deck.status != "approve" or deck.storyline is None:
            return _problem(409, "The outline can't be edited right now.")
        story = deck.storyline
        if body.order is not None:
            ids = [s.id for s in story.slides]
            if (
                sorted(body.order) != sorted(ids)
                or body.order[0] != ids[0]
                or body.order[-1] != ids[-1]
            ):
                return _problem(422, "Keep every slide, with the cover first and the ask last.")
            by = {s.id: s for s in story.slides}
            story = story.model_copy(update={"slides": [by[i] for i in body.order]})
        facts = [
            f.model_copy(update={"status": body.decisions[f.id]}) if f.id in body.decisions else f
            for f in deck.facts
        ]
        saved = t.write(
            deck.model_copy(update={"storyline": story, "facts": facts}), read_version=body.version
        )
        if not isinstance(saved, Ok):
            return _problem(409, "Someone else changed this outline. Reload to see it.")
        return out(t, t.read(deck_id))

    @api.post("/api/decks/{deck_id}/build", response_model=None)
    def build(t: Me, deck_id: str) -> DeckOut | JSONResponse:
        if not t.exists(deck_id):
            return _problem(404, missing)
        if no := capped(t):
            return no
        deck = t.read(deck_id)
        if deck.storyline is None or deck.status not in ("approve", "building", "aborted"):
            return _problem(409, "Approve an outline first.")
        if _pending(deck):
            return _problem(409, "Some numbers have no source. Keep or cut them first.")
        t.enqueue("build", deck_id)  # a double click enqueues one job
        return out(t, deck)

    @api.post("/api/decks/{deck_id}/build/abort", response_model=None)
    def abort(t: Me, deck_id: str) -> DeckOut | JSONResponse:
        if not t.exists(deck_id):
            return _problem(404, missing)
        t.abort(deck_id)
        return out(t, t.read(deck_id))

    @api.get("/api/decks/{deck_id}/events", response_model=None)
    async def events(
        t: Me,
        deck_id: str,
        last_event_id: int = Header(default=0, alias="Last-Event-ID"),
        after: int = Query(default=0, ge=0),
    ) -> StreamingResponse | JSONResponse:
        """SSE that tails events.jsonl. A reconnect sends Last-Event-ID (or
        ?after=) and gets every event since, so there is no gap."""
        if not t.exists(deck_id):
            return _problem(404, missing)
        since = max(last_event_id, after)

        async def stream() -> AsyncIterator[str]:
            seen = since
            while True:
                for event in t.events(deck_id, seen):
                    seen = int(str(event["seq"]))
                    kind = event.get("type", "message")
                    yield f"id: {seen}\nevent: {kind}\ndata: {json.dumps(event)}\n\n"
                if t.read(deck_id).status in FINAL and not t.events(deck_id, seen):
                    return
                await asyncio.sleep(POLL_S)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @api.get("/api/decks/{deck_id}/slides/{slide_id}/thumb.png", response_model=None)
    def thumb(t: Me, deck_id: str, slide_id: str) -> Response | JSONResponse:
        if not t.exists(deck_id) or not slide_id.isalnum():
            return _problem(404, missing)
        data = t.slide_png(deck_id, slide_id)
        if data is None:
            return _problem(404, "That slide isn't ready yet.")
        return Response(data, media_type="image/png")

    @api.get("/api/decks/{deck_id}/export.html", response_model=None)
    def export_html(
        t: Me, deck_id: str, flavour: Literal["present", "send"] = "present"
    ) -> HTMLResponse | JSONResponse:
        if not t.exists(deck_id):
            return _problem(404, missing)
        data = t.export(deck_id, f"export-{flavour}.html")
        if data is None:
            return _problem(404, "The deck isn't built yet.")
        # The export carries its own CSP; this header repeats the strictest part.
        return HTMLResponse(
            data.decode(),
            headers={"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"},
        )

    @api.get("/api/decks/{deck_id}/export.pdf", response_model=None)
    def export_pdf(t: Me, deck_id: str) -> Response | JSONResponse:
        if not t.exists(deck_id):
            return _problem(404, missing)
        data = t.export(deck_id, "export.pdf")
        if data is None:
            return _problem(404, "The deck isn't built yet.")
        return Response(data, media_type="application/pdf")

    # --- the style card (phase 39): one generated style, changeable, never a menu ---

    @api.get("/api/decks/{deck_id}/style", response_model=None)
    def style(t: Me, deck_id: str) -> StyleCard | JSONResponse:
        if not t.exists(deck_id):
            return _problem(404, missing)
        deck = t.read(deck_id)
        if not deck.language:
            return _problem(404, "The style is drawn with the outline.")
        c = preview.card(theme_of(deck))
        names = [n for n in preview_names(deck) if t.export(deck_id, n) is not None]
        return StyleCard(**c.__dict__, previews=names)

    @api.get("/api/decks/{deck_id}/style/{name}", response_model=None)
    def style_thumb(t: Me, deck_id: str, name: str) -> Response | JSONResponse:
        if not t.exists(deck_id) or name not in preview_names(t.read(deck_id)):
            return _problem(404, missing)
        data = t.export(deck_id, name)
        if data is None:
            return _problem(404, "That preview isn't drawn yet.")
        return Response(data, media_type="image/png")

    @api.post("/api/decks/{deck_id}/style", response_model=None)
    def another_style(t: Me, deck_id: str) -> DeckOut | JSONResponse:
        """Another style: a new language and look, never the one just shown;
        the thumbnails are redrawn by the worker for free."""
        if not t.exists(deck_id):
            return _problem(404, missing)
        deck = t.read(deck_id)
        if deck.status != "approve":
            return _problem(409, "The style can change until the build starts.")
        if t.busy(deck_id):
            return _problem(409, "The last style is still being drawn.")
        shown = frozenset({deck.language} if deck.language else set())
        deck = t.update(deck_id, look_nonce=deck.look_nonce + 1, palette_nonce=0)
        with_language(store, deck, exclude=shown)
        t.enqueue("style", deck_id)
        return out(t, t.read(deck_id))

    # --- the editor (phase 28): each change is an edit job; undo is file-only ---

    def editable(t: Tenant, deck_id: str) -> JSONResponse | None:
        if not t.exists(deck_id):
            return _problem(404, missing)
        if t.read(deck_id).status != "ready":
            return _problem(409, "This deck can't be edited until it is built.")
        return None

    def queue(t: Tenant, deck_id: str, op: ops.Op) -> DeckOut:
        t.enqueue("edit", deck_id, op.model_dump_json())
        return out(t, t.read(deck_id))

    @api.patch("/api/decks/{deck_id}/slides/{slide_id}/fields", response_model=None)
    def edit_text(t: Me, deck_id: str, slide_id: str, body: FieldText) -> DeckOut | JSONResponse:
        if (no := editable(t, deck_id)) or not slide_id.isalnum():
            return no or _problem(404, missing)
        return queue(t, deck_id, ops.TextEdit(slide=slide_id, field=body.field, text=body.text))

    @api.post("/api/decks/{deck_id}/reorder", response_model=None)
    def reorder(t: Me, deck_id: str, body: Order) -> DeckOut | JSONResponse:
        return editable(t, deck_id) or queue(t, deck_id, ops.Reorder(slides=body.slides))

    @api.delete("/api/decks/{deck_id}/slides/{slide_id}", response_model=None)
    def delete(t: Me, deck_id: str, slide_id: str) -> DeckOut | JSONResponse:
        if (no := editable(t, deck_id)) or not slide_id.isalnum():
            return no or _problem(404, missing)
        return queue(t, deck_id, ops.Delete(slide=slide_id))

    @api.post("/api/decks/{deck_id}/recolour", response_model=None)
    def recolour(t: Me, deck_id: str) -> DeckOut | JSONResponse:
        return editable(t, deck_id) or queue(t, deck_id, ops.Recolour())

    @api.post("/api/decks/{deck_id}/slides/{slide_id}/fit", response_model=None)
    def fit(t: Me, deck_id: str, slide_id: str) -> DeckOut | JSONResponse:
        if (no := editable(t, deck_id)) or not slide_id.isalnum():
            return no or _problem(404, missing)
        return queue(t, deck_id, ops.Fit(slide=slide_id))

    @api.get("/api/decks/{deck_id}/history", response_model=None)
    def history(t: Me, deck_id: str) -> History | JSONResponse:
        if not t.exists(deck_id):
            return _problem(404, missing)
        return t.history(deck_id)

    def step(t: Tenant, deck_id: str, by: int) -> History | JSONResponse:
        if not t.exists(deck_id):
            return _problem(404, missing)
        if t.busy(deck_id):
            return _problem(409, "A change is still being made. Undo once it lands.")
        moved = t.restore(deck_id, t.history(deck_id).at + by)
        return moved.value if isinstance(moved, Ok) else _problem(409, moved.error)

    @api.post("/api/decks/{deck_id}/undo", response_model=None)
    def undo(t: Me, deck_id: str) -> History | JSONResponse:
        return step(t, deck_id, -1)

    @api.post("/api/decks/{deck_id}/redo", response_model=None)
    def redo(t: Me, deck_id: str) -> History | JSONResponse:
        return step(t, deck_id, +1)

    return api


def _app() -> FastAPI:
    """The served app. Accounts are on whenever BETTER_AUTH_URL is set; a run
    without it is a laptop run, and must say so (AUTH_DISABLED=1): an API that
    forgot its auth settings refuses to start rather than serve everyone."""
    cfg = settings.load()
    if cfg.auth_url:
        return create_app(
            open_store(cfg), Verifier.remote(cfg.auth_url), daily_cap_usd=cfg.daily_cap_usd
        )
    if not cfg.auth_disabled:
        raise SystemExit(
            "Set BETTER_AUTH_URL, or AUTH_DISABLED=1 for a local run without accounts."
        )
    return create_app(open_store(cfg), daily_cap_usd=cfg.daily_cap_usd)


app = _app()
