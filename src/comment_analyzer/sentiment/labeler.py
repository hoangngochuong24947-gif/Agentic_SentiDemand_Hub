"""Sentiment labeling module for comment_analyzer.

Provides sentiment labeling capabilities using SnowNLP and other methods.
"""

from typing import List, Optional, Union

import pandas as pd
from snownlp import SnowNLP
from tqdm import tqdm


class SentimentLabeler:
    """Sentiment labeler for Chinese text.

    Labels text with sentiment scores using SnowNLP or rating-based methods.
    Supports positive/negative/neutral classification.

    Example:
        >>> labeler = SentimentLabeler(method='snownlp')
        >>> labeler.label("这个产品非常好！")
        'positive'

        >>> # Get raw score
        >>> labeler.get_score("质量一般")
        0.5

        >>> # Batch processing
        >>> labeler.label_batch(["很好", "很差", "一般"])
        ['positive', 'negative', 'neutral']
    """

    def __init__(
        self,
        method: str = "snownlp",
        threshold_positive: float = 0.6,
        threshold_negative: float = 0.4,
    ):
        """Initialize the sentiment labeler.

        Args:
            method: Labeling method. Options: 'snownlp', 'rating'.
            threshold_positive: Score threshold for positive sentiment (0-1).
            threshold_negative: Score threshold for negative sentiment (0-1).

        Raises:
            ValueError: If method is not supported.
        """
        if method not in ('snownlp', 'rating'):
            raise ValueError(f"Invalid method: {method}. Choose from 'snownlp', 'rating'")

        self.method = method
        self.threshold_positive = threshold_positive
        self.threshold_negative = threshold_negative

    def get_score(self, text: str) -> float:
        """Get sentiment score for text.

        Args:
            text: Input text.

        Returns:
            Sentiment score between 0 and 1.
        """
        if not text or not isinstance(text, str):
            return 0.5

        if self.method == 'snownlp':
            try:
                s = SnowNLP(text)
                return s.sentiments
            except Exception:
                return 0.5
        else:
            return 0.5

    def label(self, text: str) -> str:
        """Label text with sentiment category.

        Args:
            text: Input text.

        Returns:
            Sentiment label: 'positive', 'negative', or 'neutral'.
        """
        score = self.get_score(text)

        if score >= self.threshold_positive:
            return 'positive'
        elif score <= self.threshold_negative:
            return 'negative'
        else:
            return 'neutral'

    def label_batch(
        self,
        texts: Union[List[str], pd.Series],
        verbose: bool = False
    ) -> List[str]:
        """Label multiple texts with sentiment.

        Args:
            texts: List or Series of texts to label.
            verbose: Whether to show progress bar.

        Returns:
            List of sentiment labels.
        """
        if verbose:
            texts = tqdm(texts, desc="Labeling sentiment")

        return [self.label(text) for text in texts]

    def label_from_rating(
        self,
        ratings: Union[List[float], pd.Series],
        max_rating: float = 5.0,
        positive_threshold: float = 0.6,
        negative_threshold: float = 0.4
    ) -> List[str]:
        """Label sentiment from numerical ratings.

        Args:
            ratings: List or Series of ratings.
            max_rating: Maximum possible rating value.
            positive_threshold: Threshold for positive (as ratio of max).
            negative_threshold: Threshold for negative (as ratio of max).

        Returns:
            List of sentiment labels.
        """
        labels = []
        for rating in ratings:
            if pd.isna(rating):
                labels.append('neutral')
                continue

            normalized = float(rating) / max_rating

            if normalized >= positive_threshold:
                labels.append('positive')
            elif normalized <= negative_threshold:
                labels.append('negative')
            else:
                labels.append('neutral')

        return labels

    def get_sentiment_distribution(self, labels: List[str]) -> dict:
        """Calculate distribution of sentiment labels.

        Args:
            labels: List of sentiment labels.

        Returns:
            Dictionary with label counts and percentages.
        """
        total = len(labels)
        if total == 0:
            return {}

        counts = {}
        for label in ['positive', 'negative', 'neutral']:
            count = labels.count(label)
            counts[label] = {
                'count': count,
                'percentage': count / total * 100
            }

        return counts
