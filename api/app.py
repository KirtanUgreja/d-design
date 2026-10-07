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

import settings
from engine import Brief, Deck, Question, interview
from lib.result import Ok
from store.files import Store

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


class DeckOut(BaseModel):
    deck: Deck
    questions: list[Question]
    pending: list[str]  # proposed numbers that need a keep-or-cut before the build


class Problem(BaseModel):
    error: str


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

    return api


app = create_app(Store(settings.load().data_dir))
