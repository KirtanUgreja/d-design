"""Offline stand-ins for the model, one per behaviour the studio must handle.
Each answers by the job its system prompt names: the art director, the
designer, the improver, the repair, the editor."""

from __future__ import annotations

import base64
import io
import json as jsonlib
import re
from dataclasses import dataclass, field

import httpx
from PIL import Image

from benchtools import files
from engine.compose.document import Frame
from engine.studio.design import fallback


async def _no_sleep(_: float) -> None:
    return None


def _ok(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.001},
        },
    )


def _text(user: str, name: str) -> str:
    for line in user.splitlines():
        if line.startswith(f"- {name}: "):
            return str(jsonlib.loads(line.split(": ", 1)[1]))
    return ""


def _names(user: str) -> list[str]:
    return [
        line.split(":")[0].strip("- ").strip()
        for line in user.splitlines()
        if line.startswith("- ") and ': "' in line
    ]


def _job(body: dict[str, object]) -> tuple[str, str]:
    messages = body["messages"]
    assert isinstance(messages, list)
    system = messages[0]["content"]
    system = system if isinstance(system, str) else " ".join(str(p.get("text", "")) for p in system)
    user = messages[-1]["content"]
    user = user if isinstance(user, str) else str(user[0]["text"])
    openings = (
        ("You are the art director", "direct"),
        ("You are the creative director", "improve"),
        ("You repair one slide", "repair"),
        ("You are the design director", "review"),
    )
    job = next((name for opening, name in openings if opening in system), "compose")
    return job, user


def _slide(user: str, *, off_canvas: bool = False) -> str:
    """A clean column of the slide's fields, with every box the slide needs."""
    body = "".join(f'<p class="x" data-field="{n}">{_text(user, n)}</p>' for n in _names(user))
    boxes = ""
    if "chart of" in user or "<dd-chart" in user:
        boxes += '<dd-chart class="v"></dd-chart>'
    if " visual" in user and "dd-visual" in user:
        boxes += '<dd-visual class="v"></dd-visual>'
    if "has a picture" in user or "<dd-image" in user:
        boxes += '<dd-image aspect="3:2" class="i"></dd-image>'
    off = "left:1800px;top:500px;width:900px"
    where = off if off_canvas else "left:160px;top:160px;width:1200px"
    css = (
        f".c{{position:absolute;{where};display:grid;gap:var(--s-3)}}"
        ".x{font-size:var(--t-h2);color:var(--c-ink)}"
        ".v{width:900px;height:480px}.i{width:600px;height:400px}"
    )
    html = f'<section class="s"><div class="c">{body}{boxes}</div></section>'
    return f"```html\n{html}\n```\n```css\n{css}\n```"


@dataclass
class Studio:
    """A model that does every job cleanly: a plan for every slide, then a
    clean slide from the designer, the improver and any repair."""

    calls: list[str] = field(default_factory=list)
    broken: bool = False  # every slide it writes puts its text off the canvas
    prompts: list[str] = field(default_factory=list)  # what the image model was asked
    no_picture: bool = False  # the image model answers with no image

    async def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response:
        assert isinstance(json, dict)
        if json.get("modalities") == ["image", "text"]:
            self.calls.append("image")
            self.prompts.append(str(json["messages"][0]["content"]))
            if self.no_picture:
                return httpx.Response(200, json={"choices": [{"message": {"content": "no"}}]})
            return _picture()
        job, user = _job(json)
        self.calls.append(job)
        if job == "direct":
            ids = re.findall(r"^\[(s\d+)\]", user, re.M)
            plan = {
                "concept": "one bold idea",
                "slides": [
                    {
                        "id": i,
                        "hero": "headline",
                        "ground": "ground",
                        "image": n == 1,
                        "idea": "The headline huge on the left.",
                    }
                    for n, i in enumerate(ids)
                ],
            }
            return _ok(jsonlib.dumps(plan))
        if job == "review":
            ids = re.findall(r"s\d\d", user.split("Ids in order:")[-1])
            redo = [{"id": ids[1], "note": "make the headline the hero"}] if len(ids) > 1 else []
            scores = {
                k: 6 for k in ("consistency", "hierarchy", "detail", "readability", "innovation")
            }
            return _ok(jsonlib.dumps({"verdict": "close", "scores": scores, "redo": redo}))
        answer = _slide(user, off_canvas=self.broken)
        if job == "improve":
            answer = "```critique\n- bigger\n```\n" + answer
        return _ok(answer)


def _picture() -> httpx.Response:
    out = io.BytesIO()
    Image.new("RGB", (900, 600), (40, 90, 120)).save(out, "PNG")
    data = base64.b64encode(out.getvalue()).decode()
    url = f"data:image/png;base64,{data}"
    message = {"content": "", "images": [{"type": "image_url", "image_url": {"url": url}}]}
    usage = {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.002}
    return httpx.Response(200, json={"choices": [{"message": message}], "usage": usage})


def sample_frames(n: int = 99) -> tuple[list[Frame], dict[str, dict[str, str]]]:
    """Real words in the code-built layout: slides (and their fields) for
    tests that need any. Charts and visuals are left out: their own tests
    draw them."""
    outline = files.load("pitch-devtools").outline
    assert outline is not None
    frames, fields = [], {}
    for plan in outline.slides[:n]:
        made = fallback(plan.model_copy(update={"chart": None, "visual": None}))
        frames.append(Frame(plan.id, made.html, made.css))
        fields[plan.id] = {f.name: f.text for f in plan.fields}
    return frames, fields
