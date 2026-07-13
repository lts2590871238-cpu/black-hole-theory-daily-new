from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from theory_daily.fetch_inspire import InspireClient, parse_record


def _hit() -> dict[str, Any]:
    return {
        "id": "12345",
        "created": "2026-07-11T00:00:00+00:00",
        "updated": "2026-07-12T00:00:00+00:00",
        "links": {"self": "https://inspirehep.net/api/literature/12345"},
        "metadata": {
            "earliest_date": "2026-07-11",
            "titles": [{"title": "A causal structure theorem"}],
            "abstracts": [{"value": "A sufficiently long abstract about causal structure."}],
            "authors": [{"full_name": "Example, Alice"}],
            "document_type": ["article"],
            "arxiv_eprints": [{"value": "2607.00001"}],
            "dois": [{"value": "10.1000/example.1"}],
            "citation_count": 4,
            "citation_count_without_self_citations": 3,
            "publication_info": [{"journal_title": "Demo", "year": 2026}],
            "documents": [{"url": "https://example.invalid/paper.pdf"}],
        },
    }


class Response:
    def __init__(self, status: int, payload: dict[str, Any]) -> None:
        self.status_code = status
        self._payload = payload
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(str(self.status_code))


class Session:
    def __init__(self) -> None:
        self.calls = 0

    def get(self, *_args: object, **_kwargs: object) -> Response:
        self.calls += 1
        if self.calls == 1:
            return Response(429, {})
        return Response(200, {"hits": {"hits": [_hit()]}})


def test_inspire_normal_parse() -> None:
    record = parse_record(_hit())
    assert record.inspire_id == "12345"
    assert record.arxiv_id == "2607.00001"
    assert record.citation_count_without_self_citations == 3
    assert "Example, Alice" in record.authors


def test_inspire_429_is_retried(settings) -> None:
    settings.pipeline.max_inspire_pages = 1
    session = Session()
    client = InspireClient(settings, session=session, sleeper=lambda _seconds: None)  # type: ignore[arg-type]
    records, _pages = client.fetch(datetime(2026, 7, 10, tzinfo=UTC))
    assert session.calls == 2
    assert len(records) == 1
