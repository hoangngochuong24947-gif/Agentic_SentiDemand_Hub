"""Text cleaning module for comment_analyzer.

Provides utilities for cleaning and normalizing text content
before further processing.
"""

import re
import html
from typing import Optional, Pattern


class TextCleaner:
    """Text cleaner for preprocessing comments and reviews.

    Performs various cleaning operations including URL removal,
    HTML tag stripping, email removal, and whitespace normalization.

    Example:
        >>> cleaner = TextCleaner()
        >>> text = "Check out https://example.com \u003cb>great\u003c/b> product!!!"
        >>> cleaner.clean(text)
        'Check out great product!!!'

        >>> # With specific options
        >>> cleaner = TextCleaner(remove_urls=False, normalize_whitespace=True)
        >>> cleaner.clean(text)
    """

    # Regular expression patterns
    URL_PATTERN = re.compile(
        r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
        re.IGNORECASE
    )
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    HTML_PATTERN = re.compile(r'<[^\u003e]+>')
    EXTRA_SPACES_PATTERN = re.compile(r'\s+')
    SPECIAL_CHARS_PATTERN = re.compile(r'[^\w\s\u4e00-\u9fff]')  # Keep Chinese chars

    def __init__(
        self,
        remove_urls: bool = True,
        remove_emails: bool = True,
        remove_html: bool = True,
        remove_extra_spaces: bool = True,
        normalize_whitespace: bool = True,
    ):
        """Initialize the text cleaner.

        Args:
            remove_urls: Whether to remove URLs from text.
            remove_emails: Whether to remove email addresses.
            remove_html: Whether to strip HTML tags.
            remove_extra_spaces: Whether to collapse multiple spaces.
            normalize_whitespace: Whether to normalize whitespace characters.
        """
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_html = remove_html
        self.remove_extra_spaces = remove_extra_spaces
        self.normalize_whitespace = normalize_whitespace

    def clean(self, text: Optional[str]) -> str:
        """Clean the input text.

        Args:
            text: Input text to clean. Can be None.

        Returns:
            Cleaned text string.
        """
        if text is None:
            return ""

        # Convert to string if not already
        text = str(text)

        # Remove URLs
        if self.remove_urls:
            text = self.URL_PATTERN.sub(' ', text)

        # Remove email addresses
        if self.remove_emails:
            text = self.EMAIL_PATTERN.sub(' ', text)

        # Remove HTML tags
        if self.remove_html:
            text = html.unescape(text)  # Decode HTML entities first
            text = self.HTML_PATTERN.sub(' ', text)

        # Normalize whitespace
        if self.normalize_whitespace:
            # Replace various whitespace characters with regular space
            text = text.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')

        # Remove extra spaces
        if self.remove_extra_spaces:
            text = self.EXTRA_SPACES_PATTERN.sub(' ', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def clean_batch(self, texts: list) -> list:
        """Clean a batch of texts.

        Args:
            texts: List of texts to clean.

        Returns:
            List of cleaned texts.
        """
        return [self.clean(text) for text in texts]

    def remove_punctuation(self, text: str, keep_chinese: bool = True) -> str:
        """Remove punctuation from text.

        Args:
            text: Input text.
            keep_chinese: Whether to keep Chinese characters.

        Returns:
            Text without punctuation.
        """
        if keep_chinese:
            # Keep Chinese characters, letters, numbers, and spaces
            return re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        else:
            # Keep only letters, numbers, and spaces
            return re.sub(r'[^\w\s]', ' ', text)

    def remove_numbers(self, text: str) -> str:
        """Remove numbers from text.

        Args:
            text: Input text.

        Returns:
            Text without numbers.
        """
        return re.sub(r'\d+', ' ', text)

    def normalize_chinese_punctuation(self, text: str) -> str:
        """Normalize Chinese punctuation to English equivalents.

        Args:
            text: Input text.

        Returns:
            Text with normalized punctuation.
        """
        # Mapping of Chinese punctuation to English
        punctuation_map = {
            '，': ',',
            '。': '.',
            '！': '!',
            '？': '?',
            '：': ':',
            '；': ';',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '（': '(',
            '）': ')',
            '【': '[',
            '】': ']',
            '《': '<',
            '》': '>',
            '、': ',',
            '…': '...',
            '—': '-',
            '～': '~',
        }

        for chinese, english in punctuation_map.items():
            text = text.replace(chinese, english)

        return text
