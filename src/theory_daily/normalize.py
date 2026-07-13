"""Normalize arXiv and INSPIRE records into one provenance-preserving model."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import UTC, datetime

from theory_daily.models import (
    NormalizedPaper,
    RawArxivRecord,
    RawInspireRecord,
    SourceProvenance,
)

_ARXIV_VERSION = re.compile(r"v(?P<version>\d+)$", re.IGNORECASE)
_NON_WORD = re.compile(r"[^a-z0-9]+")


def normalize_arxiv_id(value: str) -> tuple[str, int | None]:
    value = value.strip().removeprefix("arXiv:")
    version_match = _ARXIV_VERSION.search(value)
    version = int(version_match.group("version")) if version_match else None
    if version_match:
        value = value[: version_match.start()]
    return value.lower(), version


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        cleaned = cleaned.removeprefix(prefix)
    return cleaned.rstrip(". ") or None


def normalized_title(value: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return _NON_WORD.sub(" ", ascii_title.lower()).strip()


def title_key(title: str) -> str:
    digest = hashlib.sha256(normalized_title(title).encode()).hexdigest()[:24]
    return f"title:{digest}"


def canonical_key(arxiv_id: str | None, doi: str | None, title: str) -> str:
    if arxiv_id:
        paper_id, _ = normalize_arxiv_id(arxiv_id)
        return f"arxiv:{paper_id}"
    normalized_doi = normalize_doi(doi)
    if normalized_doi:
        return f"doi:{normalized_doi}"
    return title_key(title)


def from_arxiv(record: RawArxivRecord, fetched_at: datetime | None = None) -> NormalizedPaper:
    fetched_at = fetched_at or datetime.now(UTC)
    paper_id, _ = normalize_arxiv_id(record.arxiv_id)
    return NormalizedPaper(
        canonical_key=canonical_key(paper_id, record.doi, record.title),
        arxiv_id=paper_id,
        arxiv_version=record.version,
        doi=normalize_doi(record.doi),
        title_en=record.title,
        abstract_en=record.abstract,
        authors=record.authors,
        categories=record.categories,
        submitted_at=record.submitted_at,
        updated_at=record.updated_at,
        journal_ref=record.journal_ref,
        abs_url=record.abs_url,
        pdf_url=record.pdf_url,
        is_update=record.version > 1,
        source_provenance=[
            SourceProvenance(
                source="arxiv", record_id=paper_id, fetched_at=fetched_at, url=record.abs_url
            )
        ],
    )


def from_inspire(record: RawInspireRecord, fetched_at: datetime | None = None) -> NormalizedPaper:
    fetched_at = fetched_at or datetime.now(UTC)
    arxiv_id = normalize_arxiv_id(record.arxiv_id)[0] if record.arxiv_id else None
    submitted = datetime.combine(record.earliest_date, datetime.min.time(), tzinfo=UTC)
    return NormalizedPaper(
        canonical_key=canonical_key(arxiv_id, record.doi, record.title),
        arxiv_id=arxiv_id,
        inspire_id=record.inspire_id,
        doi=normalize_doi(record.doi),
        title_en=record.title,
        abstract_en=record.abstract,
        authors=record.authors,
        submitted_at=submitted,
        updated_at=record.updated_at or submitted,
        document_types=record.document_type,
        publication_info=record.publication_info,
        citation_count=record.citation_count,
        citation_count_without_self_citations=record.citation_count_without_self_citations,
        inspire_url=record.record_url,
        source_provenance=[
            SourceProvenance(
                source="inspire",
                record_id=record.inspire_id,
                fetched_at=fetched_at,
                url=record.record_url,
            )
        ],
    )
