from __future__ import annotations

from pathlib import Path

from theory_daily.config import configuration_fingerprint, runtime_config
from theory_daily.llm_curation import FakeCurationClient, curate_with_cache
from theory_daily.models import FilterResult


def test_second_run_uses_cache(tmp_path: Path, paper_factory, settings, topics) -> None:
    decision = {
        "relevant": True,
        "primary_topic": "black_hole_thermodynamics",
        "theory_depth_score": 24,
        "methodological_rigor_signal": 16,
        "novelty_signal": 10,
        "clarity_score": 9,
        "metadata_quality_score": 9,
        "community_signal_score": 0,
        "other_score": 8,
        "total_score": 76,
        "selection_reason_zh": "主题、方法与适用范围明确，值得进一步阅读。",
        "title_zh": "黑洞热力学与广义熵",
        "abstract_zh": (
            "本研究在受控的半经典区域讨论黑洞热力学和广义熵。作者明确列出假设，"
            "推导第一定律关系，并与独立的欧几里得计算比较。分析说明近似有效的范围，"
            "并将得到支持的结果与仍属猜想的推广清楚区分。"
            "研究进一步逐项说明了边界条件、计算步骤和对照情形，并标明每个结果所依赖的前提。"
            "对当前近似无法确定的部分，译文保留原摘要中的不确定语气，没有把推测改写成确定事实。"
            "摘要最后讨论该方法在不同参数区域的适用范围，列出主要限制，并指出仍需进一步检验的问题。"
            "因此这份中文译文完整保留研究问题、假设、方法、结果、限定条件和局限，而不是简短概述。"
        ),
        "keywords_en": ["black hole thermodynamics"],
        "keywords_zh": ["黑洞热力学"],
    }
    client = FakeCurationClient([decision])
    runtime = runtime_config(settings)
    fingerprint = configuration_fingerprint(settings, topics)
    paper = paper_factory()
    result = FilterResult(passed=True, candidate_topics=["black_hole_thermodynamics"])
    _, cached_first = curate_with_cache(
        tmp_path, paper, result, client, runtime, settings, fingerprint
    )
    _, cached_second = curate_with_cache(
        tmp_path, paper, result, client, runtime, settings, fingerprint
    )
    assert cached_first is False
    assert cached_second is True
    assert client.calls == 1
