"""Demand correlation analysis module for comment_analyzer.

Provides demand correlation and co-occurrence analysis.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


class DemandCorrelationAnalyzer:
    """Analyze correlations between different demand categories.

    Calculates co-occurrence and correlation between demand types
to understand how different needs are mentioned together.

    Example:
        >>> analyzer = DemandCorrelationAnalyzer()
        >>> documents = [
        ...     ['味道', '不错', '价格', '便宜'],
        ...     ['服务', '态度', '好', '质量', '不错'],
        ...     ['价格', '贵', '质量', '差']
        ... ]
        >>> correlation = analyzer.analyze(documents)
        >>> print(correlation)
                taste  price  quality  service
        taste    1.0    0.3      0.1      0.2
        price    0.3    1.0      0.5      0.1
        ...
    """

    def __init__(
        self,
        keywords: Optional[Dict[str, List[str]]] = None,
        method: str = "cooccurrence",
        min_cooccurrence: int = 2,
        window_size: int = 50,
    ):
        """Initialize the demand correlation analyzer.

        Args:
            keywords: Dictionary mapping category names to keyword lists.
            method: Correlation method ('cooccurrence' or 'pmi').
            min_cooccurrence: Minimum co-occurrence count to include.
            window_size: Window size for co-occurrence calculation.
        """
        if method not in ('cooccurrence', 'pmi'):
            raise ValueError(f"Invalid method: {method}. Choose from 'cooccurrence', 'pmi'")

        self.keywords = keywords
        self.method = method
        self.min_cooccurrence = min_cooccurrence
        self.window_size = window_size

    def analyze(
        self,
        documents: List[List[str]],
        keywords: Optional[Dict[str, List[str]]] = None
    ) -> pd.DataFrame:
        """Analyze demand correlations.

        Args:
            documents: List of documents, where each document is a list of words.
            keywords: Dictionary mapping category names to keyword lists.
                     If None, uses keywords from initialization.

        Returns:
            DataFrame with correlation matrix between categories.
        """
        keywords = keywords or self.keywords
        if keywords is None:
            raise ValueError("Keywords must be provided either at initialization or at analysis time")

        if self.method == 'cooccurrence':
            return self._analyze_cooccurrence(documents, keywords)
        else:
            return self._analyze_pmi(documents, keywords)

    def _analyze_cooccurrence(
        self,
        documents: List[List[str]],
        keywords: Dict[str, List[str]]
    ) -> pd.DataFrame:
        """Analyze co-occurrence between categories."""
        categories = list(keywords.keys())

        # Initialize co-occurrence matrix
        cooccurrence = pd.DataFrame(0, index=categories, columns=categories)

        # Count co-occurrences
        for doc in documents:
            # Find which categories appear in this document
            present_categories = set()
            for cat, kws in keywords.items():
                if any(kw in doc for kw in kws):
                    present_categories.add(cat)

            # Increment co-occurrence counts
            for cat1 in present_categories:
                for cat2 in present_categories:
                    cooccurrence.loc[cat1, cat2] += 1

        # Filter by minimum co-occurrence
        cooccurrence = cooccurrence[cooccurrence >= self.min_cooccurrence].fillna(0)

        # Convert to correlation (normalize)
        correlation = self._normalize_cooccurrence(cooccurrence)

        return correlation

    def _analyze_pmi(
        self,
        documents: List[List[str]],
        keywords: Dict[str, List[str]]
    ) -> pd.DataFrame:
        """Analyze PMI (Pointwise Mutual Information) between categories."""
        categories = list(keywords.keys())
        n_docs = len(documents)

        # Count individual and joint occurrences
        cat_counts = {cat: 0 for cat in categories}
        joint_counts = pd.DataFrame(0, index=categories, columns=categories)

        for doc in documents:
            present = {}
            for cat, kws in keywords.items():
                present[cat] = any(kw in doc for kw in kws)
                if present[cat]:
                    cat_counts[cat] += 1

            for cat1 in categories:
                for cat2 in categories:
                    if present[cat1] and present[cat2]:
                        joint_counts.loc[cat1, cat2] += 1

        # Calculate PMI
        pmi_matrix = pd.DataFrame(0.0, index=categories, columns=categories)

        for cat1 in categories:
            for cat2 in categories:
                joint_prob = joint_counts.loc[cat1, cat2] / n_docs
                cat1_prob = cat_counts[cat1] / n_docs
                cat2_prob = cat_counts[cat2] / n_docs

                if joint_prob > 0 and cat1_prob > 0 and cat2_prob > 0:
                    pmi = np.log(joint_prob / (cat1_prob * cat2_prob))
                    pmi_matrix.loc[cat1, cat2] = max(0, pmi)  # Use positive PMI

        return pmi_matrix

    def _normalize_cooccurrence(self, cooccurrence: pd.DataFrame) -> pd.DataFrame:
        """Normalize co-occurrence matrix to correlation-like values."""
        # Jaccard similarity normalization
        normalized = pd.DataFrame(0.0, index=cooccurrence.index, columns=cooccurrence.columns)

        for cat1 in cooccurrence.index:
            for cat2 in cooccurrence.columns:
                intersection = cooccurrence.loc[cat1, cat2]
                union = cooccurrence.loc[cat1, cat1] + cooccurrence.loc[cat2, cat2] - intersection

                if union > 0:
                    normalized.loc[cat1, cat2] = intersection / union
                else:
                    normalized.loc[cat1, cat2] = 0.0

        return normalized

    def find_correlated_pairs(
        self,
        correlation_df: pd.DataFrame,
        threshold: float = 0.3
    ) -> List[Tuple[str, str, float]]:
        """Find highly correlated category pairs.

        Args:
            correlation_df: Correlation DataFrame from analyze().
            threshold: Minimum correlation threshold.

        Returns:
            List of (category1, category2, correlation) tuples.
        """
        pairs = []
        categories = correlation_df.index

        for i, cat1 in enumerate(categories):
            for j, cat2 in enumerate(categories):
                if i < j:  # Avoid duplicates
                    corr = correlation_df.loc[cat1, cat2]
                    if corr >= threshold:
                        pairs.append((cat1, cat2, corr))

        # Sort by correlation descending
        pairs.sort(key=lambda x: x[2], reverse=True)

        return pairs

    def get_demand_clusters(
        self,
        correlation_df: pd.DataFrame,
        threshold: float = 0.3
    ) -> List[List[str]]:
        """Cluster categories based on correlation.

        Args:
            correlation_df: Correlation DataFrame from analyze().
            threshold: Minimum correlation for clustering.

        Returns:
            List of clusters (each cluster is a list of categories).
        """
        categories = correlation_df.index.tolist()
        visited = set()
        clusters = []

        def dfs(cat, cluster):
            visited.add(cat)
            cluster.append(cat)
            for other in categories:
                if other not in visited and correlation_df.loc[cat, other] >= threshold:
                    dfs(other, cluster)

        for cat in categories:
            if cat not in visited:
                cluster = []
                dfs(cat, cluster)
                if cluster:
                    clusters.append(cluster)

        return clusters
