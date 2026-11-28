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
    assert "card.dataset.topics" in app_js
    assert "data-topics=" in html
    from xml.etree import ElementTree as ET

    atom = ET.parse(output / "feed.xml").getroot()
    namespace = "{http://www.w3.org/2005/Atom}"
    assert atom.findtext(f"{namespace}id") == settings.site.base_url
    link = atom.find(f"{namespace}link[@rel='self']")
    assert link is not None
    assert link.get("href") == f"{settings.site.base_url}/feed.xml"
    assert validate_dist(output, expected_base_url=settings.site.base_url) == []
    for relative in ("archive/index.html", "methodology/index.html", "feed.xml", "papers.json"):
        assert (output / relative).exists()


def test_demo_contains_eleven_clearly_marked_examples() -> None:
    papers = demo_papers()
    assert len(papers) == 11
    assert all(item.paper.is_demo for item in papers)
    assert all(item.paper.canonical_key.startswith("demo:") for item in papers)


def test_demo_includes_the_three_new_gravity_topics() -> None:
    topics = {paper.decision.primary_topic for paper in demo_papers()}
    assert {"metric_affine_gravity", "palatini_gravity", "modified_gravity"} <= topics


def test_archived_paper_is_collapsible_and_still_searchable(
    tmp_path: Path, settings, topics
) -> None:
    from datetime import UTC, datetime, timedelta

    paper = demo_papers(datetime.now(UTC))[0]
    paper.paper.submitted_at = datetime.now(UTC) - timedelta(days=40)
    output = build_site(
        Path(__file__).parents[1],
        [paper],
        settings,
        topics,
        output=tmp_path / "archived",
        demo=True,
    )
    homepage = (output / "index.html").read_text(encoding="utf-8")
    archive = (output / "archive" / "index.html").read_text(encoding="utf-8")
    assert "DEMO-01" not in homepage
    assert "DEMO-01" in archive
    assert 'class="archived-paper-details"' in archive
    assert "展开完整摘要、链接与评分" in archive
    assert "data-search=" in archive



def test_home_archive_partition_rolls_with_beijing_day() -> None:
    from datetime import UTC, date, datetime, timedelta, timezone

    from theory_daily.render import partition_papers

    china = timezone(timedelta(hours=8))
    now = datetime(2026, 11, 17, 4, tzinfo=UTC)
    papers = demo_papers(now)[:3]
    papers[0].paper.submitted_at = datetime(2026, 11, 2, 23, 59, tzinfo=china)
    papers[1].paper.submitted_at = datetime(2026, 11, 3, 0, tzinfo=china)
    papers[2].paper.submitted_at = datetime(2026, 11, 4, 1, tzinfo=china)
    recent, archived, cutoff = partition_papers(papers, now, "Asia/Shanghai")
    assert cutoff == date(2026, 11, 3)
    assert len(recent) == 2
    assert len(archived) == 1

    next_day = datetime(2026, 11, 17, 16, tzinfo=UTC)
    recent, archived, cutoff = partition_papers(papers, next_day, "Asia/Shanghai")
    assert cutoff == date(2026, 11, 4)
    assert len(recent) == 1
    assert len(archived) == 2


def test_secondary_topic_is_searchable(tmp_path: Path, settings, topics) -> None:
    paper = demo_papers()[0]
    paper.decision.secondary_topics = ["palatini_gravity"]
    output = build_site(
        Path(__file__).parents[1],
        [paper], settings, topics, output=tmp_path / "site", demo=True,
    )
    html = (output / "index.html").read_text(encoding="utf-8")
    assert f'data-topics="{paper.decision.primary_topic} palatini_gravity"' in html


def test_invalid_feed_url_is_rejected(tmp_path: Path, settings, topics) -> None:
    output = build_site(
        Path(__file__).parents[1],
        demo_papers(), settings, topics, output=tmp_path / "site", demo=True,
    )
    errors = validate_dist(
        output, expected_base_url="https://example.github.io/black-hole-theory-daily"
    )
    assert any("incorrect" in error or "example" in error for error in errors)
