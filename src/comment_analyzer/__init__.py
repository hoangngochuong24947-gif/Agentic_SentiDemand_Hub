"""
Comment Analyzer - A generic NLP analysis toolkit for e-commerce comments and reviews.

This package provides tools for:
- Data preprocessing (text cleaning, segmentation, filtering)
- Sentiment analysis (multi-model classification)
- Topic modeling (TF-IDF and LDA)
- Demand insights (intensity and correlation analysis)

Example:
    >>> from comment_analyzer import CommentPipeline, Config
    >>> config = Config.from_yaml("config.yaml")
    >>> pipeline = CommentPipeline(config)
    >>> results = pipeline.run(data)
"""

from comment_analyzer.core.config import Config
from comment_analyzer.core.pipeline import CommentPipeline, PipelineResults

__version__ = "0.1.0"
__author__ = "Comment Analyzer Team"

__all__ = [
    "Config",
    "CommentPipeline",
    "PipelineResults",
]
