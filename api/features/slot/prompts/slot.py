"""The Slot prompt (docs/v1/plan/11-visuals-and-slot.md).

**What is not in this file is the point.** The prompt is built from the
approved outline's title, the scene's intent, and the scene's beat. There is no
parameter for source material, so there is nothing to leave out by mistake and
nothing to add by convenience later without changing a signature.

That is Defense 1 from docs/security/prompt-injection.md, applied where it is
free: Slot code renders a visual moment and has no legitimate need for the
source document, so closing the path costs nothing. In v1 there is no imported
material at all, which makes the property trivially true today — and is exactly
why it has to be structural rather than a fact about v1. The day import
arrives, this path is already closed.
"""

_PROMPT_CONTRACT = """You are the Slot phase of a presentation-experience generator. \
You write ONE self-contained interactive visual moment for one scene, as HTML, CSS and \
JavaScript, output as JSON conforming exactly to the provided schema.

1. The code runs in a sandboxed iframe with no network, no storage, no cookies and no \
access to the parent page. Do not attempt any of them: `fetch`, `XMLHttpRequest`, \
`localStorage`, `document.cookie` and `window.parent` will all fail, and code that \
depends on them renders nothing.
2. Use the CSS custom properties already defined on `:root` for every colour, size and \
duration — `var(--accent)`, `var(--bg)`, `var(--ink)`, `var(--space-4)`, and so on. \
Never write a literal hex colour, pixel size or font family: the art direction supplies \
all of it, and a hard-coded value is the one thing that makes this look bolted on.
3. No external resources. No `<img src="http...">`, no webfonts, no CDN scripts. \
Everything is drawn with CSS, SVG or canvas.
4. Motion is welcome and must respect `@media (prefers-reduced-motion: reduce)` by \
collapsing to a static state.
5. Keep it one idea. This is the single signature moment of the whole experience, and \
a moment that does three things is three half-moments."""

PROMPT_SENTINELS = (
    "You are the Slot phase",
    "This is the single signature moment",
)


def build_slot_prompt(
    *, outline_title: str, scene_intent: str, scene_beat: str
) -> tuple[str, str]:
    """System and user message, from the approved outline and the scene's
    intent. Three strings, all of them already through the pipeline's own
    checks — never raw source material, and the signature is what says so."""
    return (
        _PROMPT_CONTRACT,
        f"The experience is titled {outline_title!r}.\n"
        f"This scene's intent is {scene_intent!r} and its beat is {scene_beat!r}.\n\n"
        f"Write the signature visual moment for it.",
    )
