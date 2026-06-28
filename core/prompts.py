"""Шаблоны промптов для LLM."""

from __future__ import annotations

ANALYSIS_PROMPT = """
Ты — эксперт по найму и карьерному консультированию. Сопоставь вакансию и резюме.

Вакансия:
{vacancy}

Резюме:
{resume}

Выполни анализ строго в формате JSON без лишнего текста:

{{
  "matching": [
    {{
      "requirement": "Требование из вакансии (скопировать дословно)",
      "status": "green" | "yellow" | "red",
      "evidence": "Что есть в резюме (цитата или 'нет упоминания')",
      "recommendation": "Конкретное действие на 1-2 дня"
    }}
  ],
  "summary": {{
    "green_count": число,
    "yellow_count": число,
    "red_count": число,
    "match_percentage": число (0-100)
  }},
  "top_3_actions": ["Действие 1", "Действие 2", "Действие 3"]
}}
"""


IMPROVE_RESUME_PROMPT = """
Ты — эксперт по карьерному консультированию и написанию резюме.
Улучши резюме кандидата под конкретную вакансию.

Вакансия:
{vacancy}

Текущее резюме:
{resume}

Слабые места из анализа (yellow/red):
{weak_points}

Топ-рекомендации:
{top_actions}

Верни только улучшенный текст резюме на русском языке.
Без комментариев, пояснений и markdown-разметки.
Сохрани логичную структуру резюме. Усиль формулировки и добавь недостающие компетенции.
"""


COVER_LETTER_PROMPT = """
Ты — карьерный консультант. Напиши сопроводительное письмо (5–7 предложений) на русском.

Вакансия:
{vacancy}

Резюме кандидата:
{resume}

Ключевые сильные стороны из анализа:
{strong_points}

Процент совпадения: {match_percentage}%

Верни только текст письма: без темы, без «Уважаемые», подписи оставь как [Ваше имя].
"""


class PromptTemplates:
    """Класс для формирования промптов к LLM."""

    def get_analysis_prompt(self, vacancy: str, resume: str) -> str:
        """
        Формирует промпт для сопоставления вакансии и резюме.

        Args:
            vacancy: Текст вакансии.
            resume: Текст резюме.

        Returns:
            Готовый промпт для отправки в LLM.
        """
        return ANALYSIS_PROMPT.format(vacancy=vacancy.strip(), resume=resume.strip())

    def get_improve_resume_prompt(
        self,
        vacancy: str,
        resume: str,
        weak_points: str,
        top_actions: str,
    ) -> str:
        """Формирует промпт для улучшения резюме."""
        return IMPROVE_RESUME_PROMPT.format(
            vacancy=vacancy.strip(),
            resume=resume.strip(),
            weak_points=weak_points.strip(),
            top_actions=top_actions.strip(),
        )

    def get_cover_letter_prompt(
        self,
        vacancy: str,
        resume: str,
        strong_points: str,
        match_percentage: int,
    ) -> str:
        """Формирует промпт для сопроводительного письма."""
        return COVER_LETTER_PROMPT.format(
            vacancy=vacancy.strip(),
            resume=resume.strip(),
            strong_points=strong_points.strip(),
            match_percentage=match_percentage,
        )
