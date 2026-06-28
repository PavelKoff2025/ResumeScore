"""Валидаторы входных данных и ответов LLM."""

from __future__ import annotations

import json
import re
from typing import Any

from core.config import MIN_TEXT_LENGTH
from core.schemas import AnalysisResult, InputValidation
from utils.logger import setup_logger

logger = setup_logger("validators")


class InputValidator:
    """Проверяет корректность текста вакансии и резюме."""

    def validate(self, vacancy: str, resume: str) -> InputValidation:
        """
        Валидирует входные тексты.

        Args:
            vacancy: Текст вакансии.
            resume: Текст резюме.

        Returns:
            InputValidation с флагом is_valid и сообщением об ошибке.
        """
        vacancy = (vacancy or "").strip()
        resume = (resume or "").strip()

        if not vacancy or not resume:
            return InputValidation(is_valid=False, error="Введите оба текста: вакансию и резюме")

        if len(vacancy) < MIN_TEXT_LENGTH:
            return InputValidation(
                is_valid=False,
                error=f"Текст вакансии слишком короткий (минимум {MIN_TEXT_LENGTH} символов)",
            )

        if len(resume) < MIN_TEXT_LENGTH:
            return InputValidation(
                is_valid=False,
                error=f"Текст резюме слишком короткий (минимум {MIN_TEXT_LENGTH} символов)",
            )

        return InputValidation(is_valid=True)


class ResponseValidator:
    """Проверяет и нормализует JSON-ответ от LLM."""

    def validate(self, json_data: dict[str, Any]) -> dict[str, Any]:
        """
        Валидирует структуру ответа через Pydantic.

        Args:
            json_data: Словарь с результатом анализа.

        Returns:
            Валидированный словарь.

        Raises:
            ValueError: Если структура ответа некорректна.
        """
        try:
            result = AnalysisResult.model_validate(json_data)
            logger.info(
                "Ответ валиден: match=%s%%",
                result.summary.match_percentage,
            )
            return result.model_dump(mode="json")
        except Exception as exc:
            logger.error("Ошибка валидации ответа LLM: %s", exc)
            raise ValueError(f"Некорректный ответ модели: {exc}") from exc

    def validate_response(self, json_data: dict[str, Any]) -> dict[str, Any]:
        """Алиас для совместимости с API Backend-агента."""
        return self.validate(json_data)

    @staticmethod
    def extract_json_from_text(text: str) -> dict[str, Any]:
        """
        Извлекает JSON из текста ответа LLM.

        Args:
            text: Сырой текст ответа.

        Returns:
            Распарсенный словарь.

        Raises:
            ValueError: Если JSON не найден или невалиден.
        """
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not match:
                raise ValueError("В ответе модели не найден JSON") from None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise ValueError("Не удалось распарсить JSON из ответа модели") from exc
