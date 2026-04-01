"""TF-IDF vectorization helpers."""

import math
from typing import List, Optional, Tuple, Union

from sklearn.feature_extraction.text import TfidfVectorizer as SklearnTfidfVectorizer


class TFIDFVectorizer:
    """Small wrapper around scikit-learn's TF-IDF vectorizer."""

    def __init__(
        self,
        max_features: int = 5000,
        min_df: Union[int, float] = 2,
        max_df: Union[int, float] = 0.95,
        ngram_range: Tuple[int, int] = (1, 2),
        stop_words: Optional[List[str]] = None,
        use_idf: bool = True,
        smooth_idf: bool = True,
        sublinear_tf: bool = False,
    ):
        self.max_features = max_features
        self.min_df = min_df
        self.max_df = max_df
        self.ngram_range = ngram_range
        self._vectorizer = None
        self._vectorizer_params = {
            "max_features": max_features,
            "ngram_range": ngram_range,
            "stop_words": stop_words,
            "use_idf": use_idf,
            "smooth_idf": smooth_idf,
            "sublinear_tf": sublinear_tf,
            "token_pattern": r"(?u)\b\w+\b",
        }
        self._is_fitted = False

    def _resolve_df_thresholds(self, doc_count: int) -> Tuple[int, int]:
        if doc_count <= 0:
            return (1, 1)

        if isinstance(self.min_df, int):
            min_docs = max(1, min(self.min_df, doc_count))
            if doc_count <= 5:
                min_docs = 1
        else:
            min_docs = max(1, math.ceil(self.min_df * doc_count))

        if isinstance(self.max_df, int):
            max_docs = max(1, min(self.max_df, doc_count))
        else:
            max_docs = max(1, math.floor(self.max_df * doc_count))

        max_docs = min(doc_count, max(max_docs, min_docs))
        return (min_docs, max_docs)

    def _build_vectorizer(self, texts: List[str]) -> SklearnTfidfVectorizer:
        min_df, max_df = self._resolve_df_thresholds(len(texts))
        return SklearnTfidfVectorizer(
            min_df=min_df,
            max_df=max_df,
            **self._vectorizer_params,
        )

    def fit(self, texts: List[str]) -> "TFIDFVectorizer":
        self._vectorizer = self._build_vectorizer(texts)
        self._vectorizer.fit(texts)
        self._is_fitted = True
        return self

    def transform(self, texts: List[str]):
        if not self._is_fitted:
            raise ValueError("Vectorizer must be fitted before transform")
        return self._vectorizer.transform(texts)

    def fit_transform(self, texts: List[str]):
        self._vectorizer = self._build_vectorizer(texts)
        result = self._vectorizer.fit_transform(texts)
        self._is_fitted = True
        return result

    def get_feature_names(self) -> List[str]:
        if not self._is_fitted:
            raise ValueError("Vectorizer must be fitted before getting features")
        return self._vectorizer.get_feature_names_out().tolist()

    def get_vocabulary(self) -> dict:
        if not self._is_fitted:
            raise ValueError("Vectorizer must be fitted before getting vocabulary")
        return self._vectorizer.vocabulary_

    def get_idf_scores(self) -> dict:
        if not self._is_fitted:
            raise ValueError("Vectorizer must be fitted before getting IDF scores")

        features = self.get_feature_names()
        idf_scores = self._vectorizer.idf_
        return {feature: score for feature, score in zip(features, idf_scores)}

    def get_top_features(self, text: str, top_n: int = 10):
        if not self._is_fitted:
            raise ValueError("Vectorizer must be fitted")

        x = self._vectorizer.transform([text])
        features = self.get_feature_names()
        scores = x.toarray()[0]
        feature_scores = [(feature, score) for feature, score in zip(features, scores) if score > 0]
        feature_scores.sort(key=lambda item: item[1], reverse=True)
        return feature_scores[:top_n]
