"""Auditable, deterministic first-stage screening."""

from __future__ import annotations

import re

from theory_daily.config import Settings, TopicsConfig
from theory_daily.models import FilterResult, NormalizedPaper, TopicId

_SPACE = re.compile(r"\s+")
_HYPHENS = str.maketrans({"-": " ", "‐": " ", "‑": " ", "–": " ", "—": " "})


def _normalize(value: str) -> str:
    return _SPACE.sub(" ", value.casefold().translate(_HYPHENS)).strip()


def _haystack(paper: NormalizedPaper) -> str:
    return _normalize(f"{paper.title_en} {paper.abstract_en}")


def filter_paper(paper: NormalizedPaper, topics: TopicsConfig, settings: Settings) -> FilterResult:
    text = _haystack(paper)
    reasons: list[str] = []
    missing_required = (
        not paper.title_en
        or not paper.authors
        or not paper.submitted_at
        or (not paper.abs_url and not paper.inspire_url)
    )
    if missing_required:
        reasons.append("缺少标题、作者、日期或规范链接")
    if len(paper.abstract_en) < settings.pipeline.min_abstract_chars:
        reasons.append(f"英文摘要少于 {settings.pipeline.min_abstract_chars} 个字符")
    exclusions = [term for term in topics.hard_exclusions if _normalize(term) in text]
    title_lower = paper.title_en.lower().strip()
    if title_lower.startswith(("erratum", "corrigendum")):
        exclusions.append("pure erratum/corrigendum")
    if exclusions:
        reasons.append(f"命中排除项：{', '.join(exclusions)}")
    if paper.categories and not set(paper.categories).intersection(topics.allowed_categories):
        reasons.append("arXiv 分类不在配置范围")

    candidate_topics: list[TopicId] = []
    high_hits: list[str] = []
    medium_hits: list[str] = []
    for topic_id, rule in topics.topics.items():
        topic_high = [term for term in rule.high_weight if _normalize(term) in text]
        topic_medium = [term for term in rule.medium_weight if _normalize(term) in text]
        if topic_high or len(topic_medium) >= 2:
            candidate_topics.append(topic_id)
            high_hits.extend(topic_high)
            medium_hits.extend(topic_medium)

    # Bare "PTA" is ambiguous. Keep it only when the abstract supplies timing/GW context.
    pta_context = (
        "pulsar",
        "nanohertz",
        "hellings downs",
        "timing residual",
        "overlap reduction",
        "common spectrum",
        "spatial correlation",
        "quadrupolar correlation",
        "supermassive black hole binary",
    )
    bare_pta = re.search(r"\bpta\b", text) is not None
    if bare_pta and not any(word in text for word in pta_context):
        if "pta" in candidate_topics:
            candidate_topics.remove("pta")
        if not candidate_topics:
            reasons.append("PTA 缩写缺少脉冲星计时语境")

    negative_hits = [term for term in topics.negative_terms if _normalize(term) in text]
    if not candidate_topics:
        reasons.append("未达到主题关键词门槛")
    score = min(100, len(high_hits) * 25 + len(medium_hits) * 10 - len(negative_hits) * 20)
    passed = not reasons and bool(candidate_topics)
    if negative_hits and score < 20:
        passed = False
        reasons.append("负面语境显著降低相关性")
    return FilterResult(
        passed=passed,
        candidate_topics=candidate_topics,
        high_weight_hits=sorted(set(high_hits)),
        medium_weight_hits=sorted(set(medium_hits)),
        negative_hits=sorted(set(negative_hits)),
        reasons=reasons,
        deterministic_score=score,
    )
