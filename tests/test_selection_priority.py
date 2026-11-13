from __future__ import annotations

from datetime import UTC, datetime, timedelta

from theory_daily.models import FilterResult
from theory_daily.pipeline import _prioritize_candidates


def test_new_gravity_topics_not_starved_by_daily_llm_limit(
    paper_factory, topics
) -> None:
    now = datetime(2026, 11, 13, tzinfo=UTC)
    candidates = []
    for i in range(70):
        paper = paper_factory(
            canonical_key=f"arxiv:old-{i}",
            updated_at=now - timedelta(minutes=i),
        )
        candidates.append((
            paper,
            FilterResult(passed=True, candidate_topics=["general_relativity_foundations"]),
        ))
    for i, topic in enumerate(
        ("metric_affine_gravity", "palatini_gravity", "modified_gravity"), 1
    ):
        paper = paper_factory(
            canonical_key=f"arxiv:new-{i}",
            updated_at=now - timedelta(days=i),
        )
        candidates.append((paper, FilterResult(passed=True, candidate_topics=[topic])))
    ranked = _prioritize_candidates(candidates, topics)
    assert len(ranked) == len(candidates)
    first_sixty_topics = {
        topic for _, result in ranked[:60] for topic in result.candidate_topics
    }
    assert {"metric_affine_gravity", "palatini_gravity", "modified_gravity"} <= first_sixty_topics
