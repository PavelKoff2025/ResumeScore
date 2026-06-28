"""CSS-стили для Streamlit UI."""

from __future__ import annotations

import streamlit as st


def inject_styles(theme: str = "light") -> None:
    """
    Внедряет CSS-стили в Streamlit-приложение.

    Args:
        theme: Тема оформления (light или dark).
    """
    is_dark = theme == "dark"
    bg = "#0f172a" if is_dark else "#f8fafc"
    card_bg = "#1e293b" if is_dark else "#ffffff"
    card_border = "#334155" if is_dark else "#f0f0f0"
    sub_header_color = "#94a3b8" if is_dark else "#666666"
    muted = "#94a3b8" if is_dark else "#64748b"
    text = "#e2e8f0" if is_dark else "#0f172a"
    card_shadow = "0 4px 20px rgba(0,0,0,0.25)" if is_dark else "0 4px 20px rgba(0,0,0,0.08)"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {bg};
            color: {text};
        }}

        .main-header {{
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
            margin-bottom: 0.25rem;
        }}

        .sub-header {{
            text-align: center;
            color: {sub_header_color};
            font-size: 1.2rem;
            margin-bottom: 2rem;
        }}

        .card {{
            background: {card_bg};
            padding: 2rem;
            border-radius: 16px;
            box-shadow: {card_shadow};
            border: 1px solid {card_border};
            margin-bottom: 1rem;
        }}

        .card-compact {{
            background: {card_bg};
            padding: 1rem 1.25rem;
            border-radius: 16px;
            box-shadow: {card_shadow};
            border: 1px solid {card_border};
            margin-bottom: 0.75rem;
        }}

        .status-green {{ color: #00b894; font-weight: 600; }}
        .status-yellow {{ color: #fdcb6e; font-weight: 600; }}
        .status-red {{ color: #e17055; font-weight: 600; }}

        .rs-status-running {{ color: #f59e0b; font-weight: 600; }}
        .rs-status-done {{ color: #00b894; font-weight: 600; }}
        .rs-status-error {{ color: #e17055; font-weight: 600; }}
        .rs-status-cancelled {{ color: {muted}; font-weight: 600; }}

        .rs-match-value {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .rs-muted {{ color: {muted}; font-size: 0.9rem; }}

        .match-row {{
            padding: 0.75rem 0;
            border-bottom: 1px solid {card_border};
        }}

        .match-row:last-child {{
            border-bottom: none;
        }}

        .match-requirement {{
            font-weight: 600;
            margin-bottom: 0.35rem;
        }}

        .match-detail {{
            color: {sub_header_color};
            font-size: 0.9rem;
            margin: 0.15rem 0;
        }}

        .pipeline-card {{
            padding: 1.5rem 2rem;
        }}

        .pipeline-title {{
            font-size: 1.15rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }}

        .pipeline-steps {{
            margin-bottom: 1rem;
        }}

        .pipeline-step {{
            padding: 0.35rem 0 0.35rem 1.25rem;
            font-size: 0.95rem;
            line-height: 1.5;
        }}

        .pipeline-bar {{
            font-family: "SF Mono", "Menlo", "Consolas", monospace;
            font-size: 0.95rem;
            letter-spacing: 0.02em;
            color: {text};
            padding-top: 0.5rem;
        }}

        @media (max-width: 768px) {{
            .main-header {{ font-size: 2rem; }}
            .sub-header {{ font-size: 1rem; }}
            .card {{ padding: 1.25rem; }}
            .rs-match-value {{ font-size: 2rem; }}
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: {card_bg};
            padding: 1.25rem 1.5rem;
            border-radius: 16px;
            box-shadow: {card_shadow};
            border: 1px solid {card_border} !important;
            margin-bottom: 1rem;
        }}

        section[data-testid="stSidebar"] {{
            background: {card_bg};
        }}

        section[data-testid="stSidebar"] * {{
            color: {text};
        }}

        .stTextArea textarea, .stTextInput input {{
            background: {"#0f172a" if is_dark else "#ffffff"} !important;
            color: {text} !important;
        }}

        div[data-baseweb="tab-list"] button {{
            color: {text};
        }}

        .wow-hero {{
            display: grid;
            grid-template-columns: 1fr auto auto;
            gap: 1.5rem;
            align-items: center;
            background: linear-gradient(135deg, rgba(102,126,234,0.12), rgba(118,75,162,0.12));
            border: 1px solid {card_border};
            border-radius: 20px;
            padding: 1.5rem 2rem;
            margin: 1rem 0 1.5rem;
            box-shadow: {card_shadow};
        }}

        .wow-hero-left {{
            display: flex;
            gap: 1rem;
            align-items: flex-start;
        }}

        .wow-badge {{
            font-size: 2.5rem;
            line-height: 1;
        }}

        .wow-level {{
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.25rem;
        }}

        .wow-headline {{
            font-size: 1.35rem;
            font-weight: 700;
            color: {text};
            margin-bottom: 0.35rem;
        }}

        .wow-subline, .wow-checklist {{
            color: {sub_header_color};
            font-size: 0.95rem;
            line-height: 1.45;
        }}

        .wow-ring-wrap {{
            position: relative;
            width: 110px;
            height: 110px;
            flex-shrink: 0;
        }}

        .wow-ring {{
            width: 110px;
            height: 110px;
            transform: rotate(-90deg);
        }}

        .wow-ring-bg {{
            fill: none;
            stroke: {card_border};
            stroke-width: 10;
        }}

        .wow-ring-fg {{
            fill: none;
            stroke-width: 10;
            stroke-linecap: round;
            transition: stroke-dasharray 0.6s ease;
        }}

        .wow-ring-label {{
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 800;
            color: {text};
        }}

        .wow-xp {{
            min-width: 120px;
        }}

        .wow-xp-title {{
            font-size: 0.8rem;
            font-weight: 600;
            color: {muted};
            margin-bottom: 0.35rem;
        }}

        .wow-xp-bar {{
            height: 8px;
            background: {card_border};
            border-radius: 999px;
            overflow: hidden;
        }}

        .wow-xp-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 999px;
        }}

        .wow-market-card {{
            background: {card_bg};
            border: 1px solid {card_border};
            border-radius: 14px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
        }}

        .wow-market-title {{
            font-weight: 700;
            font-size: 1.05rem;
            color: {text};
        }}

        .wow-market-sub {{
            color: {muted};
            font-size: 0.85rem;
            margin-top: 0.25rem;
        }}

        @media (max-width: 900px) {{
            .wow-hero {{
                grid-template-columns: 1fr;
            }}
            .wow-ring-wrap {{
                margin: 0 auto;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
