"""The API (docs/v4/engine.md -> API surface): thin routes that enqueue and
read. It never calls a model or a browser — the worker does (worker.py). Each
route parses its input once, at entry; every error the UI can show is human
copy, never an exception string.

    cd api && uv run uvicorn app:app --port 8000

ponytail: no auth until phase 29; the decks are whoever-can-reach-localhost's.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import FastAPI, Header, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

import ops
import settings
from engine import Brief, Deck, Question, interview
from engine.compose import preview
from lib.result import Ok
from looks import theme_of, with_language
from store.files import History, Store

FINAL = {"ready", "error", "aborted"}
PREVIEWS = ("preview-1.png", "preview-2.png", "preview-3.png")
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


def create_app(store: Store) -> FastAPI:
    api = FastAPI(title="d-design", version="0.4.0")
    missing = "There's no deck here. It may have been deleted."

    def out(deck: Deck) -> DeckOut:
        return DeckOut(deck=deck, questions=store.questions(deck.id), pending=_pending(deck))

    @api.post("/api/decks", status_code=201)
    def create(body: CreateDeck) -> DeckOut:
        brief = Brief(
            id="new",
            prompt=body.prompt.strip(),
            deck_type=body.deck_type,
            tone=body.tone,
            audience=body.audience,
            ask=body.ask,
            slide_count=body.slide_count,
        )
        deck = store.create(brief)
        store.enqueue("interview", deck.id)
        return out(deck)

    @api.get("/api/decks")
    def listing() -> list[Deck]:
        return [
            d.model_copy(update={"slides": []}) for d in store.all()
        ]  # thumbnails, not payloads

    @api.get("/api/decks/{deck_id}", response_model=None)
    def read(deck_id: str) -> DeckOut | JSONResponse:
        if not store.exists(deck_id):
            return _problem(404, missing)
        return out(store.read(deck_id))

    @api.post("/api/decks/{deck_id}/interview", response_model=None)
    def answer(deck_id: str, body: Answers) -> DeckOut | JSONResponse:
        if not store.exists(deck_id):
            return _problem(404, missing)
        deck = store.read(deck_id)
        if deck.status not in ("brief", "interview"):
            return _problem(409, "The interview is already done for this deck.")
        qs = store.questions(deck_id)
        given = [] if body.skip else list(zip(qs, body.answers, strict=False))
        brief = interview.apply(deck.brief, given)
        store.update(deck_id, brief=brief, status="outline")
        store.enqueue("outline", deck_id)
        return out(store.read(deck_id))

    @api.patch("/api/decks/{deck_id}/outline", response_model=None)
    def edit(deck_id: str, body: OutlineEdit) -> DeckOut | JSONResponse:
        if not store.exists(deck_id):
            return _problem(404, missing)
        deck = store.read(deck_id)
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
        saved = store.write(
            deck.model_copy(update={"storyline": story, "facts": facts}), read_version=body.version
        )
        if not isinstance(saved, Ok):
            return _problem(409, "Someone else changed this outline. Reload to see it.")
        return out(store.read(deck_id))

    @api.post("/api/decks/{deck_id}/build", response_model=None)
    def build(deck_id: str) -> DeckOut | JSONResponse:
        if not store.exists(deck_id):
            return _problem(404, missing)
        deck = store.read(deck_id)
        if deck.storyline is None or deck.status not in ("approve", "building", "aborted"):
            return _problem(409, "Approve an outline first.")
        if _pending(deck):
            return _problem(409, "Some numbers have no source. Keep or cut them first.")
        store.enqueue("build", deck_id)  # a double click enqueues one job
        return out(deck)

    @api.post("/api/decks/{deck_id}/build/abort", response_model=None)
    def abort(deck_id: str) -> DeckOut | JSONResponse:
        if not store.exists(deck_id):
            return _problem(404, missing)
        store.abort(deck_id)
        return out(store.read(deck_id))

    @api.get("/api/decks/{deck_id}/events", response_model=None)
    async def events(
        deck_id: str,
        last_event_id: int = Header(default=0, alias="Last-Event-ID"),
        after: int = Query(default=0, ge=0),
    ) -> StreamingResponse | JSONResponse:
        """SSE that tails events.jsonl. A reconnect sends Last-Event-ID (or
        ?after=) and gets every event since, so there is no gap."""
        if not store.exists(deck_id):
            return _problem(404, missing)
        since = max(last_event_id, after)

        async def stream() -> AsyncIterator[str]:
            seen = since
            while True:
                for event in store.events(deck_id, seen):
                    seen = int(str(event["seq"]))
                    kind = event.get("type", "message")
                    yield f"id: {seen}\nevent: {kind}\ndata: {json.dumps(event)}\n\n"
                if store.read(deck_id).status in FINAL and not store.events(deck_id, seen):
                    return
                await asyncio.sleep(POLL_S)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @api.get("/api/decks/{deck_id}/slides/{slide_id}/thumb.png", response_model=None)
    def thumb(deck_id: str, slide_id: str) -> FileResponse | JSONResponse:
        if not store.exists(deck_id) or not slide_id.isalnum():
            return _problem(404, missing)
        path = store.slides_dir(deck_id) / f"{slide_id}.png"
        if not path.exists():
            return _problem(404, "That slide isn't ready yet.")
        return FileResponse(path, media_type="image/png")

    @api.get("/api/decks/{deck_id}/export.html", response_model=None)
    def export_html(
        deck_id: str, flavour: Literal["present", "send"] = "present"
    ) -> HTMLResponse | JSONResponse:
        if not store.exists(deck_id):
            return _problem(404, missing)
        path = store.dir(deck_id) / f"export-{flavour}.html"
        if not path.exists():
            return _problem(404, "The deck isn't built yet.")
        # The export carries its own CSP; this header repeats the strictest part.
        return HTMLResponse(
            path.read_text(),
            headers={"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"},
        )

    @api.get("/api/decks/{deck_id}/export.pdf", response_model=None)
    def export_pdf(deck_id: str) -> Response | JSONResponse:
        if not store.exists(deck_id):
            return _problem(404, missing)
        path = store.dir(deck_id) / "export.pdf"
        if not path.exists():
            return _problem(404, "The deck isn't built yet.")
        return Response(path.read_bytes(), media_type="application/pdf")

    # --- the style card (phase 39): one generated style, changeable, never a menu ---

    @api.get("/api/decks/{deck_id}/style", response_model=None)
    def style(deck_id: str) -> StyleCard | JSONResponse:
        if not store.exists(deck_id):
            return _problem(404, missing)
        deck = store.read(deck_id)
        if not deck.language:
            return _problem(404, "The style is drawn with the outline.")
        c = preview.card(theme_of(deck))
        names = [n for n in PREVIEWS if (store.dir(deck_id) / n).exists()]
        return StyleCard(**c.__dict__, previews=names)

    @api.get("/api/decks/{deck_id}/style/{name}", response_model=None)
    def style_thumb(deck_id: str, name: str) -> FileResponse | JSONResponse:
        if not store.exists(deck_id) or name not in (
            "preview-1.png",
            "preview-2.png",
            "preview-3.png",
        ):
            return _problem(404, missing)
        path = store.dir(deck_id) / name
        if not path.exists():
            return _problem(404, "That preview isn't drawn yet.")
        return FileResponse(path, media_type="image/png")

    @api.post("/api/decks/{deck_id}/style", response_model=None)
    def another_style(deck_id: str) -> DeckOut | JSONResponse:
        """Another style: a new language and look, never the one just shown;
        the thumbnails are redrawn by the worker for free."""
        if not store.exists(deck_id):
            return _problem(404, missing)
        deck = store.read(deck_id)
        if deck.status != "approve":
            return _problem(409, "The style can change until the build starts.")
        if store.busy(deck_id):
            return _problem(409, "The last style is still being drawn.")
        for old in PREVIEWS:
            (store.dir(deck_id) / old).unlink(missing_ok=True)
        shown = frozenset({deck.language} if deck.language else set())
        deck = store.update(deck_id, look_nonce=deck.look_nonce + 1, palette_nonce=0)
        with_language(store, deck, exclude=shown)
        store.enqueue("style", deck_id)
        return out(store.read(deck_id))

    # --- the editor (phase 28): each change is an edit job; undo is file-only ---

    def editable(deck_id: str) -> JSONResponse | None:
        if not store.exists(deck_id):
            return _problem(404, missing)
        if store.read(deck_id).status != "ready":
            return _problem(409, "This deck can't be edited until it is built.")
        return None

    def queue(deck_id: str, op: ops.Op) -> DeckOut:
        store.enqueue("edit", deck_id, op.model_dump_json())
        return out(store.read(deck_id))

    @api.patch("/api/decks/{deck_id}/slides/{slide_id}/fields", response_model=None)
    def edit_text(deck_id: str, slide_id: str, body: FieldText) -> DeckOut | JSONResponse:
        if (no := editable(deck_id)) or not slide_id.isalnum():
            return no or _problem(404, missing)
        return queue(deck_id, ops.TextEdit(slide=slide_id, field=body.field, text=body.text))

    @api.post("/api/decks/{deck_id}/reorder", response_model=None)
    def reorder(deck_id: str, body: Order) -> DeckOut | JSONResponse:
        return editable(deck_id) or queue(deck_id, ops.Reorder(slides=body.slides))

    @api.delete("/api/decks/{deck_id}/slides/{slide_id}", response_model=None)
    def delete(deck_id: str, slide_id: str) -> DeckOut | JSONResponse:
        if (no := editable(deck_id)) or not slide_id.isalnum():
            return no or _problem(404, missing)
        return queue(deck_id, ops.Delete(slide=slide_id))

    @api.post("/api/decks/{deck_id}/recolour", response_model=None)
    def recolour(deck_id: str) -> DeckOut | JSONResponse:
        return editable(deck_id) or queue(deck_id, ops.Recolour())

    @api.post("/api/decks/{deck_id}/slides/{slide_id}/fit", response_model=None)
    def fit(deck_id: str, slide_id: str) -> DeckOut | JSONResponse:
        if (no := editable(deck_id)) or not slide_id.isalnum():
            return no or _problem(404, missing)
        return queue(deck_id, ops.Fit(slide=slide_id))

    @api.get("/api/decks/{deck_id}/history", response_model=None)
    def history(deck_id: str) -> History | JSONResponse:
        if not store.exists(deck_id):
            return _problem(404, missing)
        return store.history(deck_id)

    def step(deck_id: str, by: int) -> History | JSONResponse:
        if not store.exists(deck_id):
            return _problem(404, missing)
        if store.busy(deck_id):
            return _problem(409, "A change is still being made. Undo once it lands.")
        moved = store.restore(deck_id, store.history(deck_id).at + by)
        return moved.value if isinstance(moved, Ok) else _problem(409, moved.error)

    @api.post("/api/decks/{deck_id}/undo", response_model=None)
    def undo(deck_id: str) -> History | JSONResponse:
        return step(deck_id, -1)

    @api.post("/api/decks/{deck_id}/redo", response_model=None)
    def redo(deck_id: str) -> History | JSONResponse:
        return step(deck_id, +1)

    return api


app = create_app(Store(settings.load().data_dir))
