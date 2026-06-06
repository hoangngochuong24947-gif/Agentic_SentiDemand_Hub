"""TF-IDF vectorization module for comment_analyzer.

Provides TF-IDF vectorization for text classification.
"""

from math import ceil
from typing import List, Optional, Tuple, Union

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer as SklearnTfidfVectorizer


class TFIDFVectorizer:
    """TF-IDF vectorizer for text classification.

    Wraps scikit-learn's TfidfVectorizer with simplified interface
    and default settings optimized for comment analysis.

    Example:
        >>> vectorizer = TFIDFVectorizer(max_features=1000)
        >>> texts = ["产品很好", "服务不错", "质量一般"]
        >>> X = vectorizer.fit_transform(texts)
        >>> X.shape
        (3, 1000)

        >>> # Get feature names
        >>> vectorizer.get_feature_names()[:5]
        ['一个', '一般', '不错', '产品', '很好']

        >>> # Transform new texts
        >>> new_X = vectorizer.transform(["质量很好"])
    """

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
        """Initialize the TF-IDF vectorizer.

        Args:
            max_features: Maximum number of features to extract.
            min_df: Minimum document frequency for a term.
            max_df: Maximum document frequency for a term.
            ngram_range: Range of n-grams to extract (min_n, max_n).
            stop_words: List of stopwords to ignore.
            use_idf: Whether to use IDF weighting.
            smooth_idf: Whether to smooth IDF weights.
            sublinear_tf: Whether to use sublinear TF scaling.
        """
        self.max_features = max_features
        self.min_df = min_df
        self.max_df = max_df
        self.ngram_range = ngram_range
        self.stop_words = stop_words
        self.use_idf = use_idf
        self.smooth_idf = smooth_idf
        self.sublinear_tf = sublinear_tf

        self._vectorizer = self._create_vectorizer(min_df=min_df, max_df=max_df)

        self._is_fitted = False

    def _create_vectorizer(
        self,
        min_df: Union[int, float],
        max_df: Union[int, float],
    ) -> SklearnTfidfVectorizer:
        return SklearnTfidfVectorizer(
            max_features=self.max_features,
            min_df=min_df,
            max_df=max_df,
            ngram_range=self.ngram_range,
            stop_words=self.stop_words,
            use_idf=self.use_idf,
            smooth_idf=self.smooth_idf,
            sublinear_tf=self.sublinear_tf,
            token_pattern=r'(?u)\b\w+\b',
        )

    def _resolve_doc_frequency_thresholds(self, document_count: int) -> Tuple[Union[int, float], Union[int, float]]:
        """Relax thresholds for tiny corpora so uploads with only a few rows still work."""
        min_df = self.min_df
        max_df = self.max_df

        if document_count <= 1:
            return 1, 1.0
        if document_count < 5:
            return 1, 1.0

        if isinstance(min_df, int):
            min_df = max(1, min(min_df, document_count))
        else:
            min_df = max(0.0, min(min_df, 1.0))

        if isinstance(max_df, int):
            max_df = max(1, min(max_df, document_count))
        else:
            max_df = max(0.0, min(max_df, 1.0))

        if isinstance(min_df, int) and not isinstance(max_df, int):
            if max_df * document_count < min_df:
                min_df = 1
        elif not isinstance(min_df, int) and isinstance(max_df, int):
            min_required_docs = max(1, ceil(min_df * document_count))
            if max_df < min_required_docs:
                max_df = document_count
        elif isinstance(min_df, int) and isinstance(max_df, int) and max_df < min_df:
            min_df = 1
            max_df = max(max_df, 1)
        elif not isinstance(min_df, int) and not isinstance(max_df, int) and max_df < min_df:
            min_df = min(min_df, 0.5)
            max_df = max(max_df, min_df)

        return min_df, max_df

    def fit(self, texts: List[str]) -> "TFIDFVectorizer":
        """Fit the vectorizer to the texts.

        Args:
            texts: List of texts to fit on.

        Returns:
            Self for method chaining.
        """
        min_df, max_df = self._resolve_doc_frequency_thresholds(len(texts))
        self._vectorizer = self._create_vectorizer(min_df=min_df, max_df=max_df)
        self._vectorizer.fit(texts)
        self._is_fitted = True
        return self

    def transform(self, texts: List[str]):
        """Transform texts to TF-IDF matrix.

        Args:
            texts: List of texts to transform.

        Returns:
            Sparse matrix of TF-IDF features.

        Raises:
            ValueError: If vectorizer hasn't been fitted.
        """
        if not self._is_fitted:
            raise ValueError("Vectorizer must be fitted before transform")
        return self._vectorizer.transform(texts)

    def fit_transform(self, texts: List[str]):
        """Fit and transform texts in one step.

        Args:
            texts: List of texts to fit and transform.

        Returns:
            Sparse matrix of TF-IDF features.
        """
        min_df, max_df = self._resolve_doc_frequency_thresholds(len(texts))
        self._vectorizer = self._create_vectorizer(min_df=min_df, max_df=max_df)
        result = self._vectorizer.fit_transform(texts)
        self._is_fitted = True
        return result

    def get_feature_names(self) -> List[str]:
        """Get the feature names (vocabulary terms).

        Returns:
            List of feature names.

        Raises:
            ValueError: If vectorizer hasn't been fitted.
        """
        if not self._is_fitted:
            raise ValueError("Vectorizer must be fitted before getting features")
        return self._vectorizer.get_feature_names_out().tolist()

    def get_vocabulary(self) -> dict:
        """Get the vocabulary mapping.

        Returns:
            Dictionary mapping terms to indices.

        Raises:
            ValueError: If vectorizer hasn't been fitted.
        """
        if not self._is_fitted:
            raise ValueError("Vectorizer must be fitted before getting vocabulary")
        return self._vectorizer.vocabulary_

    def get_idf_scores(self) -> dict:
        """Get IDF scores for all features.

        Returns:
            Dictionary mapping feature names to IDF scores.

        Raises:
            ValueError: If vectorizer hasn't been fitted.
        """
        if not self._is_fitted:
            raise ValueError("Vectorizer must be fitted before getting IDF scores")

        features = self.get_feature_names()
        idf_scores = self._vectorizer.idf_

        return {feature: score for feature, score in zip(features, idf_scores)}

    def get_top_features(
        self,
        text: str,
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """Get top features for a specific text.

        Args:
            text: Input text.
            top_n: Number of top features to return.

        Returns:
            List of (feature, score) tuples.

        Raises:
            ValueError: If vectorizer hasn't been fitted.
        """
        if not self._is_fitted:
            raise ValueError("Vectorizer must be fitted")

        # Transform single text
        X = self._vectorizer.transform([text])

        # Get non-zero features
        features = self.get_feature_names()
        scores = X.toarray()[0]

        # Sort by score
        feature_scores = [(f, s) for f, s in zip(features, scores) if s > 0]
        feature_scores.sort(key=lambda x: x[1], reverse=True)

        return feature_scores[:top_n]
