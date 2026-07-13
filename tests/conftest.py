from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from theory_daily.config import Settings, TopicsConfig, load_settings, load_topics
from theory_daily.models import NormalizedPaper

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings() -> Settings:
    return load_settings(ROOT)


@pytest.fixture
def topics() -> TopicsConfig:
    return load_topics(ROOT)


@pytest.fixture
def paper_factory():
    def make(**updates: object) -> NormalizedPaper:
        now = datetime(2026, 7, 12, 8, tzinfo=UTC)
        data: dict[str, object] = {
            "canonical_key": "arxiv:2607.00001",
            "arxiv_id": "2607.00001",
            "arxiv_version": 1,
            "title_en": "Black hole thermodynamics and generalized entropy",
            "abstract_en": (
                "We study black hole thermodynamics and generalized entropy in a controlled "
                "semiclassical regime. We state the assumptions, derive a first-law relation, "
                "and compare the result with an independent Euclidean calculation. The analysis "
                "identifies the range in which the approximation remains valid and separates "
                "the established result from a conjectured extension. " * 2
            ),
            "authors": ["A. Researcher", "B. Scholar"],
            "categories": ["gr-qc"],
            "submitted_at": now,
            "updated_at": now,
            "abs_url": "https://arxiv.org/abs/2607.00001v1",
            "pdf_url": "https://arxiv.org/pdf/2607.00001v1",
            "source_provenance": [
                {
                    "source": "arxiv",
                    "record_id": "2607.00001",
                    "fetched_at": now,
                    "url": "https://arxiv.org/abs/2607.00001v1",
                }
            ],
        }
        data.update(updates)
        return NormalizedPaper.model_validate(data)

    return make
