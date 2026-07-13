"""Versioned Pydantic models shared by every pipeline stage."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

SCHEMA_VERSION = "1.0"
TopicId = Literal[
    "black_hole_thermodynamics",
    "pta",
    "holography_condensed_matter",
    "general_relativity_foundations",
]


class StrictModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RawArxivRecord(StrictModel):
    schema_version: str = SCHEMA_VERSION
    arxiv_id: str
    version: int = Field(ge=1)
    submitted_at: datetime
    updated_at: datetime
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    comments: str | None = None
    journal_ref: str | None = None
    doi: str | None = None
    abs_url: HttpUrl
    pdf_url: HttpUrl


class RawInspireRecord(StrictModel):
    schema_version: str = SCHEMA_VERSION
    inspire_id: str
    earliest_date: date
    updated_at: datetime | None = None
    title: str
    abstract: str
    authors: list[str]
    document_type: list[str] = Field(default_factory=list)
    arxiv_id: str | None = None
    doi: str | None = None
    citation_count: int | None = Field(default=None, ge=0)
    citation_count_without_self_citations: int | None = Field(default=None, ge=0)
    publication_info: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    record_url: HttpUrl


class SourceProvenance(StrictModel):
    source: Literal["arxiv", "inspire", "demo"]
    record_id: str
    fetched_at: datetime
    url: HttpUrl


class NormalizedPaper(StrictModel):
    schema_version: str = SCHEMA_VERSION
    canonical_key: str
    arxiv_id: str | None = None
    arxiv_version: int | None = Field(default=None, ge=1)
    inspire_id: str | None = None
    doi: str | None = None
    title_en: str
    abstract_en: str
    authors: list[str]
    categories: list[str] = Field(default_factory=list)
    submitted_at: datetime
    updated_at: datetime
    document_types: list[str] = Field(default_factory=list)
    journal_ref: str | None = None
    publication_info: list[str] = Field(default_factory=list)
    citation_count: int | None = Field(default=None, ge=0)
    citation_count_without_self_citations: int | None = Field(default=None, ge=0)
    abs_url: HttpUrl | None = None
    pdf_url: HttpUrl | None = None
    inspire_url: HttpUrl | None = None
    is_update: bool = False
    source_provenance: list[SourceProvenance]
    is_demo: bool = False

    @field_validator("authors")
    @classmethod
    def require_author(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("at least one author is required")
        return value


class FilterResult(StrictModel):
    schema_version: str = SCHEMA_VERSION
    passed: bool
    candidate_topics: list[TopicId] = Field(default_factory=list)
    high_weight_hits: list[str] = Field(default_factory=list)
    medium_weight_hits: list[str] = Field(default_factory=list)
    negative_hits: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    deterministic_score: int = 0


class ScoreBreakdown(StrictModel):
    theory_depth: int = Field(ge=0, le=30)
    methodological_rigor: int = Field(ge=0, le=20)
    novelty: int = Field(ge=0, le=15)
    clarity: int = Field(ge=0, le=10)
    metadata_quality: int = Field(ge=0, le=10)
    community_signal: int = Field(ge=0, le=5)
    other: int = Field(ge=0, le=10)

    @property
    def total(self) -> int:
        return sum(self.model_dump().values())


class CurationDecision(StrictModel):
    schema_version: str = SCHEMA_VERSION
    relevant: bool
    primary_topic: TopicId
    secondary_topics: list[TopicId] = Field(default_factory=list)
    scores: ScoreBreakdown
    total_score: int = Field(ge=0, le=100)
    reject_reason_zh: str = ""
    selection_reason_zh: str = ""
    title_zh: str
    abstract_zh: str
    keywords_en: list[str] = Field(default_factory=list)
    keywords_zh: list[str] = Field(default_factory=list)
    translation_warning: str = ""
    model: str
    prompt_version: str
    schema_version_used: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def totals_must_match(self) -> CurationDecision:
        if self.total_score != self.scores.total:
            raise ValueError("total_score must equal the score component sum")
        return self


class PublishedPaper(StrictModel):
    schema_version: str = SCHEMA_VERSION
    paper: NormalizedPaper
    filter_result: FilterResult
    decision: CurationDecision
    published_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PipelineState(StrictModel):
    schema_version: str = SCHEMA_VERSION
    last_successful_run: datetime | None = None
    processed_cache_keys: list[str] = Field(default_factory=list)
    latest_site_build: datetime | None = None


class RunReport(StrictModel):
    schema_version: str = SCHEMA_VERSION
    started_at: datetime
    completed_at: datetime | None = None
    status: Literal["running", "success", "degraded", "failed"] = "running"
    fetched_arxiv: int = 0
    fetched_inspire: int = 0
    normalized: int = 0
    deduplicated: int = 0
    candidates: int = 0
    selected: int = 0
    review_queue: int = 0
    rejected: int = 0
    llm_calls: int = 0
    cached_decisions: int = 0
    errors: list[str] = Field(default_factory=list)


class PaperCollection(StrictModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: datetime
    papers: list[PublishedPaper]
