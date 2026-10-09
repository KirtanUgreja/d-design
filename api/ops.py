"""Editor operations (docs/v4/plan/28-editor.md): what the API accepts, the
job queue carries, and the worker does. Each one ends with QA run again on
what it touched and a labelled version for undo. Only Ask calls a model, and
it never changes the deck: it makes a proposal the person accepts or not."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter


class TextEdit(BaseModel):
    kind: Literal["text"] = "text"
    slide: str = Field(pattern=r"^\w+$")
    field: str = Field(pattern=r"^[\w-]+$")
    text: str = Field(min_length=1, max_length=600)


class Reorder(BaseModel):
    kind: Literal["order"] = "order"
    slides: list[str]


class Delete(BaseModel):
    kind: Literal["delete"] = "delete"
    slide: str = Field(pattern=r"^\w+$")


class Recolour(BaseModel):
    kind: Literal["recolour"] = "recolour"


class Fit(BaseModel):
    kind: Literal["fit"] = "fit"
    slide: str = Field(pattern=r"^\w+$")


class Ask(BaseModel):
    """A change in words ("make the number the hero"): a proposal, never applied."""

    kind: Literal["ask"] = "ask"
    slide: str = Field(pattern=r"^\w+$")
    instruction: str = Field(min_length=3, max_length=300)


class AskDeck(BaseModel):
    """A change in words for every slide ("bigger headlines, more air"):
    each slide redesigned with it, kept where QA passes, one step to undo
    (owner, 2026-10-09: an edit for the whole deck)."""

    kind: Literal["askdeck"] = "askdeck"
    instruction: str = Field(min_length=3, max_length=300)


class Accept(BaseModel):
    """Apply the slide's waiting proposal."""

    kind: Literal["accept"] = "accept"
    slide: str = Field(pattern=r"^\w+$")


AnyOp = TextEdit | Reorder | Delete | Recolour | Fit | Ask | AskDeck | Accept
Op = Annotated[AnyOp, Field(discriminator="kind")]
OP: TypeAdapter[AnyOp] = TypeAdapter(Op)

LABEL = {
    "text": "Edited text",
    "order": "Reordered slides",
    "delete": "Deleted a slide",
    "recolour": "New colours",
    "fit": "Fitted a slide",
    "ask": "Asked for a change",
    "accept": "Changed a slide by request",
    "askdeck": "Changed the whole deck by request",
}
