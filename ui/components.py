"""Переиспользуемые Streamlit-компоненты."""

from __future__ import annotations

from typing import Any

import streamlit as st

STATUS_ICONS = {
    "pending": "⏳",
    "running": "⏳",
    "done": "✅",
    "error": "❌",
    "cancelled": "🛑",
}

MATCH_ICONS = {
    "green": "🟢",
    "yellow": "🟡",
    "red": "🔴",
}

MATCH_STATUS_LABELS = {
    "green": "Полное соответствие",
    "yellow": "Частичное соответствие",
    "red": "Не соответствует",
}

AGENT_LABELS = {
    "frontend": "Frontend-агент",
    "orchestrator": "Оркестратор",
    "backend": "Backend-агент",
}


def format_ascii_progress(percent: int, width: int = 27) -> str:
    """Формирует ASCII-прогресс-бар вида [████░░░] 72%."""
    percent = max(0, min(100, percent))
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {percent}%"


def build_pipeline_html(status: dict[str, Any]) -> str:
    """
    Собирает HTML-блок pipeline со статусами агентов и прогресс-баром.

    Args:
        status: Словарь статуса из session_manager.

    Returns:
        HTML-строка для st.markdown.
    """
    steps = status.get("steps") or status.get("agents") or []
    progress = status.get("progress_percent", 0)
    is_running = status.get("is_running", False)
    title = "🔍 Анализирую вакансию..." if is_running else "🔍 Анализ завершён"

    lines = []
    for step in steps:
        agent_key = step.get("agent", "")
        label = AGENT_LABELS.get(agent_key, agent_key)
        state = step.get("state", "pending")
        icon = STATUS_ICONS.get(state, "⏳")
        css_class = f"rs-status-{state}"
        message = step.get("message", "")
        lines.append(
            f'<div class="pipeline-step {css_class}">{icon} {label}: {message}</div>'
        )

    steps_html = "\n".join(lines)
    bar = format_ascii_progress(progress)

    return f"""
    <div class="card pipeline-card">
        <div class="pipeline-title">{title}</div>
        <div class="pipeline-steps">{steps_html}</div>
        <div class="pipeline-bar">{bar}</div>
    </div>
    """


def render_pipeline_status(status: dict[str, Any], placeholder: Any | None = None) -> None:
    """
    Отображает pipeline статусов агентов с ASCII-прогресс-баром.

    Args:
        status: Текущий статус анализа.
        placeholder: Streamlit empty() для live-обновления.
    """
    steps = status.get("steps") or status.get("agents") or []
    if not steps and not status.get("is_running"):
        return

    html = build_pipeline_html(status)
    if placeholder is not None:
        placeholder.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)


def render_agent_status(agents: list[dict[str, Any]]) -> None:
    """Отображает статусы агентов в pipeline (совместимость)."""
    if not agents:
        return
    render_pipeline_status({"steps": agents, "progress_percent": 0, "is_running": True})


def _verdict_text(match_percentage: int) -> str:
    """Возвращает текстовую оценку уровня совпадения."""
    if match_percentage >= 80:
        return "отличное соответствие — можно откликаться"
    if match_percentage >= 65:
        return "хорошее соответствие — стоит доработать резюме по рекомендациям"
    if match_percentage >= 50:
        return "среднее соответствие — нужны точечные улучшения"
    return "низкое соответствие — резюме требует существенной доработки"


def render_executive_summary(data: dict[str, Any]) -> None:
    """
    Отображает краткий текстовый итог анализа для обычного пользователя.

    Args:
        data: Результат анализа.
    """
    summary = data.get("summary", {})
    match = summary.get("match_percentage", 0)
    green = summary.get("green_count", 0)
    yellow = summary.get("yellow_count", 0)
    red = summary.get("red_count", 0)

    st.markdown("### 📝 Краткий итог")
    st.success(
        f"**Совпадение с вакансией: {match}%** — {_verdict_text(match)}.\n\n"
        f"Из требований вакансии: **{green}** полностью закрыты, "
        f"**{yellow}** — частично, **{red}** — не найдены в резюме."
    )


def render_match_progress(match_percentage: int) -> None:
    """Отображает прогресс-бар совпадения."""
    st.metric("Совпадение с вакансией", f"{match_percentage}%")
    st.progress(match_percentage / 100)


def render_summary_badges(summary: dict[str, Any]) -> None:
    """Отображает сводные метрики green/yellow/red."""
    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Полное", summary.get("green_count", 0))
    col2.metric("🟡 Частичное", summary.get("yellow_count", 0))
    col3.metric("🔴 Нет", summary.get("red_count", 0))


def render_matching_table(matching: list[dict[str, Any]]) -> None:
    """
    Отображает сопоставление требований в читаемом текстовом виде.

    Args:
        matching: Список элементов matching из результата анализа.
    """
    st.markdown("### 🔎 Разбор по требованиям вакансии")

    for idx, item in enumerate(matching, start=1):
        status = item.get("status", "red")
        icon = MATCH_ICONS.get(status, "🔴")
        status_label = MATCH_STATUS_LABELS.get(status, status)
        requirement = item.get("requirement", "")
        preview = requirement if len(requirement) <= 90 else f"{requirement[:90]}…"

        with st.expander(f"{idx}. {icon} {preview}", expanded=idx <= 3):
            st.markdown(f"**Статус:** {status_label}")
            st.markdown(f"**Требование вакансии:**  \n{requirement}")
            st.markdown(f"**Что есть в резюме:**  \n{item.get('evidence', '')}")
            st.markdown(f"**Что сделать за 1–2 дня:**  \n{item.get('recommendation', '')}")


def build_report_text(data: dict[str, Any]) -> str:
    """Собирает полный текстовый отчёт для копирования и экспорта."""
    summary = data.get("summary", {})
    lines = [
        "ОТЧЁТ RESUMESCORE",
        "=" * 40,
        f"Совпадение: {summary.get('match_percentage', 0)}%",
        f"Полное: {summary.get('green_count', 0)} | "
        f"Частичное: {summary.get('yellow_count', 0)} | "
        f"Нет: {summary.get('red_count', 0)}",
        "",
        "ТОП-3 ДЕЙСТВИЯ:",
    ]
    for idx, action in enumerate(data.get("top_3_actions", []), start=1):
        lines.append(f"  {idx}. {action}")

    lines.append("")
    lines.append("ДЕТАЛИ ПО ТРЕБОВАНИЯМ:")
    for idx, item in enumerate(data.get("matching", []), start=1):
        status_label = MATCH_STATUS_LABELS.get(item.get("status", ""), "")
        lines.extend(
            [
                "",
                f"{idx}. [{status_label}] {item.get('requirement', '')}",
                f"   Резюме: {item.get('evidence', '')}",
                f"   Рекомендация: {item.get('recommendation', '')}",
            ]
        )
    return "\n".join(lines)


def build_cover_letter_fallback(data: dict[str, Any]) -> str:
    """Формирует простой шаблон письма без LLM (запасной вариант)."""
    match = data.get("summary", {}).get("match_percentage", 0)
    greens = [m for m in data.get("matching", []) if m.get("status") == "green"][:3]
    points = "\n".join(f"• {item.get('evidence', '')}" for item in greens)
    actions = "\n".join(f"• {a}" for a in data.get("top_3_actions", [])[:2])
    return (
        f"Здравствуйте!\n\n"
        f"Меня заинтересовала ваша вакансия. По предварительной оценке, "
        f"мой профиль соответствует требованиям на {match}%.\n\n"
        f"Ключевые компетенции:\n{points}\n\n"
        f"Готов оперативно усилить резюме:\n{actions}\n\n"
        f"Буду рад обсудить детали на собеседовании."
    )


def render_copy_to_clipboard(text: str, label: str, button_id: str) -> None:
    """
    Кнопка копирования текста в буфер обмена через браузер.

    Args:
        text: Текст для копирования.
        label: Подпись кнопки.
        button_id: Уникальный HTML-id кнопки.
    """
    import json

    import streamlit.components.v1 as components

    safe_text = json.dumps(text)
    safe_label = json.dumps(label)
    components.html(
        f"""
        <button id="{button_id}" style="
            width:100%; padding:0.55rem 1rem; border-radius:0.5rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color:white; border:none; cursor:pointer; font-size:14px; font-weight:600;">
            {label}
        </button>
        <script>
        (function() {{
            const btn = document.getElementById("{button_id}");
            const original = {safe_label};
            btn.onclick = async function() {{
                try {{
                    await navigator.clipboard.writeText({safe_text});
                    btn.innerText = "✓ Скопировано";
                    setTimeout(() => btn.innerText = original, 2000);
                }} catch (e) {{
                    btn.innerText = "Скопируйте вручную";
                }}
            }};
        }})();
        </script>
        """,
        height=48,
    )


def render_action_bar(
    data: dict[str, Any],
    cover_letter: str,
    pdf_bytes: bytes,
    pdf_name: str,
) -> None:
    """
    Панель критичных действий: копирование, PDF, улучшение резюме.

    Args:
        data: Результат анализа.
        cover_letter: Текст сопроводительного письма.
        pdf_bytes: PDF-файл отчёта.
        pdf_name: Имя PDF-файла.
    """
    st.markdown("### 🛠 Действия")
    report_text = build_report_text(data)

    col_copy_report, col_copy_letter, col_pdf = st.columns(3)

    with col_copy_report:
        render_copy_to_clipboard(report_text, "📋 Копировать отчёт", "copy_report_btn")

    with col_copy_letter:
        render_copy_to_clipboard(cover_letter, "📋 Копировать для письма", "copy_letter_btn")

    with col_pdf:
        st.download_button(
            "📥 Скачать PDF",
            data=pdf_bytes,
            file_name=pdf_name,
            mime="application/pdf",
            use_container_width=True,
        )


def render_text_report(data: dict[str, Any]) -> None:
    """
    Формирует сплошной текстовый отчёт (удобно читать и копировать).

    Args:
        data: Результат анализа.
    """
    st.text_area(
        "Полный текстовый отчёт",
        value=build_report_text(data),
        height=320,
        disabled=True,
        label_visibility="collapsed",
    )


def render_top_actions(actions: list[str], key_prefix: str = "action") -> None:
    """Отображает топ-3 рекомендации с чекбоксами (устаревший, см. render_recommendation_checklist)."""
    st.markdown("### ✅ Топ-3 действия для улучшения резюме")
    for idx, action in enumerate(actions, start=1):
        st.checkbox(f"**{idx}.** {action}", key=f"{key_prefix}_{idx}")


def render_recommendation_checklist(
    data: dict[str, Any],
    checklist_manager: Any,
    analysis_id: str,
) -> None:
    """
    Чек-лист рекомендаций с прогрессом «сделано / не сделано».

    Args:
        data: Результат анализа.
        checklist_manager: Экземпляр ChecklistManager.
        analysis_id: Уникальный ID анализа для хранения отметок.
    """
    items = checklist_manager.build_items(analysis_id, data)
    done, total = checklist_manager.get_progress(items)

    st.markdown("### ✅ Чек-лист рекомендаций")
    if total:
        st.caption(f"Выполнено **{done}** из **{total}**")
        st.progress(done / total if total else 0)
    else:
        st.caption("Нет рекомендаций для отслеживания")

    for item in items:
        item_id = item["id"]
        checkbox_key = f"checklist_cb_{item_id}"
        if checkbox_key not in st.session_state:
            st.session_state[checkbox_key] = checklist_manager.is_done(item_id)
        checked = st.checkbox(
            f"**{item['source']}:** {item['text']}",
            key=checkbox_key,
        )
        checklist_manager.set_done(item_id, checked)


def render_history_timeline(history: list[dict[str, Any]]) -> None:
    """
    График прогресса совпадения по датам анализов.

    Args:
        history: Записи из session_manager.get_history().
    """
    if len(history) < 2:
        return

    import pandas as pd

    rows: list[dict[str, Any]] = []
    for item in reversed(history):
        ts = item.get("timestamp", "")
        label = _format_history_date(ts)
        title = item.get("vacancy_title") or item.get("vacancy_preview", "Вакансия")
        rows.append(
            {
                "Дата": label,
                "Совпадение %": item.get("match_percentage", 0),
                "Вакансия": str(title)[:40],
            }
        )

    st.markdown("#### 📈 Прогресс во времени")
    chart_df = pd.DataFrame(rows)
    st.line_chart(chart_df, x="Дата", y="Совпадение %", height=220)


def _format_history_date(timestamp: str) -> str:
    """Форматирует ISO-дату для отображения в истории."""
    if not timestamp:
        return "—"
    try:
        from datetime import datetime

        if timestamp.endswith("Z"):
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        return str(timestamp)[:16]


def render_history_item_label(item: dict[str, Any]) -> str:
    """Формирует подпись для записи истории."""
    match = item.get("match_percentage", 0)
    date_label = _format_history_date(item.get("timestamp", ""))
    title = item.get("vacancy_title") or item.get("vacancy_preview", "Вакансия")
    return f"{match}% · {date_label} · {str(title)[:50]}"


def render_vacancy_comparison(comparisons: list[dict[str, Any]]) -> None:
    """
    Таблица сравнения нескольких вакансий с одним резюме.

    Args:
        comparisons: Список из compare_vacancies (отсортирован по match %).
    """
    if not comparisons:
        st.warning("Нет вакансий для сравнения")
        return

    st.markdown("### 📊 Сравнение вакансий")
    medals = ("🥇", "🥈", "🥉")

    chart_rows = []
    for rank, row in enumerate(comparisons, start=1):
        medal = medals[rank - 1] if rank <= 3 else f"{rank}."
        title = row.get("title", f"Вакансия {rank}")
        pct = row.get("match_percentage", 0)

        if row.get("error"):
            st.error(f"{medal} **{title}** — ошибка: {row['error']}")
            continue

        st.metric(label=f"{medal} {title}", value=f"{pct}%")
        if rank == 1:
            st.success("Лучший вариант для отклика — откройте детали ниже")
        chart_rows.append({"Вакансия": str(title)[:30], "Совпадение %": pct})

    if chart_rows:
        import pandas as pd

        st.bar_chart(pd.DataFrame(chart_rows), x="Вакансия", y="Совпадение %", height=280)


def render_paste_zone() -> str | None:
    """
    Зона вставки ссылки или текста вакансии с HH.ru.

    Returns:
        Текст для загрузки, если нажата кнопка «Заполнить вакансию».
    """
    if st.session_state.pop("hh_paste_clear_pending", False):
        st.session_state["hh_paste_buffer"] = ""

    st.markdown("#### 📋 Вставить с HH.ru")
    st.caption(
        "Вставьте **ссылку** `https://hh.ru/vacancy/…` в поле ниже (Ctrl+V), "
        "затем нажмите кнопку"
    )

    st.text_area(
        "Ссылка или текст вакансии",
        height=100,
        placeholder="https://hh.ru/vacancy/123456789",
        key="hh_paste_buffer",
        label_visibility="collapsed",
    )

    col_apply, col_clear = st.columns([4, 1])
    with col_apply:
        apply_clicked = st.button(
            "📥 Заполнить вакансию из буфера",
            key="hh_paste_apply",
            type="primary",
            use_container_width=True,
        )
    with col_clear:
        clear_clicked = st.button(
            "Очистить",
            key="hh_paste_clear",
            use_container_width=True,
        )

    if clear_clicked:
        st.session_state["hh_paste_clear_pending"] = True
        st.rerun()

    if apply_clicked:
        text = st.session_state.get("hh_paste_buffer", "").strip()
        if not text:
            st.warning("Поле пустое. Вставьте ссылку на вакансию в поле выше (Ctrl+V).")
            return None
        return text

    return None


def render_share_button(share_url: str) -> None:
    """
    Кнопка копирования ссылки на результат.

    Args:
        share_url: Полный URL с параметром share=.
    """
    st.text_input("Ссылка для ментора или друга", value=share_url, key="share_url_display")
    render_copy_to_clipboard(share_url, "📋 Копировать ссылку", "copy_share_link_btn")
