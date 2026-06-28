"""Тесты WOW-функций: карта навыков, геймификация, рынок, QR."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from core.demo_data import DEMO_ANALYSIS_RESULT
from utils.gamification import build_gamification_message, estimate_days_to_ready, get_level
from utils.hh_salary import (
    extract_search_query,
    fetch_market_salary,
    format_salary,
)
from utils.skills_graph import build_skills_graph, short_skill_label


class TestSkillsGraph:
    def test_build_graph_nodes(self) -> None:
        graph = build_skills_graph(DEMO_ANALYSIS_RESULT["matching"])
        assert graph["nodes"][0]["id"] == "you"
        assert len(graph["nodes"]) == len(DEMO_ANALYSIS_RESULT["matching"]) + 1
        assert len(graph["edges"]) == len(DEMO_ANALYSIS_RESULT["matching"])

    def test_short_label(self) -> None:
        label = short_skill_label(
            "Базовые навыки программирования на Python или JavaScript/TypeScript"
        )
        assert len(label) <= 43


class TestGamification:
    def test_level_tiers(self) -> None:
        assert get_level(85)["badge"] == "⭐"
        assert get_level(40)["badge"] == "🌱"

    def test_message_contains_percent(self) -> None:
        msg = build_gamification_message(73, DEMO_ANALYSIS_RESULT["summary"])
        assert msg["match_percentage"] == 73
        assert "73" in msg["headline"]
        assert msg["remaining"] == 27

    def test_days_estimate(self) -> None:
        assert estimate_days_to_ready(0, 0) == 0
        assert estimate_days_to_ready(2, 1) == 2


class TestHhSalary:
    def test_extract_query(self) -> None:
        assert extract_search_query("Python Dev", "") == "Python Dev"

    def test_format_salary(self) -> None:
        assert "₽" in format_salary(150000)

    def test_fetch_with_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "found": 50,
                "items": [
                    {"salary": {"from": 100000, "to": 150000, "currency": "RUR"}},
                    {"salary": {"from": 120000, "to": 180000, "currency": "RUR"}},
                ],
            }
        ).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr(
            "utils.hh_salary.urllib.request.urlopen",
            lambda *a, **k: mock_response,
        )
        result = fetch_market_salary("python", use_demo_fallback=False)
        assert result["salary_count"] == 2
        assert result["median"] == 150000


class TestQrCode:
    def test_qr_generation(self) -> None:
        qrcode = pytest.importorskip("qrcode")
        import io

        qr = qrcode.QRCode(version=1, box_size=4, border=1)
        qr.add_data("http://localhost:8501?share=abc")
        qr.make(fit=True)
        img = qr.make_image()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        assert len(buf.getvalue()) > 100
