"""Editor operations (docs/v4/plan/28-editor.md): what the API accepts, the
job queue carries, and the worker does. None of them calls a model; each one
ends with QA run again on what it touched and a labelled version for undo."""

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


Op = Annotated[TextEdit | Reorder | Delete | Recolour | Fit, Field(discriminator="kind")]
OP: TypeAdapter[TextEdit | Reorder | Delete | Recolour | Fit] = TypeAdapter(Op)

LABEL = {
    "text": "Edited text",
    "order": "Reordered slides",
    "delete": "Deleted a slide",
    "recolour": "New colours",
    "fit": "Fitted a slide",
}
