"""Central configuration loading with environment overrides."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from theory_daily.models import TopicId


class SiteConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title_en: str
    title_zh: str
    timezone: str
    base_url: str


class PipelineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    since_days: int = Field(ge=1, le=30)
    selection_threshold: int = Field(ge=0, le=100)
    review_min_score: int = Field(ge=0, le=100)
    max_llm_papers_per_run: int = Field(ge=1)
    min_abstract_chars: int = Field(ge=1)
    request_timeout_seconds: int = Field(ge=1)
    retry_attempts: int = Field(ge=1)
    backoff_seconds: float = Field(gt=0)
    arxiv_page_size: int = Field(ge=1, le=2000)
    arxiv_max_pages: int = Field(ge=1, le=20)
    arxiv_request_interval_seconds: float = Field(ge=0)
    inspire_page_size: int = Field(ge=1, le=250)
    max_inspire_pages: int = Field(ge=1, le=100)
    user_agent: str


class VersionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str
    llm_schema: str
    translation: str
    filter: str


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str
    config_version: str
    site: SiteConfig
    pipeline: PipelineConfig
    versions: VersionConfig


class TopicRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label_zh: str
    label_en: str
    high_weight: list[str]
    medium_weight: list[str]


class TopicsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str
    config_version: str
    allowed_categories: list[str]
    topics: dict[TopicId, TopicRule]
    negative_terms: list[str]
    hard_exclusions: list[str]


class RuntimeConfig(BaseModel):
    provider: Literal["openai", "deepseek"]
    model: str
    reasoning_effort: str
    max_llm_papers: int
    api_key_env: str
    base_url: str | None = None


def _yaml(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_settings(root: Path) -> Settings:
    return Settings.model_validate(_yaml(root / "config" / "settings.yaml"))


def load_topics(root: Path) -> TopicsConfig:
    return TopicsConfig.model_validate(_yaml(root / "config" / "topics.yaml"))


def runtime_config(settings: Settings) -> RuntimeConfig:
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider == "deepseek":
        return RuntimeConfig(
            provider="deepseek",
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            reasoning_effort="disabled",
            max_llm_papers=int(
                os.getenv("MAX_LLM_PAPERS_PER_RUN", settings.pipeline.max_llm_papers_per_run)
            ),
            api_key_env="DEEPSEEK_API_KEY",
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
    if provider != "openai":
        raise ValueError("LLM_PROVIDER 必须是 openai 或 deepseek")
    return RuntimeConfig(
        provider="openai",
        model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
        reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "low"),
        max_llm_papers=int(
            os.getenv("MAX_LLM_PAPERS_PER_RUN", settings.pipeline.max_llm_papers_per_run)
        ),
        api_key_env="OPENAI_API_KEY",
    )


def configuration_fingerprint(settings: Settings, topics: TopicsConfig) -> str:
    payload = {
        "settings": settings.model_dump(mode="json"),
        "topics": topics.model_dump(mode="json"),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]
