"""Парсинг текста вакансии из буфера обмена (HH.ru и похожие сайты)."""

from __future__ import annotations

import re

_FOOTER_MARKERS = (
    "напишите телефон",
    "пользуясь сайтом",
    "соглашаетесь с",
    "политикой конфиденциальности",
    "обработкой персональных данных",
)

_TITLE_SKIP_PREFIXES = (
    "вакансия",
    "компания",
    "зарплата",
    "опыт работы",
    "занятость",
    "график",
)


def parse_hh_clipboard(text: str) -> tuple[str, str]:
    """
    Извлекает название и очищенный текст вакансии из вставки с HH.ru.

    Args:
        text: Сырой текст из буфера обмена.

    Returns:
        Кортеж (название, текст вакансии).
    """
    raw = text.strip()
    if not raw:
        return "", ""

    lines = raw.splitlines()
    body_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if any(marker in lower for marker in _FOOTER_MARKERS):
            break
        if stripped:
            body_lines.append(stripped)

    vacancy_text = "\n".join(body_lines) if body_lines else raw
    title = _extract_title(body_lines or [raw.splitlines()[0].strip()])
    return title, vacancy_text


def _extract_title(lines: list[str]) -> str:
    """Выбирает наиболее подходящую строку как название вакансии."""
    for line in lines[:8]:
        lower = line.lower()
        if any(lower.startswith(prefix) for prefix in _TITLE_SKIP_PREFIXES):
            continue
        if len(line) < 4:
            continue
        if re.match(r"^\d", line):
            continue
        return line[:120]
    return lines[0][:120] if lines else "Вакансия с HH.ru"


def resolve_vacancy_from_paste(text: str) -> tuple[str, str]:
    """
    Разбирает вставку: ссылка hh.ru → загрузка через API, иначе — текст из буфера.

    Args:
        text: Ссылка или скопированный текст вакансии.

    Returns:
        Кортеж (название, текст вакансии).

    Raises:
        ValueError, RuntimeError: при ошибке загрузки или разбора.
    """
    from utils.hh_vacancy_fetch import fetch_vacancy_from_hh, is_hh_vacancy_url

    raw = text.strip()
    if not raw:
        return "", ""
    if is_hh_vacancy_url(raw):
        return fetch_vacancy_from_hh(raw)
    return parse_hh_clipboard(raw)
