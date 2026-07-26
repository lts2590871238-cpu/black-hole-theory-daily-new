from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from requests import ReadTimeout

from theory_daily.llm_curation import FakeCurationClient
from theory_daily.pipeline import update


def _site_root(tmp_path: Path) -> Path:
    project_root = Path(__file__).resolve().parents[1]
    shutil.copytree(project_root / "static", tmp_path / "static")
    shutil.copytree(project_root / "templates", tmp_path / "templates")
    return tmp_path


def test_update_continues_with_inspire_when_arxiv_is_unavailable(
    tmp_path: Path, settings, topics, monkeypatch
) -> None:
    def fail_arxiv(*_args: object, **_kwargs: object) -> object:
        raise ReadTimeout("arXiv timed out")

    def empty_inspire(*_args: object, **_kwargs: object) -> tuple[list[object], list[dict]]:
        return [], []

    monkeypatch.setattr("theory_daily.pipeline.ArxivClient.fetch", fail_arxiv)
    monkeypatch.setattr("theory_daily.pipeline.InspireClient.fetch", empty_inspire)

    report = update(
        _site_root(tmp_path),
        settings,
        topics,
        curation_client=FakeCurationClient([]),
    )

    assert report.status == "degraded"
    assert report.fetched_arxiv == 0
    assert any("arXiv data source temporarily unavailable" in error for error in report.errors)
    assert (tmp_path / "dist" / "index.html").exists()


def test_update_stops_when_both_sources_are_unavailable(
    tmp_path: Path, settings, topics, monkeypatch
) -> None:
    def fail_source(*_args: object, **_kwargs: object) -> object:
        raise ReadTimeout("source timed out")

    monkeypatch.setattr("theory_daily.pipeline.ArxivClient.fetch", fail_source)
    monkeypatch.setattr("theory_daily.pipeline.InspireClient.fetch", fail_source)

    with pytest.raises(RuntimeError, match="arXiv and INSPIRE data sources are both unavailable"):
        update(
            _site_root(tmp_path),
            settings,
            topics,
            curation_client=FakeCurationClient([]),
        )
