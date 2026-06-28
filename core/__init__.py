"""Ядро приложения ResumeScore."""

from core.config import (
    get_active_provider,
    get_provider_label,
    is_demo_mode,
    resolve_provider,
)
from core.schemas import AnalysisResult, AnalysisStatus

__all__ = [
    "AnalysisResult",
    "AnalysisStatus",
    "get_active_provider",
    "get_provider_label",
    "is_demo_mode",
    "resolve_provider",
]
