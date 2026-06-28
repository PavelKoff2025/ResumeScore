"""Парсинг PDF и DOCX документов."""

from __future__ import annotations

import io
from typing import Literal

from docx import Document
from pypdf import PdfReader

from utils.logger import setup_logger

FileType = Literal["pdf", "docx", "txt"]
logger = setup_logger("document_parser")


class DocumentParser:
    """Извлекает текст из загруженных файлов."""

    SUPPORTED_TYPES = {"pdf", "docx", "txt"}

    def parse(self, file_bytes: bytes, file_type: str) -> str:
        """
        Парсит документ и возвращает извлечённый текст.

        Args:
            file_bytes: Содержимое файла в байтах.
            file_type: Тип файла (pdf, docx, txt).

        Returns:
            Извлечённый текст.

        Raises:
            ValueError: Если тип файла не поддерживается или текст пуст.
        """
        normalized = file_type.lower().lstrip(".")
        if normalized not in self.SUPPORTED_TYPES:
            raise ValueError(f"Неподдерживаемый формат: {file_type}. Допустимо: PDF, DOCX, TXT")

        logger.info("Парсинг документа типа %s, размер %s байт", normalized, len(file_bytes))

        if normalized == "pdf":
            text = self._parse_pdf(file_bytes)
        elif normalized == "docx":
            text = self._parse_docx(file_bytes)
        else:
            text = self._parse_txt(file_bytes)

        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Не удалось извлечь текст из файла")

        logger.info("Извлечено %s символов", len(cleaned))
        return cleaned

    def parse_document(self, file_bytes: bytes, file_type: str) -> str:
        """Алиас для совместимости с API Backend-агента."""
        return self.parse(file_bytes, file_type)

    def _parse_pdf(self, file_bytes: bytes) -> str:
        """Извлекает текст из PDF."""
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    def _parse_docx(self, file_bytes: bytes) -> str:
        """Извлекает текст из DOCX."""
        document = Document(io.BytesIO(file_bytes))
        paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
        return "\n".join(paragraphs)

    def _parse_txt(self, file_bytes: bytes) -> str:
        """Декодирует текстовый файл."""
        for encoding in ("utf-8", "cp1251", "latin-1"):
            try:
                return file_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("Не удалось декодировать текстовый файл")
