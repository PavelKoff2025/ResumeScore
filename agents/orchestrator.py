"""Главный агент-оркестратор ResumeScore."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Literal

from fpdf import FPDF

from agents.backend_agent import BackendAgent
from core.config import is_demo_mode, resolve_provider
from storage.session_manager import SessionManager
from utils.logger import setup_logger
from utils.validators import InputValidator

ExportFormat = Literal["json", "pdf"]
UiCallback = Callable[[], None]


class Orchestrator:
    """Координирует workflow между Frontend и Backend агентами."""

    def __init__(self, session_manager: SessionManager | None = None) -> None:
        self.backend = BackendAgent()
        self.session_manager = session_manager or SessionManager()
        self.input_validator = InputValidator()
        self.logger = setup_logger("orchestrator")
        self._queue: list[dict[str, str]] = []

    def start_analysis(
        self,
        vacancy: str,
        resume: str,
        ui_callback: UiCallback | None = None,
        *,
        vacancy_title: str = "Вакансия",
        save_history: bool = True,
    ) -> dict[str, Any]:
        """
        Главный метод. Координирует весь процесс анализа.

        Args:
            vacancy: Текст вакансии.
            resume: Текст резюме.
            ui_callback: Колбэк для live-обновления UI.
            vacancy_title: Название вакансии для истории.
            save_history: Сохранять ли результат в историю.

        Returns:
            Результат анализа или словарь с ключом error.
        """
        self._ui_callback = ui_callback
        self.logger.info("Начало анализа")
        self.session_manager.reset_cancel()
        self.session_manager.set_status(
            {
                "is_running": True,
                "is_cancelled": False,
                "current_step": "validation",
                "error": None,
                "agents": [],
                "steps": [],
                "progress_percent": 5,
                "match_percentage": None,
            }
        )
        self._notify_ui()
        self._update_status("frontend", "данные получены", "done", 15)
        self._update_status("orchestrator", "запускаю анализ...", "running", 25)

        validation = self.input_validator.validate(vacancy, resume)
        if not validation.is_valid:
            self.logger.warning("Валидация не пройдена: %s", validation.error)
            self._update_status("orchestrator", validation.error or "ошибка валидации", "error")
            self.session_manager.set_status({"is_running": False, "error": validation.error})
            return {"error": validation.error}

        self._queue.append({"vacancy": vacancy[:80], "resume": resume[:80]})

        try:
            selected_provider = self.session_manager.get_selected_provider()
            result = self.backend.analyze(
                vacancy,
                resume,
                cancel_checker=self.session_manager.is_cancel_requested,
                status_callback=self._update_status,
                provider=selected_provider,
            )
        except RuntimeError as exc:
            message = str(exc)
            if "отменён" in message.lower():
                self.logger.info("Анализ отменён пользователем")
                self._update_status("orchestrator", "анализ отменён", "cancelled")
                self.session_manager.set_status({"is_running": False})
                return {"error": message, "cancelled": True}
            self.logger.error("Ошибка анализа: %s", exc)
            self._update_status("orchestrator", message, "error")
            self.session_manager.set_status({"is_running": False, "error": message})
            return {"error": message}
        except Exception as exc:
            self.logger.error("Ошибка анализа: %s", exc)
            self._update_status("orchestrator", str(exc), "error")
            self.session_manager.set_status({"is_running": False, "error": str(exc)})
            return {"error": str(exc)}

        if save_history:
            item = self.session_manager.save(
                result,
                vacancy_preview=vacancy,
                resume_preview=resume,
                vacancy_title=vacancy_title,
            )
            result.setdefault("meta", {})
            result["meta"]["history_id"] = item.id

        match_pct = result["summary"]["match_percentage"]
        self._update_status("orchestrator", "анализ завершён!", "done", match_pct)
        self.session_manager.set_status(
            {
                "is_running": False,
                "last_result": result,
                "match_percentage": match_pct,
                "progress_percent": match_pct,
            }
        )
        self._notify_ui()
        self.logger.info(
            "Анализ завершён. Совпадение: %s%%",
            result["summary"]["match_percentage"],
        )
        return result

    def compare_vacancies(
        self,
        resume: str,
        vacancies: list[dict[str, str]],
    ) -> dict[str, Any]:
        """
        Сравнивает одно резюме с несколькими вакансиями.

        Args:
            resume: Текст резюме.
            vacancies: Список {title, text}.

        Returns:
            Словарь comparisons (отсортирован по match %) и best.
        """
        self.logger.info("Сравнение %s вакансий", len(vacancies))
        comparisons: list[dict[str, Any]] = []
        provider = self.session_manager.get_selected_provider()

        for idx, vacancy in enumerate(vacancies):
            text = vacancy.get("text", "").strip()
            title = (vacancy.get("title") or f"Вакансия {idx + 1}").strip()
            if not text:
                continue
            validation = self.input_validator.validate(text, resume)
            if not validation.is_valid:
                comparisons.append(
                    {"title": title, "match_percentage": 0, "error": validation.error}
                )
                continue
            try:
                result = self.backend.analyze(text, resume, provider=provider)
                comparisons.append(
                    {
                        "title": title,
                        "match_percentage": result["summary"]["match_percentage"],
                        "summary": result["summary"],
                        "result": result,
                    }
                )
            except Exception as exc:
                self.logger.error("Ошибка сравнения для %s: %s", title, exc)
                comparisons.append(
                    {"title": title, "match_percentage": 0, "error": str(exc)}
                )

        comparisons.sort(key=lambda row: row.get("match_percentage", 0), reverse=True)

        if comparisons and comparisons[0].get("result"):
            best = comparisons[0]
            self.session_manager.save(
                best["result"],
                vacancy_preview=best["title"],
                resume_preview=resume,
                vacancy_title=str(best["title"]),
            )

        return {
            "comparisons": comparisons,
            "best": comparisons[0] if comparisons else None,
        }

    def create_share_link(
        self,
        result: dict[str, Any],
        vacancy_preview: str = "",
        resume_preview: str = "",
    ) -> str:
        """
        Создаёт публичную ссылку на результат анализа.

        Returns:
            URL для отправки ментору или другу.
        """
        from core.config import APP_BASE_URL
        from storage.share_storage import create_share

        share_id = create_share(result, vacancy_preview, resume_preview)
        return f"{APP_BASE_URL.rstrip('/')}?share={share_id}"

    def improve_resume(
        self,
        vacancy: str,
        resume: str,
        analysis_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Улучшает резюме на основе анализа.

        Returns:
            Словарь с improved_resume или error.
        """
        try:
            provider = self.session_manager.get_selected_provider()
            improved = self.backend.improve_resume(
                vacancy, resume, analysis_result, provider=provider
            )
            self.logger.info("Резюме улучшено, длина %s символов", len(improved))
            return {"improved_resume": improved}
        except Exception as exc:
            self.logger.error("Ошибка улучшения резюме: %s", exc)
            return {"error": str(exc)}

    def generate_cover_letter(
        self,
        vacancy: str,
        resume: str,
        analysis_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Генерирует текст для сопроводительного письма.

        Returns:
            Словарь с cover_letter или error.
        """
        try:
            provider = self.session_manager.get_selected_provider()
            letter = self.backend.generate_cover_letter(
                vacancy, resume, analysis_result, provider=provider
            )
            return {"cover_letter": letter}
        except Exception as exc:
            self.logger.error("Ошибка генерации письма: %s", exc)
            return {"error": str(exc)}

    def get_status(self) -> dict[str, Any]:
        """Возвращает статус текущего анализа."""
        return self.session_manager.get_status()

    def get_history(self) -> list[dict[str, Any]]:
        """Возвращает последние 5 анализов."""
        return self.session_manager.get_history()

    def cancel_analysis(self) -> None:
        """Запрашивает отмену текущего анализа."""
        self.logger.info("Запрошена отмена анализа")
        self.session_manager.request_cancel()

    def export_report(
        self,
        data: dict[str, Any],
        export_format: ExportFormat = "json",
    ) -> tuple[bytes, str, str]:
        """
        Экспортирует результат анализа в JSON или PDF.

        Args:
            data: Результат анализа.
            export_format: Формат экспорта (json или pdf).

        Returns:
            Кортеж (bytes, mime_type, filename).
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if export_format == "json":
            content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            return content, "application/json", f"resumescore_report_{timestamp}.json"

        pdf_bytes = self._build_pdf_report(data)
        return pdf_bytes, "application/pdf", f"resumescore_report_{timestamp}.pdf"

    def load_demo_texts(self) -> tuple[str, str]:
        """
        Загружает демо-тексты из файлов пользователя или встроенных данных.

        Returns:
            Кортеж (vacancy_text, resume_text).
        """
        from core.demo_data import DEMO_RESUME_TEXT, DEMO_VACANCY_TEXT
        from core.config import DEMO_RESUME_PATH, DEMO_VACANCY_PATH

        vacancy = DEMO_VACANCY_TEXT
        resume = DEMO_RESUME_TEXT

        try:
            if DEMO_VACANCY_PATH.exists():
                vacancy = self.backend.parse_document(
                    DEMO_VACANCY_PATH.read_bytes(),
                    "docx",
                )
        except Exception as exc:
            self.logger.warning("Не удалось загрузить демо-вакансию: %s", exc)

        try:
            if DEMO_RESUME_PATH.exists():
                resume = self.backend.parse_document(
                    DEMO_RESUME_PATH.read_bytes(),
                    "pdf",
                )
        except Exception as exc:
            self.logger.warning("Не удалось загрузить демо-резюме: %s", exc)

        return vacancy, resume

    def is_demo_mode(self) -> bool:
        """Проверяет, активен ли демо-режим для выбранного провайдера."""
        return is_demo_mode(self.session_manager.get_selected_provider())

    def get_resolved_provider(self) -> str:
        """Возвращает провайдера, который будет использован при анализе."""
        return resolve_provider(self.session_manager.get_selected_provider())

    def _update_status(
        self,
        agent: str,
        message: str,
        state: str,
        progress: int | None = None,
    ) -> None:
        """Обновляет статус агента в session_state и UI."""
        self.session_manager.update_agent_status(agent, message, state, progress)
        self._notify_ui()

    def _notify_ui(self) -> None:
        """Вызывает колбэк live-обновления интерфейса."""
        if getattr(self, "_ui_callback", None):
            self._ui_callback()

    def _build_pdf_report(self, data: dict[str, Any]) -> bytes:
        """Формирует PDF-отчёт по результатам анализа."""
        from core.config import BASE_DIR

        font_candidates = [
            BASE_DIR / "fonts" / "DejaVuSans.ttf",
            BASE_DIR / "fonts" / "ArialUnicode.ttf",
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            Path("/Library/Fonts/Arial Unicode.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
        font_path = next((path for path in font_candidates if path.exists()), None)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        if font_path:
            pdf.add_font("UnicodeFont", "", str(font_path))
            pdf.set_font("UnicodeFont", size=14)
            title = "ResumeScore — Отчёт"
            body_font = "UnicodeFont"
        else:
            pdf.set_font("Helvetica", size=14)
            title = "ResumeScore - Report"
            body_font = "Helvetica"

        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")

        summary = data.get("summary", {})
        pdf.set_font(body_font, size=11)
        pdf.cell(
            0,
            8,
            (
                f"Совпадение: {summary.get('match_percentage', 0)}% | "
                f"Green: {summary.get('green_count', 0)} | "
                f"Yellow: {summary.get('yellow_count', 0)} | "
                f"Red: {summary.get('red_count', 0)}"
            ),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(4)

        pdf.set_font(body_font, size=12)
        pdf.cell(0, 8, "Топ-3 рекомендации:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(body_font, size=10)
        for idx, action in enumerate(data.get("top_3_actions", []), start=1):
            pdf.multi_cell(pdf.epw, 6, f"{idx}. {action}")

        pdf.ln(4)
        pdf.set_font(body_font, size=12)
        pdf.cell(0, 8, "Детали сопоставления:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(body_font, size=9)

        for item in data.get("matching", []):
            pdf.multi_cell(
                pdf.epw,
                5,
                (
                    f"[{item.get('status', '').upper()}] "
                    f"{item.get('requirement', '')}\n"
                    f"Доказательство: {item.get('evidence', '')}\n"
                    f"Рекомендация: {item.get('recommendation', '')}\n"
                ),
            )
            pdf.ln(2)

        buffer = BytesIO()
        pdf.output(buffer)
        return buffer.getvalue()
