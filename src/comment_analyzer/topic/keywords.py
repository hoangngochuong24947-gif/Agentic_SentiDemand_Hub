"""Keyword extraction based on TF-IDF."""

import math
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer as SklearnTfidfVectorizer


class KeywordExtractor:
    """Extract keywords from a text corpus."""

    def __init__(
        self,
        method: str = "tfidf",
        top_k: int = 20,
        max_features: int = 10000,
        min_df: int = 2,
        max_df: float = 0.95,
    ):
        if method not in ("tfidf",):
            raise ValueError(f"Invalid method: {method}. Choose from 'tfidf'")

        self.method = method
        self.top_k = top_k
        self.max_features = max_features
        self.min_df = min_df
        self.max_df = max_df
        self._vectorizer = None
        self._is_fitted = False

    def _resolve_df_thresholds(self, doc_count: int) -> Tuple[int, int]:
        if doc_count <= 0:
            return (1, 1)

        min_docs = max(1, min(self.min_df, doc_count))
        if doc_count <= 5:
            min_docs = 1
        max_docs = max(1, math.floor(self.max_df * doc_count))
        max_docs = min(doc_count, max(max_docs, min_docs))
        return (min_docs, max_docs)

    def extract(self, texts: List[str]) -> List[Tuple[str, float]]:
        min_df, max_df = self._resolve_df_thresholds(len(texts))
        self._vectorizer = SklearnTfidfVectorizer(
            max_features=self.max_features,
            min_df=min_df,
            max_df=max_df,
            token_pattern=r"(?u)\b\w+\b",
        )

        tfidf_matrix = self._vectorizer.fit_transform(texts)
        self._is_fitted = True

        mean_scores = np.array(tfidf_matrix.mean(axis=0)).flatten()
        feature_names = self._vectorizer.get_feature_names_out()
        keywords = list(zip(feature_names, mean_scores))
        keywords.sort(key=lambda item: item[1], reverse=True)
        return keywords[: self.top_k]

    def extract_for_document(self, text: str) -> List[Tuple[str, float]]:
        if not self._is_fitted:
            raise ValueError("Extractor must be fitted before extracting document keywords")

        tfidf_vector = self._vectorizer.transform([text])
        feature_names = self._vectorizer.get_feature_names_out()
        scores = tfidf_vector.toarray()[0]
        keywords = [(word, score) for word, score in zip(feature_names, scores) if score > 0]
        keywords.sort(key=lambda item: item[1], reverse=True)
        return keywords

    def extract_batch(self, texts: List[str]) -> List[List[Tuple[str, float]]]:
        if not self._is_fitted:
            self.extract(texts)
        return [self.extract_for_document(text) for text in texts]

    def get_word_frequency(self, texts: List[str]) -> List[Tuple[str, int]]:
        word_freq = {}
        for text in texts:
            for word in text.split():
                word_freq[word] = word_freq.get(word, 0) + 1

        freq_list = list(word_freq.items())
        freq_list.sort(key=lambda item: item[1], reverse=True)
        return freq_list
