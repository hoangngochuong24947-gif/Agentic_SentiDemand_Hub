"""Demand intensity calculation module for comment_analyzer.

Provides demand intensity calculation based on keyword occurrence and TF-IDF weights.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer as SklearnTfidfVectorizer


class DemandIntensityCalculator:
    """Calculate demand intensity for different demand categories.

    Analyzes text to determine the intensity of different types of demands
    (e.g., taste, price, quality, service) based on keyword occurrence.

    Example:
        >>> calculator = DemandIntensityCalculator()
        >>> documents = [['味道', '不错', '价格', '便宜'], ['服务', '态度', '好']]
        >>> intensity = calculator.calculate(documents)
        >>> print(intensity)
           taste  price  service
        0   0.5    0.5      0.0
        1   0.0    0.0      0.7

        >>> # Get category distribution
        >>> calculator.get_category_distribution()
    """

    def __init__(
        self,
        keywords_path: Optional[Union[str, Path]] = None,
        method: str = "tfidf_weighted",
        normalization: str = "minmax",
    ):
        """Initialize the demand intensity calculator.

        Args:
            keywords_path: Path to demand keywords JSON file.
            method: Calculation method ('simple' or 'tfidf_weighted').
            normalization: Normalization method ('minmax', 'standard', or 'none').
        """
        if method not in ('simple', 'tfidf_weighted'):
            raise ValueError(f"Invalid method: {method}. Choose from 'simple', 'tfidf_weighted'")

        if normalization not in ('minmax', 'standard', 'none'):
            raise ValueError(f"Invalid normalization: {normalization}")

        self.method = method
        self.normalization = normalization

        # Load keywords
        self.keywords = self._load_keywords(keywords_path)
        self.categories = list(self.keywords.keys())

    def _load_keywords(self, path: Optional[Union[str, Path]]) -> Dict[str, List[str]]:
        """Load demand keywords from file.

        Args:
            path: Path to keywords JSON file.

        Returns:
            Dictionary mapping category names to keyword lists.
        """
        if path is None:
            return self._get_default_keywords()

        path = Path(path)
        if not path.exists():
            return self._get_default_keywords()

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'categories' in data:
            return {
                cat_id: cat_data.get('keywords', [])
                for cat_id, cat_data in data['categories'].items()
            }
        return data

    def _get_default_keywords(self) -> Dict[str, List[str]]:
        """Get default demand keywords."""
        return {
            'taste': ['味道', '口味', '口感', '好吃', '美味', '香甜'],
            'price': ['价格', '价钱', '贵', '便宜', '实惠', '划算'],
            'quality': ['质量', '品质', '做工', '材料', '耐用'],
            'packaging': ['包装', '外观', '盒子', '袋子', '精美'],
            'logistics': ['物流', '快递', '发货', '送货', '速度'],
            'service': ['服务', '客服', '售后', '态度', '热情'],
        }

    def calculate(self, documents: List[List[str]]) -> pd.DataFrame:
        """Calculate demand intensity for documents.

        Args:
            documents: List of documents, where each document is a list of words.

        Returns:
            DataFrame with demand intensity scores for each category.
        """
        if self.method == 'simple':
            return self._calculate_simple(documents)
        else:
            return self._calculate_tfidf_weighted(documents)

    def _calculate_simple(self, documents: List[List[str]]) -> pd.DataFrame:
        """Calculate simple keyword-based intensity."""
        results = []

        for doc in documents:
            doc_set = set(doc)
            scores = {}

            for category, keywords in self.keywords.items():
                # Count matching keywords
                matches = sum(1 for kw in keywords if kw in doc_set)
                # Normalize by number of keywords in category
                scores[category] = matches / len(keywords) if keywords else 0

            results.append(scores)

        df = pd.DataFrame(results)
        return self._normalize(df)

    def _calculate_tfidf_weighted(self, documents: List[List[str]]) -> pd.DataFrame:
        """Calculate TF-IDF weighted intensity."""
        # Join documents for TF-IDF
        texts = [' '.join(doc) for doc in documents]

        # Create TF-IDF vectorizer
        vectorizer = SklearnTfidfVectorizer(
            token_pattern=r'(?u)\b\w+\b',
            min_df=1,
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
        except ValueError:
            # Empty vocabulary
            return pd.DataFrame(0, index=range(len(documents)), columns=self.categories)

        # Calculate category scores
        results = []

        for i in range(len(documents)):
            doc_vector = tfidf_matrix[i].toarray()[0]
            scores = {}

            for category, keywords in self.keywords.items():
                # Get TF-IDF scores for category keywords
                keyword_scores = []
                for kw in keywords:
                    if kw in feature_names:
                        idx = np.where(feature_names == kw)[0]
                        if len(idx) > 0:
                            keyword_scores.append(doc_vector[idx[0]])

                # Use max score or mean score
                if keyword_scores:
                    scores[category] = np.mean(keyword_scores)
                else:
                    scores[category] = 0

            results.append(scores)

        df = pd.DataFrame(results)
        return self._normalize(df)

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize intensity scores."""
        if self.normalization == 'none':
            return df

        if self.normalization == 'minmax':
            # Min-Max normalization to [0, 1]
            for col in df.columns:
                col_max = df[col].max()
                col_min = df[col].min()
                if col_max > col_min:
                    df[col] = (df[col] - col_min) / (col_max - col_min)
                elif col_max > 0:
                    df[col] = 1.0
                else:
                    df[col] = 0.0

        elif self.normalization == 'standard':
            # Standard normalization (z-score)
            for col in df.columns:
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:
                    df[col] = (df[col] - mean) / std
                else:
                    df[col] = 0.0

        return df

    def get_category_distribution(self, intensity_df: pd.DataFrame) -> Dict[str, float]:
        """Get average intensity distribution across categories.

        Args:
            intensity_df: DataFrame from calculate().

        Returns:
            Dictionary mapping category to average intensity.
        """
        return intensity_df.mean().to_dict()

    def get_top_documents(
        self,
        intensity_df: pd.DataFrame,
        category: str,
        n: int = 10
    ) -> List[int]:
        """Get indices of documents with highest intensity for a category.

        Args:
            intensity_df: DataFrame from calculate().
            category: Category to check.
            n: Number of top documents to return.

        Returns:
            List of document indices.
        """
        return intensity_df[category].nlargest(n).index.tolist()

    def compare_categories(self, intensity_df: pd.DataFrame) -> pd.DataFrame:
        """Compare category intensities statistically.

        Args:
            intensity_df: DataFrame from calculate().

        Returns:
            DataFrame with statistics for each category.
        """
        stats = pd.DataFrame({
            'mean': intensity_df.mean(),
            'std': intensity_df.std(),
            'min': intensity_df.min(),
            'max': intensity_df.max(),
            'median': intensity_df.median(),
        })

        return stats
