from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from theory_daily.config import runtime_config
from theory_daily.llm_curation import DeepSeekCurationClient


def _valid_decision() -> dict[str, Any]:
    return {
        "relevant": True,
        "primary_topic": "black_hole_thermodynamics",
        "secondary_topics": [],
        "theory_depth_score": 24,
        "methodological_rigor_signal": 16,
        "novelty_signal": 10,
        "clarity_score": 9,
        "metadata_quality_score": 9,
        "community_signal_score": 0,
        "other_score": 8,
        "total_score": 76,
        "reject_reason_zh": "",
        "selection_reason_zh": "主题、方法与适用范围明确，值得进一步阅读。",
        "title_zh": "黑洞热力学与广义熵",
        "abstract_zh": (
            "本研究在受控的半经典区域讨论黑洞热力学和广义熵。作者明确列出假设，"
            "推导第一定律关系，并与独立的欧几里得计算比较。分析说明近似有效的范围，"
            "并将得到支持的结果与仍属猜想的推广清楚区分。"
        ),
        "keywords_en": ["black hole thermodynamics"],
        "keywords_zh": ["黑洞热力学"],
        "translation_warning": "",
    }


class FakeCompletions:
    def __init__(self) -> None:
        self.request: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.request = kwargs
        message = SimpleNamespace(content=json.dumps(_valid_decision(), ensure_ascii=False))
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=message)])


class FakeSDK:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def test_deepseek_json_output_is_validated() -> None:
    sdk = FakeSDK()
    client = DeepSeekCurationClient(
        model="deepseek-v4-flash",
        api_key="test-key",
        base_url="https://api.deepseek.com",
        client=sdk,
    )
    decision = client.evaluate({"untrusted_paper_data": {"title": "test"}})
    assert decision.total_score == 76
    assert sdk.completions.request["response_format"] == {"type": "json_object"}
    assert sdk.completions.request["extra_body"] == {"thinking": {"type": "disabled"}}
    system_prompt = sdk.completions.request["messages"][0]["content"]
    assert "JSON Schema" in system_prompt
    assert "UNTRUSTED DATA" in system_prompt


def test_deepseek_runtime_configuration(monkeypatch, settings) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    runtime = runtime_config(settings)
    assert runtime.provider == "deepseek"
    assert runtime.model == "deepseek-v4-flash"
    assert runtime.api_key_env == "DEEPSEEK_API_KEY"
    assert runtime.base_url == "https://api.deepseek.com"
