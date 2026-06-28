"""Загрузка вакансии с hh.ru по ссылке или ID."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from html import unescape
from typing import Any

from utils.http_client import urlopen as http_urlopen
from utils.logger import setup_logger

logger = setup_logger("hh_vacancy_fetch")

# Формат User-Agent обязателен для API hh.ru: App/версия (контакт)
API_USER_AGENT = "ResumeScore/1.0 (resume-score@example.com)"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

HH_VACANCY_ID_RE = re.compile(
    r"(?:https?://)?(?:[a-z0-9-]+\.)?hh\.ru/vacancy/(\d+)",
    re.IGNORECASE,
)
HH_VACANCY_ID_QUERY_RE = re.compile(
    r"(?:vacancyId|vacancy_id)=(\d+)",
    re.IGNORECASE,
)
HTML_TAG_RE = re.compile(r"<[^>]+>")
DESCRIPTION_JSON_RE = re.compile(
    r'"description"\s*:\s*"((?:\\.|[^"\\])*)"',
    re.DOTALL,
)


def extract_vacancy_id(text: str) -> str | None:
    """Извлекает ID вакансии из ссылки hh.ru или из голого числа."""
    raw = text.strip()
    match = HH_VACANCY_ID_RE.search(raw)
    if match:
        return match.group(1)
    query_match = HH_VACANCY_ID_QUERY_RE.search(raw)
    if query_match:
        return query_match.group(1)
    if raw.isdigit():
        return raw
    return None


def is_hh_vacancy_url(text: str) -> bool:
    """Проверяет, является ли вставка ссылкой на вакансию hh.ru."""
    return extract_vacancy_id(text) is not None


def _html_to_text(html: str) -> str:
    text = HTML_TAG_RE.sub("\n", html or "")
    text = unescape(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _format_salary(salary: dict[str, Any] | None) -> str:
    if not salary:
        return ""
    parts: list[str] = []
    if salary.get("from") is not None:
        parts.append(f"от {salary['from']:,}".replace(",", " "))
    if salary.get("to") is not None:
        parts.append(f"до {salary['to']:,}".replace(",", " "))
    currency = salary.get("currency", "RUR")
    symbol = "₽" if currency == "RUR" else currency
    return f"Зарплата: {' '.join(parts)} {symbol}".strip()


def _build_vacancy_text(data: dict[str, Any]) -> tuple[str, str]:
    title = str(data.get("name", "Вакансия"))
    blocks: list[str] = [title]

    employer = data.get("employer", {}).get("name")
    if employer:
        blocks.append(f"Компания: {employer}")

    salary_line = _format_salary(data.get("salary"))
    if salary_line:
        blocks.append(salary_line)

    area = data.get("area", {}).get("name")
    if area:
        blocks.append(f"Город: {area}")

    experience = data.get("experience", {}).get("name")
    if experience:
        blocks.append(f"Опыт: {experience}")

    employment = data.get("employment", {}).get("name")
    schedule = data.get("schedule", {}).get("name")
    if employment or schedule:
        blocks.append(f"Занятость: {employment or '—'}, график: {schedule or '—'}")

    description = data.get("description", "")
    if description:
        blocks.append(_html_to_text(description))

    skills = [skill.get("name", "") for skill in data.get("key_skills", []) if skill.get("name")]
    if skills:
        blocks.append("Ключевые навыки: " + ", ".join(skills))

    full_text = "\n\n".join(blocks)
    return title, full_text


def _fetch_api_json(vacancy_id: str) -> dict[str, Any]:
    url = f"https://api.hh.ru/vacancies/{vacancy_id}"
    request = urllib.request.Request(url, headers={"User-Agent": API_USER_AGENT})
    with http_urlopen(request, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))
    if data.get("errors"):
        raise RuntimeError(f"API hh.ru: {data['errors']}")
    if not data.get("name"):
        raise RuntimeError("API hh.ru вернул пустой ответ")
    return data


def _extract_title_from_page(html: str) -> str:
    match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if not match:
        return "Вакансия"
    title_raw = unescape(match.group(1).strip())
    title = re.sub(r"^Вакансия\s+", "", title_raw, flags=re.IGNORECASE)
    title = re.split(r",\s*работа в компании", title, maxsplit=1)[0].strip()
    title = re.split(r"\s+\(вакансия", title, maxsplit=1)[0].strip()
    title = re.split(r"\s+в\s+[А-Яа-яЁё\-]+$", title, maxsplit=1)[0].strip()
    return title[:120] or "Вакансия"


def _extract_description_from_page(html: str) -> str:
    match = DESCRIPTION_JSON_RE.search(html)
    if not match:
        return ""
    try:
        description_html = json.loads(f'"{match.group(1)}"')
    except json.JSONDecodeError:
        return ""
    return _html_to_text(description_html)


def _fetch_from_page(vacancy_id: str) -> tuple[str, str]:
    """Запасной способ: парсинг публичной страницы вакансии."""
    page_url = f"https://hh.ru/vacancy/{vacancy_id}"
    request = urllib.request.Request(
        page_url,
        headers={
            "User-Agent": BROWSER_USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9",
        },
    )
    try:
        with http_urlopen(request, timeout=15) as response:
            html = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            "Не удалось открыть страницу вакансии на hh.ru — проверьте ссылку и интернет"
        ) from exc

    title = _extract_title_from_page(html)
    description = _extract_description_from_page(html)
    if not description:
        raise ValueError(
            "Не удалось прочитать описание вакансии. "
            "Скопируйте полный текст вакансии со страницы hh.ru вручную."
        )

    full_text = f"{title}\n\n{description}"
    if len(full_text) < 50:
        raise ValueError("Описание вакансии слишком короткое")
    return title, full_text


def fetch_vacancy_from_hh(url_or_id: str) -> tuple[str, str]:
    """
    Загружает вакансию: сначала API hh.ru, при ошибке — страница вакансии.

    Args:
        url_or_id: Ссылка вида https://hh.ru/vacancy/123 или ID.

    Returns:
        Кортеж (название, полный текст вакансии).

    Raises:
        ValueError: Если ссылка некорректна или вакансия не найдена.
        RuntimeError: При ошибке сети.
    """
    vacancy_id = extract_vacancy_id(url_or_id)
    if not vacancy_id:
        raise ValueError(
            "Не удалось распознать ссылку. "
            "Вставьте ссылку вида https://hh.ru/vacancy/12345678"
        )

    try:
        data = _fetch_api_json(vacancy_id)
        title, full_text = _build_vacancy_text(data)
        if len(full_text) >= 50:
            return title, full_text
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ValueError(f"Вакансия {vacancy_id} не найдена на hh.ru") from exc
        logger.warning("API hh.ru HTTP %s, пробую страницу вакансии", exc.code)
    except Exception as exc:
        logger.warning("API hh.ru недоступен (%s), пробую страницу вакансии", exc)

    return _fetch_from_page(vacancy_id)
