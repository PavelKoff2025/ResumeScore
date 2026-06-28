"""Настройки приложения ResumeScore."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _apply_streamlit_secrets() -> None:
    """Подгружает ключи из Streamlit Cloud Secrets (share.streamlit.io)."""
    try:
        import streamlit as st

        for key, value in st.secrets.items():
            if isinstance(value, str) and value.strip():
                os.environ.setdefault(key, value)
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    env_key = str(sub_key).upper()
                    if str(sub_value).strip():
                        os.environ.setdefault(env_key, str(sub_value))
    except Exception:
        pass


_apply_streamlit_secrets()

LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
SHARES_DIR = BASE_DIR / "storage" / "shares"

APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8501")

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL: str | None = os.getenv("OPENAI_BASE_URL") or None

# DeepSeek — OpenAI-совместимый API, работает без VPN
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
YANDEX_API_KEY: str = os.getenv("YANDEX_API_KEY", "")
YANDEX_FOLDER_ID: str = os.getenv("YANDEX_FOLDER_ID", "")

MAX_HISTORY_ITEMS: int = int(os.getenv("MAX_HISTORY_ITEMS", "20"))
MIN_TEXT_LENGTH: int = int(os.getenv("MIN_TEXT_LENGTH", "50"))

# Стоимость за 1000 токенов (USD)
COST_PER_1K_INPUT_TOKENS: float = float(os.getenv("COST_PER_1K_INPUT_TOKENS", "0.00015"))
COST_PER_1K_OUTPUT_TOKENS: float = float(os.getenv("COST_PER_1K_OUTPUT_TOKENS", "0.0006"))
DEEPSEEK_COST_PER_1K_INPUT: float = float(os.getenv("DEEPSEEK_COST_PER_1K_INPUT", "0.00027"))
DEEPSEEK_COST_PER_1K_OUTPUT: float = float(os.getenv("DEEPSEEK_COST_PER_1K_OUTPUT", "0.0011"))

PROVIDER_LABELS: dict[str, str] = {
    "auto": "Авто",
    "openai": "OpenAI",
    "deepseek": "DeepSeek",
    "yandex": "YandexGPT",
    "demo": "Демо",
}

PROVIDER_CHOICES: list[str] = ["auto", "openai", "deepseek", "yandex", "demo"]

PROVIDER_UI_LABELS: dict[str, str] = {
    "auto": "🔄 Авто (лучший доступный)",
    "openai": "OpenAI (GPT)",
    "deepseek": "DeepSeek (без VPN)",
    "yandex": "YandexGPT",
    "demo": "🎭 Демо (тестовые данные)",
}

DEMO_VACANCY_PATH = Path(
    os.getenv("DEMO_VACANCY_PATH", str(BASE_DIR / "data" / "demo_vacancy.docx"))
)
DEMO_RESUME_PATH = Path(
    os.getenv("DEMO_RESUME_PATH", str(BASE_DIR / "data" / "demo_resume.pdf"))
)


def refresh_settings() -> None:
    """Перечитывает .env и Streamlit Secrets (вызывается при старте приложения)."""
    global OPENAI_API_KEY, DEEPSEEK_API_KEY, YANDEX_API_KEY, YANDEX_FOLDER_ID
    global LLM_PROVIDER, APP_BASE_URL

    load_dotenv(BASE_DIR / ".env", override=True)
    _apply_streamlit_secrets()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
    YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8501")


def is_provider_configured(provider: str) -> bool:
    """Проверяет, настроен ли API-ключ для провайдера."""
    if provider == "demo":
        return True
    if provider == "openai":
        return bool(OPENAI_API_KEY.strip())
    if provider == "deepseek":
        return bool(DEEPSEEK_API_KEY.strip())
    if provider == "yandex":
        return bool(YANDEX_API_KEY.strip() and YANDEX_FOLDER_ID.strip())
    return False


def get_active_provider() -> str:
    """
    Определяет фактического LLM-провайдера с учётом доступных API-ключей.

    Если OpenAI недоступен (нет ключа или VPN), автоматически переключается
    на DeepSeek при наличии DEEPSEEK_API_KEY.
    """
    provider = LLM_PROVIDER.strip().lower()

    if provider == "deepseek":
        if DEEPSEEK_API_KEY.strip():
            return "deepseek"
        if OPENAI_API_KEY.strip():
            return "openai"
        return "deepseek"

    if provider == "yandex":
        if YANDEX_API_KEY.strip() and YANDEX_FOLDER_ID.strip():
            return "yandex"
        if DEEPSEEK_API_KEY.strip():
            return "deepseek"
        if OPENAI_API_KEY.strip():
            return "openai"
        return "yandex"

    # openai (по умолчанию) → fallback на DeepSeek без VPN
    if OPENAI_API_KEY.strip():
        return "openai"
    if DEEPSEEK_API_KEY.strip():
        return "deepseek"
    if YANDEX_API_KEY.strip() and YANDEX_FOLDER_ID.strip():
        return "yandex"
    return "openai"


def resolve_provider(preferred: str | None = None) -> str:
    """
    Определяет провайдера с учётом выбора пользователя в UI.

    Args:
        preferred: Выбор из UI (auto, openai, deepseek, yandex, demo).

    Returns:
        Итоговый идентификатор провайдера.
    """
    choice = (preferred or "auto").strip().lower()
    if choice == "auto":
        return get_active_provider()
    if choice in PROVIDER_CHOICES:
        return choice
    return get_active_provider()


def is_demo_mode(provider: str | None = None) -> bool:
    """Возвращает True, если анализ пойдёт в демо-режиме."""
    choice = (provider or "auto").strip().lower()
    if choice == "demo":
        return True
    if choice == "auto":
        resolved = get_active_provider()
        return not is_provider_configured(resolved)
    return False


def get_provider_label(provider: str | None = None) -> str:
    """Возвращает человекочитаемое название провайдера."""
    return PROVIDER_LABELS.get(resolve_provider(provider), resolve_provider(provider))


def get_providers_status() -> dict[str, bool]:
    """Возвращает статус настройки каждого провайдера для UI."""
    return {
        "openai": is_provider_configured("openai"),
        "deepseek": is_provider_configured("deepseek"),
        "yandex": is_provider_configured("yandex"),
    }
