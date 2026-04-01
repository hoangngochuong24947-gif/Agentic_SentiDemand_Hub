"""Stopword filtering utilities."""

from pathlib import Path
from typing import List, Optional, Set, Union


class StopwordFilter:
    """Filter stopwords from token lists."""

    # Keep this built-in set conservative so short opinion corpora keep
    # meaningful descriptive words such as "濂?".
    DEFAULT_STOPWORDS = {
        "的",
        "了",
        "在",
        "是",
        "我",
        "有",
        "和",
        "就",
        "不",
        "都",
        "一个",
        "我们",
        "你",
        "他",
        "鐨?",
        "浜?",
        "鍦?",
        "鏄?",
        "鎴?",
        "鏈?",
        "鍜?",
        "灏?",
        "涓?",
        "閮?",
        "涓€",
        "涓€涓?",
        "涔?",
        "寰?",
        "鍒?",
        "璇?",
        "瑕?",
        "鍘?",
        "浣?",
        "浼?",
        "鐫€",
        "娌℃湁",
        "鐪?",
        "鑷繁",
        "杩?",
        "閭?",
        "鍙?",
        "绛?",
    }

    def __init__(
        self,
        stopwords_path: Optional[Union[str, Path]] = None,
        extra_words: Optional[List[str]] = None,
        min_word_length: int = 1,
    ):
        self.min_word_length = min_word_length
        self.stopwords: Set[str] = set()

        if stopwords_path:
            self.stopwords.update(self._load_stopwords(stopwords_path))
        else:
            self.stopwords.update(self.DEFAULT_STOPWORDS)

        if extra_words:
            self.stopwords.update(extra_words)

    def _load_stopwords(self, path: Union[str, Path]) -> Set[str]:
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
        return [
            word
            for word in words
            if len(word) >= self.min_word_length and word not in self.stopwords
        ]

    def filter_batch(self, word_lists: List[List[str]]) -> List[List[str]]:
        return [self.filter(words) for words in word_lists]

    def add_stopwords(self, words: List[str]) -> None:
        self.stopwords.update(words)

    def remove_stopwords(self, words: List[str]) -> None:
        for word in words:
            self.stopwords.discard(word)

    def is_stopword(self, word: str) -> bool:
        return word in self.stopwords

    def get_stopwords(self) -> Set[str]:
        return self.stopwords.copy()

    def save_stopwords(self, path: Union[str, Path]) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write("# Stopwords list\n")
            f.write(f"# Total: {len(self.stopwords)} words\n\n")
            for word in sorted(self.stopwords):
                f.write(f"{word}\n")
