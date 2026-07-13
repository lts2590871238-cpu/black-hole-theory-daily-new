"""Human-readable logging without secrets or external paper bodies."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(root: Path, *, verbose: bool = False) -> None:
    log_dir = root / "data" / "reports"
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    handlers.append(logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8"))
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
