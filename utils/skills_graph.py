"""Построение данных для карты навыков из результата анализа."""

from __future__ import annotations

import json
import re
from typing import Any

_STATUS_GROUPS = {
    "green": {"color": "#00b894", "label": "Есть"},
    "yellow": {"color": "#f6c23e", "label": "Частично"},
    "red": {"color": "#e17055", "label": "Нет"},
}


def short_skill_label(requirement: str, max_len: int = 42) -> str:
    """Сокращает требование вакансии до короткой подписи узла графа."""
    text = requirement.strip()
    text = re.sub(r"^(опыт|навыки?|знание|умение|владение)\s+", "", text, flags=re.I)
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


def build_skills_graph(matching: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Формирует узлы и рёбра для интерактивного графа навыков.

    Центральный узел «Вы» связан с каждым требованием вакансии.
    """
    nodes: list[dict[str, Any]] = [
        {
            "id": "you",
            "label": "Вы",
            "group": "center",
            "title": "Ваш профиль",
            "shape": "dot",
            "size": 28,
        }
    ]
    edges: list[dict[str, str]] = []

    for idx, item in enumerate(matching):
        status = item.get("status", "red")
        if status not in _STATUS_GROUPS:
            status = "red"
        node_id = f"skill_{idx}"
        label = short_skill_label(str(item.get("requirement", f"Навык {idx + 1}")))
        nodes.append(
            {
                "id": node_id,
                "label": label,
                "group": status,
                "title": str(item.get("requirement", "")),
                "shape": "dot",
                "size": 18 if status == "green" else 16,
            }
        )
        edges.append({"from": "you", "to": node_id})

    return {"nodes": nodes, "edges": edges}


def skills_graph_summary(matching: list[dict[str, Any]]) -> dict[str, int]:
    """Сводка по статусам для легенды карты."""
    counts = {"green": 0, "yellow": 0, "red": 0}
    for item in matching:
        status = item.get("status", "red")
        if status in counts:
            counts[status] += 1
    return counts


def graph_to_json(graph: dict[str, Any]) -> str:
    """Сериализует граф для передачи в HTML-компонент."""
    return json.dumps(graph, ensure_ascii=False)
