from __future__ import annotations

from theory_daily.cli import main


def test_formal_update_without_api_key_fails_clearly(monkeypatch, capsys) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = main(["update", "--since-days", "3"])
    assert result == 1
    assert "OPENAI_API_KEY" in capsys.readouterr().err


def test_deepseek_update_without_api_key_fails_clearly(monkeypatch, capsys) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    result = main(["update", "--since-days", "3"])
    assert result == 1
    assert "DEEPSEEK_API_KEY" in capsys.readouterr().err
