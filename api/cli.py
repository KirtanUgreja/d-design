"""The v1 pipeline CLI — the lean flow, driven from the terminal.

v1 has no editor (docs/v1/spec.md -> "What changes from the last version"):
interview → mapping → build → review → export. This CLI is the v1 driver for
the first two human steps — run the interview, show the outline, get approval
— and the later phases plug in as they land. It is deliberately thin: it parses
input, calls a feature's public function, and shows the result.

The human gate lives here and nowhere else: an outline is only approved by a
person typing `y`. That is the trust device (spec.md risk 2) — an invented
claim is visible before any slide is built.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai.complete import ModelError, make_seam
from lib.result import Err
from pipeline.interview.interview import run_interview
from pipeline.mapping.mapping import run_mapping
from schema.outline import Brief, Outline


def _parse_brief(args: argparse.Namespace) -> Brief:
    return Brief(
        topic=args.topic,
        slide_count=args.slides,
        audience=args.audience or "",
        goal=args.goal or "",
        brand_kit={
            "colors": args.colors or "",
            "fonts": args.fonts or "",
            "vibe": args.vibe or "",
        },
        extra_info=args.extra or "",
    )


def _print_outline(outline: object) -> None:
    """Print the outline in a form a human reads and approves."""

    # Avoid importing at module top so the CLI stays thin; the outline shape is
    # stable and known here.
    title = outline.title  # type: ignore[attr-defined]
    audience = outline.audience  # type: ignore[attr-defined]
    goal = outline.goal  # type: ignore[attr-defined]
    sections = outline.sections  # type: ignore[attr-defined]

    print(f"\n=== {title} ===")
    print(f"Audience: {audience}")
    print(f"Goal:     {goal}")
    print()
    for i, section in enumerate(sections, 1):
        print(f"{i}. {section.heading} — {section.summary}")
        for claim in section.claims:
            mark = "YOU" if claim.source == "user" else "AI "
            print(f"   [{mark}] {claim.text}")
    print()


def _show_error(error: ModelError) -> None:
    print(f"pipeline failed ({error.kind}): {error.detail}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="d-design", description="The v1 deck pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    interview = sub.add_parser("interview", help="Run the AI-led interview and approve the outline")
    interview.add_argument("--topic", required=True, help="What the deck is about")
    interview.add_argument("--slides", type=int, default=8, help="Approximate slide count")
    interview.add_argument("--audience", default="", help="Who the deck is for")
    interview.add_argument("--goal", default="", help="What the deck should achieve")
    interview.add_argument("--colors", default="", help="Brand kit: colors (typed text)")
    interview.add_argument("--fonts", default="", help="Brand kit: fonts (typed text)")
    interview.add_argument("--vibe", default="", help="Brand kit: vibe (typed text)")
    interview.add_argument("--extra", default="", help="Extra context")
    interview.add_argument("--model", default="openai/gpt-4o-mini", help="OpenRouter model id")
    interview.add_argument(
        "--out", default="outline.json", help="Where to write the approved outline"
    )

    mapping = sub.add_parser("mapping", help="Turn an approved outline into a per-slide Deck")
    mapping.add_argument("--outline", default="outline.json", help="The approved outline file")
    mapping.add_argument(
        "--family", default=None, help="Design family id (default: deterministic pick)"
    )
    mapping.add_argument("--model", default="openai/gpt-4o-mini", help="OpenRouter model id")
    mapping.add_argument("--out", default="deck.json", help="Where to write the mapped Deck")

    args = parser.parse_args(argv)

    if args.command == "interview":
        brief = _parse_brief(args)
        seam = make_seam()
        result = run_interview(brief, seam, model=args.model)

        if isinstance(result, Err):
            _show_error(result.error)
            return 1

        outline = result.value
        # The human gate: show, get explicit approval, loop on rejection.
        while True:
            _print_outline(outline)
            choice = input("Approve this outline? [y/n] ").strip().lower()
            if choice in ("y", "yes"):
                break
            if choice in ("n", "no"):
                print(
                    "Outline rejected. Re-run with edited input — the interview "
                    "is deterministic per brief."
                )
                return 2
            print("Please answer y or n.")

        Path(args.out).write_text(
            json.dumps(outline.model_dump(), indent=2),
            encoding="utf8",
        )
        print(f"Approved. Wrote {args.out}")
        return 0

    if args.command == "mapping":
        try:
            raw = json.loads(Path(args.outline).read_text(encoding="utf8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"cannot read outline {args.outline}: {exc}", file=sys.stderr)
            return 1
        outline = Outline.model_validate(raw)
        seam = make_seam()
        result = run_mapping(outline, seam, model=args.model, family_id=args.family)

        if isinstance(result, Err):
            _show_error(result.error)
            return 1

        deck = result.value
        Path(args.out).write_text(
            json.dumps(deck.model_dump(), indent=2),
            encoding="utf8",
        )
        print(f"Mapped {len(deck.slides)} slides -> {args.out}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
