"""The one-shot baseline: the same best model, asked once for a whole deck.

If the engine cannot beat a single prompt, the orchestration is overhead
(docs/v4/spec.md -> Bets). The prompt is kept plain on purpose — it is what a
person would type — plus the one structural line the wall needs to screenshot
the result.
"""

from __future__ import annotations

from engine import Brief, ModelError, Reply, Seam, parse_fenced
from lib.result import Err, Result, err, ok

PROMPT_VERSION = "bench-oneshot.v1"

SYSTEM = "You are an expert presentation designer who writes HTML."


def _prompt(brief: Brief) -> str:
    pasted = "\n\n".join(f"{p.title}:\n{p.text}" for p in brief.pasted)
    return (
        f"Make a {brief.slide_count}-slide presentation as one self-contained HTML file.\n\n"
        f"{brief.prompt}\nAudience: {brief.audience}\nGoal: {brief.ask}\n\n"
        f"{pasted}\n\n"
        "Make it look professionally designed. Each slide must be a "
        '<section class="slide"> exactly 1920px wide and 1080px tall, stacked vertically, '
        "with no JavaScript and no external files or fonts. "
        "Answer with the file in one ```html block."
    )


def _parse(reply: Reply) -> Result[str, str]:
    blocks = parse_fenced(reply.text, "html")
    if isinstance(blocks, Err):
        return blocks
    html = blocks.value["html"]
    if 'class="slide"' not in html:
        return err('the file has no <section class="slide">')
    return ok(html)


async def one_shot(seam: Seam, brief: Brief, model: str) -> Result[str, ModelError]:
    return await seam.complete_text(
        "baseline",
        _parse,
        system=SYSTEM,
        user=_prompt(brief),
        model=model,
        prompt_version=PROMPT_VERSION,
        max_tokens=32000,
    )
