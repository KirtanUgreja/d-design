"""Where the bench keeps things (docs/v4/bench.md)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from engine import Brief, LedgerEntry, Storyline

BENCH = Path(__file__).resolve().parent.parent.parent / "bench"
BRIEFS = BENCH / "briefs"
BASELINES = BENCH / "baselines"
SMOKE = ("pitch-devtools", "sales-data-platform", "update-q3")
ONE = ("update-q3",)


class BenchBrief(BaseModel):
    brief: Brief
    outline: Storyline | None = None


def brief_ids() -> list[str]:
    return sorted(p.stem for p in BRIEFS.glob("*.json"))


def load(brief_id: str) -> BenchBrief:
    return BenchBrief.model_validate_json((BRIEFS / f"{brief_id}.json").read_text())


def save(item: BenchBrief) -> None:
    path = BRIEFS / f"{item.brief.id}.json"
    path.write_text(
        json.dumps(item.model_dump(mode="json", exclude_defaults=True), indent=2) + "\n"
    )


def append_ledger(path: Path, entries: list[LedgerEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as out:
        for entry in entries:
            out.write(entry.model_dump_json() + "\n")
