"""Чек-лист рекомендаций: сделано / не сделано."""

from __future__ import annotations

from typing import Any

try:
    import streamlit as st

    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False

CHECKLIST_KEY = "recommendation_checklist"


class ChecklistManager:
    """Хранит отметки выполненных рекомендаций в session_state."""

    def __init__(self) -> None:
        self._memory: dict[str, dict[str, bool]] = {}

    def _get_store(self) -> dict[str, dict[str, bool]]:
        if _HAS_STREAMLIT:
            try:
                from streamlit.runtime.scriptrunner import get_script_run_ctx

                if get_script_run_ctx() is not None:
                    if CHECKLIST_KEY not in st.session_state:
                        st.session_state[CHECKLIST_KEY] = {}
                    return st.session_state[CHECKLIST_KEY]
            except Exception:
                pass
        if CHECKLIST_KEY not in self._memory:
            self._memory[CHECKLIST_KEY] = {}
        return self._memory[CHECKLIST_KEY]

    def build_items(self, analysis_id: str, data: dict[str, Any]) -> list[dict[str, str]]:
        """
        Формирует список рекомендаций для чек-листа.

        Args:
            analysis_id: ID анализа (history_id).
            data: Результат анализа.

        Returns:
            Список элементов {id, text, source}.
        """
        items: list[dict[str, str]] = []
        seen: set[str] = set()

        for idx, action in enumerate(data.get("top_3_actions", []), start=1):
            text = action.strip()
            if text and text not in seen:
                items.append({"id": f"{analysis_id}_top_{idx}", "text": text, "source": "Топ-3"})
                seen.add(text)

        for idx, match in enumerate(data.get("matching", []), start=1):
            if match.get("status") in ("yellow", "red"):
                text = str(match.get("recommendation", "")).strip()
                if text and text not in seen:
                    items.append(
                        {
                            "id": f"{analysis_id}_match_{idx}",
                            "text": text,
                            "source": "Требование",
                        }
                    )
                    seen.add(text)

        return items

    def is_done(self, item_id: str) -> bool:
        """Проверяет, отмечен ли пункт как выполненный."""
        return bool(self._get_store().get(item_id, False))

    def set_done(self, item_id: str, done: bool) -> None:
        """Устанавливает статус пункта чек-листа."""
        self._get_store()[item_id] = done

    def get_progress(self, items: list[dict[str, str]]) -> tuple[int, int]:
        """Возвращает (выполнено, всего)."""
        if not items:
            return 0, 0
        done = sum(1 for item in items if self.is_done(item["id"]))
        return done, len(items)
