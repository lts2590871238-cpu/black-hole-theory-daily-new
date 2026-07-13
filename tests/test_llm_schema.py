from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from theory_daily.llm_curation import LLMDecisionPayload, paper_payload
from theory_daily.models import FilterResult


def test_invalid_structured_response_is_rejected() -> None:
    with pytest.raises(ValidationError):
        LLMDecisionPayload.model_validate(
            {
                "relevant": True,
                "primary_topic": "not-a-topic",
                "theory_depth_score": 99,
            }
        )


def test_zero_citations_are_neutral_for_new_paper(paper_factory) -> None:
    paper = paper_factory(
        submitted_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        citation_count=0,
    )
    payload = paper_payload(paper, FilterResult(passed=True))
    assert payload["metadata"]["new_paper_zero_citations_are_neutral"] is True
    assert payload["metadata"]["citation_count"] == 0
    assert "authors" not in payload["metadata"]
