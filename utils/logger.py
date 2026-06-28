"""Настройка логирования для агентов ResumeScore."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core.config import LOGS_DIR


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Создаёт логгер с записью в файл logs/{name}.log.

    Args:
        name: Имя логгера и файла (orchestrator, backend, frontend).
        level: Уровень логирования.

    Returns:
        Настроенный экземпляр logging.Logger.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(f"resumescore.{name}")
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOGS_DIR / f"{name}.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
