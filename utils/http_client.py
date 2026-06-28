"""HTTP-запросы с корректной проверкой SSL (macOS / Python)."""

from __future__ import annotations

import ssl
import urllib.request

import certifi


def urlopen(request: urllib.request.Request, timeout: float = 12):
    """
    Открывает URL с корневыми сертификатами certifi.

    На macOS стандартный urllib часто падает с CERTIFICATE_VERIFY_FAILED.
    """
    context = ssl.create_default_context(cafile=certifi.where())
    return urllib.request.urlopen(request, timeout=timeout, context=context)
