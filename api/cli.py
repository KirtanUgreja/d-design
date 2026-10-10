"""The CLI. Until the app exists (phase 27) this is how the engine is driven.

uv run python -m cli smoke                      one live call; prints its cost
uv run python -m cli freeze [--set smoke|all]   freeze outlines for bench briefs
uv run python -m cli baseline [--set smoke|all] one-shot baseline decks + screenshots
uv run python -m cli wall --run NAME            build the wall page for a human to score
uv run python -m cli outline --brief ID         interview, research, storyline, the gate, notes
uv run python -m cli content --run NAME         phase 24 bench: every brief, metrics, inverse spec
uv run python -m cli injection --run NAME       the injection corpus through the content stages
uv run python -m cli fonts                      measure the vendored faces into meta.json
uv run python -m cli export --run NAME [--pdf]  re-assemble built decks with the current player
uv run python -m cli openapi                    the API's schema, for the web's generated types
uv run python -m cli schema                     both databases' tables as SQL, into db/
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

import settings
from benchtools import (
    baseline,
    content,
    files,
    fonts,
    outline,
    shots,
    wall,
)
from engine import Brief, Seam, Slide, pipeline
from engine.compose.document import Frame
from engine.design.sampler import look_for, sample
from engine.design.theme import THEMES, Theme
from engine.design.theme import build as build_theme
from engine.export import pdf as pdf_export
from engine.export.assemble import assemble, fingerprint
from lib.result import Err


class _Pong(BaseModel):
    word: str


def _ids(which: str) -> list[str]:
    if which == "one":
        return list(files.ONE)
    return list(files.SMOKE) if which == "smoke" else files.brief_ids()


def _seam(cfg: settings.Settings, deck_id: str = "") -> Seam:
    return Seam(api_key=cfg.openrouter_api_key, providers=cfg.providers, deck_id=deck_id)


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
    # --repeat N builds every brief N times, each with its own generated look:
    # the sameness bench needs many decks from few frozen outlines (phase 36).
    briefs = _ids(args.set)[: args.briefs or None]
    jobs = [(r, b) for r in range(args.repeat) for b in briefs]
    # Usage within the run, so a bench run rotates languages as the worker
    # does across a user's decks.
    lang_usage: Counter[str] = Counter()
    for index, (repeat, brief_id) in enumerate(jobs):
        item = files.load(brief_id)
        if args.outlines:  # the content engine's outlines (cli content), not the frozen ones
            source = files.BENCH / "runs" / args.outlines / "content" / f"{brief_id}.json"
            if not source.exists():
                print(f"{brief_id}: no outline in {args.outlines} — run `content` first")
                continue
            item.outline = content.load(source)[0]
        if item.outline is None:
            print(f"{brief_id}: no frozen outline — run `freeze` first")
            continue
        name = brief_id if repeat == 0 else f"{brief_id}-r{repeat}"
        out = root / name
        if (out / "deck.html").exists() and not args.force:
            print(f"{name}: already built")
            continue
        out.mkdir(parents=True, exist_ok=True)
        if args.themes == "fixed":
            theme = themes[index % len(themes)]
        else:
            theme = _generated(item.brief, nonce=repeat, usage=lang_usage)
        seam = _seam(cfg, f"{args.run}-{label}-{name}")
        built = await pipeline.build(
            seam,
            item.outline,
            theme,
            image_model=args.image_model,
            improving=not args.no_improve,
            model=args.model,
            title=item.brief.prompt[:80],
            work_file=str(out / "qa.html"),
            shots_dir=str(out),
            budget_usd=args.budget,
        )
        lang_usage[theme.language] += 1
        (out / "deck.html").write_text(built.html)
        (out / "deck-send.html").write_text(built.send)
        files.append_ledger(root / "ledger.jsonl", seam.ledger)
        origins = [s.origin for s in built.slides]
        row: dict[str, object] = {
            "brief": brief_id,
            "repeat": repeat,
            "model": args.model,
            "theme": theme.id,
            "language": theme.language,
            "slides": len(built.slides),
            "clean_first_pass": built.first_pass_clean,
            "improved": built.improved,
            "repaired": origins.count("repaired"),
            "fallback": origins.count("fallback"),
            "flagged": sum(s.qa.status != "passed" for s in built.slides),
            "cost_usd": round(seam.spent_usd, 4),
            "seconds": round(built.seconds),
            "calls": len(seam.ledger),
            "cached_tokens": sum(e.cached_tokens for e in seam.ledger),
            "defects": sorted({d.code for s in built.slides for d in s.qa.errors}),
            "refusals": built.refusals,
            "export_bytes": len(built.html.encode()),
            "export_sha256": fingerprint(built.html),
            "send_sha256": fingerprint(built.send),
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


async def _bakeoff(cfg: settings.Settings, args: argparse.Namespace) -> int:
    """Each model builds the same briefs into bench/runs/<run>/<model>/; then
    `cli wall --run <run>` puts every model's decks on one wall to score."""
    failed = 0
    for model in [m.strip() for m in args.models.split(",") if m.strip()]:
        one = argparse.Namespace(
            **{
                **vars(args),
                "model": model,
                "label": "",
                "force": False,
                "themes": "sampled",
                "repeat": 1,
                "outlines": "",
                "no_improve": False,
            }
        )
        failed += await _build(cfg, one)
    return _wall(args.run, 0, False) or (1 if failed else 0)


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


def _brand(brief: Brief) -> str | None:
    return brief.brand.colors[0] if brief.brand and brief.brand.colors else None


def _generated(brief: Brief, nonce: int = 0, usage: Mapping[str, int] | None = None) -> Theme:
    """The one look a deck gets, generated from its own words (no menu)."""
    return build_theme(
        look_for(
            brief.id,
            deck_type=brief.deck_type,
            tone=brief.tone,
            words=brief.prompt,
            brand_hex=_brand(brief),
            nonce=nonce,
            usage=usage,
        )
    )


def _sampled(brief: Brief) -> list[Theme]:
    """Three far-apart looks, for the internal tile wall only."""
    return [
        build_theme(look)
        for look in sample(brief.id, deck_type=brief.deck_type, brand_hex=_brand(brief))
    ]


def _theme_for(theme_id: str, brief: Brief) -> Theme:
    """The theme a run recorded: one of phase 22's three, or a sampled look."""
    if theme_id in THEMES:
        return THEMES[theme_id]
    generated = _generated(brief)
    if generated.id == theme_id:
        return generated
    return next(t for t in _sampled(brief) if t.id == theme_id)


async def _export(run: str, label: str, which: str, pdf: bool) -> int:
    """Re-assemble built decks with the current player, both flavours, and the
    PDF. No model call: the slides are read back from slides.json."""
    root = files.BENCH / "runs" / run / label
    themes = {
        row["brief"]: row["theme"]
        for row in map(json.loads, (root / "summary.jsonl").read_text().splitlines())
    }
    for brief_id in _ids(which):
        out = root / brief_id
        if not (out / "slides.json").exists() or brief_id not in themes:
            continue
        item = files.load(brief_id)
        slides = [Slide.model_validate(s) for s in json.loads((out / "slides.json").read_text())]
        frames = [Frame(s.id, s.html, s.css) for s in slides]
        theme = _theme_for(str(themes[brief_id]), item.brief)
        plans = {p.id: p.notes for p in (item.outline.slides if item.outline else [])}
        title = item.brief.prompt.split(".")[0]
        present = assemble(theme, frames, title, flavour="present", notes=plans)
        send = assemble(theme, frames, title, flavour="send")
        (out / "deck.html").write_text(present)
        (out / "deck-send.html").write_text(send)
        line = f"{brief_id}: {len(frames)} slides, {len(present.encode()) / 1e6:.2f} MB"
        if pdf:
            data = await pdf_export.render(send)
            (out / "deck.pdf").write_bytes(data)
            line += f", pdf {len(data) / 1e6:.2f} MB"
        print(line, flush=True)
    return 0


def _year() -> int:
    return datetime.now(UTC).year


async def _outline(cfg: settings.Settings, brief_id: str, run: str) -> int:
    seam = _seam(cfg, f"{run}-{brief_id}")
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
        seam = _seam(cfg, f"{run}-{brief_id}")
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
        seam = _seam(cfg, f"{run}-{case.id}")
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


def _openapi() -> int:
    """The API's OpenAPI document, for web/lib/api/schema.d.ts (phase 27).
    Written sorted, so the gate can fail on any drift between the two."""
    import tempfile

    from app import create_app
    from store.files import Store

    api = create_app(Store(Path(tempfile.mkdtemp())))  # only for its schema; nothing is stored

    out = files.BENCH.parent / "web" / "lib" / "api" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(api.openapi(), indent=2, sort_keys=True) + "\n")
    print(out)
    return 0


def _schema() -> int:
    """Both databases written out as plain SQL, for reading (owner, 2026-10-10).
    db/app.sql is the Alembic migration rendered offline (no database touched);
    db/auth.sql is Better Auth's tables read from AUTH_DATABASE_URL, structure
    only, never rows. Neither is applied by hand: Alembic and Better Auth's CLI
    own the tables."""
    import io
    import os

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import MetaData, create_engine
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateIndex, CreateTable

    from store.sql import direct_url

    here = Path(__file__).resolve().parent
    out = here.parent / "db"
    out.mkdir(exist_ok=True)
    head = "-- Generated by `uv run python -m cli schema`; do not edit.\n"

    buf = io.StringIO()
    cfg = Config(str(here / "alembic.ini"), output_buffer=buf)
    cfg.attributes["url"] = "postgresql://user@localhost/app"  # offline: only the dialect is used
    command.upgrade(cfg, "head", sql=True)
    (out / "app.sql").write_text(
        head + "-- The app database: decks, jobs, files, users, spend.\n\n" + buf.getvalue()
    )
    print(out / "app.sql")

    url = os.environ.get("AUTH_DATABASE_URL") or _dotenv(here.parent / ".env").get(
        "AUTH_DATABASE_URL", ""
    )
    if not url:
        print("AUTH_DATABASE_URL is not set: db/auth.sql left as it is")
        return 0
    meta = MetaData()
    meta.reflect(create_engine(direct_url(url.strip().strip('"'))))
    dialect = postgresql.dialect()  # type: ignore[no-untyped-call]
    parts = []
    for table in meta.sorted_tables:
        parts.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        for index in sorted(table.indexes, key=lambda i: str(i.name)):
            parts.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
    body = "-- The auth database: Better Auth's tables (users, sessions, keys).\n\n"
    (out / "auth.sql").write_text(head + body + "\n\n".join(parts) + "\n")
    print(out / "auth.sql")
    return 0


def _dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    pairs = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)
    return {k.strip(): v.strip() for k, v in pairs if not k.startswith("#")}


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
    cmd.add_argument("--themes", choices=("sampled", "fixed"), default="sampled")
    cmd.add_argument("--repeat", type=int, default=1, help="build each brief N times, N looks")
    cmd.add_argument("--outlines", default="", help="a `cli content` run to take outlines from")
    cmd.add_argument("--image-model", default="", help="slide images; empty = no images")
    cmd.add_argument("--briefs", type=int, default=0, help="only the first N briefs of the set")
    cmd.add_argument("--no-improve", action="store_true", help="skip the improver layer")
    cmd = sub.add_parser("bakeoff", help="the same briefs built by each model, one wall")
    cmd.add_argument("--run", required=True)
    cmd.add_argument("--models", required=True, help="comma-separated compose models")
    cmd.add_argument("--set", choices=("one", "smoke", "all"), default="all")
    cmd.add_argument("--briefs", type=int, default=2)
    cmd.add_argument("--budget", type=float, default=0.5, help="hard cap per deck, USD")
    cmd.add_argument("--image-model", default="", help="slide images; empty = no images")
    cmd = sub.add_parser("outline")
    cmd.add_argument("--brief", required=True)
    cmd.add_argument("--run", default="outlines")
    cmd = sub.add_parser("content")
    cmd.add_argument("--run", required=True)
    cmd.add_argument("--set", choices=("one", "smoke", "all"), default="smoke")
    cmd = sub.add_parser("injection")
    cmd.add_argument("--run", required=True)
    sub.add_parser("fonts")
    cmd = sub.add_parser("export")
    cmd.add_argument("--run", required=True)
    cmd.add_argument("--label", default="engine")
    cmd.add_argument("--set", choices=("one", "smoke", "all"), default="all")
    cmd.add_argument("--pdf", action="store_true")
    sub.add_parser("openapi")
    sub.add_parser("schema")
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
    if args.command == "bakeoff":
        return asyncio.run(_bakeoff(cfg, args))
    if args.command == "outline":
        return asyncio.run(_outline(cfg, args.brief, args.run))
    if args.command == "content":
        return asyncio.run(_content(cfg, args.run, args.set))
    if args.command == "injection":
        return asyncio.run(_injection(cfg, args.run))
    if args.command == "export":
        return asyncio.run(_export(args.run, args.label, args.set, args.pdf))
    if args.command == "openapi":
        return _openapi()
    if args.command == "schema":
        return _schema()
    if args.command == "fonts":
        measured = asyncio.run(fonts.measure())
        for family, meta in measured.items():
            print(family, json.dumps(meta["metrics"]))
        return 0
    return _wall(args.run, args.seed, args.baselines)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
