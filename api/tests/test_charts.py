"""Charts (phase 25 -> Verify): golden SVG files, and every chart type passes
browser QA inside a slide. Regenerate the goldens with UPDATE_GOLDEN=1 only
when a change to the drawing is intended, and look at them when you do."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from engine.components import charts
from engine.compose.document import Frame
from engine.design.sampler import sample
from engine.design.theme import build
from engine.models import ChartPoint, ChartSeries, ChartSpec
from engine.qa import browser

GOLDEN = Path(__file__).parent / "golden" / "charts"


def _spec(
    kind: str,
    points: list[tuple[str, float]],
    unit: str = "",
    highlight: str | None = None,
    second: list[tuple[str, float]] | None = None,
) -> ChartSpec:
    series = [ChartSeries(name="a", points=[ChartPoint(label=k, value=v) for k, v in points])]
    if second:
        series.append(
            ChartSeries(name="b", points=[ChartPoint(label=k, value=v) for k, v in second])
        )
    return ChartSpec.model_validate(
        {
            "type": kind,
            "title": kind,
            "unit": unit,
            "series": series,
            "highlight": highlight,
            "fact_ids": ["f1"],
        }
    )


SPECS = {
    "bar": _spec(
        "bar", [("Manual checks", 41), ("Legacy ETL", 23), ("Strata", 6)], highlight="Strata"
    ),
    "column": _spec("column", [("Q1", 0.6), ("Q2", 1.0), ("Q3", 1.6), ("Q4", 2.3)], unit="$M"),
    "line": _spec(
        "line",
        [("2022", 12), ("2023", 19), ("2024", 31), ("2025", 48)],
        unit="%",
        second=[("2022", 8), ("2023", 11), ("2024", 14), ("2025", 17)],
    ),
    "donut": _spec(
        "donut",
        [("Engineering", 52), ("Go-to-market", 33), ("Infra", 10), ("Reserve", 5)],
        unit="%",
    ),
}


@pytest.mark.parametrize("kind", sorted(SPECS))
def test_chart_matches_its_golden_file(kind: str) -> None:
    got = charts.svg(SPECS[kind])
    path = GOLDEN / f"{kind}.svg"
    if os.environ.get("UPDATE_GOLDEN") == "1":
        path.write_text(got + "\n")
    assert got + "\n" == path.read_text()


def test_charts_use_theme_tokens_only() -> None:
    for spec in SPECS.values():
        out = charts.svg(spec)
        assert "#" not in out.replace('xmlns="http://www.w3.org/2000/svg"', "")
        assert "var(--c-series-1" in out


def test_every_chart_passes_qa_in_a_slide(tmp_path: Path) -> None:
    html = (
        '<section class="s"><h2 class="h" data-field="headline">One chart, one claim</h2>'
        '<dd-chart class="c"></dd-chart></section>'
    )
    css = (
        ".s{padding:var(--margin);display:grid;grid-template-rows:auto 1fr;gap:var(--s-4)}"
        ".h{font-family:var(--f-display);font-weight:var(--w-display);font-size:var(--t-h2);"
        "line-height:var(--lh-display)}.c{min-height:0}"
    )
    frames = [Frame(k, charts.fill(html, s), css) for k, s in SPECS.items()]
    fields = {k: {"headline": "One chart, one claim"} for k in SPECS}
    for look in sample("charts", count=3):
        result = asyncio.run(
            browser.measure(build(look), frames, fields, str(tmp_path / "qa.html"))
        )
        bad = {k: [d.code for d in m.errors] for k, m in result.items() if m.errors}
        assert bad == {}, look.record()


def test_the_chart_fallback_passes_qa(tmp_path: Path) -> None:
    from engine.compose import author
    from engine.models import PlanField, SlidePlan

    plan = SlidePlan(
        id="c1",
        beat="traction",
        intent="chart",
        chart=SPECS["column"],
        fields=[
            PlanField(name="kicker", text="Traction", budget_words=3),
            PlanField(
                name="headline", text="ARR nearly quadrupled in four quarters", budget_words=12
            ),
            PlanField(name="source", text="Company financials", budget_words=4),
        ],
    )
    composed = author.fallback(plan)
    frame = Frame("c1", charts.fill(composed.html, plan.chart), composed.css)
    fields = {"c1": {f.name: f.text for f in plan.fields}}
    for look in sample("chart-fallback", count=3):
        result = asyncio.run(
            browser.measure(build(look), [frame], fields, str(tmp_path / "q.html"))
        )
        assert [d.code for d in result["c1"].errors] == [], look.record()
