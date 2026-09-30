"""The CLI. Until the app exists (phase 27) this is how the engine is driven.

uv run python -m cli smoke                      one live call; prints its cost
uv run python -m cli freeze [--set smoke|all]   freeze outlines for bench briefs
uv run python -m cli baseline [--set smoke|all] one-shot baseline decks + screenshots
uv run python -m cli wall --run NAME            build the wall page for a human to score
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from pathlib import Path

from pydantic import BaseModel

import settings
from benchtools import baseline, files, outline, shots, wall
from engine import Seam, pipeline
from engine.design.theme import THEMES
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
        out.mkdir(parents=True, exist_ok=True)
        theme = themes[index % len(themes)]
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
        print(json.dumps(row))
    with (root / "summary.jsonl").open("a") as out_file:
        out_file.writelines(json.dumps(r) + "\n" for r in rows)
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
    return _wall(args.run, args.seed, args.baselines)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
