"""arXiv Atom API client; no HTML scraping."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import struct_time

import feedparser
from pydantic import HttpUrl
from requests import Session

from theory_daily.config import Settings, TopicsConfig
from theory_daily.http_client import build_session
from theory_daily.models import RawArxivRecord

LOGGER = logging.getLogger(__name__)
API_URL = "https://export.arxiv.org/api/query"
_VERSION = re.compile(r"v(?P<version>\d+)$")


def _datetime(value: struct_time | None) -> datetime:
    if value is None:
        raise ValueError("missing date")
    return datetime(*value[:6], tzinfo=UTC)


def _text(entry: object, name: str, default: str = "") -> str:
    value = getattr(entry, name, default)
    return " ".join(str(value).split())


def parse_atom(content: bytes | str) -> list[RawArxivRecord]:
    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"invalid arXiv Atom response: {feed.bozo_exception}")
    records: list[RawArxivRecord] = []
    for entry in feed.entries:
        try:
            entry_id = _text(entry, "id")
            identifier = entry_id.rsplit("/", 1)[-1]
            version_match = _VERSION.search(identifier)
            version = int(version_match.group("version")) if version_match else 1
            categories = [tag.term for tag in getattr(entry, "tags", []) if tag.term]
            authors = [_text(author, "name") for author in getattr(entry, "authors", [])]
            links = {getattr(link, "rel", ""): getattr(link, "href", "") for link in entry.links}
            pdf = next(
                (
                    getattr(link, "href", "")
                    for link in entry.links
                    if getattr(link, "type", "") == "application/pdf"
                ),
                f"https://arxiv.org/pdf/{identifier}",
            )
            primary = getattr(entry, "arxiv_primary_category", {}).get(
                "term", categories[0] if categories else ""
            )
            records.append(
                RawArxivRecord(
                    arxiv_id=identifier,
                    version=version,
                    submitted_at=_datetime(getattr(entry, "published_parsed", None)),
                    updated_at=_datetime(getattr(entry, "updated_parsed", None)),
                    title=_text(entry, "title"),
                    abstract=_text(entry, "summary"),
                    authors=authors,
                    categories=categories,
                    primary_category=primary,
                    comments=_text(entry, "arxiv_comment") or None,
                    journal_ref=_text(entry, "arxiv_journal_ref") or None,
                    doi=_text(entry, "arxiv_doi") or None,
                    abs_url=HttpUrl(str(links.get("alternate", entry_id))),
                    pdf_url=HttpUrl(str(pdf)),
                )
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            LOGGER.warning("Skipping malformed arXiv entry: %s", exc)
    return records


class ArxivClient:
    def __init__(
        self,
        settings: Settings,
        session: Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.session = session or build_session(
            settings.pipeline.user_agent,
            settings.pipeline.retry_attempts,
            settings.pipeline.backoff_seconds,
        )
        self.sleeper = sleeper

    def fetch(
        self, topics: TopicsConfig, since: datetime
    ) -> tuple[list[RawArxivRecord], list[bytes]]:
        category_query = " OR ".join(f"cat:{category}" for category in topics.allowed_categories)
        collected: list[RawArxivRecord] = []
        raw_pages: list[bytes] = []
        page_size = self.settings.pipeline.arxiv_page_size
        for page in range(self.settings.pipeline.arxiv_max_pages):
            params: dict[str, str | int] = {
                "search_query": f"({category_query})",
                "start": page * page_size,
                "max_results": page_size,
                "sortBy": "lastUpdatedDate",
                "sortOrder": "descending",
            }
            response = self.session.get(
                API_URL,
                params=params,
                timeout=self.settings.pipeline.request_timeout_seconds,
            )
            response.raise_for_status()
            raw_pages.append(response.content)
            page_records = parse_atom(response.content)
            if not page_records:
                break
            collected.extend(record for record in page_records if record.updated_at >= since)
            reached_cutoff = min(record.updated_at for record in page_records) < since
            if reached_cutoff or len(page_records) < page_size:
                break
            if page + 1 < self.settings.pipeline.arxiv_max_pages:
                self.sleeper(self.settings.pipeline.arxiv_request_interval_seconds)
        return collected, raw_pages


def default_since(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def save_raw_response(root: Path, content: bytes, fetched_at: datetime | None = None) -> Path:
    fetched_at = fetched_at or datetime.now(UTC)
    path = root / "data" / "raw" / "arxiv" / f"{fetched_at:%Y%m%dT%H%M%SZ}.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def save_raw_responses(
    root: Path, contents: list[bytes], fetched_at: datetime | None = None
) -> list[Path]:
    fetched_at = fetched_at or datetime.now(UTC)
    paths: list[Path] = []
    for index, content in enumerate(contents, 1):
        path = root / "data" / "raw" / "arxiv" / f"{fetched_at:%Y%m%dT%H%M%SZ}-page-{index:03d}.xml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        paths.append(path)
    return paths
