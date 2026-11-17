"""Bounded diagnostics and lossless compression of historical papers."""

from __future__ import annotations

import gzip
import os
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from theory_daily.models import PublishedPaper

_STAMP = re.compile(r"^(\d{8}T\d{6}Z)")


def read_published(path: Path) -> PublishedPaper:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return PublishedPaper.model_validate_json(stream.read())
    return PublishedPaper.model_validate_json(path.read_text(encoding="utf-8"))


def paper_path(root: Path, filename: str) -> Path | None:
    plain = root / "data" / "papers" / filename
    if plain.exists():
        return plain
    archive = plain.with_name(plain.name + ".gz")
    return archive if archive.exists() else None


def _compress(path: Path) -> Path:
    target = path.with_name(path.name + ".gz")
    temporary = target.with_name(target.name + ".tmp")
    try:
        with path.open("rb") as source, gzip.open(temporary, "wb", compresslevel=6) as output:
            shutil.copyfileobj(source, output)
        os.replace(temporary, target)
        path.unlink()
    finally:
        temporary.unlink(missing_ok=True)
    return target


def maintain_retention(root: Path, now: datetime, *, days: int = 30) -> None:
    """Prune old fetch snapshots; never delete published papers or LLM cache."""
    if now.tzinfo is None:
        raise ValueError("retention timestamp must be timezone-aware")
    cutoff = now.astimezone(UTC) - timedelta(days=days)
    for folder in ("data/raw/arxiv", "data/raw/inspire", "data/normalized"):
        location = root / folder
        if not location.exists():
            continue
        for path in location.iterdir():
            if not path.is_file() or path.name.endswith(".tmp"):
                continue
            match = _STAMP.match(path.name)
            if match is None:
                continue
            stamped = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            if stamped < cutoff:
                path.unlink()
            elif path.suffix in {".xml", ".json"}:
                _compress(path)

    published = root / "data" / "papers"
    if published.exists():
        for path in published.glob("*.json"):
            paper = read_published(path)
            if paper.paper.submitted_at < cutoff:
                _compress(path)
