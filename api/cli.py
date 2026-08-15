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
import base64
import json
import sys
from pathlib import Path

from ai.complete import ModelError, make_seam
from ai.images import make_image_seam
from lib.result import Err
from pipeline.interview.interview import run_interview
from pipeline.mapping.mapping import run_mapping
from pipeline.review.review import revise_slide
from pipeline.slide_builder.slide_builder import run_build
from schema.deck import Deck
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

    build = sub.add_parser("build", help="Build every slide of a mapped Deck, one call each")
    build.add_argument("--deck", default="deck.json", help="The mapped Deck file")
    build.add_argument("--model", default="openai/gpt-4o-mini", help="OpenRouter model id")
    build.add_argument("--image-model", default="openai/dall-e-3", help="OpenRouter image model id")
    build.add_argument(
        "--out", default="built.json", help="Where to write the built Deck + image assets"
    )

    review = sub.add_parser(
        "review",
        help="Regenerate one slide with written feedback (the human review loop)",
    )
    review.add_argument("--built", default="built.json", help="The built Deck + images file")
    review.add_argument("--slide", type=int, required=True, help="1-based slide index to revise")
    review.add_argument("--feedback", required=True, help="The reviewer's written feedback")
    review.add_argument("--model", default="openai/gpt-4o-mini", help="OpenRouter model id")
    review.add_argument("--out", default="built.json", help="Where to write the revised built Deck")

    critic = sub.add_parser(
        "critic",
        help="Run the vision critic on one rendered slide (bounded to one revision)",
    )
    critic.add_argument("--built", default="built.json", help="The built Deck + images file")
    critic.add_argument(
        "--screenshot", required=True, help="Path to the rendered slide screenshot (png)"
    )
    critic.add_argument("--slide", type=int, required=True, help="1-based slide index to critic")
    critic.add_argument(
        "--model", default="openai/gpt-4o-mini", help="OpenRouter text model for a revision"
    )
    critic.add_argument(
        "--critic-model",
        default="openai/gpt-4o-mini",
        help="OpenRouter vision model that reviews the screenshot",
    )
    critic.add_argument(
        "--out", default="built.json", help="Where to write the revised built Deck (if revised)"
    )

    acceptance = sub.add_parser(
        "acceptance",
        help="Run the golden briefs and assert schema-validity + variety (the fingerprint gate)",
    )
    acceptance.add_argument("--model", default="openai/gpt-4o-mini", help="OpenRouter model id")
    acceptance.add_argument(
        "--out", default="acceptance.json", help="Where to write the acceptance report"
    )

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

    if args.command == "build":
        try:
            raw = json.loads(Path(args.deck).read_text(encoding="utf8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"cannot read deck {args.deck}: {exc}", file=sys.stderr)
            return 1
        deck = Deck.model_validate(raw)
        seam = make_seam()
        image_seam = make_image_seam()
        result = run_build(deck, seam, image_seam, model=args.model, image_model=args.image_model)

        if isinstance(result, Err):
            _show_error(result.error)
            return 1

        built = result.value
        # The image assets are data URIs, kept beside the deck (the schema has
        # no field for them; the exporter inlines them in phase 05).
        payload = {"deck": built.deck.model_dump(), "images": built.images}
        Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf8")
        print(f"Built {len(built.deck.slides)} slides ({len(built.images)} images) -> {args.out}")
        return 0

    if args.command == "review":
        try:
            raw = json.loads(Path(args.built).read_text(encoding="utf8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"cannot read built deck {args.built}: {exc}", file=sys.stderr)
            return 1
        built = raw["deck"]
        images = raw.get("images", {})
        deck = Deck.model_validate(built)
        seam = make_seam()
        result = revise_slide(deck, args.slide - 1, args.feedback, seam, model=args.model)

        if isinstance(result, Err):
            _show_error(result.error)
            return 1

        revised = result.value
        # Replace the slide in place; the review loop is slide-by-slide.
        slides = deck.model_dump()["slides"]
        slides[args.slide - 1] = revised.model_dump()
        payload = {
            "deck": Deck.model_validate(
                {"family_id": deck.family_id, "slides": slides}
            ).model_dump(),
            "images": images,
        }
        Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf8")
        print(f"Revised slide {args.slide} -> {args.out}")
        return 0

    if args.command == "critic":
        from pipeline.vision_critic import run_critic

        try:
            raw = json.loads(Path(args.built).read_text(encoding="utf8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"cannot read built deck {args.built}: {exc}", file=sys.stderr)
            return 1
        built = raw["deck"]
        images = raw.get("images", {})
        deck = Deck.model_validate(built)

        # The screenshot is the rendered slide (the render service produces it
        # in the real flow); read it and embed as a data URI for the vision
        # model. No URL is fetched — the file is the input.
        try:
            png = Path(args.screenshot).read_bytes()
        except FileNotFoundError as exc:
            print(f"cannot read screenshot {args.screenshot}: {exc}", file=sys.stderr)
            return 1

        screenshot = f"data:image/png;base64,{base64.b64encode(png).decode('ascii')}"

        seam = make_seam()
        result = run_critic(
            deck,
            args.slide - 1,
            screenshot,
            seam,
            model=args.model,
            critic_model=args.critic_model,
        )

        if isinstance(result, Err):
            _show_error(result.error)
            return 1

        outcome = result.value
        for f in outcome.findings:
            print(f"  [{f.severity}] {f.kind}: {f.note}")
        if outcome.revised:
            payload = {
                "deck": outcome.deck.model_dump(),
                "images": images,
            }
            Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf8")
            print(f"critic revised slide {args.slide} -> {args.out}")
        else:
            print(f"critic accepted slide {args.slide} (no revision)")
        return 0

    if args.command == "acceptance":
        from pipeline.acceptance.acceptance import (
            acceptance_summary,
            run_acceptance_brief,
        )
        from pipeline.acceptance.briefs import GOLDEN_BRIEFS

        seam = make_seam()
        results = []
        failures = []
        for brief in GOLDEN_BRIEFS:
            result = run_acceptance_brief(brief, seam, model=args.model)
            if isinstance(result, Err):
                failures.append({"topic": brief.topic, "error": result.error.detail})
            else:
                results.append(result.value)

        passed, report = acceptance_summary(results)
        payload = {
            "passed": passed,
            "report": report,
            "briefs": len(GOLDEN_BRIEFS),
            "succeeded": len(results),
            "failures": failures,
        }
        Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf8")
        print(report)
        print(f"acceptance: {len(results)}/{len(GOLDEN_BRIEFS)} briefs -> {args.out}")
        return 0 if passed else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
