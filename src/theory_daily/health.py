"""Static artifact validation used locally and before deployment."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path


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


def validate_dist(dist: Path) -> list[str]:
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
        if "OPENAI_API_KEY" in content or "sk-" in content:
            errors.append(f"possible credential in {path.name}")
    papers_path = dist / "papers.json"
    if papers_path.exists():
        try:
            payload = json.loads(papers_path.read_text(encoding="utf-8"))
            if not payload.get("schema_version"):
                errors.append("papers.json has no schema_version")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid papers.json: {exc}")
    return errors
