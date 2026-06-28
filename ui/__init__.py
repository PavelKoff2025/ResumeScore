"""UI-компоненты ResumeScore."""

from ui.components import (
    build_pipeline_html,
    build_cover_letter_fallback,
    build_report_text,
    format_ascii_progress,
    render_action_bar,
    render_agent_status,
    render_copy_to_clipboard,
    render_executive_summary,
    render_match_progress,
    render_matching_table,
    render_pipeline_status,
    render_summary_badges,
    render_text_report,
    render_top_actions,
)
from ui.styles import inject_styles

__all__ = [
    "inject_styles",
    "render_agent_status",
    "render_match_progress",
    "render_matching_table",
    "render_summary_badges",
    "render_top_actions",
]
