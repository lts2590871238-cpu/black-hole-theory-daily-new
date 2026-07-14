from __future__ import annotations

from pathlib import Path

from theory_daily.demo import demo_papers
from theory_daily.health import validate_dist
from theory_daily.render import build_site


def test_static_build_outputs_and_html_escaping(tmp_path: Path, settings, topics) -> None:
    papers = demo_papers()
    papers[0].decision.title_zh = "危险 <script>alert(1)</script> 标题"
    papers[0].paper.authors[0] = '<img src=x onerror="alert(1)">'
    papers[0].paper.abstract_en += r" We compare $S=A/(4G)$ with \cite{Demo:2026}."
    papers[0].decision.abstract_zh += r" 并比较 $S=A/(4G)$，参见 \cite{Demo:2026}。"
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
    assert 'class="mathjax_ignore"' in html
    assert 'class="mathjax_process"' in html
    assert "mathjax@4.0.0/tex-svg.js" in html
    assert "ui/safe" in html
    assert r"$S=A/(4G)$" in html
    assert r"\cite{Demo:2026}" in html
    app_js = (output / "static" / "app.js").read_text(encoding="utf-8")
    assert "citation-token" in app_js
    assert "innerHTML" not in app_js
    for relative in ("archive/index.html", "methodology/index.html", "feed.xml", "papers.json"):
        assert (output / relative).exists()


def test_demo_contains_eight_clearly_marked_examples() -> None:
    papers = demo_papers()
    assert len(papers) == 8
    assert all(item.paper.is_demo for item in papers)
    assert all(item.paper.canonical_key.startswith("demo:") for item in papers)
