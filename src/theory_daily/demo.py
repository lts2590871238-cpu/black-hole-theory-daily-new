"""Clearly labelled offline demo content; never written to production history."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import HttpUrl

from theory_daily.models import (
    CurationDecision,
    FilterResult,
    NormalizedPaper,
    PublishedPaper,
    ScoreBreakdown,
    SourceProvenance,
    TopicId,
)

_TOPICS: list[tuple[TopicId, str, str, list[str], list[str]]] = [
    (
        "black_hole_thermodynamics",
        "Near-extremal black-hole thermodynamics in a solvable semiclassical model",
        "可解半经典模型中的近极端黑洞热力学",
        ["near-extremal black hole", "generalized entropy"],
        ["近极端黑洞", "广义熵"],
    ),
    (
        "black_hole_thermodynamics",
        "Generalized second laws for slowly evolving quantum horizons",
        "缓慢演化量子视界的广义第二定律",
        ["generalized second law", "quantum horizon"],
        ["广义第二定律", "量子视界"],
    ),
    (
        "pta",
        "An overlap-reduction framework for polarized nanohertz backgrounds",
        "偏振纳赫兹背景的重叠约化函数框架",
        ["pulsar timing array", "overlap reduction function"],
        ["脉冲星计时阵列", "重叠约化函数"],
    ),
    (
        "pta",
        "Cosmic-string inference with pulsar timing correlations",
        "利用脉冲星计时相关性推断宇宙弦",
        ["pulsar timing", "cosmic strings"],
        ["脉冲星计时", "宇宙弦"],
    ),
    (
        "holography_condensed_matter",
        "Holographic transport across a quantum critical interface",
        "量子临界界面上的全息输运",
        ["holographic transport", "quantum criticality"],
        ["全息输运", "量子临界性"],
    ),
    (
        "holography_condensed_matter",
        "A holographic superfluid with explicitly broken translations",
        "显式平移对称破缺的全息超流",
        ["holographic superfluid", "broken translations"],
        ["全息超流", "平移对称破缺"],
    ),
    (
        "general_relativity_foundations",
        "Null infinity and gravitational memory in asymptotically flat spacetimes",
        "渐近平直时空中的零无穷远与引力记忆",
        ["null infinity", "gravitational memory"],
        ["零无穷远", "引力记忆"],
    ),
    (
        "general_relativity_foundations",
        "A stability criterion for trapped surfaces under causal perturbations",
        "因果扰动下俘获面的稳定性判据",
        ["trapped surface", "causal structure"],
        ["俘获面", "因果结构"],
    ),
]


def demo_papers(now: datetime | None = None) -> list[PublishedPaper]:
    now = now or datetime.now(UTC)
    papers: list[PublishedPaper] = []
    for index, (topic, title_en, title_zh, keywords_en, keywords_zh) in enumerate(_TOPICS, 1):
        submitted = now - timedelta(hours=index * 7)
        abstract_en = (
            "This explicitly fictional demonstration record studies a controlled theoretical "
            f"problem related to {keywords_en[0]}. We formulate the assumptions, derive the "
            "relevant equations, compare two limiting regimes, and identify which conclusion is "
            "supported by the stated approximation. The text is deliberately long enough to test "
            "layout, filtering, metadata validation, and bilingual rendering. It is not a real "
            "paper, must not be cited, and exists only for the offline demo build. "
            "No claim here represents a scientific result."
        )
        abstract_zh = (
            f"这是一条明确标记为虚构示例的记录，用于展示与“{keywords_zh[0]}”有关的理论论文版式。"
            "示例先列出假设，再推导相关方程，比较两个极限情形，并说明在给定近似下摘要能够支持何种结论。"
            "这段文字只用于测试筛选、元数据校验、双语显示和移动端布局，不是真实论文，不能引用，也不代表任何科学结果。"
        )
        paper = NormalizedPaper(
            canonical_key=f"demo:paper-{index:02d}",
            arxiv_id=f"DEMO-{index:02d}",
            arxiv_version=1,
            title_en=f"[DEMO] {title_en}",
            abstract_en=abstract_en,
            authors=["Demo Author A", "Demo Author B", "Demo Author C"],
            categories=["gr-qc" if topic != "holography_condensed_matter" else "hep-th"],
            submitted_at=submitted,
            updated_at=submitted,
            abs_url=HttpUrl(f"https://example.invalid/papers/demo-{index:02d}"),
            pdf_url=HttpUrl(f"https://example.invalid/papers/demo-{index:02d}.pdf"),
            is_demo=True,
            source_provenance=[
                SourceProvenance(
                    source="demo",
                    record_id=f"demo-{index:02d}",
                    fetched_at=now,
                    url=HttpUrl(f"https://example.invalid/papers/demo-{index:02d}"),
                )
            ],
        )
        scores = ScoreBreakdown(
            theory_depth=24,
            methodological_rigor=16,
            novelty=10,
            clarity=9,
            metadata_quality=9,
            community_signal=0,
            other=8,
        )
        decision = CurationDecision(
            relevant=True,
            primary_topic=topic,
            scores=scores,
            total_score=scores.total,
            selection_reason_zh="演示记录：主题匹配明确，摘要包含研究问题、方法与适用范围。",
            title_zh=f"【演示】{title_zh}",
            abstract_zh=abstract_zh,
            keywords_en=keywords_en,
            keywords_zh=keywords_zh,
            model="offline-demo-client",
            prompt_version="demo-1.0",
            schema_version_used="demo-1.0",
        )
        result = FilterResult(
            passed=True,
            candidate_topics=[topic],
            high_weight_hits=[keywords_en[0]],
            deterministic_score=80,
        )
        papers.append(PublishedPaper(paper=paper, filter_result=result, decision=decision))
    return papers
