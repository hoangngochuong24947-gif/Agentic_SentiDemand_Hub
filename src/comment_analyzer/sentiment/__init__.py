"""Sentiment analysis modules for comment_analyzer.

This package provides sentiment labeling, vectorization, and classification
capabilities for comment sentiment analysis.
"""

from comment_analyzer.sentiment.labeler import SentimentLabeler
from comment_analyzer.sentiment.vectorizer import TFIDFVectorizer
from comment_analyzer.sentiment.classifier import Classifier, ModelResults

__all__ = ["SentimentLabeler", "TFIDFVectorizer", "Classifier", "ModelResults"]
