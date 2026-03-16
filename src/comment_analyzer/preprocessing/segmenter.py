"""Text segmentation module for comment_analyzer.

Uses jieba for Chinese text segmentation with support for custom dictionaries.
"""

import re
from pathlib import Path
from typing import List, Optional

import jieba
import jieba.posseg as pseg


class JiebaSegmenter:
    """Chinese text segmenter using jieba.

    Provides word segmentation for Chinese text with support for
different segmentation modes and custom dictionaries.

    Example:
        >>> segmenter = JiebaSegmenter(mode='precise')
        >>> segmenter.segment("这个产品非常好！")
        ['这个', '产品', '非常', '好']

        >>> # With part-of-speech tagging
        >>> segmenter.segment_with_pos("产品质量不错")
        [('产品', 'n'), ('质量', 'n'), ('不错', 'a')]
    """

    def __init__(
        self,
        mode: str = "precise",
        custom_dict_path: Optional[str] = None,
    ):
        """Initialize the segmenter.

        Args:
            mode: Segmentation mode. Options: 'precise', 'full', 'search'.
            custom_dict_path: Path to custom dictionary file.

        Raises:
            ValueError: If mode is not one of the supported options.
        """
        if mode not in ('precise', 'full', 'search'):
            raise ValueError(f"Invalid mode: {mode}. Choose from 'precise', 'full', 'search'")

        self.mode = mode

        # Load custom dictionary if provided
        if custom_dict_path:
            self.load_custom_dict(custom_dict_path)

    def load_custom_dict(self, dict_path: str) -> None:
        """Load a custom dictionary.

        Dictionary format: word [frequency] [tag]
        Example:
            云计算 1000 n
            大数据 2000 n

        Args:
            dict_path: Path to dictionary file.

        Raises:
            FileNotFoundError: If dictionary file doesn't exist.
        """
        dict_path = Path(dict_path)
        if not dict_path.exists():
            raise FileNotFoundError(f"Dictionary file not found: {dict_path}")

        jieba.load_userdict(str(dict_path))

    def add_word(self, word: str, freq: Optional[int] = None, tag: Optional[str] = None) -> None:
        """Add a single word to the dictionary.

        Args:
            word: Word to add.
            freq: Optional word frequency.
            tag: Optional part-of-speech tag.
        """
        jieba.add_word(word, freq, tag)

    def segment(self, text: str) -> List[str]:
        """Segment text into words.

        Args:
            text: Input text to segment.

        Returns:
            List of segmented words.
        """
        if not text or not isinstance(text, str):
            return []

        if self.mode == 'precise':
            # Precise mode: accurate segmentation, suitable for text analysis
            words = list(jieba.cut(text, cut_all=False))
        elif self.mode == 'full':
            # Full mode: all possible words, high recall
            words = list(jieba.cut(text, cut_all=True))
        elif self.mode == 'search':
            # Search engine mode: precise + long word re-segmentation
            words = list(jieba.cut_for_search(text))
        else:
            words = []

        # Filter out empty strings and whitespace-only tokens
        words = [w.strip() for w in words if w.strip()]

        return words

    def segment_with_pos(self, text: str) -> List[tuple]:
        """Segment text with part-of-speech tagging.

        Args:
            text: Input text to segment.

        Returns:
            List of (word, pos_tag) tuples.
        """
        if not text or not isinstance(text, str):
            return []

        return [(word, flag) for word, flag in pseg.cut(text) if word.strip()]

    def segment_batch(self, texts: List[str]) -> List[List[str]]:
        """Segment a batch of texts.

        Args:
            texts: List of texts to segment.

        Returns:
            List of segmented word lists.
        """
        return [self.segment(text) for text in texts]

    def extract_nouns(self, text: str) -> List[str]:
        """Extract nouns from text.

        Args:
            text: Input text.

        Returns:
            List of nouns.
        """
        nouns = []
        for word, flag in self.segment_with_pos(text):
            # n: noun, nr: person name, ns: place name, nt: organization
            if flag.startswith('n') or flag in ['nr', 'ns', 'nt', 'nw', 'nz']:
                nouns.append(word)
        return nouns

    def extract_verbs(self, text: str) -> List[str]:
        """Extract verbs from text.

        Args:
            text: Input text.

        Returns:
            List of verbs.
        """
        verbs = []
        for word, flag in self.segment_with_pos(text):
            # v: verb
            if flag.startswith('v'):
                verbs.append(word)
        return verbs

    def extract_adjectives(self, text: str) -> List[str]:
        """Extract adjectives from text.

        Args:
            text: Input text.

        Returns:
            List of adjectives.
        """
        adjectives = []
        for word, flag in self.segment_with_pos(text):
            # a: adjective, ad: adverb
            if flag.startswith('a'):
                adjectives.append(word)
        return adjectives

    def get_word_freq(self, texts: List[str]) -> dict:
        """Calculate word frequency across multiple texts.

        Args:
            texts: List of texts.

        Returns:
            Dictionary mapping words to their frequencies.
        """
        freq = {}
        for text in texts:
            for word in self.segment(text):
                freq[word] = freq.get(word, 0) + 1
        return freq
