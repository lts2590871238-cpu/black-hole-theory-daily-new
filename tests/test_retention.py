from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from theory_daily.demo import demo_papers
from theory_daily.render import load_published_papers
from theory_daily.retention import maintain_retention, paper_path, read_published
from theory_daily.storage import write_json


def test_old_paper_is_losslessly_compressed_and_remains_available(tmp_path: Path) -> None:
    now = datetime(2026, 11, 17, tzinfo=UTC)
    old = demo_papers(now)[0]
    old.paper.submitted_at = now - timedelta(days=40)
    new = demo_papers(now)[1]
    root = tmp_path / "data" / "papers"
    write_json(root / "old.json", old)
    write_json(root / "new.json", new)
    original = (root / "old.json").read_bytes()
    maintain_retention(tmp_path, now)
    assert not (root / "old.json").exists()
    assert gzip.decompress((root / "old.json.gz").read_bytes()) == original
    assert (root / "new.json").exists()
    assert paper_path(tmp_path, "old.json") == root / "old.json.gz"
    assert read_published(root / "old.json.gz").paper.canonical_key == old.paper.canonical_key
    assert len(load_published_papers(tmp_path)) == 2


def test_old_raw_snapshots_are_pruned_newer_snapshots_compressed(tmp_path: Path) -> None:
    root = tmp_path / "data" / "raw" / "inspire"
    root.mkdir(parents=True)
    (root / "20260901T000000Z.json").write_text('{"old": true}', encoding="utf-8")
    recent = root / "20261116T000000Z.json"
    recent.write_text('{"new": true}', encoding="utf-8")
    maintain_retention(tmp_path, datetime(2026, 11, 17, tzinfo=UTC))
    assert not (root / "20260901T000000Z.json").exists()
    assert not recent.exists()
    assert json.loads(gzip.decompress(
        (root / "20261116T000000Z.json.gz").read_bytes()
    )) == {"new": True}



def test_rolling_cutoff_uses_beijing_calendar_days() -> None:
    from datetime import date

    from theory_daily.retention import archive_cutoff_date

    # Beijing 2026-11-17 12:00 and the next local midnight.
    assert archive_cutoff_date(datetime(2026, 11, 17, 4, tzinfo=UTC)) == date(
        2026, 11, 3
    )
    assert archive_cutoff_date(datetime(2026, 11, 17, 16, tzinfo=UTC)) == date(
        2026, 11, 4
    )


def test_archive_boundary_date_is_included_until_next_day(tmp_path: Path) -> None:
    from datetime import timezone

    local = timezone(timedelta(hours=8))
    noon_17 = datetime(2026, 11, 17, 12, tzinfo=local)
    boundary = demo_papers(noon_17)[0]
    boundary.paper.submitted_at = datetime(2026, 11, 3, 0, tzinfo=local)
    older = demo_papers(noon_17)[1]
    older.paper.submitted_at = datetime(2026, 11, 2, 23, 59, tzinfo=local)

    root = tmp_path / "data" / "papers"
    write_json(root / "boundary.json", boundary)
    write_json(root / "older.json", older)
    maintain_retention(tmp_path, noon_17)
    assert (root / "boundary.json").exists()
    assert not (root / "older.json").exists()
    assert (root / "older.json.gz").exists()

    # On November 18, the November 3 article is also archived.
    maintain_retention(tmp_path, noon_17 + timedelta(days=1))
    assert not (root / "boundary.json").exists()
    assert (root / "boundary.json.gz").exists()
