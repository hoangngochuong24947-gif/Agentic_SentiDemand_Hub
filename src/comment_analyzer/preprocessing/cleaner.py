"""Text cleaning module for comment_analyzer.

Provides utilities for cleaning and normalizing text content
before further processing.
"""

from __future__ import annotations

import html
import re
from typing import Optional


class TextCleaner:
    """Text cleaner for preprocessing comments and reviews."""

    URL_PATTERN = re.compile(
        r"https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?",
        re.IGNORECASE,
    )
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    HTML_PATTERN = re.compile(r"<[^>]+>")
    EXTRA_SPACES_PATTERN = re.compile(r"\s+")

    def __init__(
        self,
        remove_urls: bool = True,
        remove_emails: bool = True,
        remove_html: bool = True,
        remove_extra_spaces: bool = True,
        normalize_whitespace: bool = True,
    ) -> None:
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_html = remove_html
        self.remove_extra_spaces = remove_extra_spaces
        self.normalize_whitespace = normalize_whitespace

    def clean(self, text: Optional[str]) -> str:
        """Clean the input text."""
        if text is None:
            return ""

        text = str(text)

        if self.remove_urls:
            text = self.URL_PATTERN.sub(" ", text)

        if self.remove_emails:
            text = self.EMAIL_PATTERN.sub(" ", text)

        if self.remove_html:
            text = html.unescape(text)
            text = self.HTML_PATTERN.sub(" ", text)

        if self.normalize_whitespace:
            text = text.replace("\t", " ").replace("\n", " ").replace("\r", " ")

        if self.remove_extra_spaces:
            text = self.EXTRA_SPACES_PATTERN.sub(" ", text)

        return text.strip()

    def clean_batch(self, texts: list) -> list:
        """Clean a batch of texts."""
        return [self.clean(text) for text in texts]

    def remove_punctuation(self, text: str, keep_chinese: bool = True) -> str:
        """Remove punctuation from text while preserving words."""
        if keep_chinese:
            cleaned = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", text)
        else:
            cleaned = re.sub(r"[^\w\s]", " ", text)
        return self.EXTRA_SPACES_PATTERN.sub(" ", cleaned).strip()

    def remove_numbers(self, text: str) -> str:
        """Remove numbers from text."""
        return re.sub(r"\d+", " ", text)

    def normalize_chinese_punctuation(self, text: str) -> str:
        """Normalize Chinese punctuation to English equivalents."""
        punctuation_map = {
            "，": ",",
            "。": ".",
            "！": "!",
            "？": "?",
            "：": ":",
            "；": ";",
            "（": "(",
            "）": ")",
            "【": "[",
            "】": "]",
            "《": "<",
            "》": ">",
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "、": ",",
            "…": "...",
            "—": "-",
            "～": "~",
        }

        for chinese, english in punctuation_map.items():
            text = text.replace(chinese, english)

        return text
