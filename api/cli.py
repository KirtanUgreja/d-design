"""The CLI. Until the app exists (phase 27) this is how the engine is driven.

uv run python -m cli smoke                      one live call; prints its cost
uv run python -m cli freeze [--set smoke|all]   freeze outlines for bench briefs
uv run python -m cli baseline [--set smoke|all] one-shot baseline decks + screenshots
uv run python -m cli wall --run NAME            build the wall page for a human to score
uv run python -m cli outline --brief ID         interview, research, storyline, the gate, notes
uv run python -m cli content --run NAME         phase 24 bench: every brief, metrics, inverse spec
uv run python -m cli injection --run NAME       the injection corpus through the content stages
uv run python -m cli fonts                      measure the vendored faces into meta.json
uv run python -m cli tiles --run NAME           3 sampled looks per brief, as style tiles
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

import settings
from benchtools import baseline, content, files, fonts, outline, shots, wall
from engine import Brief, Seam, pipeline
from engine.design import tiles
from engine.design.sampler import sample
from engine.design.theme import THEMES, Theme
from engine.design.theme import build as build_theme
from lib.result import Err


class _Pong(BaseModel):
    word: str


def _ids(which: str) -> list[str]:
    if which == "one":
        return list(files.ONE)
    return list(files.SMOKE) if which == "smoke" else files.brief_ids()


def _seam(cfg: settings.Settings) -> Seam:
    return Seam(api_key=cfg.openrouter_api_key)


async def _smoke(cfg: settings.Settings) -> int:
    seam = _seam(cfg)
    result = await seam.complete_json(
        "smoke",
        _Pong,
        system="Answer in JSON.",
        user='Set word to "pong".',
        model=cfg.model_cheap,
        max_tokens=200,
    )
    entry = seam.ledger[-1] if seam.ledger else None
    if isinstance(result, Err) or entry is None:
        print(f"smoke failed: {result}")
        return 1
    print(
        f"ok  model={entry.model} in={entry.input_tokens} out={entry.output_tokens} "
        f"cost=${entry.cost_usd:.5f} {entry.latency_ms}ms"
    )
    return 0


async def _freeze(cfg: settings.Settings, which: str, force: bool) -> int:
    failed = 0
    for brief_id in _ids(which):
        item = files.load(brief_id)
        if item.outline is not None and not force:
            print(f"{brief_id}: already frozen")
            continue
        seam = _seam(cfg)
        result = await outline.freeze(seam, item.brief, cfg.model_writing)
        files.append_ledger(files.BENCH / "runs" / "ledger.jsonl", seam.ledger)
        if isinstance(result, Err):
            print(f"{brief_id}: FAILED {result.error.kind} {result.error.detail[:200]}")
            failed += 1
            continue
        item.outline = result.value
        files.save(item)
        print(f"{brief_id}: {len(result.value.slides)} slides  ${seam.spent_usd:.3f}")
    return 1 if failed else 0


async def _baseline(cfg: settings.Settings, which: str, force: bool) -> int:
    root = files.BASELINES / "oneshot"

    async def one(brief_id: str) -> bool:
        html_file = root / f"{brief_id}.html"
        if not html_file.exists() or force:
            seam = _seam(cfg)
            result = await baseline.one_shot(seam, files.load(brief_id).brief, cfg.model_design)
            files.append_ledger(files.BENCH / "runs" / "ledger.jsonl", seam.ledger)
            if isinstance(result, Err):
                print(f"{brief_id}: FAILED {result.error.kind} {result.error.detail[:200]}")
                return False
            root.mkdir(parents=True, exist_ok=True)
            html_file.write_text(result.value)
            last = seam.ledger[-1]
            print(f"{brief_id}: ${seam.spent_usd:.3f} {last.latency_ms / 1000:.0f}s")
        (root / brief_id).mkdir(parents=True, exist_ok=True)
        count = await shots.shoot(html_file.resolve().as_uri(), str(root / brief_id))
        print(f"{brief_id}: {count} slides screenshotted")
        return count > 0

    results = await asyncio.gather(*(one(b) for b in _ids(which)))
    return 0 if all(results) else 1


async def _build(cfg: settings.Settings, args: argparse.Namespace) -> int:
    """Build decks from frozen outlines into bench/runs/<run>/<label>/<brief>/."""
    label = args.label or args.model.split("/")[-1]
    root = files.BENCH / "runs" / args.run / label
    themes = list(THEMES.values())
    rows: list[dict[str, object]] = []
    for index, brief_id in enumerate(_ids(args.set)):
        item = files.load(brief_id)
        if item.outline is None:
            print(f"{brief_id}: no frozen outline — run `freeze` first")
            continue
        out = root / brief_id
        if (out / "deck.html").exists() and not args.force:
            print(f"{brief_id}: already built")
            continue
        out.mkdir(parents=True, exist_ok=True)
        theme = themes[index % len(themes)] if args.themes == "fixed" else _sampled(item.brief)[0]
        seam = Seam(api_key=cfg.openrouter_api_key, deck_id=f"{args.run}-{label}-{brief_id}")
        built = await pipeline.build(
            seam,
            item.outline,
            theme,
            model=args.model,
            title=item.brief.prompt[:80],
            work_file=str(out / "qa.html"),
            shots_dir=str(out),
            budget_usd=args.budget,
        )
        (out / "deck.html").write_text(built.html)
        files.append_ledger(root / "ledger.jsonl", seam.ledger)
        origins = [s.origin for s in built.slides]
        row: dict[str, object] = {
            "brief": brief_id,
            "model": args.model,
            "theme": theme.id,
            "slides": len(built.slides),
            "clean_first_pass": built.first_pass_clean,
            "repaired": origins.count("repaired"),
            "fallback": origins.count("fallback"),
            "flagged": sum(s.qa.status != "passed" for s in built.slides),
            "cost_usd": round(seam.spent_usd, 4),
            "seconds": round(built.seconds),
            "calls": len(seam.ledger),
            "cached_tokens": sum(e.cached_tokens for e in seam.ledger),
            "defects": sorted({d.code for s in built.slides for d in s.qa.errors}),
            "refusals": built.refusals,
        }
        rows.append(row)
        # Written per deck: a run that is cut short keeps what it finished.
        with (root / "summary.jsonl").open("a") as out_file:
            out_file.write(json.dumps(row) + "\n")
        (out / "slides.json").write_text(
            json.dumps([s.model_dump(mode="json") for s in built.slides])
        )
        print(json.dumps(row), flush=True)
    if rows:
        costs = [float(str(r["cost_usd"])) for r in rows]
        print(f"{label}: {len(rows)} decks, median ${statistics.median(costs):.3f}")
    return 0 if rows else 1


def _wall(run: str, seed: int, baselines: bool) -> int:
    run_dir = files.BENCH / "runs" / run
    decks: list[wall.WallDeck] = []
    for system in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        decks += wall.collect(system, system.name)
    if baselines:
        for name in ("oneshot", "gamma", "v3"):
            decks += wall.collect(files.BASELINES / name, name)
    out: Path = run_dir / "wall.html"
    count = wall.build(decks, out, run, seed)
    print(f"{count} decks -> {out}")
    return 0 if count else 1


def _sampled(brief: Brief) -> list[Theme]:
    """The brief's three looks; the bench builds with the first."""
    brand_hex = brief.brand.colors[0] if brief.brand and brief.brand.colors else None
    return [
        build_theme(look)
        for look in sample(brief.id, deck_type=brief.deck_type, brand_hex=brand_hex)
    ]


async def _tiles(run: str, which: str) -> int:
    root = files.BENCH / "runs" / run / "tiles"
    root.mkdir(parents=True, exist_ok=True)
    rows: list[str] = []
    broken = 0
    for brief_id in _ids(which):
        item = files.load(brief_id)
        if item.outline is None:
            continue
        cells: list[str] = []
        for variant, theme in enumerate(_sampled(item.brief)):
            frames, bad = await tiles.render(
                theme, item.outline, variant, str(root / "work.html"), str(root)
            )
            broken += len(bad)
            look = theme.look
            caption = (
                f"{look['pairing']} · {look['palette']} · {look['grid']} · {look['motif']} · "
                f"{look['scale']}" + (f" · <b>QA {'; '.join(bad)}</b>" if bad else "")
            )
            imgs = "".join(f'<img src="tiles/{f.slide_id}.png">' for f in frames)
            cells.append(f"<figure>{imgs}<figcaption>{caption}</figcaption></figure>")
        rows.append(f"<section><h2>{brief_id}</h2><div class=row>{''.join(cells)}</div></section>")
    page = files.BENCH / "runs" / run / "tiles.html"
    page.write_text(
        "<!doctype html><meta charset=utf-8><title>Style tiles</title><style>"
        "body{font:14px system-ui;margin:24px;background:#ddd}h2{margin:24px 0 8px}"
        ".row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}"
        "figure{margin:0;background:#fff;padding:8px}img{width:100%;display:block;margin-bottom:6px}"
        "</style>" + "".join(rows)
    )
    print(f"{len(rows)} briefs x 3 looks -> {page}  ({broken} tiles with QA errors)")
    return 0


def _year() -> int:
    return datetime.now(UTC).year


async def _outline(cfg: settings.Settings, brief_id: str, run: str) -> int:
    seam = Seam(api_key=cfg.openrouter_api_key, deck_id=f"{run}-{brief_id}")
    made = await content.make(
        seam, files.load(brief_id).brief, model=cfg.model_writing, year=_year(), ask=input
    )
    files.append_ledger(files.BENCH / "runs" / "ledger.jsonl", seam.ledger)
    if isinstance(made, str):
        print(made)
        return 1
    out = files.BENCH / "runs" / run / "content" / f"{brief_id}.json"
    content.save(out, made)
    print(content.show(made.story, made.facts))
    print(f"\napproved -> {out}  ${seam.spent_usd:.3f}")
    return 0


async def _content(cfg: settings.Settings, run: str, which: str) -> int:
    root = files.BENCH / "runs" / run / "content"
    rows: list[dict[str, object]] = []
    for brief_id in _ids(which):
        brief = files.load(brief_id).brief
        out = root / f"{brief_id}.json"
        seam = Seam(api_key=cfg.openrouter_api_key, deck_id=f"{run}-{brief_id}")
        if out.exists():
            story, _ = content.load(out)
            row = json.loads(out.read_text())["row"]
        else:
            made = await content.make(seam, brief, model=cfg.model_writing, year=_year(), ask=None)
            if isinstance(made, str):
                print(f"{brief_id}: {made}")
                files.append_ledger(files.BENCH / "runs" / "ledger.jsonl", seam.ledger)
                continue
            story, row = made.story, made.row
            content.save(out, made)
        if not isinstance(row.get("inverse"), dict):
            score = await content.inverse(seam, brief, story, model=cfg.model_cheap)
            row["inverse"] = score
            data = json.loads(out.read_text())
            data["row"] = row
            out.write_text(json.dumps(data, indent=2))
        files.append_ledger(files.BENCH / "runs" / "ledger.jsonl", seam.ledger)
        row["notes_unsourced"] = content.notes_unsourced(brief, *content.load(out))
        rows.append(row)
        print(json.dumps(row), flush=True)
    if not rows:
        return 1
    page = root.parent / "review.md"
    page.write_text(content.review(sorted(root.glob("*.json"))))
    print(f"review -> {page}")
    inv = [r.get("inverse") for r in rows]
    scores = [float(str(i["mean"])) for i in inv if isinstance(i, dict)]
    print(
        f"{len(rows)} outlines · numbers without an approved fact "
        f"{sum(int(str(r['numbers_without_approved_fact'])) for r in rows)} · banned "
        f"{sum(int(str(r['banned_after'])) for r in rows)} · max topic labels before "
        f"{max(int(str(r['topic_labels_before'])) for r in rows)} · inverse spec "
        f"{statistics.mean(scores) if scores else 0:.2f} · max research "
        f"${max(float(str(r['research_usd'])) for r in rows):.3f} · numbers in notes no fact "
        f"states {sum(int(str(r['notes_unsourced'])) for r in rows)} · notes "
        f"{sum(int(str(r['notes'])) for r in rows)}/{sum(int(str(r['slides'])) for r in rows)}"
    )
    return 0


async def _injection(cfg: settings.Settings, run: str) -> int:
    leaked = 0
    for path in sorted((files.BENCH / "injection").glob("*.json")):
        case = content.Case.model_validate_json(path.read_text())
        seam = Seam(api_key=cfg.openrouter_api_key, deck_id=f"{run}-{case.id}")
        found = await content.injection(seam, case, model=cfg.model_writing)
        files.append_ledger(files.BENCH / "runs" / "ledger.jsonl", seam.ledger)
        if isinstance(found, str):
            leaked += found == "unmeasured"
            print(f"{case.id}: {found}  ${seam.spent_usd:.3f}", flush=True)
            continue
        leaked += bool(found)
        print(
            f"{case.id}: {'LEAKED ' + ', '.join(found) if found else 'held'}  "
            f"${seam.spent_usd:.3f}",
            flush=True,
        )
    print(f"{leaked} of the corpus changed the output or went unmeasured")
    return 1 if leaked else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("smoke")
    for name in ("freeze", "baseline"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--set", choices=("smoke", "all"), default="smoke")
        cmd.add_argument("--force", action="store_true")
    cmd = sub.add_parser("build")
    cmd.add_argument("--run", required=True)
    cmd.add_argument("--model", required=True)
    cmd.add_argument("--label", default="")
    cmd.add_argument("--set", choices=("one", "smoke", "all"), default="smoke")
    cmd.add_argument("--budget", type=float, default=0.5, help="hard cap per deck, USD")
    cmd.add_argument("--force", action="store_true")
    cmd.add_argument("--no-exemplars", action="store_true", help="the phase-22 A/B")
    cmd.add_argument("--themes", choices=("sampled", "fixed"), default="sampled")
    cmd = sub.add_parser("tiles")
    cmd.add_argument("--run", required=True)
    cmd.add_argument("--set", choices=("one", "smoke", "all"), default="all")
    cmd = sub.add_parser("outline")
    cmd.add_argument("--brief", required=True)
    cmd.add_argument("--run", default="outlines")
    cmd = sub.add_parser("content")
    cmd.add_argument("--run", required=True)
    cmd.add_argument("--set", choices=("one", "smoke", "all"), default="smoke")
    cmd = sub.add_parser("injection")
    cmd.add_argument("--run", required=True)
    sub.add_parser("fonts")
    cmd = sub.add_parser("wall")
    cmd.add_argument("--run", required=True)
    cmd.add_argument("--seed", type=int, default=0)
    cmd.add_argument("--baselines", action="store_true")
    args = parser.parse_args(argv)

    cfg = settings.load()
    if args.command == "smoke":
        return asyncio.run(_smoke(cfg))
    if args.command == "freeze":
        return asyncio.run(_freeze(cfg, args.set, args.force))
    if args.command == "baseline":
        return asyncio.run(_baseline(cfg, args.set, args.force))
    if args.command == "build":
        return asyncio.run(_build(cfg, args))
    if args.command == "outline":
        return asyncio.run(_outline(cfg, args.brief, args.run))
    if args.command == "content":
        return asyncio.run(_content(cfg, args.run, args.set))
    if args.command == "injection":
        return asyncio.run(_injection(cfg, args.run))
    if args.command == "tiles":
        return asyncio.run(_tiles(args.run, args.set))
    if args.command == "fonts":
        measured = asyncio.run(fonts.measure())
        for family, meta in measured.items():
            print(family, json.dumps(meta["metrics"]))
        return 0
    return _wall(args.run, args.seed, args.baselines)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
