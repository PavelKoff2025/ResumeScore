"""WOW-компоненты для демонстрации: карта навыков, геймификация, QR, рынок."""

from __future__ import annotations

import io
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from utils.gamification import build_gamification_message
from utils.hh_salary import (
    extract_salary_from_vacancy_text,
    extract_search_query,
    fetch_market_salary,
    format_salary,
)
from utils.skills_graph import build_skills_graph, graph_to_json, skills_graph_summary


def render_gamification_hero(
    data: dict[str, Any],
    checklist_done: int = 0,
    checklist_total: int = 0,
) -> None:
    """Баннер геймификации с уровнем, XP и мотивацией."""
    summary = data.get("summary", {})
    match_pct = int(summary.get("match_percentage", 0))
    stats = build_gamification_message(match_pct, summary, checklist_done, checklist_total)
    level = stats["level"]
    ring_pct = match_pct

    st.markdown(
        f"""
        <div class="wow-hero">
            <div class="wow-hero-left">
                <div class="wow-badge">{level["badge"]}</div>
                <div>
                    <div class="wow-level" style="color:{level['color']}">{level["title"]}</div>
                    <div class="wow-headline">{stats["headline"]}</div>
                    <div class="wow-subline">{stats["subline"]}</div>
                    {f'<div class="wow-checklist">{stats["checklist_hint"]}</div>' if stats["checklist_hint"] else ""}
                </div>
            </div>
            <div class="wow-ring-wrap">
                <svg class="wow-ring" viewBox="0 0 120 120">
                    <circle class="wow-ring-bg" cx="60" cy="60" r="52"/>
                    <circle class="wow-ring-fg" cx="60" cy="60" r="52"
                        stroke="{level['color']}"
                        stroke-dasharray="{ring_pct * 3.27} 327"/>
                </svg>
                <div class="wow-ring-label">{match_pct}%</div>
            </div>
            <div class="wow-xp">
                <div class="wow-xp-title">XP: {stats["xp"]}</div>
                <div class="wow-xp-bar"><div class="wow-xp-fill" style="width:{stats['xp_progress']}%"></div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_skills_map(matching: list[dict[str, Any]], height: int = 480) -> None:
    """Интерактивная карта навыков на vis-network."""
    if not matching:
        st.info("Нет данных для карты навыков")
        return

    graph = build_skills_graph(matching)
    counts = skills_graph_summary(matching)
    graph_json = graph_to_json(graph)

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Есть", counts["green"])
    col2.metric("🟡 Частично", counts["yellow"])
    col3.metric("🔴 Нет", counts["red"])

    components.html(
        f"""
        <div id="skills-network" style="width:100%;height:{height}px;border-radius:16px;
            border:1px solid #e2e8f0;background:linear-gradient(180deg,#f8fafc,#fff);"></div>
        <script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
        <script>
        (function() {{
            const graph = {graph_json};
            const groups = {{
                center: {{ color: {{ background: '#764ba2', border: '#667eea' }}, font: {{ color: '#fff' }} }},
                green: {{ color: {{ background: '#00b894', border: '#00a383' }}, font: {{ color: '#fff' }} }},
                yellow: {{ color: {{ background: '#f6c23e', border: '#dfa408' }}, font: {{ color: '#1e293b' }} }},
                red: {{ color: {{ background: '#e17055', border: '#d35400' }}, font: {{ color: '#fff' }} }},
            }};
            const nodes = new vis.DataSet(graph.nodes.map(n => ({{
                ...n,
                font: {{ size: 13, face: 'arial', color: n.group === 'yellow' ? '#1e293b' : '#fff' }},
            }})));
            const edges = new vis.DataSet(graph.edges.map(e => ({{
                ...e,
                color: {{ color: '#cbd5e1', highlight: '#667eea' }},
                width: 2,
                smooth: {{ type: 'continuous' }},
            }})));
            const container = document.getElementById('skills-network');
            const network = new vis.Network(container, {{ nodes, edges }}, {{
                groups,
                physics: {{
                    stabilization: {{ iterations: 120 }},
                    barnesHut: {{ gravitationalConstant: -4200, springLength: 140 }},
                }},
                interaction: {{ hover: true, tooltipDelay: 80 }},
                layout: {{ improvedLayout: true }},
            }});
            network.once('stabilizationIterationsDone', () => network.setOptions({{ physics: false }}));
        }})();
        </script>
        """,
        height=height + 10,
        scrolling=False,
    )
    st.caption("Кликните на узел — полное требование в подсказке. Зелёные — есть в резюме, красные — пробелы.")


def render_market_comparison(
    vacancy_title: str,
    vacancy_text: str = "",
    match_percentage: int = 0,
) -> None:
    """Блок сравнения с рынком по данным hh.ru."""
    query = extract_search_query(vacancy_title, vacancy_text)
    cache_key = f"market_{hash(query) % 10_000_000}"

    if cache_key not in st.session_state:
        with st.spinner("Загружаю данные рынка с hh.ru…"):
            st.session_state[cache_key] = fetch_market_salary(query)

    market = st.session_state[cache_key]
    if market.get("error") and not market.get("median"):
        st.warning(market["error"])
        return

    vac_from, vac_to = extract_salary_from_vacancy_text(vacancy_text)
    source = market.get("source", "hh.ru")
    note = market.get("note", "")

    st.markdown(
        f"""
        <div class="wow-market-card">
            <div class="wow-market-title">💰 Рынок: {market.get("query", query)[:50]}</div>
            <div class="wow-market-sub">{market.get("area_name", "Россия")} ·
                {market.get("vacancy_count", 0)} вакансий · источник: {source}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Медиана", format_salary(market.get("median"), market.get("currency", "RUR")))
    c2.metric("Вилка от", format_salary(market.get("avg_from"), market.get("currency", "RUR")))
    c3.metric("Вилка до", format_salary(market.get("avg_to"), market.get("currency", "RUR")))

    if vac_from or vac_to:
        st.info(
            f"В вашей вакансии указано: "
            f"**{format_salary(vac_from)}** — **{format_salary(vac_to or vac_from)}**"
        )

    if match_percentage >= 75:
        st.success("При таком совпадении вы конкурентоспособны на этом уровне зарплат")
    elif match_percentage >= 55:
        st.warning("Доработайте резюме — это может дать +10–15% к переговорам о зарплате")
    else:
        st.caption("Сначала закройте ключевые пробелы — потом обсуждайте вилку")

    if note:
        st.caption(note)
    st.caption(f"Выборка: {market.get('salary_count', 0)} вакансий с указанной зарплатой")


def render_result_qr(share_url: str) -> None:
    """QR-код для открытия результата на телефоне."""
    if not share_url:
        st.caption("Сначала создайте ссылку «Поделиться»")
        return

    try:
        import qrcode
    except ImportError:
        st.warning("Установите qrcode: pip install qrcode[pil]")
        return

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(share_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#667eea", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    col_img, col_info = st.columns([1, 2])
    with col_img:
        st.image(buf.getvalue(), caption="Сканируйте камерой", use_container_width=True)
    with col_info:
        st.markdown("#### 📱 Открыть на телефоне")
        st.markdown(
            "Наведите камеру — результат откроется в браузере. "
            "Удобно показать ментору или HR на встрече."
        )
        st.code(share_url, language=None)


def render_wow_dashboard(
    data: dict[str, Any],
    vacancy_title: str,
    vacancy_text: str,
    share_url: str = "",
    checklist_done: int = 0,
    checklist_total: int = 0,
) -> None:
    """Сводная WOW-панель после анализа."""
    st.markdown("### ✨ WOW-панель")
    render_gamification_hero(data, checklist_done, checklist_total)

    tab_map, tab_market, tab_mobile = st.tabs(
        ["🗺 Карта навыков", "💰 Рынок", "📱 QR-код"]
    )

    with tab_map:
        render_skills_map(data.get("matching", []))

    with tab_market:
        render_market_comparison(
            vacancy_title,
            vacancy_text,
            int(data.get("summary", {}).get("match_percentage", 0)),
        )

    with tab_mobile:
        render_result_qr(share_url)
