from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from theory_daily.fetch_arxiv import ArxivClient, parse_atom

FIXTURES = Path(__file__).parent / "fixtures"


def test_arxiv_atom_normal_parse() -> None:
    records = parse_atom((FIXTURES / "arxiv.xml").read_bytes())
    assert len(records) == 1
    record = records[0]
    assert record.arxiv_id == "2607.00001v2"
    assert record.version == 2
    assert record.primary_category == "gr-qc"
    assert str(record.pdf_url).endswith("2607.00001v2")


def test_arxiv_missing_fields_are_rejected() -> None:
    assert parse_atom((FIXTURES / "arxiv_missing.xml").read_bytes()) == []


class Response:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


class Session:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.pages = [
            (FIXTURES / "arxiv.xml").read_bytes(),
            b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>',
        ]

    def get(self, *_args: object, **kwargs: Any) -> Response:
        self.calls.append(kwargs)
        return Response(self.pages[len(self.calls) - 1])


def test_arxiv_paginates_until_an_empty_page(settings, topics) -> None:
    settings.pipeline.arxiv_page_size = 1
    settings.pipeline.arxiv_max_pages = 3
    settings.pipeline.arxiv_request_interval_seconds = 0
    session = Session()
    client = ArxivClient(
        settings,
        session=session,  # type: ignore[arg-type]
        sleeper=lambda _seconds: None,
    )
    records, raw_pages = client.fetch(topics, datetime(2026, 7, 10, tzinfo=UTC))
    assert len(records) == 1
    assert len(raw_pages) == 2
    assert len(session.calls) == 2
    assert session.calls[0]["params"]["start"] == 0
    assert session.calls[1]["params"]["start"] == 1
