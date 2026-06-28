"""Pydantic-схемы для валидации данных ResumeScore."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MatchStatus(str, Enum):
    """Статус соответствия требования вакансии."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class MatchingItem(BaseModel):
    """Одно требование вакансии и его соответствие резюме."""

    requirement: str = Field(..., min_length=1)
    status: MatchStatus
    evidence: str = Field(..., min_length=1)
    recommendation: str = Field(..., min_length=1)


class AnalysisSummary(BaseModel):
    """Сводка по результатам анализа."""

    green_count: int = Field(..., ge=0)
    yellow_count: int = Field(..., ge=0)
    red_count: int = Field(..., ge=0)
    match_percentage: int = Field(..., ge=0, le=100)


class AnalysisResult(BaseModel):
    """Полный результат анализа резюме и вакансии."""

    matching: list[MatchingItem] = Field(..., min_length=1)
    summary: AnalysisSummary
    top_3_actions: list[str] = Field(..., min_length=3, max_length=3)
    meta: dict | None = None

    def to_dict(self) -> dict:
        """Сериализация в словарь для JSON."""
        return self.model_dump(mode="json")


class AnalysisHistoryItem(BaseModel):
    """Запись в истории анализов."""

    id: str
    timestamp: datetime
    match_percentage: int
    vacancy_preview: str
    resume_preview: str
    vacancy_title: str = "Вакансия"
    result: AnalysisResult


class AgentStatusItem(BaseModel):
    """Статус одного агента в pipeline."""

    agent: str
    message: str
    state: Literal["pending", "running", "done", "error", "cancelled"] = "pending"


class AnalysisStatus(BaseModel):
    """Текущий статус выполнения анализа."""

    is_running: bool = False
    is_cancelled: bool = False
    current_step: str = ""
    agents: list[AgentStatusItem] = Field(default_factory=list)
    last_result: dict | None = None
    error: str | None = None


class InputValidation(BaseModel):
    """Результат валидации входных данных."""

    is_valid: bool
    error: str | None = None


class LLMUsage(BaseModel):
    """Метрики использования LLM."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""
    provider: str = "openai"

    @field_validator("cost_usd")
    @classmethod
    def round_cost(cls, value: float) -> float:
        """Округление стоимости до 6 знаков."""
        return round(value, 6)
