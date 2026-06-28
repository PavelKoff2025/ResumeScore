"""Хранение истории анализов в session_state Streamlit."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.config import MAX_HISTORY_ITEMS
from core.schemas import AnalysisHistoryItem, AnalysisResult

try:
    import streamlit as st

    _HAS_STREAMLIT = True
except ImportError:  # pragma: no cover
    _HAS_STREAMLIT = False


class SessionManager:
    """Управляет историей анализов и состоянием сессии."""

    HISTORY_KEY = "analysis_history"
    STATUS_KEY = "analysis_status"
    CANCEL_KEY = "cancel_analysis"
    LLM_PROVIDER_KEY = "selected_llm_provider"

    def __init__(self) -> None:
        self._memory: dict[str, Any] = {
            self.HISTORY_KEY: [],
            self.STATUS_KEY: {
                "is_running": False,
                "is_cancelled": False,
                "current_step": "",
                "agents": [],
                "steps": [],
                "progress_percent": 0,
                "match_percentage": None,
                "last_result": None,
                "error": None,
            },
            self.CANCEL_KEY: False,
            self.LLM_PROVIDER_KEY: "auto",
        }

    def _get_state(self) -> dict[str, Any]:
        """Возвращает хранилище состояния (Streamlit или in-memory)."""
        if not _HAS_STREAMLIT:
            return self._memory

        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx

            if get_script_run_ctx() is None:
                return self._memory
            return st.session_state
        except Exception:
            return self._memory

    def _ensure_state(self) -> None:
        """Инициализирует ключи состояния при первом обращении."""
        state = self._get_state()
        if self.HISTORY_KEY not in state:
            state[self.HISTORY_KEY] = []
        if self.STATUS_KEY not in state:
            state[self.STATUS_KEY] = {
                "is_running": False,
                "is_cancelled": False,
                "current_step": "",
                "agents": [],
                "steps": [],
                "progress_percent": 0,
                "match_percentage": None,
                "error": None,
                "last_result": None,
            }
        if self.CANCEL_KEY not in state:
            state[self.CANCEL_KEY] = False
        if self.LLM_PROVIDER_KEY not in state:
            state[self.LLM_PROVIDER_KEY] = "auto"

    def save(
        self,
        result: dict[str, Any],
        vacancy_preview: str = "",
        resume_preview: str = "",
        vacancy_title: str = "Вакансия",
    ) -> AnalysisHistoryItem:
        """
        Сохраняет результат анализа в историю сессии.

        Args:
            result: Результат анализа.
            vacancy_preview: Краткий фрагмент вакансии.
            resume_preview: Краткий фрагмент резюме.

        Returns:
            Созданная запись истории.
        """
        self._ensure_state()

        validated = AnalysisResult.model_validate(result)
        item = AnalysisHistoryItem(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(timezone.utc),
            match_percentage=validated.summary.match_percentage,
            vacancy_preview=vacancy_preview[:120] or "Вакансия",
            resume_preview=resume_preview[:120] or "Резюме",
            vacancy_title=vacancy_title[:80] or "Вакансия",
            result=validated,
        )

        state = self._get_state()
        history: list[dict] = state[self.HISTORY_KEY]
        history.insert(0, item.model_dump(mode="json"))
        state[self.HISTORY_KEY] = history[:MAX_HISTORY_ITEMS]
        state[self.STATUS_KEY]["last_result"] = result
        return item

    def get_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Возвращает историю анализов.

        Args:
            limit: Максимальное количество записей.

        Returns:
            Список записей истории.
        """
        self._ensure_state()
        history = self._get_state()[self.HISTORY_KEY]
        if limit is None:
            return history
        return history[:limit]

    def get_status(self) -> dict[str, Any]:
        """Возвращает текущий статус анализа."""
        self._ensure_state()
        return dict(self._get_state()[self.STATUS_KEY])

    def set_status(self, status: dict[str, Any]) -> None:
        """Обновляет статус анализа."""
        self._ensure_state()
        self._get_state()[self.STATUS_KEY].update(status)

    def update_agent_status(
        self,
        agent: str,
        message: str,
        state: str = "running",
        progress: int | None = None,
    ) -> None:
        """
        Добавляет шаг в pipeline и обновляет прогресс.

        Args:
            agent: Имя агента.
            message: Сообщение для UI.
            state: Состояние (pending, running, done, error, cancelled).
            progress: Процент выполнения pipeline (0-100).
        """
        self.append_pipeline_step(agent, message, state, progress)

    def append_pipeline_step(
        self,
        agent: str,
        message: str,
        state: str = "running",
        progress: int | None = None,
    ) -> None:
        """
        Добавляет шаг в ленту статусов агентов.

        При новом шаге того же агента предыдущий «running» помечается как «done».
        """
        self._ensure_state()
        store = self._get_state()
        status = store[self.STATUS_KEY]
        steps: list[dict] = status.setdefault("steps", [])

        for step in steps:
            if step["agent"] == agent and step["state"] == "running":
                step["state"] = "done"

        steps.append({"agent": agent, "message": message, "state": state})
        status["agents"] = steps

        if progress is not None:
            status["progress_percent"] = max(0, min(100, progress))

    def request_cancel(self) -> None:
        """Запрашивает отмену текущего анализа."""
        self._ensure_state()
        state = self._get_state()
        state[self.CANCEL_KEY] = True
        state[self.STATUS_KEY]["is_cancelled"] = True

    def reset_cancel(self) -> None:
        """Сбрасывает флаг отмены перед новым анализом."""
        self._ensure_state()
        state = self._get_state()
        state[self.CANCEL_KEY] = False
        state[self.STATUS_KEY]["is_cancelled"] = False

    def is_cancel_requested(self) -> bool:
        """Проверяет, запрошена ли отмена анализа."""
        self._ensure_state()
        return bool(self._get_state().get(self.CANCEL_KEY, False))

    def clear_history(self) -> None:
        """Очищает историю анализов."""
        self._ensure_state()
        self._get_state()[self.HISTORY_KEY] = []

    def get_selected_provider(self) -> str:
        """Возвращает выбранный в UI LLM-провайдер."""
        self._ensure_state()
        return str(self._get_state().get(self.LLM_PROVIDER_KEY, "auto"))

    def set_selected_provider(self, provider: str) -> None:
        """Сохраняет выбранный LLM-провайдер в session_state."""
        self._ensure_state()
        self._get_state()[self.LLM_PROVIDER_KEY] = provider.strip().lower()
