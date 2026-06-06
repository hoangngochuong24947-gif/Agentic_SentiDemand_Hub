"""Keyword extraction module for comment_analyzer.

Provides TF-IDF based keyword extraction from text corpora.
"""

from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer as SklearnTfidfVectorizer


class KeywordExtractor:
    """TF-IDF based keyword extractor.

    Extracts important keywords from a corpus of text using TF-IDF scores.

    Example:
        >>> extractor = KeywordExtractor(top_k=20)
        >>> texts = ["产品质量很好", "服务态度不错", ...]
        >>> keywords = extractor.extract(texts)
        >>> print(keywords[:5])
        [('质量', 0.5234), ('服务', 0.4892), ...]

        >>> # Extract keywords for specific documents
        >>> doc_keywords = extractor.extract_for_document(texts[0])
    """

    def __init__(
        self,
        method: str = "tfidf",
        top_k: int = 20,
        max_features: int = 10000,
        min_df: int = 2,
        max_df: float = 0.95,
    ):
        """Initialize the keyword extractor.

        Args:
            method: Extraction method. Currently only 'tfidf' is supported.
            top_k: Number of top keywords to return.
            max_features: Maximum number of features for TF-IDF.
            min_df: Minimum document frequency.
            max_df: Maximum document frequency.
        """
        if method not in ('tfidf',):
            raise ValueError(f"Invalid method: {method}. Choose from 'tfidf'")

        self.method = method
        self.top_k = top_k
        self.max_features = max_features
        self.min_df = min_df
        self.max_df = max_df

        self._vectorizer = None
        self._is_fitted = False

    def _resolve_doc_frequency_thresholds(self, document_count: int) -> Tuple[int, float]:
        min_df = max(1, min(self.min_df, document_count))
        max_df = max(0.0, min(self.max_df, 1.0))
        if document_count <= 1:
            return 1, 1.0
        if max_df * document_count < min_df:
            min_df = 1
        return min_df, max_df

    def extract(self, texts: List[str]) -> List[Tuple[str, float]]:
        """Extract keywords from a corpus of texts.

        Args:
            texts: List of texts (space-joined segmented words).

        Returns:
            List of (keyword, score) tuples sorted by score.
        """
        if not texts:
            self._vectorizer = None
            self._is_fitted = True
            return []

        min_df, max_df = self._resolve_doc_frequency_thresholds(len(texts))

        # Create and fit TF-IDF vectorizer
        self._vectorizer = SklearnTfidfVectorizer(
            max_features=self.max_features,
            min_df=min_df,
            max_df=max_df,
            token_pattern=r'(?u)\b\w+\b',
        )

        tfidf_matrix = self._vectorizer.fit_transform(texts)
        self._is_fitted = True

        # Calculate mean TF-IDF score for each term
        mean_scores = np.array(tfidf_matrix.mean(axis=0)).flatten()

        # Get feature names
        feature_names = self._vectorizer.get_feature_names_out()

        # Create (word, score) pairs and sort
        keywords = list(zip(feature_names, mean_scores))
        keywords.sort(key=lambda x: x[1], reverse=True)

        return keywords[:self.top_k]

    def extract_for_document(self, text: str) -> List[Tuple[str, float]]:
        """Extract keywords for a specific document.

        Args:
            text: Input text (space-joined segmented words).

        Returns:
            List of (keyword, score) tuples for the document.

        Raises:
            ValueError: If extractor hasn't been fitted.
        """
        if not self._is_fitted:
            raise ValueError("Extractor must be fitted before extracting document keywords")
        if self._vectorizer is None:
            return []

        # Transform the document
        tfidf_vector = self._vectorizer.transform([text])

        # Get non-zero features
        feature_names = self._vectorizer.get_feature_names_out()
        scores = tfidf_vector.toarray()[0]

        # Create (word, score) pairs
        keywords = [(word, score) for word, score in zip(feature_names, scores) if score > 0]
        keywords.sort(key=lambda x: x[1], reverse=True)

        return keywords

    def extract_batch(self, texts: List[str]) -> List[List[Tuple[str, float]]]:
        """Extract keywords for multiple documents.

        Args:
            texts: List of texts.

        Returns:
            List of keyword lists, one per document.
        """
        if not self._is_fitted:
            # Fit on all texts first
            self.extract(texts)

        return [self.extract_for_document(text) for text in texts]

    def get_word_frequency(self, texts: List[str]) -> List[Tuple[str, int]]:
        """Get word frequency across the corpus.

        Args:
            texts: List of texts.

        Returns:
            List of (word, frequency) tuples sorted by frequency.
        """
        word_freq = {}
        for text in texts:
            words = text.split()
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency
        freq_list = list(word_freq.items())
        freq_list.sort(key=lambda x: x[1], reverse=True)

        return freq_list
