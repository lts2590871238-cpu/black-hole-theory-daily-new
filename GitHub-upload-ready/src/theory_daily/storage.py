"""Atomic, schema-versioned JSON persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from theory_daily.models import SCHEMA_VERSION, PipelineState


def ensure_directories(root: Path) -> None:
    for relative in (
        "data/raw/arxiv",
        "data/raw/inspire",
        "data/normalized",
        "data/papers",
        "data/review_queue",
        "data/rejected",
        "data/cache/llm",
        "data/reports",
        "dist",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)


def write_json(path: Path, value: BaseModel | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.setdefault("schema_version", SCHEMA_VERSION)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def read_model[ModelT: BaseModel](path: Path, model: type[ModelT]) -> ModelT:
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def load_state(root: Path) -> PipelineState:
    path = root / "data" / "state.json"
    if not path.exists():
        state = PipelineState()
        write_json(path, state)
        return state
    return read_model(path, PipelineState)
