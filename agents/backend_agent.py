"""Backend-агент: анализ резюме и вакансий через LLM."""

from __future__ import annotations

import json
import time
from typing import Any, Callable

from openai import OpenAI

import core.config as app_config
from core.config import (
    COST_PER_1K_INPUT_TOKENS,
    COST_PER_1K_OUTPUT_TOKENS,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_COST_PER_1K_INPUT,
    DEEPSEEK_COST_PER_1K_OUTPUT,
    DEEPSEEK_MODEL,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    get_provider_label,
    is_demo_mode,
    is_provider_configured,
    resolve_provider,
)
from core.demo_data import DEMO_ANALYSIS_RESULT
from core.prompts import PromptTemplates
from core.schemas import LLMUsage
from utils.document_parser import DocumentParser
from utils.logger import setup_logger
from utils.validators import ResponseValidator

CancelChecker = Callable[[], bool]
StatusCallback = Callable[[str, str, str, int | None], None]


class BackendAgent:
    """Агент анализа: промпты, LLM, парсинг и валидация ответа."""

    def __init__(self) -> None:
        self.prompts = PromptTemplates()
        self.validator = ResponseValidator()
        self.document_parser = DocumentParser()
        self.logger = setup_logger("backend")
        self._last_usage: LLMUsage | None = None
        self._current_provider: str = "auto"

    def analyze(
        self,
        vacancy: str,
        resume: str,
        cancel_checker: CancelChecker | None = None,
        status_callback: StatusCallback | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """
        Отправляет запрос к LLM и возвращает структурированный JSON.

        Args:
            vacancy: Текст вакансии.
            resume: Текст резюме.
            cancel_checker: Функция проверки отмены.
            status_callback: Колбэк (agent, message, state) для UI.
            provider: Выбранный провайдер (auto, openai, deepseek, yandex, demo).

        Returns:
            Валидированный результат анализа.

        Raises:
            RuntimeError: При отмене или ошибке LLM.
        """
        self._current_provider = resolve_provider(provider)
        self._check_cancel(cancel_checker)

        if status_callback:
            status_callback("backend", "формирую промпт для ИИ...", "running", 35)

        if is_demo_mode(provider):
            self.logger.info("Демо-режим: возвращаю тестовый результат")
            if status_callback:
                status_callback(
                    "backend",
                    "отправляю запрос к ИИ (ожидание 5-10 сек)",
                    "running",
                    50,
                )
            time.sleep(0.8)
            self._check_cancel(cancel_checker)
            if status_callback:
                status_callback("backend", "парсинг ответа...", "running", 75)
            time.sleep(0.5)
            self._check_cancel(cancel_checker)
            result = dict(DEMO_ANALYSIS_RESULT)
            if status_callback:
                status_callback("backend", "ответ получен", "done", 90)
            return result

        if not is_provider_configured(self._current_provider):
            label = get_provider_label(self._current_provider)
            raise RuntimeError(
                f"Провайдер {label}: API-ключ не задан в .env. "
                "Выберите другого провайдера или добавьте ключ."
            )

        prompt = self.prompts.get_analysis_prompt(vacancy, resume)
        self.logger.info(
            "Промпт сформирован, провайдер %s, длина %s символов",
            self._current_provider,
            len(prompt),
        )

        if status_callback:
            provider_label = get_provider_label(self._current_provider)
            status_callback(
                "backend",
                f"отправляю запрос к {provider_label} (ожидание 5-10 сек)",
                "running",
                50,
            )

        self._check_cancel(cancel_checker)
        raw_response, usage = self._call_llm(prompt)
        self._last_usage = usage
        self._log_cost(usage)

        if status_callback:
            status_callback("backend", "парсинг ответа...", "running", 75)

        parsed = self._parse_response(raw_response)
        validated = self.validator.validate(parsed)
        validated["meta"] = {
            "demo_mode": False,
            "provider": self._current_provider,
            "model": usage.model,
            "usage": usage.model_dump(),
        }

        if status_callback:
            status_callback("backend", "ответ получен", "done", 90)

        return validated

    def improve_resume(
        self,
        vacancy: str,
        resume: str,
        analysis: dict[str, Any],
        provider: str | None = None,
    ) -> str:
        """
        Улучшает резюме на основе результатов анализа.

        Args:
            vacancy: Текст вакансии.
            resume: Текущее резюме.
            analysis: Результат анализа.
            provider: LLM-провайдер.

        Returns:
            Улучшенный текст резюме.
        """
        from core.demo_data import DEMO_IMPROVED_RESUME

        self._current_provider = resolve_provider(provider)
        weak_points = self._format_weak_points(analysis)
        top_actions = "\n".join(f"- {a}" for a in analysis.get("top_3_actions", []))

        if is_demo_mode(provider):
            self.logger.info("Демо-режим: возвращаю улучшенное резюме")
            time.sleep(1.0)
            return DEMO_IMPROVED_RESUME

        if not is_provider_configured(self._current_provider):
            raise RuntimeError("API-ключ не задан для выбранного провайдера")

        prompt = self.prompts.get_improve_resume_prompt(
            vacancy, resume, weak_points, top_actions
        )
        text, _ = self._call_llm_text(prompt)
        return text.strip()

    def generate_cover_letter(
        self,
        vacancy: str,
        resume: str,
        analysis: dict[str, Any],
        provider: str | None = None,
    ) -> str:
        """
        Генерирует текст сопроводительного письма.

        Args:
            vacancy: Текст вакансии.
            resume: Текст резюме.
            analysis: Результат анализа.
            provider: LLM-провайдер.

        Returns:
            Текст для сопроводительного письма.
        """
        from core.demo_data import DEMO_COVER_LETTER

        self._current_provider = resolve_provider(provider)
        match = analysis.get("summary", {}).get("match_percentage", 0)
        strong_points = self._format_strong_points(analysis)

        if is_demo_mode(provider):
            self.logger.info("Демо-режим: возвращаю текст сопроводительного письма")
            time.sleep(0.8)
            return DEMO_COVER_LETTER

        if not is_provider_configured(self._current_provider):
            raise RuntimeError("API-ключ не задан для выбранного провайдера")

        self.logger.info("Генерация сопроводительного письма, провайдер %s", self._current_provider)
        prompt = self.prompts.get_cover_letter_prompt(vacancy, resume, strong_points, match)
        text, _ = self._call_llm_text(prompt)
        return text.strip()

    def parse_document(self, file_bytes: bytes, file_type: str) -> str:
        """
        Парсит PDF/DOCX/TXT и возвращает текст.

        Args:
            file_bytes: Содержимое файла.
            file_type: Расширение или тип файла.

        Returns:
            Извлечённый текст.
        """
        return self.document_parser.parse(file_bytes, file_type)

    def validate_response(self, json_data: dict[str, Any]) -> dict[str, Any]:
        """Проверяет структуру JSON-ответа."""
        return self.validator.validate(json_data)

    def calculate_cost(self, tokens_used: dict[str, int], model: str = "") -> float:
        """
        Рассчитывает стоимость запроса в USD.

        Args:
            tokens_used: Словарь с prompt_tokens и completion_tokens.
            model: Имя модели (для логов).

        Returns:
            Стоимость в долларах.
        """
        usage = LLMUsage(
            prompt_tokens=tokens_used.get("prompt_tokens", 0),
            completion_tokens=tokens_used.get("completion_tokens", 0),
            total_tokens=tokens_used.get("total_tokens", 0),
            model=model or self._default_model(),
            provider=self._current_provider,
        )
        usage.cost_usd = self._compute_cost(
            usage.prompt_tokens,
            usage.completion_tokens,
            provider=usage.provider,
        )
        return usage.cost_usd

    def get_last_usage(self) -> LLMUsage | None:
        """Возвращает метрики последнего LLM-запроса."""
        return self._last_usage

    def _call_llm(self, prompt: str) -> tuple[str, LLMUsage]:
        """Вызывает провайдера LLM и возвращает текст и метрики."""
        provider = self._current_provider
        if provider == "yandex":
            return self._call_yandex(prompt)
        if provider == "deepseek":
            return self._call_deepseek(prompt)
        return self._call_openai(prompt)

    def _default_model(self) -> str:
        """Возвращает модель для текущего провайдера."""
        if self._current_provider == "deepseek":
            return DEEPSEEK_MODEL
        return OPENAI_MODEL

    def _call_openai_compatible(
        self,
        prompt: str,
        *,
        api_key: str,
        base_url: str | None,
        model: str,
        provider: str,
        json_mode: bool = True,
    ) -> tuple[str, LLMUsage]:
        """Общий метод для OpenAI-совместимых API (OpenAI, DeepSeek)."""
        if not api_key:
            raise RuntimeError(f"API-ключ для {provider} не задан")

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)
        self.logger.info("Запрос к %s, модель %s", provider, model)

        system_content = (
            "Ты эксперт по найму. Отвечай только валидным JSON без markdown и пояснений."
            if json_mode
            else "Ты эксперт по карьере. Отвечай только запрошенным текстом на русском."
        )
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        if json_mode:
            request_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            self.logger.error("Ошибка %s API: %s", provider, exc)
            raise RuntimeError(f"Ошибка {provider} API: {exc}") from exc

        content = response.choices[0].message.content or ""
        usage_data = response.usage
        usage = LLMUsage(
            prompt_tokens=usage_data.prompt_tokens if usage_data else 0,
            completion_tokens=usage_data.completion_tokens if usage_data else 0,
            total_tokens=usage_data.total_tokens if usage_data else 0,
            model=model,
            provider=provider,
        )
        usage.cost_usd = self._compute_cost(
            usage.prompt_tokens,
            usage.completion_tokens,
            provider=provider,
        )
        return content, usage

    def _call_deepseek(self, prompt: str) -> tuple[str, LLMUsage]:
        """Отправляет запрос в DeepSeek API (OpenAI-совместимый, без VPN)."""
        if not app_config.DEEPSEEK_API_KEY:
            raise RuntimeError(
                "DEEPSEEK_API_KEY не задан. Получите ключ на https://platform.deepseek.com"
            )
        return self._call_openai_compatible(
            prompt,
            api_key=app_config.DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            model=DEEPSEEK_MODEL,
            provider="deepseek",
        )

    def _call_openai(self, prompt: str) -> tuple[str, LLMUsage]:
        """Отправляет запрос в OpenAI API."""
        if not app_config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY не задан. Используйте DeepSeek или демо-режим")
        return self._call_openai_compatible(
            prompt,
            api_key=app_config.OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            model=OPENAI_MODEL,
            provider="openai",
        )

    def _call_yandex(self, prompt: str) -> tuple[str, LLMUsage]:
        """Отправляет запрос в YandexGPT через REST API."""
        import urllib.error
        import urllib.request

        if not app_config.YANDEX_API_KEY or not app_config.YANDEX_FOLDER_ID:
            raise RuntimeError("YANDEX_API_KEY и YANDEX_FOLDER_ID обязательны для YandexGPT")

        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        payload = {
            "modelUri": f"gpt://{app_config.YANDEX_FOLDER_ID}/yandexgpt-lite",
            "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": 4000},
            "messages": [
                {
                    "role": "system",
                    "text": "Отвечай только валидным JSON без markdown.",
                },
                {"role": "user", "text": prompt},
            ],
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Api-Key {app_config.YANDEX_API_KEY}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            self.logger.error("Ошибка YandexGPT API: %s", exc)
            raise RuntimeError(f"Ошибка YandexGPT API: {exc}") from exc

        content = body["result"]["alternatives"][0]["message"]["text"]
        usage = LLMUsage(model="yandexgpt-lite", provider="yandex")
        return content, usage

    def _call_llm_text(self, prompt: str) -> tuple[str, LLMUsage]:
        """Вызывает LLM и возвращает произвольный текст (не JSON)."""
        provider = self._current_provider
        if provider == "yandex":
            return self._call_yandex_text(prompt)
        if provider == "deepseek":
            return self._call_openai_compatible(
                prompt,
                api_key=app_config.DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                model=DEEPSEEK_MODEL,
                provider="deepseek",
                json_mode=False,
            )
        return self._call_openai_compatible(
            prompt,
            api_key=app_config.OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            model=OPENAI_MODEL,
            provider="openai",
            json_mode=False,
        )

    def _call_yandex_text(self, prompt: str) -> tuple[str, LLMUsage]:
        """Запрос к YandexGPT с текстовым ответом."""
        import urllib.error
        import urllib.request

        if not app_config.YANDEX_API_KEY or not app_config.YANDEX_FOLDER_ID:
            raise RuntimeError("YANDEX_API_KEY и YANDEX_FOLDER_ID обязательны для YandexGPT")

        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        payload = {
            "modelUri": f"gpt://{app_config.YANDEX_FOLDER_ID}/yandexgpt-lite",
            "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 4000},
            "messages": [
                {"role": "system", "text": "Отвечай только запрошенным текстом на русском."},
                {"role": "user", "text": prompt},
            ],
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Api-Key {app_config.YANDEX_API_KEY}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ошибка YandexGPT API: {exc}") from exc

        content = body["result"]["alternatives"][0]["message"]["text"]
        return content, LLMUsage(model="yandexgpt-lite", provider="yandex")

    @staticmethod
    def _format_weak_points(analysis: dict[str, Any]) -> str:
        """Форматирует слабые места из анализа для промпта."""
        lines = []
        for item in analysis.get("matching", []):
            if item.get("status") in ("yellow", "red"):
                lines.append(
                    f"- {item.get('requirement')}: {item.get('recommendation')}"
                )
        return "\n".join(lines) or "Нет явных слабых мест"

    @staticmethod
    def _format_strong_points(analysis: dict[str, Any]) -> str:
        """Форматирует сильные стороны из анализа."""
        lines = []
        for item in analysis.get("matching", []):
            if item.get("status") == "green":
                lines.append(f"- {item.get('requirement')}: {item.get('evidence')}")
        return "\n".join(lines[:5]) or "Релевантный опыт в профиле кандидата"

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Парсит JSON из ответа LLM."""
        return self.validator.extract_json_from_text(response_text)

    def _log_cost(self, usage: LLMUsage) -> None:
        """Логирует токены и стоимость запроса."""
        self.logger.info(
            "Токены: prompt=%s, completion=%s, total=%s, cost=$%s",
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.total_tokens,
            usage.cost_usd,
        )

    def _compute_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        provider: str | None = None,
    ) -> float:
        """Вычисляет стоимость по количеству токенов."""
        active = provider or self._current_provider
        if active == "deepseek":
            input_rate = DEEPSEEK_COST_PER_1K_INPUT
            output_rate = DEEPSEEK_COST_PER_1K_OUTPUT
        else:
            input_rate = COST_PER_1K_INPUT_TOKENS
            output_rate = COST_PER_1K_OUTPUT_TOKENS
        input_cost = (prompt_tokens / 1000) * input_rate
        output_cost = (completion_tokens / 1000) * output_rate
        return round(input_cost + output_cost, 6)

    @staticmethod
    def _check_cancel(cancel_checker: CancelChecker | None) -> None:
        """Проверяет флаг отмены и прерывает выполнение."""
        if cancel_checker and cancel_checker():
            raise RuntimeError("Анализ отменён пользователем")
