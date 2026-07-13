import pytest

from theory_daily.models import CurationDecision, ScoreBreakdown
from theory_daily.translation import validate_translation


def _decision(**updates):
    scores = ScoreBreakdown(
        theory_depth=20,
        methodological_rigor=15,
        novelty=10,
        clarity=8,
        metadata_quality=8,
        community_signal=0,
        other=5,
    )
    data = {
        "relevant": True,
        "primary_topic": "black_hole_thermodynamics",
        "scores": scores,
        "total_score": scores.total,
        "selection_reason_zh": "主题与方法明确，值得进一步阅读。",
        "title_zh": "黑洞热力学",
        "abstract_zh": (
            "本研究在明确的半经典近似下讨论黑洞热力学。作者列出假设并推导第一定律关系，"
            "同时比较欧几里得方法的独立计算。摘要区分了得到支持的结果与仍然属于猜想的"
            "推广，并说明近似的适用范围和相关限制。文中没有把推测改写成确定结论。"
            "研究还逐项给出了边界条件、计算步骤和对照情形，并说明各项结果分别依赖哪些前提。"
            "对于不能由当前近似确定的部分，摘要保留了原有的不确定语气，没有把可能性改写成事实。"
            "最后，作者讨论了该方法在不同参数区域中的适用性，列出主要限制，并指出需要进一步检验的问题。"
            "这段译文完整保留研究问题、假设、方法、结果、限定条件以及局限，不将原摘要压缩成简短概述。"
        ),
        "model": "fake",
        "prompt_version": "1",
        "schema_version_used": "1",
    }
    data.update(updates)
    return CurationDecision.model_validate(data)


def test_empty_or_short_translation_is_rejected(paper_factory) -> None:
    with pytest.raises(ValueError, match="压缩或省略"):
        validate_translation(paper_factory(), _decision(abstract_zh="太短"))


def test_valid_translation_passes(paper_factory) -> None:
    validate_translation(paper_factory(), _decision())
