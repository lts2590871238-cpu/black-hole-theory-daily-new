"""End-to-end update orchestration with failure-safe deployment staging."""

from __future__ import annotations

import logging
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from theory_daily.config import (
    Settings,
    TopicsConfig,
    configuration_fingerprint,
    runtime_config,
)
from theory_daily.deduplicate import deduplicate
from theory_daily.deterministic_filter import filter_paper
from theory_daily.fetch_arxiv import ArxivClient, save_raw_responses
from theory_daily.fetch_inspire import InspireClient, save_raw_pages
from theory_daily.health import validate_dist
from theory_daily.llm_curation import (
    CurationClient,
    build_curation_client,
    curate_with_cache,
)
from theory_daily.models import PublishedPaper, RawInspireRecord, RunReport
from theory_daily.normalize import from_arxiv, from_inspire
from theory_daily.render import build_site, load_published_papers
from theory_daily.storage import ensure_directories, load_state, write_json

LOGGER = logging.getLogger(__name__)


def _filename(canonical_key: str) -> str:
    return canonical_key.replace(":", "_").replace("/", "_") + ".json"


def _publish_staging(root: Path, staging: Path) -> None:
    dist = root / "dist"
    backup = root / "work" / "dist-previous"
    if backup.exists():
        shutil.rmtree(backup)
    if dist.exists():
        shutil.move(str(dist), str(backup))
    try:
        shutil.move(str(staging), str(dist))
    except Exception:
        if backup.exists() and not dist.exists():
            shutil.move(str(backup), str(dist))
        raise
    if backup.exists():
        shutil.rmtree(backup)


def update(
    root: Path,
    settings: Settings,
    topics: TopicsConfig,
    *,
    since_days: int | None = None,
    curation_client: CurationClient | None = None,
) -> RunReport:
    runtime = runtime_config(settings)
    if curation_client is None:
        api_key = os.getenv(runtime.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"{runtime.provider} 正式更新需要 {runtime.api_key_env}。"
                "请设置环境变量；无密钥预览请运行 demo --fixtures。"
            )
        curation_client = build_curation_client(runtime, api_key)
    ensure_directories(root)
    started = datetime.now(UTC)
    report = RunReport(started_at=started)
    state = load_state(root)
    days = since_days or settings.pipeline.since_days
    rolling_since = started - timedelta(days=days)
    if state.last_successful_run:
        since = min(rolling_since, state.last_successful_run - timedelta(hours=6))
    else:
        since = rolling_since
    try:
        arxiv_records, arxiv_raw_pages = ArxivClient(settings).fetch(topics, since)
        save_raw_responses(root, arxiv_raw_pages, started)
        report.fetched_arxiv = len(arxiv_records)
        inspire_records: list[RawInspireRecord] = []
        try:
            inspire_records, inspire_pages = InspireClient(settings).fetch(since)
            save_raw_pages(root, inspire_pages, started)
            report.fetched_inspire = len(inspire_records)
        except Exception as exc:  # source degradation is intentional
            message = f"INSPIRE 数据源暂时不可用：{exc}"
            LOGGER.warning(message)
            report.errors.append(message)

        normalized = [from_arxiv(item, started) for item in arxiv_records]
        normalized.extend(from_inspire(item, started) for item in inspire_records)
        report.normalized = len(normalized)
        merged = deduplicate(normalized)
        report.deduplicated = len(merged)
        write_json(
            root / "data" / "normalized" / f"{started:%Y%m%dT%H%M%SZ}.json",
            {
                "generated_at": started.isoformat(),
                "papers": [item.model_dump(mode="json") for item in merged],
            },
        )

        candidates = []
        for paper in merged:
            result = filter_paper(paper, topics, settings)
            if result.passed:
                candidates.append((paper, result))
                continue
            report.rejected += 1
            write_json(
                root / "data" / "rejected" / _filename(paper.canonical_key),
                {
                    "paper": paper.model_dump(mode="json"),
                    "filter_result": result.model_dump(mode="json"),
                },
            )
        report.candidates = len(candidates)

        client = curation_client
        fingerprint = configuration_fingerprint(settings, topics)
        failures = 0
        for paper, result in candidates[: runtime.max_llm_papers]:
            try:
                decision, cached = curate_with_cache(
                    root, paper, result, client, runtime, settings, fingerprint
                )
            except Exception as exc:
                failures += 1
                report.errors.append(f"{paper.canonical_key}: 评分或翻译失败：{exc}")
                continue
            if cached:
                report.cached_decisions += 1
            else:
                report.llm_calls += 1
            published = PublishedPaper(paper=paper, filter_result=result, decision=decision)
            filename = _filename(paper.canonical_key)
            if decision.relevant and decision.total_score >= settings.pipeline.selection_threshold:
                write_json(root / "data" / "papers" / filename, published)
                report.selected += 1
            elif decision.total_score >= settings.pipeline.review_min_score:
                write_json(root / "data" / "review_queue" / filename, published)
                report.review_queue += 1
            else:
                write_json(root / "data" / "rejected" / filename, published)
                report.rejected += 1

        for paper, result in candidates[runtime.max_llm_papers :]:
            report.review_queue += 1
            write_json(
                root / "data" / "review_queue" / _filename(paper.canonical_key),
                {
                    "paper": paper.model_dump(mode="json"),
                    "filter_result": result.model_dump(mode="json"),
                    "queue_reason": "超过本次 MAX_LLM_PAPERS_PER_RUN，留待下次处理",
                },
            )
        if candidates and failures == min(len(candidates), runtime.max_llm_papers):
            raise RuntimeError("本次所有模型评分均失败；为保护上一版站点，本次不构建或部署")

        staging = root / "work" / "dist-staging"
        build_site(root, load_published_papers(root), settings, topics, output=staging)
        validation_errors = validate_dist(staging)
        if validation_errors:
            raise RuntimeError("静态输出验证失败：" + "; ".join(validation_errors))
        _publish_staging(root, staging)
        completed = datetime.now(UTC)
        state.last_successful_run = completed
        state.latest_site_build = completed
        write_json(root / "data" / "state.json", state)
        report.completed_at = completed
        report.status = "degraded" if report.errors else "success"
        write_json(root / "data" / "reports" / f"{started:%Y%m%dT%H%M%SZ}.json", report)
        return report
    except Exception as exc:
        report.completed_at = datetime.now(UTC)
        report.status = "failed"
        report.errors.append(str(exc))
        write_json(root / "data" / "reports" / f"{started:%Y%m%dT%H%M%SZ}.json", report)
        raise
