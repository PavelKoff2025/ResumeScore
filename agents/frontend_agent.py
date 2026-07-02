"""Frontend-агент: пользовательский интерфейс Streamlit."""

from __future__ import annotations

from typing import Any

import streamlit as st

from agents.orchestrator import Orchestrator
from core.config import (
    PROVIDER_CHOICES,
    PROVIDER_UI_LABELS,
    get_provider_label,
    get_providers_status,
    is_demo_mode,
    is_provider_configured,
    resolve_provider,
)
from core.demo_data import DEMO_RESUME_TEXT, DEMO_VACANCY_TEXT
from storage.checklist_manager import ChecklistManager
from storage.share_storage import load_share
from ui.components import (
    build_pipeline_html,
    build_cover_letter_fallback,
    render_action_bar,
    render_copy_to_clipboard,
    render_executive_summary,
    render_history_item_label,
    render_history_timeline,
    render_match_progress,
    render_matching_table,
    render_paste_zone,
    render_pipeline_status,
    render_recommendation_checklist,
    render_share_button,
    render_summary_badges,
    render_text_report,
    render_vacancy_comparison,
)
from ui.wow_components import render_wow_dashboard
from ui.styles import inject_styles
from utils.document_parser import DocumentParser
from utils.hh_parser import parse_hh_clipboard, resolve_vacancy_from_paste
from utils.logger import setup_logger


class FrontendAgent:
    """Агент UI: формы, визуализация результатов и история."""

    def __init__(self) -> None:
        self.orchestrator = Orchestrator()
        self.document_parser = DocumentParser()
        self.checklist_manager = ChecklistManager()
        self.logger = setup_logger("frontend")

    def render(self) -> None:
        """Главный метод рендеринга UI."""
        st.set_page_config(
            page_title="ResumeScore",
            page_icon="🎯",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        theme = self._render_sidebar()
        inject_styles(theme)
        self._render_header()
        self._try_load_shared_result()

        if st.session_state.get("shared_view"):
            st.info("🔗 Вы просматриваете результат по общей ссылке (только чтение)")

        if self.orchestrator.is_demo_mode():
            selected = self.orchestrator.session_manager.get_selected_provider()
            if selected == "demo":
                st.info("🎭 **Демо-режим**: используются тестовые данные без вызова API.")
            else:
                st.info(
                    "🎭 **Демо-режим**: для выбранного провайдера нет API-ключа. "
                    "На Streamlit Cloud добавьте ключ в **Settings → Secrets**, "
                    "локально — в `.env`."
                )
        else:
            resolved = self.orchestrator.get_resolved_provider()
            selected = self.orchestrator.session_manager.get_selected_provider()
            if selected == "auto":
                st.caption(f"Провайдер: **{get_provider_label(resolved)}** (автовыбор)")

        tab_single, tab_compare = st.tabs(["📋 Одна вакансия", "⚖️ Сравнить вакансии"])

        pipeline_placeholder = None
        with tab_single:
            vacancy, resume, vacancy_title = self.render_input_form()
            pipeline_placeholder = st.empty()
            self._render_action_buttons(
                vacancy, resume, pipeline_placeholder, vacancy_title=vacancy_title
            )

        with tab_compare:
            resume = self._render_resume_column()
            vacancies = self._render_multi_vacancy_form()
            self._render_compare_button(resume, vacancies)

        status = self.orchestrator.get_status()
        if status.get("steps") or status.get("agents") or status.get("is_running"):
            self.render_loading_state(status, pipeline_placeholder)

        if st.session_state.get("comparison_result"):
            render_vacancy_comparison(
                st.session_state["comparison_result"].get("comparisons", [])
            )

        if "last_result" in st.session_state:
            self.render_results(st.session_state["last_result"])

        self.render_history()

    def _try_load_shared_result(self) -> None:
        """Загружает результат по параметру ?share= в URL."""
        share_id = st.query_params.get("share")
        if not share_id:
            return
        if st.session_state.get("_loaded_share_id") == share_id:
            return

        payload = load_share(share_id)
        if not payload:
            st.error("Ссылка недействительна или устарела")
            return

        st.session_state["last_result"] = payload.get("result", {})
        st.session_state["_loaded_share_id"] = share_id
        st.session_state["shared_view"] = True
        if payload.get("vacancy_preview"):
            st.session_state["vacancy_text"] = payload["vacancy_preview"]
        if payload.get("resume_preview"):
            st.session_state["resume_text"] = payload["resume_preview"]

    def render_input_form(self) -> tuple[str, str, str]:
        """
        Отображает форму ввода вакансии и резюме.

        Returns:
            Кортеж (vacancy_text, resume_text, vacancy_title).
        """
        vacancy_title = st.session_state.get("vacancy_title", "Вакансия")

        pasted = render_paste_zone()
        if pasted:
            try:
                with st.spinner("Загружаю вакансию с hh.ru…"):
                    title, cleaned = resolve_vacancy_from_paste(pasted)
            except Exception as exc:
                st.error(f"Не удалось загрузить вакансию: {exc}")
            else:
                if cleaned:
                    self._apply_vacancy_to_form(title, cleaned)
                    st.session_state["hh_paste_clear_pending"] = True
                    st.success(f"Вакансия загружена: **{title}** ({len(cleaned)} символов)")
                    st.rerun()
                else:
                    st.warning("Вставьте ссылку hh.ru или полный текст вакансии")

        col_vacancy, col_resume = st.columns(2)

        with col_vacancy:
            st.subheader("📋 Вакансия")
            vacancy_file = st.file_uploader(
                "Загрузить вакансию (DOCX/PDF/TXT)",
                type=["docx", "pdf", "txt"],
                key="vacancy_file",
            )

            if vacancy_file is not None:
                upload_token = f"{vacancy_file.name}:{vacancy_file.size}"
                if st.session_state.get("vacancy_upload_token") != upload_token:
                    try:
                        file_type = vacancy_file.name.rsplit(".", 1)[-1]
                        parsed = self.document_parser.parse(vacancy_file.getvalue(), file_type)
                        file_title = vacancy_file.name.rsplit(".", 1)[0]
                        if (
                            st.session_state.get("vacancy_title")
                            and st.session_state["vacancy_title"] != "Вакансия"
                        ):
                            file_title = st.session_state["vacancy_title"]
                        self._apply_vacancy_to_form(file_title, parsed)
                        st.session_state["vacancy_upload_token"] = upload_token
                        st.success(f"Вакансия загружена: {vacancy_file.name}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Ошибка чтения вакансии: {exc}")

            if "vacancy_input" not in st.session_state:
                st.session_state["vacancy_input"] = st.session_state.get("vacancy_text", "")

            vacancy = st.text_area(
                "Текст вакансии",
                height=280,
                placeholder="Вставьте текст вакансии, ссылку hh.ru или загрузите файл...",
                key="vacancy_input",
            )
            st.session_state["vacancy_text"] = vacancy

            if "vacancy_title_input" not in st.session_state:
                st.session_state["vacancy_title_input"] = st.session_state.get(
                    "vacancy_title", "Вакансия"
                )
            title_input = st.text_input(
                "Название вакансии (для истории)",
                key="vacancy_title_input",
            )
            vacancy_title = title_input.strip() or "Вакансия"
            st.session_state["vacancy_title"] = vacancy_title

        with col_resume:
            st.subheader("👤 Резюме")
            resume = self._render_resume_column_pair(key_prefix="single")

        return vacancy.strip(), resume.strip(), vacancy_title

    def _apply_vacancy_to_form(self, title: str, text: str) -> None:
        """Синхронизирует текст вакансии со всеми полями формы."""
        st.session_state["vacancy_text"] = text
        st.session_state["vacancy_input"] = text
        st.session_state["vacancy_title"] = title
        st.session_state["vacancy_title_input"] = title

    def _render_resume_column(self) -> str:
        """Только колонка резюме (для режима сравнения)."""
        st.subheader("👤 Резюме")
        return self._render_resume_column_pair(key_prefix="compare").strip()

    def _render_resume_column_pair(self, *, key_prefix: str = "single") -> str:
        """Поле ввода резюме с загрузкой файла."""
        file_key = f"{key_prefix}_resume_file"
        input_key = f"{key_prefix}_resume_input"
        upload_token_key = f"{key_prefix}_resume_upload_token"

        resume_file = st.file_uploader(
            "Загрузить резюме (PDF/DOCX/TXT)",
            type=["pdf", "docx", "txt"],
            key=file_key,
        )

        if resume_file is not None:
            upload_token = f"{resume_file.name}:{resume_file.size}"
            if st.session_state.get(upload_token_key) != upload_token:
                try:
                    file_type = resume_file.name.rsplit(".", 1)[-1]
                    parsed = self.document_parser.parse(resume_file.getvalue(), file_type)
                    st.session_state[input_key] = parsed
                    st.session_state["resume_text"] = parsed
                    st.session_state[upload_token_key] = upload_token
                    st.success(f"Резюме загружено: {resume_file.name}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Ошибка чтения резюме: {exc}")

        if input_key not in st.session_state:
            st.session_state[input_key] = st.session_state.get("resume_text", "")

        resume = st.text_area(
            "Текст резюме",
            height=280,
            placeholder="Вставьте текст резюме или загрузите файл...",
            key=input_key,
        )

        st.session_state["resume_text"] = resume
        return resume

    def _render_multi_vacancy_form(self) -> list[dict[str, str]]:
        """Форма для нескольких вакансий в режиме сравнения."""
        st.subheader("📋 Вакансии для сравнения")

        if "vacancy_list" not in st.session_state:
            st.session_state.vacancy_list = [
                {"title": "Вакансия 1", "text": ""},
                {"title": "Вакансия 2", "text": ""},
            ]

        col_add, col_remove = st.columns(2)
        with col_add:
            if st.button("➕ Добавить вакансию", key="add_vacancy_slot"):
                n = len(st.session_state.vacancy_list) + 1
                st.session_state.vacancy_list.append({"title": f"Вакансия {n}", "text": ""})
                st.rerun()
        with col_remove:
            if len(st.session_state.vacancy_list) > 2 and st.button(
                "➖ Убрать последнюю", key="remove_vacancy_slot"
            ):
                st.session_state.vacancy_list.pop()
                st.rerun()

        vacancies: list[dict[str, str]] = []
        for idx, slot in enumerate(st.session_state.vacancy_list):
            with st.expander(f"Вакансия {idx + 1}", expanded=idx < 2):
                title = st.text_input(
                    "Название",
                    value=slot.get("title", f"Вакансия {idx + 1}"),
                    key=f"cmp_title_{idx}",
                )
                text = st.text_area(
                    "Текст вакансии",
                    value=slot.get("text", ""),
                    height=160,
                    key=f"cmp_text_{idx}",
                )
                upload = st.file_uploader(
                    f"Файл (PDF/DOCX/TXT)",
                    type=["pdf", "docx", "txt"],
                    key=f"cmp_file_{idx}",
                )
                if upload is not None:
                    try:
                        file_type = upload.name.rsplit(".", 1)[-1]
                        text = self.document_parser.parse(upload.getvalue(), file_type)
                        st.success(f"Загружено: {upload.name}")
                    except Exception as exc:
                        st.error(str(exc))
                vacancies.append({"title": title.strip(), "text": text.strip()})
                st.session_state.vacancy_list[idx] = {"title": title, "text": text}

        return vacancies

    def _render_compare_button(self, resume: str, vacancies: list[dict[str, str]]) -> None:
        """Запускает сравнение вакансий."""
        filled = [v for v in vacancies if v.get("text", "").strip()]
        if st.button(
            "⚖️ Сравнить вакансии",
            type="primary",
            use_container_width=True,
            disabled=not resume or len(filled) < 2,
        ):
            with st.spinner(f"Сравниваю {len(filled)} вакансий..."):
                result = self.orchestrator.compare_vacancies(resume, filled)
            st.session_state["comparison_result"] = result
            if result.get("best") and result["best"].get("result"):
                st.session_state["last_result"] = result["best"]["result"]
            st.session_state.pop("improved_resume", None)
            st.session_state.pop("cover_letter_text", None)
            st.rerun()

        if not resume:
            st.caption("Загрузите или вставьте резюме")
        elif len(filled) < 2:
            st.caption("Нужно минимум 2 вакансии с текстом")

    def render_results(self, data: dict[str, Any]) -> None:
        """
        Визуализирует результаты анализа.

        Args:
            data: Результат анализа или словарь с ошибкой.
        """
        if data.get("error"):
            if data.get("cancelled"):
                st.warning(data["error"])
            else:
                st.error(data["error"])
            return

        st.markdown("---")
        st.subheader("📊 Результаты анализа")

        render_executive_summary(data)

        vacancy = self._get_vacancy_text()
        resume = self._get_resume_text()
        vacancy_title = st.session_state.get("vacancy_title", "Вакансия")
        analysis_id = str(
            data.get("meta", {}).get("history_id")
            or vacancy_title
        )
        checklist_items = self.checklist_manager.build_items(analysis_id, data)
        checklist_done, checklist_total = self.checklist_manager.get_progress(checklist_items)

        share_url = st.session_state.get("share_url", "")
        if not share_url and st.session_state.get("shared_view"):
            share_id = st.query_params.get("share", "")
            if share_id:
                from core.config import APP_BASE_URL

                share_url = f"{APP_BASE_URL.rstrip('/')}?share={share_id}"
        elif not share_url and not st.session_state.get("shared_view"):
            share_url = self.orchestrator.create_share_link(
                data,
                vacancy_preview=vacancy[:300],
                resume_preview=resume[:300],
            )
            st.session_state["share_url"] = share_url

        render_wow_dashboard(
            data,
            vacancy_title=vacancy_title,
            vacancy_text=vacancy,
            share_url=share_url,
            checklist_done=checklist_done,
            checklist_total=checklist_total,
        )

        pdf_bytes, _, pdf_name = self.orchestrator.export_report(data, "pdf")

        cover_letter = self._render_cover_letter_section(vacancy, resume, data)

        render_action_bar(data, cover_letter, pdf_bytes, pdf_name)

        if not st.session_state.get("shared_view"):
            if st.button("🔗 Поделиться ссылкой", key="create_share_link"):
                share_url = self.orchestrator.create_share_link(
                    data,
                    vacancy_preview=vacancy[:300],
                    resume_preview=resume[:300],
                )
                st.session_state["share_url"] = share_url
            if st.session_state.get("share_url"):
                render_share_button(st.session_state["share_url"])
                st.caption("QR-код для телефона — во вкладке «📱 QR-код» в WOW-панели выше")

        if st.button("✨ Улучшить резюме", type="primary", use_container_width=False, key="btn_improve_resume"):
            self._run_improve_resume(vacancy, resume, data)

        if st.session_state.get("improved_resume"):
            st.markdown("### ✨ Улучшенное резюме")
            st.text_area(
                "Улучшенное резюме",
                value=st.session_state["improved_resume"],
                height=360,
                label_visibility="collapsed",
            )
            col_apply, col_copy = st.columns(2)
            with col_apply:
                if st.button("📝 Применить в форму резюме"):
                    st.session_state["resume_text"] = st.session_state["improved_resume"]
                    st.success("Улучшенное резюме подставлено в форму выше")
                    st.rerun()
            with col_copy:
                render_copy_to_clipboard(
                    st.session_state["improved_resume"],
                    "📋 Копировать резюме",
                    "copy_improved_resume",
                )

        summary = data.get("summary", {})
        tab_overview, tab_details, tab_text = st.tabs(
            ["Обзор", "По требованиям", "Текстовый отчёт"]
        )

        with tab_overview:
            col_left, col_right = st.columns([1, 2])
            with col_left:
                render_match_progress(summary.get("match_percentage", 0))
                render_summary_badges(summary)
                meta = data.get("meta", {})
                if meta:
                    usage = meta.get("usage", {})
                    if usage.get("total_tokens"):
                        st.caption(
                            f"Токены: {usage.get('total_tokens')} | "
                            f"Стоимость: ${usage.get('cost_usd', 0):.6f}"
                        )
                    provider = meta.get("provider", "")
                    if provider:
                        st.caption(f"Провайдер: {get_provider_label(provider)}")
                    if meta.get("demo_mode"):
                        st.caption("Режим: демо")
            with col_right:
                analysis_id = str(
                    data.get("meta", {}).get("history_id")
                    or st.session_state.get("vacancy_title", "current")
                )
                render_recommendation_checklist(
                    data, self.checklist_manager, analysis_id
                )

        with tab_details:
            render_matching_table(data.get("matching", []))

        with tab_text:
            render_text_report(data)
            st.caption("Или используйте кнопку «Копировать отчёт» выше.")

        self.render_export_button(data)

    def _get_vacancy_text(self) -> str:
        """Текст вакансии из session_state (с запасными ключами виджетов)."""
        return (
            st.session_state.get("vacancy_text")
            or st.session_state.get("vacancy_input")
            or ""
        ).strip()

    def _get_resume_text(self) -> str:
        """Текст резюме из session_state (с запасными ключами виджетов)."""
        return (
            st.session_state.get("resume_text")
            or st.session_state.get("single_resume_input")
            or st.session_state.get("compare_resume_input")
            or ""
        ).strip()

    def _render_cover_letter_section(
        self,
        vacancy: str,
        resume: str,
        data: dict[str, Any],
    ) -> str:
        """Блок сопроводительного письма: генерация, просмотр и копирование."""
        st.markdown("### ✉️ Сопроводительное письмо")

        if st.button(
            "✉️ Сгенерировать письмо ИИ",
            key="btn_generate_cover_letter",
            use_container_width=False,
        ):
            self._generate_cover_letter_ai(vacancy, resume, data)

        letter = st.session_state.get("cover_letter_text")
        if letter:
            if "cover_letter_editor" not in st.session_state:
                st.session_state["cover_letter_editor"] = letter
            edited = st.text_area(
                "Текст сопроводительного письма",
                height=280,
                key="cover_letter_editor",
                label_visibility="collapsed",
            )
            st.session_state["cover_letter_text"] = edited
            render_copy_to_clipboard(edited, "📋 Копировать письмо", "copy_cover_letter_main")
            return edited

        fallback = build_cover_letter_fallback(data)
        st.info(
            "Нажмите **«Сгенерировать письмо ИИ»** — письмо появится здесь через 15–30 секунд. "
            "Пока можно использовать шаблон в кнопке «Копировать для письма» выше."
        )
        return fallback

    def _generate_cover_letter_ai(
        self,
        vacancy: str,
        resume: str,
        data: dict[str, Any],
    ) -> None:
        """Генерирует сопроводительное письмо через LLM."""
        vacancy = vacancy.strip() or self._get_vacancy_text()
        resume = resume.strip() or self._get_resume_text()
        if not vacancy:
            st.error("Нет текста вакансии. Загрузите вакансию в форме выше.")
            return
        if not resume:
            st.error("Нет текста резюме. Загрузите резюме в форме выше.")
            return
        with st.spinner("ИИ пишет сопроводительное письмо… (15–30 сек)"):
            result = self.orchestrator.generate_cover_letter(vacancy, resume, data)
        if result.get("error"):
            st.error(f"Ошибка генерации: {result['error']}")
            return
        letter = result.get("cover_letter", "").strip()
        if not letter:
            st.error("ИИ вернул пустой ответ — попробуйте ещё раз")
            return
        st.session_state["cover_letter_text"] = letter
        st.session_state["cover_letter_editor"] = letter
        st.success("Сопроводительное письмо готово!")
        st.rerun()

    def _run_improve_resume(
        self,
        vacancy: str,
        resume: str,
        data: dict[str, Any],
    ) -> None:
        """Запускает улучшение резюме через Backend-агента."""
        if not vacancy.strip() or not resume.strip():
            st.error("Нужны тексты вакансии и резюме для улучшения")
            return
        with st.spinner("ИИ улучшает слабые места резюме..."):
            result = self.orchestrator.improve_resume(vacancy, resume, data)
        if result.get("error"):
            st.error(result["error"])
            return
        st.session_state["improved_resume"] = result["improved_resume"]
        st.success("Резюме улучшено! Прокрутите вниз к блоку «Улучшенное резюме».")
        st.rerun()

    def render_history(self) -> None:
        """Отображает историю последних анализов."""
        history = self.orchestrator.get_history()
        if not history:
            return

        st.markdown("---")
        st.subheader("🕘 История анализов")

        render_history_timeline(history)

        for item in history:
            with st.expander(render_history_item_label(item)):
                st.write(f"**ID:** {item.get('id')}")
                title = item.get("vacancy_title") or item.get("vacancy_preview", "")
                st.write(f"**Вакансия:** {title}")
                st.write(f"**Резюме:** {item.get('resume_preview', '')[:100]}...")
                if st.button("Показать результат", key=f"show_history_{item.get('id')}"):
                    result = item.get("result", {})
                    if hasattr(result, "model_dump"):
                        result = result.model_dump(mode="json")
                    st.session_state["last_result"] = result
                    st.session_state.pop("share_url", None)
                    st.rerun()

    def render_loading_state(
        self,
        status: dict[str, Any] | None = None,
        placeholder: Any | None = None,
    ) -> None:
        """
        Отображает индикацию загрузки и статусы агентов.

        Args:
            status: Текущий статус анализа.
            placeholder: Streamlit empty() для отображения pipeline.
        """
        status = status or self.orchestrator.get_status()
        render_pipeline_status(status, placeholder=placeholder)

    def render_export_button(self, data: dict[str, Any]) -> None:
        """Экспорт JSON (для разработчиков)."""
        if data.get("error"):
            return
        with st.expander("📎 Экспорт JSON (для разработчиков)"):
            json_bytes, json_mime, json_name = self.orchestrator.export_report(data, "json")
            st.download_button(
                "Скачать JSON",
                data=json_bytes,
                file_name=json_name,
                mime=json_mime,
                use_container_width=True,
            )

    def _render_header(self) -> None:
        """Отображает заголовок приложения."""
        st.markdown(
            """
            <div class="main-header">🎯 ResumeScore</div>
            <div class="sub-header">
                Многоагентное сопоставление резюме и вакансий с рекомендациями
            </div>
            """,
            unsafe_allow_html=True,
        )

    def _render_sidebar(self) -> str:
        """
        Отображает боковую панель с настройками.

        Returns:
            Выбранная тема (light/dark).
        """
        with st.sidebar:
            st.header("⚙️ Настройки")

            if "ui_theme" not in st.session_state:
                st.session_state.ui_theme = "light"

            theme = st.selectbox(
                "Тема",
                ["light", "dark"],
                index=0 if st.session_state.ui_theme == "light" else 1,
                format_func=lambda x: "☀️ Светлая" if x == "light" else "🌙 Тёмная",
            )
            st.session_state.ui_theme = theme

            st.markdown("---")
            st.markdown("**Быстрый старт**")
            if st.button("Загрузить демо-данные", use_container_width=True):
                demo_vacancy, demo_resume = self.orchestrator.load_demo_texts()
                st.session_state["vacancy_text"] = demo_vacancy or DEMO_VACANCY_TEXT
                st.session_state["resume_text"] = demo_resume or DEMO_RESUME_TEXT
                st.rerun()

            if st.button("Очистить историю", use_container_width=True):
                self.orchestrator.session_manager.clear_history()
                st.session_state.pop("last_result", None)
                st.rerun()

            st.markdown("---")
            self._render_provider_selector()

            st.markdown("---")
            st.caption("Архитектура: Frontend → Orchestrator → Backend → LLM")

        return theme

    def _render_provider_selector(self) -> None:
        """Отображает выбор LLM-провайдера в боковой панели."""
        st.markdown("**LLM-провайдер**")
        current = self.orchestrator.session_manager.get_selected_provider()
        if current not in PROVIDER_CHOICES:
            current = "auto"

        selected = st.selectbox(
            "Провайдер для анализа",
            options=PROVIDER_CHOICES,
            index=PROVIDER_CHOICES.index(current),
            format_func=lambda key: PROVIDER_UI_LABELS.get(key, key),
            label_visibility="collapsed",
            key="llm_provider_select",
        )
        self.orchestrator.session_manager.set_selected_provider(selected)

        resolved = resolve_provider(selected)
        if selected == "auto":
            st.caption(f"Будет использован: **{get_provider_label(resolved)}**")
        elif selected == "deepseek":
            st.caption("Работает без VPN")

        st.markdown("**Статус API-ключей**")
        for provider_id, configured in get_providers_status().items():
            icon = "✅" if configured else "❌"
            st.caption(f"{icon} {get_provider_label(provider_id)}")

        if selected not in ("demo", "auto") and not is_provider_configured(selected):
            st.warning(
                f"Ключ для {get_provider_label(selected)} не найден. "
                "Облако: **Settings → Secrets** · локально: `.env`"
            )
        elif is_demo_mode(selected):
            st.caption("🎭 Анализ на тестовых данных")

    def _render_action_buttons(
        self,
        vacancy: str,
        resume: str,
        pipeline_placeholder: Any,
        *,
        vacancy_title: str = "Вакансия",
    ) -> None:
        """Отображает кнопки запуска и отмены анализа."""
        col_analyze, col_cancel = st.columns([3, 1])

        with col_analyze:
            analyze_clicked = st.button(
                "Анализировать 🚀",
                type="primary",
                use_container_width=True,
            )

        with col_cancel:
            cancel_clicked = st.button(
                "Отмена",
                use_container_width=True,
            )

        if cancel_clicked:
            self.orchestrator.cancel_analysis()
            st.warning("Запрос на отмену отправлен")

        if analyze_clicked:
            self.logger.info("Пользователь запустил анализ")

            def refresh_pipeline() -> None:
                render_pipeline_status(
                    self.orchestrator.get_status(),
                    placeholder=pipeline_placeholder,
                )

            result = self.orchestrator.start_analysis(
                vacancy,
                resume,
                ui_callback=refresh_pipeline,
                vacancy_title=vacancy_title,
            )
            st.session_state["last_result"] = result
            st.session_state.pop("improved_resume", None)
            st.session_state.pop("cover_letter_text", None)
            st.session_state.pop("share_url", None)
            st.session_state.pop("comparison_result", None)
            render_pipeline_status(self.orchestrator.get_status(), placeholder=pipeline_placeholder)
            st.rerun()
