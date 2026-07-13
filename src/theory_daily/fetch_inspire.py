"""INSPIRE-HEP literature REST client with graceful source degradation."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from dateutil.parser import isoparse
from pydantic import HttpUrl
from requests import Response, Session

from theory_daily.config import Settings
from theory_daily.http_client import build_session
from theory_daily.models import RawInspireRecord
from theory_daily.storage import write_json

LOGGER = logging.getLogger(__name__)
API_URL = "https://inspirehep.net/api/literature"


def _first(items: list[dict[str, Any]] | None, field: str) -> str | None:
    if not items:
        return None
    value = items[0].get(field)
    return str(value) if value else None


def parse_record(hit: dict[str, Any]) -> RawInspireRecord:
    metadata = hit.get("metadata", {})
    titles = metadata.get("titles") or []
    abstracts = metadata.get("abstracts") or []
    arxiv_eprints = metadata.get("arxiv_eprints") or []
    dois = metadata.get("dois") or []
    authors = [
        str(item.get("full_name")) for item in metadata.get("authors", []) if item.get("full_name")
    ]
    publication_info = [
        ", ".join(str(value) for value in item.values() if value)
        for item in metadata.get("publication_info", [])
    ]
    documents = [str(item.get("url")) for item in metadata.get("documents", []) if item.get("url")]
    created = str(metadata.get("earliest_date") or hit.get("created") or "")[:10]
    updated_raw = hit.get("updated")
    links = hit.get("links") or {}
    record_id = str(hit.get("id") or metadata.get("control_number") or "")
    return RawInspireRecord(
        inspire_id=record_id,
        earliest_date=date.fromisoformat(created),
        updated_at=isoparse(updated_raw).astimezone(UTC) if updated_raw else None,
        title=_first(titles, "title") or "",
        abstract=_first(abstracts, "value") or "",
        authors=authors,
        document_type=[str(item) for item in metadata.get("document_type", [])],
        arxiv_id=_first(arxiv_eprints, "value"),
        doi=_first(dois, "value"),
        citation_count=metadata.get("citation_count"),
        citation_count_without_self_citations=metadata.get("citation_count_without_self_citations"),
        publication_info=publication_info,
        documents=documents,
        record_url=HttpUrl(
            str(links.get("self") or f"https://inspirehep.net/literature/{record_id}")
        ),
    )


class InspireClient:
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

    def _get(self, params: dict[str, Any]) -> Response:
        attempts = self.settings.pipeline.retry_attempts
        for attempt in range(attempts):
            response = self.session.get(
                API_URL, params=params, timeout=self.settings.pipeline.request_timeout_seconds
            )
            if response.status_code not in {429, 500, 502, 503, 504}:
                response.raise_for_status()
                return response
            if attempt < attempts - 1:
                retry_after = response.headers.get("Retry-After")
                delay = (
                    float(retry_after)
                    if retry_after
                    else self.settings.pipeline.backoff_seconds * 2**attempt
                )
                self.sleeper(delay)
        response.raise_for_status()
        raise RuntimeError("unreachable")

    def fetch(self, since: datetime) -> tuple[list[RawInspireRecord], list[dict[str, Any]]]:
        records: list[RawInspireRecord] = []
        pages: list[dict[str, Any]] = []
        cutoff = since.date()
        for page in range(1, self.settings.pipeline.max_inspire_pages + 1):
            response = self._get(
                {
                    "sort": "mostrecent",
                    "size": self.settings.pipeline.inspire_page_size,
                    "page": page,
                    "fields": (
                        "titles,abstracts,authors,document_type,arxiv_eprints,dois,"
                        "citation_count,citation_count_without_self_citations,earliest_date,"
                        "publication_info,documents"
                    ),
                }
            )
            payload = response.json()
            pages.append(payload)
            hits = payload.get("hits", {}).get("hits", [])
            if not hits:
                break
            stop = False
            for hit in hits:
                try:
                    record = parse_record(hit)
                except (TypeError, ValueError) as exc:
                    LOGGER.warning("Skipping malformed INSPIRE record: %s", exc)
                    continue
                if record.earliest_date < cutoff:
                    stop = True
                    continue
                records.append(record)
            if stop:
                break
        return records, pages


def save_raw_pages(
    root: Path, pages: list[dict[str, Any]], fetched_at: datetime | None = None
) -> Path:
    fetched_at = fetched_at or datetime.now(UTC)
    path = root / "data" / "raw" / "inspire" / f"{fetched_at:%Y%m%dT%H%M%SZ}.json"
    write_json(path, {"fetched_at": fetched_at.isoformat(), "pages": pages})
    return path
