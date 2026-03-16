"""Stopword filtering module for comment_analyzer.

Provides stopword filtering capabilities with support for custom stopword lists.
"""

from pathlib import Path
from typing import List, Optional, Set, Union


class StopwordFilter:
    """Stopword filter for text processing.

    Filters out common stopwords from segmented text. Supports
custom stopword lists and additional word filtering.

    Example:
        >>> filter = StopwordFilter()
        >>> filter.filter(['这个', '产品', '非常', '好'])
        ['产品', '非常', '好']

        >>> # With custom stopwords
        >>> filter = StopwordFilter(extra_words=['非常'])
        >>> filter.filter(['这个', '产品', '非常', '好'])
        ['产品', '好']
    """

    # Default Chinese stopwords (small built-in set)
    DEFAULT_STOPWORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
        '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
        '看', '好', '自己', '这', '那', '之', '与', '及', '等', '或',
    }

    def __init__(
        self,
        stopwords_path: Optional[Union[str, Path]] = None,
        extra_words: Optional[List[str]] = None,
        min_word_length: int = 1,
    ):
        """Initialize the stopword filter.

        Args:
            stopwords_path: Path to stopwords file (one word per line).
            extra_words: Additional words to filter.
            min_word_length: Minimum word length to keep.
        """
        self.min_word_length = min_word_length
        self.stopwords: Set[str] = set()

        # Load stopwords from file if provided
        if stopwords_path:
            self.stopwords.update(self._load_stopwords(stopwords_path))
        else:
            self.stopwords.update(self.DEFAULT_STOPWORDS)

        # Add extra words
        if extra_words:
            self.stopwords.update(extra_words)

    def _load_stopwords(self, path: Union[str, Path]) -> Set[str]:
        """Load stopwords from file.

        Args:
            path: Path to stopwords file.

        Returns:
            Set of stopwords.

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Stopwords file not found: {path}")

        stopwords = set()
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                # Skip empty lines and comments
                if word and not word.startswith('#'):
                    stopwords.add(word)

        return stopwords

    def filter(self, words: List[str]) -> List[str]:
        """Filter stopwords from word list.

        Args:
            words: List of words to filter.

        Returns:
            Filtered list of words.
        """
        return [
            word for word in words
            if len(word) >= self.min_word_length
            and word not in self.stopwords
        ]

    def filter_batch(self, word_lists: List[List[str]]) -> List[List[str]]:
        """Filter stopwords from multiple word lists.

        Args:
            word_lists: List of word lists to filter.

        Returns:
            List of filtered word lists.
        """
        return [self.filter(words) for words in word_lists]

    def add_stopwords(self, words: List[str]) -> None:
        """Add words to the stopword list.

        Args:
            words: Words to add.
        """
        self.stopwords.update(words)

    def remove_stopwords(self, words: List[str]) -> None:
        """Remove words from the stopword list.

        Args:
            words: Words to remove.
        """
        for word in words:
            self.stopwords.discard(word)

    def is_stopword(self, word: str) -> bool:
        """Check if a word is a stopword.

        Args:
            word: Word to check.

        Returns:
            True if word is a stopword, False otherwise.
        """
        return word in self.stopwords

    def get_stopwords(self) -> Set[str]:
        """Get the current set of stopwords.

        Returns:
            Set of stopwords.
        """
        return self.stopwords.copy()

    def save_stopwords(self, path: Union[str, Path]) -> None:
        """Save current stopwords to file.

        Args:
            path: Path to save stopwords file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write("# Stopwords list\n")
            f.write(f"# Total: {len(self.stopwords)} words\n\n")
            for word in sorted(self.stopwords):
                f.write(f"{word}\n")
