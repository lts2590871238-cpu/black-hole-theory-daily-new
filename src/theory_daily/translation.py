"""Conservative validation for Chinese translations returned by the model."""

from __future__ import annotations

import math
import re

from theory_daily.models import CurationDecision, NormalizedPaper

_CJK = re.compile(r"[\u3400-\u9fff]")


def validate_translation(paper: NormalizedPaper, decision: CurationDecision) -> None:
    if not decision.title_zh or not decision.abstract_zh:
        raise ValueError("中文标题或摘要为空")
    if not _CJK.search(decision.title_zh) or not _CJK.search(decision.abstract_zh):
        raise ValueError("中文翻译未包含中文字符")
    english_length = len(re.sub(r"\s+", "", paper.abstract_en))
    chinese_length = len(re.sub(r"\s+", "", decision.abstract_zh))
    minimum = max(100, math.ceil(english_length * 0.28))
    maximum = max(500, math.ceil(english_length * 1.2))
    if chinese_length < minimum:
        raise ValueError(f"中文摘要疑似被压缩或省略：至少需要 {minimum} 个非空白字符")
    if chinese_length > maximum:
        raise ValueError(f"中文摘要异常长，可能包含扩写：最多允许 {maximum} 个非空白字符")
    if decision.relevant and not decision.selection_reason_zh:
        raise ValueError("入选论文缺少中文入选理由")
