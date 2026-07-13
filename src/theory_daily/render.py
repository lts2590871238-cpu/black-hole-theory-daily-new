"""Jinja2 static-site rendering with automatic HTML escaping."""

from __future__ import annotations

import json
import shutil
from collections import defaultdict
from datetime import UTC, datetime, tzinfo
from pathlib import Path
from typing import cast
from xml.etree import ElementTree as ET

from dateutil.tz import gettz
from jinja2 import Environment, FileSystemLoader, select_autoescape

from theory_daily.config import Settings, TopicsConfig
from theory_daily.models import PaperCollection, PublishedPaper
from theory_daily.storage import write_json


def _timezone(value: str) -> tzinfo:
    zone = gettz(value)
    if zone is None:
        raise ValueError(f"未知页面时区: {value}")
    return cast(tzinfo, zone)


def _environment(root: Path, timezone: str) -> Environment:
    environment = Environment(
        loader=FileSystemLoader(root / "templates"),
        autoescape=select_autoescape(("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    local_zone = _timezone(timezone)
    environment.filters["iso_date"] = lambda value: value.astimezone(local_zone).strftime(
        "%Y-%m-%d"
    )
    environment.filters["json"] = lambda value: json.dumps(value, ensure_ascii=False)
    return environment


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _feed(settings: Settings, papers: list[PublishedPaper], generated: datetime) -> str:
    feed = ET.Element("feed", {"xmlns": "http://www.w3.org/2005/Atom"})
    ET.SubElement(feed, "title").text = settings.site.title_zh
    ET.SubElement(feed, "id").text = settings.site.base_url
    ET.SubElement(feed, "updated").text = generated.isoformat().replace("+00:00", "Z")
    ET.SubElement(feed, "link", {"href": settings.site.base_url + "/feed.xml", "rel": "self"})
    for item in papers[:50]:
        paper = item.paper
        decision = item.decision
        entry = ET.SubElement(feed, "entry")
        ET.SubElement(entry, "id").text = paper.canonical_key
        ET.SubElement(entry, "title").text = decision.title_zh
        ET.SubElement(entry, "updated").text = paper.updated_at.isoformat().replace("+00:00", "Z")
        ET.SubElement(entry, "summary").text = decision.abstract_zh
        link = str(paper.abs_url or paper.inspire_url or settings.site.base_url)
        ET.SubElement(entry, "link", {"href": link})
        for author_name in paper.authors:
            author = ET.SubElement(entry, "author")
            ET.SubElement(author, "name").text = author_name
    return ET.tostring(feed, encoding="unicode", xml_declaration=True)


def build_site(
    root: Path,
    papers: list[PublishedPaper],
    settings: Settings,
    topics: TopicsConfig,
    *,
    output: Path | None = None,
    demo: bool = False,
) -> Path:
    output = output or root / "dist"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    shutil.copytree(root / "static", output / "static")
    env = _environment(root, settings.site.timezone)
    generated_utc = datetime.now(UTC)
    generated = generated_utc.astimezone(_timezone(settings.site.timezone))
    papers = sorted(papers, key=lambda item: item.paper.updated_at, reverse=True)
    common = {
        "settings": settings,
        "topics": topics,
        "generated": generated,
        "papers": papers,
        "demo": demo,
    }
    _write(
        output / "index.html",
        env.get_template("index.html").render(**common, asset_prefix="", page_prefix=""),
    )
    grouped: dict[str, list[PublishedPaper]] = defaultdict(list)
    for paper in papers:
        grouped[paper.paper.submitted_at.date().isoformat()].append(paper)
    _write(
        output / "archive" / "index.html",
        env.get_template("archive.html").render(
            **common,
            grouped=dict(sorted(grouped.items(), reverse=True)),
            asset_prefix="../",
            page_prefix="../",
        ),
    )
    _write(
        output / "methodology" / "index.html",
        env.get_template("methodology.html").render(
            **common, asset_prefix="../", page_prefix="../"
        ),
    )
    collection = PaperCollection(generated_at=generated_utc, papers=papers)
    write_json(output / "papers.json", collection)
    _write(output / "feed.xml", _feed(settings, papers, generated_utc))
    return output


def load_published_papers(root: Path) -> list[PublishedPaper]:
    papers: list[PublishedPaper] = []
    for path in sorted((root / "data" / "papers").glob("*.json")):
        papers.append(PublishedPaper.model_validate_json(path.read_text(encoding="utf-8")))
    return papers
