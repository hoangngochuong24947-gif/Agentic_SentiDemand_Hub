"""Stopword filtering module for comment_analyzer.

Provides stopword filtering capabilities with support for custom stopword lists
and layered stopword strategies.
"""

from pathlib import Path
from typing import List, Literal, Optional, Set, Union


class StopwordFilter:
    """Stopword filter for text processing.

    Filters out common stopwords from segmented text. Supports
    custom stopword lists and additional word filtering.
    """

    DEFAULT_STOPWORDS = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
        "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
        "看", "自己", "这", "那", "吧", "吗", "呢", "啊", "呀", "哦", "还", "又",
        "被", "把", "跟", "让", "给", "对", "与", "并", "但", "而", "及",
    }

    def __init__(
        self,
        stopwords_path: Optional[Union[str, Path]] = None,
        extra_words: Optional[List[str]] = None,
        min_word_length: int = 1,
        strategy: Literal["default", "custom", "hybrid"] = "hybrid",
        use_default: bool = True,
    ):
        """Initialize the stopword filter.

        Args:
            stopwords_path: Path to stopwords file (one word per line).
            extra_words: Additional words to filter.
            min_word_length: Minimum word length to keep.
            strategy: Stopword loading strategy.
            use_default: Whether built-in default stopwords are enabled.
        """
        self.min_word_length = min_word_length
        self.strategy = strategy
        self.use_default = use_default
        self.stopwords: Set[str] = set()

        if strategy not in {"default", "custom", "hybrid"}:
            raise ValueError(f"Unknown stopword strategy: {strategy}")

        if strategy in {"default", "hybrid"} and use_default:
            self.stopwords.update(self.DEFAULT_STOPWORDS)

        if stopwords_path and strategy in {"custom", "hybrid"}:
            self.stopwords.update(self._load_stopwords(stopwords_path))

        if extra_words:
            self.stopwords.update(extra_words)

    def _load_stopwords(self, path: Union[str, Path]) -> Set[str]:
        """Load stopwords from file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Stopwords file not found: {path}")

        stopwords = set()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith("#"):
                    stopwords.add(word)

        return stopwords

    def filter(self, words: List[str]) -> List[str]:
        """Filter stopwords from word list."""
        return [
            word for word in words
            if len(word) >= self.min_word_length
            and word not in self.stopwords
        ]

    def filter_batch(self, word_lists: List[List[str]]) -> List[List[str]]:
        """Filter stopwords from multiple word lists."""
        return [self.filter(words) for words in word_lists]

    def add_stopwords(self, words: List[str]) -> None:
        """Add words to the stopword list."""
        self.stopwords.update(words)

    def remove_stopwords(self, words: List[str]) -> None:
        """Remove words from the stopword list."""
        for word in words:
            self.stopwords.discard(word)

    def is_stopword(self, word: str) -> bool:
        """Check if a word is a stopword."""
        return word in self.stopwords

    def get_stopwords(self) -> Set[str]:
        """Get the current set of stopwords."""
        return self.stopwords.copy()

    def save_stopwords(self, path: Union[str, Path]) -> None:
        """Save current stopwords to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write("# Stopwords list\n")
            f.write(f"# Total: {len(self.stopwords)} words\n\n")
            for word in sorted(self.stopwords):
                f.write(f"{word}\n")
