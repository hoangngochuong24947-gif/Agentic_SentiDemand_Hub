"""Language-aware text segmentation helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

import jieba
import jieba.posseg as pseg

_HANGUL_RE = re.compile(r"[가-힣]+")
_LATIN_RE = re.compile(r"[A-Za-z0-9]+")


class JiebaSegmenter:
    """Chinese text segmenter using jieba."""

    def __init__(self, mode: str = "precise", custom_dict_path: Optional[str] = None):
        if mode not in ("precise", "full", "search"):
            raise ValueError(f"Invalid mode: {mode}. Choose from 'precise', 'full', 'search'")
        self.mode = mode
        if custom_dict_path:
            self.load_custom_dict(custom_dict_path)

    def load_custom_dict(self, dict_path: str) -> None:
        path = Path(dict_path)
        if not path.exists():
            raise FileNotFoundError(f"Dictionary file not found: {path}")
        jieba.load_userdict(str(path))

    def add_word(self, word: str, freq: Optional[int] = None, tag: Optional[str] = None) -> None:
        jieba.add_word(word, freq, tag)

    def segment(self, text: str) -> List[str]:
        if not text or not isinstance(text, str):
            return []
        if self.mode == "precise":
            words = list(jieba.cut(text, cut_all=False))
        elif self.mode == "full":
            words = list(jieba.cut(text, cut_all=True))
        else:
            words = list(jieba.cut_for_search(text))
        return [word.strip() for word in words if word.strip()]

    def segment_with_pos(self, text: str) -> List[Tuple[str, str]]:
        if not text or not isinstance(text, str):
            return []
        return [(word, flag) for word, flag in pseg.cut(text) if word.strip()]

    def segment_batch(self, texts: List[str]) -> List[List[str]]:
        return [self.segment(text) for text in texts]

    def extract_nouns(self, text: str) -> List[str]:
        return [word for word, flag in self.segment_with_pos(text) if flag.startswith("n") or flag in {"nr", "ns", "nt", "nw", "nz"}]

    def extract_verbs(self, text: str) -> List[str]:
        return [word for word, flag in self.segment_with_pos(text) if flag.startswith("v")]

    def extract_adjectives(self, text: str) -> List[str]:
        return [word for word, flag in self.segment_with_pos(text) if flag.startswith("a")]

    def get_word_freq(self, texts: List[str]) -> dict:
        freq = {}
        for text in texts:
            for word in self.segment(text):
                freq[word] = freq.get(word, 0) + 1
        return freq


class KoreanSegmenter:
    """Korean segmenter with KoNLPy backends and a regex fallback."""

    def __init__(self, backend: str = "auto", custom_dict_path: Optional[str] = None):
        self.backend = backend
        self.custom_dict_path = Path(custom_dict_path) if custom_dict_path else None
        self._analyzer = None
        self._resolved_backend = "regex"
        self._setup_backend()

    @property
    def resolved_backend(self) -> str:
        return self._resolved_backend

    def _setup_backend(self) -> None:
        ordered_backends = {
            "auto": ("okt", "mecab", "regex"),
            "okt": ("okt",),
            "mecab": ("mecab",),
            "regex": ("regex",),
        }.get(self.backend, (self.backend,))

        for candidate in ordered_backends:
            if candidate == "regex":
                self._resolved_backend = "regex"
                self._analyzer = None
                return
            try:
                if candidate == "okt":
                    from konlpy.tag import Okt

                    self._analyzer = Okt()
                    self._resolved_backend = "okt"
                    return
                if candidate == "mecab":
                    from konlpy.tag import Mecab

                    self._analyzer = Mecab()
                    self._resolved_backend = "mecab"
                    return
            except Exception:
                continue

        self._resolved_backend = "regex"
        self._analyzer = None

    @staticmethod
    def _regex_segment(text: str) -> List[str]:
        return _HANGUL_RE.findall(text) + _LATIN_RE.findall(text)

    def segment(self, text: str) -> List[str]:
        if not text or not isinstance(text, str):
            return []
        if self._resolved_backend == "okt":
            return [token for token in self._analyzer.morphs(text, norm=True, stem=True) if token.strip()]
        if self._resolved_backend == "mecab":
            return [token for token in self._analyzer.morphs(text) if token.strip()]
        return self._regex_segment(text)

    def segment_with_pos(self, text: str) -> List[Tuple[str, str]]:
        if not text or not isinstance(text, str):
            return []
        if self._resolved_backend == "okt":
            return [(token, tag) for token, tag in self._analyzer.pos(text, norm=True, stem=True) if token.strip()]
        if self._resolved_backend == "mecab":
            return [(token, tag) for token, tag in self._analyzer.pos(text) if token.strip()]
        return [(token, "Korean") for token in self._regex_segment(text)]

    def segment_batch(self, texts: List[str]) -> List[List[str]]:
        return [self.segment(text) for text in texts]

    def extract_nouns(self, text: str) -> List[str]:
        nouns: List[str] = []
        for token, tag in self.segment_with_pos(text):
            if self._resolved_backend == "regex" or tag.startswith("N"):
                nouns.append(token)
        return nouns

    def get_word_freq(self, texts: List[str]) -> dict:
        freq = {}
        for text in texts:
            for word in self.segment(text):
                freq[word] = freq.get(word, 0) + 1
        return freq


class MultilingualSegmenter:
    """Dispatch segmentation by configured language."""

    def __init__(
        self,
        language: str = "zh",
        mode: str = "precise",
        backend: str = "auto",
        custom_dict_path: Optional[str] = None,
    ):
        self.language = language
        self.mode = mode
        self.backend = backend
        self.custom_dict_path = custom_dict_path
        self._segmenter = self._build_segmenter()

    def _build_segmenter(self):
        if self.language == "ko":
            return KoreanSegmenter(backend=self.backend, custom_dict_path=self.custom_dict_path)
        return JiebaSegmenter(mode=self.mode, custom_dict_path=self.custom_dict_path)

    @property
    def resolved_backend(self) -> str:
        return getattr(self._segmenter, "resolved_backend", "jieba")

    def segment(self, text: str) -> List[str]:
        return self._segmenter.segment(text)

    def segment_with_pos(self, text: str) -> List[Tuple[str, str]]:
        if hasattr(self._segmenter, "segment_with_pos"):
            return self._segmenter.segment_with_pos(text)
        return [(token, "") for token in self.segment(text)]

    def segment_batch(self, texts: List[str]) -> List[List[str]]:
        return self._segmenter.segment_batch(texts)

    def extract_nouns(self, text: str) -> List[str]:
        if hasattr(self._segmenter, "extract_nouns"):
            return self._segmenter.extract_nouns(text)
        return self.segment(text)

    def get_word_freq(self, texts: List[str]) -> dict:
        return self._segmenter.get_word_freq(texts)
