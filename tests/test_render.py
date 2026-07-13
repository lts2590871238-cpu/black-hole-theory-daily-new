from __future__ import annotations

from pathlib import Path

from theory_daily.demo import demo_papers
from theory_daily.health import validate_dist
from theory_daily.render import build_site


def test_static_build_outputs_and_html_escaping(tmp_path: Path, settings, topics) -> None:
    papers = demo_papers()
    papers[0].decision.title_zh = "危险 <script>alert(1)</script> 标题"
    papers[0].paper.authors[0] = '<img src=x onerror="alert(1)">'
    output = build_site(
        Path(__file__).parents[1],
        papers,
        settings,
        topics,
        output=tmp_path / "dist",
        demo=True,
    )
    assert validate_dist(output) == []
    html = (output / "index.html").read_text(encoding="utf-8")
    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert "arXiv ID" in html
    assert "DEMO-01" in html
    assert "虚构示例" in html
    assert 'id="date-scope"' in html
    assert 'value="day"' in html
    assert 'value="month"' in html
    assert 'value="year"' in html
    assert 'value="range"' in html
    assert 'id="date-from"' in html
    assert 'id="date-to"' in html
    for relative in ("archive/index.html", "methodology/index.html", "feed.xml", "papers.json"):
        assert (output / relative).exists()


def test_demo_contains_eight_clearly_marked_examples() -> None:
    papers = demo_papers()
    assert len(papers) == 8
    assert all(item.paper.is_demo for item in papers)
    assert all(item.paper.canonical_key.startswith("demo:") for item in papers)
