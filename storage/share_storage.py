"""Сохранение и загрузка результатов для шаринга по ссылке."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import BASE_DIR

SHARES_DIR = BASE_DIR / "storage" / "shares"


def create_share(
    result: dict[str, Any],
    vacancy_preview: str = "",
    resume_preview: str = "",
) -> str:
    """
    Сохраняет результат анализа и возвращает ID для ссылки.

    Args:
        result: Результат анализа.
        vacancy_preview: Краткое описание вакансии.
        resume_preview: Краткое описание резюме.

    Returns:
        Уникальный идентификатор share.
    """
    SHARES_DIR.mkdir(parents=True, exist_ok=True)
    share_id = uuid.uuid4().hex[:12]
    payload = {
        "id": share_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "vacancy_preview": vacancy_preview[:200],
        "resume_preview": resume_preview[:200],
        "result": result,
    }
    path = SHARES_DIR / f"{share_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return share_id


def load_share(share_id: str) -> dict[str, Any] | None:
    """
    Загружает результат по ID ссылки.

    Args:
        share_id: Идентификатор share.

    Returns:
        Словарь с данными или None.
    """
    if not share_id or not share_id.isalnum():
        return None
    path = SHARES_DIR / f"{share_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
