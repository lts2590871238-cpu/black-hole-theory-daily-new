"""Static artifact validation used locally and before deployment."""

from __future__ import annotations

import json
import os
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return

        values = dict(attrs)
        href = values.get("href") or ""
        if href.startswith(("http://", "https://")):
            rel = set((values.get("rel") or "").split())
            if values.get("target") != "_blank" or not {"noopener", "noreferrer"}.issubset(rel):
                self.errors.append(f"unsafe external link: {href}")


def validate_dist(dist: Path, *, expected_base_url: str | None = None) -> list[str]:
    errors: list[str] = []

    required = (
        "index.html",
        "archive/index.html",
        "methodology/index.html",
        "feed.xml",
        "papers.json",
        "static/styles.css",
        "static/app.js",
    )
    for relative in required:
        if not (dist / relative).is_file():
            errors.append(f"missing static output: {relative}")

    for path in dist.rglob("*.html"):
        content = path.read_text(encoding="utf-8")
        parser = _LinkParser()
        parser.feed(content)
        errors.extend(parser.errors)

        for name in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
            secret = os.getenv(name, "")
            if len(secret) >= 20 and secret in content:
                errors.append(
                    f"possible credential in {path.relative_to(dist)} ({name})"
                )

    papers_path = dist / "papers.json"
    if papers_path.exists():
        try:
            payload = json.loads(papers_path.read_text(encoding="utf-8"))
            if not payload.get("schema_version"):
                errors.append("papers.json has no schema_version")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid papers.json: {exc}")

    if expected_base_url:
        base_url = expected_base_url.rstrip("/")
        repo = os.getenv("GITHUB_REPOSITORY", "")
        if repo and "/" in repo:
            owner, repository = repo.split("/", 1)
            expected_pages = f"https://{owner}.github.io/{repository}"
            if base_url.lower() != expected_pages.lower():
                errors.append(
                    f"site URL does not match GitHub Pages repository: {base_url}"
                )
        if "example." in base_url:
            errors.append("site URL still points to an example domain")
        feed_path = dist / "feed.xml"
        if feed_path.is_file():
            try:
                feed = ET.parse(feed_path).getroot()
                namespace = "{http://www.w3.org/2005/Atom}"
                if feed.findtext(f"{namespace}id") != base_url:
                    errors.append("Atom feed has an incorrect site ID")
                self_link = feed.find(f"{namespace}link[@rel='self']")
                if self_link is None or self_link.get("href") != f"{base_url}/feed.xml":
                    errors.append("Atom feed has an incorrect self URL")
            except ET.ParseError as exc:
                errors.append(f"invalid Atom feed XML: {exc}")

    return errors
