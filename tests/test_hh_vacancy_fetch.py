"""Тесты загрузки вакансии с hh.ru по ссылке."""

from __future__ import annotations

import json

import pytest

from utils.hh_parser import resolve_vacancy_from_paste
from utils.hh_vacancy_fetch import (
    _fetch_from_page,
    extract_vacancy_id,
    fetch_vacancy_from_hh,
    is_hh_vacancy_url,
)


class TestHhVacancyFetch:
    def test_extract_id_from_url(self) -> None:
        url = "https://hh.ru/vacancy/12345678?hhtmFrom=main"
        assert extract_vacancy_id(url) == "12345678"
        assert is_hh_vacancy_url(url) is True

    def test_extract_id_from_regional_url(self) -> None:
        url = "https://spb.hh.ru/vacancy/87654321"
        assert extract_vacancy_id(url) == "87654321"

    def test_is_not_url(self) -> None:
        assert is_hh_vacancy_url("Python developer") is False

    def test_fetch_vacancy_api_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = {
            "name": "Python Developer",
            "employer": {"name": "Test Co"},
            "description": "<p>Нужен Python и Django для backend</p>",
            "key_skills": [{"name": "Python"}],
            "experience": {"name": "1–3 года"},
            "area": {"name": "Москва"},
        }

        class FakeResponse:
            def read(self) -> bytes:
                return json.dumps(payload).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        monkeypatch.setattr(
            "utils.hh_vacancy_fetch.http_urlopen",
            lambda *a, **k: FakeResponse(),
        )
        title, text = fetch_vacancy_from_hh("https://hh.ru/vacancy/999")
        assert title == "Python Developer"
        assert "Python" in text
        assert len(text) >= 50

    def test_fetch_fallback_to_page(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_urlopen(request, timeout=0):
            url = request.full_url
            if "api.hh.ru" in url:
                raise urllib.error.HTTPError(url, 403, "forbidden", None, None)

            html = (
                "<title>Вакансия Data Scientist в Москве, работа в компании X</title>"
                '"description":"\\u003cp\\u003eАнализ данных и ML модели для продукта\\u003c/p\\u003e"'
            )
            return type(
                "R",
                (),
                {
                    "read": lambda self: html.encode(),
                    "__enter__": lambda self: self,
                    "__exit__": lambda self, *a: False,
                },
            )()

        import urllib.error

        monkeypatch.setattr("utils.hh_vacancy_fetch.http_urlopen", fake_urlopen)
        title, text = fetch_vacancy_from_hh("https://hh.ru/vacancy/555")
        assert "Data Scientist" in title
        assert "Анализ данных" in text

    def test_resolve_url_uses_api(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "utils.hh_vacancy_fetch.fetch_vacancy_from_hh",
            lambda _: ("Title", "A" * 60),
        )
        title, text = resolve_vacancy_from_paste("https://hh.ru/vacancy/1")
        assert title == "Title"
        assert len(text) == 60
