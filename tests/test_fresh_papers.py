from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from theory_daily.demo import demo_papers
from theory_daily.models import FilterResult
from theory_daily.pipeline import _pending_candidate, _prioritize_candidates
from theory_daily.retention import maintain_retention
from theory_daily.storage import write_json


def test_published_paper_is_skipped_until_revised(tmp_path: Path) -> None:
    paper = demo_papers(datetime.now(UTC))[0]
    paper.paper.submitted_at = datetime.now(UTC) - timedelta(days=40)
    filename = "demo_paper-01.json"
    write_json(tmp_path / "data" / "papers" / filename, paper)
    assert not _pending_candidate(tmp_path, paper.paper)
    maintain_retention(tmp_path, datetime.now(UTC))
    assert not _pending_candidate(tmp_path, paper.paper)
    changed = paper.paper.model_copy(update={"updated_at": datetime.now(UTC) + timedelta(days=1)})
    assert _pending_candidate(tmp_path, changed)


def test_topic_balancing_still_applies_to_new_candidates(
    tmp_path: Path, paper_factory, topics
) -> None:
    now = datetime(2026, 11, 17, tzinfo=UTC)
    source = []
    for i in range(70):
        paper = paper_factory(canonical_key=f"arxiv:old-{i}", updated_at=now)
        source.append((
            paper, FilterResult(passed=True, candidate_topics=["general_relativity_foundations"])
        ))
    for i, topic in enumerate(("metric_affine_gravity", "palatini_gravity", "modified_gravity")):
        paper = paper_factory(canonical_key=f"arxiv:fresh-{i}", updated_at=now)
        source.append((paper, FilterResult(passed=True, candidate_topics=[topic])))
    ordered = _prioritize_candidates(
        [pair for pair in source if _pending_candidate(tmp_path, pair[0])], topics
    )
    selected = {x for _, result in ordered[:60] for x in result.candidate_topics}
    assert {"metric_affine_gravity", "palatini_gravity", "modified_gravity"} <= selected
