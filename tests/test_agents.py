"""Unit-тесты для агентов ResumeScore."""

from __future__ import annotations

import pytest

from agents.backend_agent import BackendAgent
from agents.orchestrator import Orchestrator
from core.config import get_active_provider, is_demo_mode, resolve_provider
from core.demo_data import DEMO_ANALYSIS_RESULT
from utils.validators import InputValidator, ResponseValidator


class TestProviderConfig:
    """Тесты выбора LLM-провайдера."""

    def test_auto_fallback_to_deepseek(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("core.config.OPENAI_API_KEY", "")
        monkeypatch.setattr("core.config.DEEPSEEK_API_KEY", "sk-test")
        monkeypatch.setattr("core.config.LLM_PROVIDER", "openai")
        assert get_active_provider() == "deepseek"
        assert is_demo_mode() is False

    def test_explicit_deepseek(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("core.config.DEEPSEEK_API_KEY", "sk-test")
        monkeypatch.setattr("core.config.LLM_PROVIDER", "deepseek")
        assert resolve_provider("deepseek") == "deepseek"

    def test_resolve_explicit_demo(self) -> None:
        assert resolve_provider("demo") == "demo"

    def test_demo_when_no_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("core.config.OPENAI_API_KEY", "")
        monkeypatch.setattr("core.config.DEEPSEEK_API_KEY", "")
        assert is_demo_mode() is True


class TestInputValidator:
    """Тесты валидации входных данных."""

    def test_valid_input(self) -> None:
        validator = InputValidator()
        result = validator.validate("A" * 60, "B" * 60)
        assert result.is_valid is True

    def test_empty_input(self) -> None:
        validator = InputValidator()
        result = validator.validate("", "text")
        assert result.is_valid is False
        assert "оба текста" in (result.error or "").lower()


class TestResponseValidator:
    """Тесты валидации ответа LLM."""

    def test_valid_response(self) -> None:
        validator = ResponseValidator()
        validated = validator.validate(DEMO_ANALYSIS_RESULT)
        assert validated["summary"]["match_percentage"] == 82

    def test_invalid_response(self) -> None:
        validator = ResponseValidator()
        with pytest.raises(ValueError):
            validator.validate({"matching": []})


class TestBackendAgent:
    """Тесты Backend-агента."""

    def test_demo_analyze(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("core.config.OPENAI_API_KEY", "")
        monkeypatch.setattr("core.config.DEEPSEEK_API_KEY", "")
        agent = BackendAgent()
        result = agent.analyze("A" * 60, "B" * 60, provider="demo")
        assert "summary" in result
        assert result["meta"]["demo_mode"] is True

    def test_explicit_openai_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("core.config.OPENAI_API_KEY", "")
        agent = BackendAgent()
        with pytest.raises(RuntimeError, match="OpenAI"):
            agent.analyze("A" * 60, "B" * 60, provider="openai")

    def test_calculate_cost(self) -> None:
        agent = BackendAgent()
        cost = agent.calculate_cost({"prompt_tokens": 1000, "completion_tokens": 500})
        assert cost >= 0


class TestOrchestrator:
    """Тесты Orchestrator."""

    def test_start_analysis_demo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("core.config.OPENAI_API_KEY", "")
        monkeypatch.setattr("core.config.DEEPSEEK_API_KEY", "")
        orchestrator = Orchestrator()
        orchestrator.session_manager.set_selected_provider("demo")
        result = orchestrator.start_analysis("A" * 60, "B" * 60)
        assert "summary" in result

    def test_export_json(self) -> None:
        orchestrator = Orchestrator()
        content, mime, name = orchestrator.export_report(DEMO_ANALYSIS_RESULT, "json")
        assert mime == "application/json"
        assert name.endswith(".json")
        assert len(content) > 0

    def test_export_pdf(self) -> None:
        orchestrator = Orchestrator()
        content, mime, name = orchestrator.export_report(DEMO_ANALYSIS_RESULT, "pdf")
        assert mime == "application/pdf"
        assert name.endswith(".pdf")
        assert content[:4] == b"%PDF"

    def test_validation_error(self) -> None:
        orchestrator = Orchestrator()
        result = orchestrator.start_analysis("", "")
        assert "error" in result
