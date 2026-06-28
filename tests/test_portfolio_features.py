"""Тесты портфельных функций: шаринг, сравнение, чек-лист, HH-парсер."""

from __future__ import annotations

import json

import pytest

from agents.orchestrator import Orchestrator
from core.demo_data import DEMO_ANALYSIS_RESULT
from storage.checklist_manager import ChecklistManager
from storage.share_storage import create_share, load_share
from utils.hh_parser import parse_hh_clipboard


class TestShareStorage:
    """Тесты сохранения и загрузки share-ссылок."""

    def test_create_and_load_share(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("storage.share_storage.SHARES_DIR", tmp_path)
        share_id = create_share(DEMO_ANALYSIS_RESULT, "Вакансия", "Резюме")
        assert len(share_id) == 12
        payload = load_share(share_id)
        assert payload is not None
        assert payload["result"]["summary"]["match_percentage"] == 82

    def test_load_invalid_share(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("storage.share_storage.SHARES_DIR", tmp_path)
        assert load_share("") is None
        assert load_share("../bad") is None


class TestChecklistManager:
    """Тесты чек-листа рекомендаций."""

    def test_build_and_progress(self) -> None:
        manager = ChecklistManager()
        items = manager.build_items("test-id", DEMO_ANALYSIS_RESULT)
        assert len(items) > 0
        done, total = manager.get_progress(items)
        assert done == 0
        assert total == len(items)
        manager.set_done(items[0]["id"], True)
        done, _ = manager.get_progress(items)
        assert done == 1


class TestHhParser:
    """Тесты парсера HH.ru."""

    def test_parse_title_and_footer(self) -> None:
        text = (
            "Python Developer\n"
            "Компания: Test\n"
            "Описание вакансии\n"
            "Нужен Python\n"
            "Напишите телефон, чтобы работодатель мог связаться"
        )
        title, cleaned = parse_hh_clipboard(text)
        assert title == "Python Developer"
        assert "Напишите телефон" not in cleaned


class TestCompareVacancies:
    """Тесты сравнения вакансий."""

    def test_compare_demo_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("core.config.OPENAI_API_KEY", "")
        monkeypatch.setattr("core.config.DEEPSEEK_API_KEY", "")
        orchestrator = Orchestrator()
        orchestrator.session_manager.set_selected_provider("demo")
        resume = "B" * 60
        vacancies = [
            {"title": "Вакансия A", "text": "A" * 60},
            {"title": "Вакансия B", "text": "C" * 60},
        ]
        result = orchestrator.compare_vacancies(resume, vacancies)
        assert len(result["comparisons"]) == 2
        assert result["best"] is not None
        assert (
            result["comparisons"][0]["match_percentage"]
            >= result["comparisons"][1]["match_percentage"]
        )

    def test_create_share_link(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("storage.share_storage.SHARES_DIR", tmp_path)
        monkeypatch.setattr("core.config.APP_BASE_URL", "http://localhost:8501")
        orchestrator = Orchestrator()
        url = orchestrator.create_share_link(DEMO_ANALYSIS_RESULT, "vac", "res")
        assert url.startswith("http://localhost:8501?share=")
        share_id = url.split("share=")[-1]
        path = tmp_path / f"{share_id}.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["vacancy_preview"] == "vac"
