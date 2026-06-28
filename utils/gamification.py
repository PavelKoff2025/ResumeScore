"""Геймификация прогресса подготовки к отклику."""

from __future__ import annotations

from typing import Any


def estimate_days_to_ready(red_count: int, yellow_count: int) -> int:
    """Оценивает дней до «готовности» по числу пробелов."""
    gaps = red_count + yellow_count
    if gaps <= 0:
        return 0
    if gaps == 1:
        return 1
    if gaps <= 3:
        return 2
    if gaps <= 5:
        return 3
    return min(7, gaps)


def get_level(match_percentage: int) -> dict[str, str]:
    """Возвращает уровень кандидата и бейдж."""
    if match_percentage >= 90:
        return {"title": "Легенда рынка", "badge": "🏆", "color": "#8b5cf6"}
    if match_percentage >= 80:
        return {"title": "Топ-кандидат", "badge": "⭐", "color": "#00b894"}
    if match_percentage >= 65:
        return {"title": "Сильный претендент", "badge": "🚀", "color": "#667eea"}
    if match_percentage >= 50:
        return {"title": "В процессе роста", "badge": "📈", "color": "#f6c23e"}
    return {"title": "Старт карьеры", "badge": "🌱", "color": "#e17055"}


def build_gamification_message(
    match_percentage: int,
    summary: dict[str, Any],
    checklist_done: int = 0,
    checklist_total: int = 0,
) -> dict[str, Any]:
    """
    Собирает данные для WOW-баннера геймификации.

    Returns:
        Словарь с процентами, уровнем, текстом мотивации и XP.
    """
    remaining = max(0, 100 - match_percentage)
    red = int(summary.get("red_count", 0))
    yellow = int(summary.get("yellow_count", 0))
    days = estimate_days_to_ready(red, yellow)
    level = get_level(match_percentage)

    if remaining == 0:
        headline = "Вы на 100% готовы к отклику!"
        subline = "Можно отправлять резюме прямо сейчас 🎉"
    elif days <= 1:
        subline = f"Осталось {remaining}% — закройте пару пунктов чек-листа сегодня"
        headline = f"Вы на {match_percentage}% готовы"
    else:
        day_word = "день" if days == 1 else "дня" if days < 5 else "дней"
        subline = f"Осталось {remaining}% — сделайте это за {days} {day_word}"
        headline = f"Вы на {match_percentage}% готовы"

    checklist_hint = ""
    if checklist_total > 0:
        left = checklist_total - checklist_done
        if left > 0:
            checklist_hint = f"В чек-листе ещё {left} из {checklist_total} рекомендаций"

    xp = match_percentage * 10 + checklist_done * 25
    next_level_xp = ((match_percentage // 10) + 1) * 1000
    xp_progress = min(100, int((xp % 1000) / 10))

    return {
        "match_percentage": match_percentage,
        "remaining": remaining,
        "days": days,
        "level": level,
        "headline": headline,
        "subline": subline,
        "checklist_hint": checklist_hint,
        "xp": xp,
        "xp_progress": xp_progress,
        "next_level_xp": next_level_xp,
    }
