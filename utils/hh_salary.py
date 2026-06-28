"""Сравнение с рынком: средняя зарплата по данным API hh.ru."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from utils.http_client import urlopen as http_urlopen

HH_API = "https://api.hh.ru/vacancies"
USER_AGENT = "ResumeScore/1.0 (portfolio demo; +https://github.com)"

# Запасные данные для демо без сети
DEMO_MARKET_STATS: dict[str, Any] = {
    "query": "промпт-инженер",
    "area_name": "Москва",
    "vacancy_count": 312,
    "salary_count": 148,
    "avg_from": 140_000,
    "avg_to": 210_000,
    "median": 175_000,
    "currency": "RUR",
    "source": "demo",
}


def extract_search_query(vacancy_title: str, vacancy_text: str = "") -> str:
    """Формирует поисковый запрос для HH из названия и текста вакансии."""
    title = vacancy_title.strip()
    if title and title != "Вакансия":
        return title[:80]

    for line in vacancy_text.splitlines():
        line = line.strip()
        if len(line) < 5:
            continue
        lower = line.lower()
        if any(lower.startswith(p) for p in ("компания", "зарплата", "опыт", "график")):
            continue
        return line[:80]
    return "специалист"


def _parse_salary(salary: dict[str, Any] | None) -> tuple[int | None, int | None, str]:
    if not salary:
        return None, None, "RUR"
    return salary.get("from"), salary.get("to"), salary.get("currency") or "RUR"


def _midpoint(s_from: int | None, s_to: int | None) -> int | None:
    if s_from is not None and s_to is not None:
        return (s_from + s_to) // 2
    return s_from or s_to


def fetch_market_salary(
    query: str,
    area: int = 1,
    *,
    use_demo_fallback: bool = True,
) -> dict[str, Any]:
    """
    Запрашивает вакансии на HH и считает среднюю зарплату.

    Args:
        query: Поисковый запрос (название вакансии).
        area: ID региона HH (1 — Москва).
        use_demo_fallback: Вернуть демо-данные при ошибке сети.

    Returns:
        Словарь со статистикой рынка.
    """
    params = urllib.parse.urlencode(
        {"text": query, "area": area, "per_page": 100, "page": 0}
    )
    url = f"{HH_API}?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with http_urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        if use_demo_fallback:
            result = dict(DEMO_MARKET_STATS)
            result["query"] = query[:80]
            result["note"] = "Демо-данные (API недоступен)"
            return result
        return {"error": "Не удалось получить данные с hh.ru", "query": query}

    items = payload.get("items", [])
    mids: list[int] = []
    lows: list[int] = []
    highs: list[int] = []
    currency = "RUR"

    for item in items:
        s_from, s_to, currency = _parse_salary(item.get("salary"))
        mid = _midpoint(s_from, s_to)
        if mid is not None:
            mids.append(mid)
        if s_from is not None:
            lows.append(s_from)
        if s_to is not None:
            highs.append(s_to)

    if not mids:
        if use_demo_fallback:
            result = dict(DEMO_MARKET_STATS)
            result["query"] = query[:80]
            result["vacancy_count"] = payload.get("found", 0)
            result["note"] = "Мало вакансий с зарплатой — показаны ориентиры"
            return result
        return {
            "query": query,
            "vacancy_count": payload.get("found", 0),
            "salary_count": 0,
            "error": "В выборке нет зарплат",
        }

    mids.sort()
    median = mids[len(mids) // 2]
    return {
        "query": query[:80],
        "area_name": "Москва" if area == 1 else f"Регион {area}",
        "vacancy_count": payload.get("found", len(items)),
        "salary_count": len(mids),
        "avg_from": int(sum(lows) / len(lows)) if lows else None,
        "avg_to": int(sum(highs) / len(highs)) if highs else None,
        "median": median,
        "currency": currency,
        "source": "hh.ru",
    }


def format_salary(amount: int | None, currency: str = "RUR") -> str:
    """Форматирует сумму зарплаты для UI."""
    if amount is None:
        return "—"
    symbol = "₽" if currency == "RUR" else currency
    return f"{amount:,}".replace(",", " ") + f" {symbol}"


def extract_salary_from_vacancy_text(text: str) -> tuple[int | None, int | None]:
    """Пытается вытащить вилку зарплаты из текста вакансии."""
    patterns = [
        r"(\d[\d\s]{2,})\s*[-–—]\s*(\d[\d\s]{2,})\s*₽",
        r"от\s*(\d[\d\s]{2,})\s*до\s*(\d[\d\s]{2,})",
        r"(\d[\d\s]{2,})\s*руб",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        groups = [int(re.sub(r"\s", "", g)) for g in match.groups()]
        if len(groups) == 1:
            return groups[0], None
        return groups[0], groups[1]
    return None, None
