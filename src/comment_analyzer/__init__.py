"""
Comment Analyzer - A generic NLP analysis toolkit for e-commerce comments and reviews.

This package provides tools for:
- Data preprocessing (text cleaning, segmentation, filtering)
- Sentiment analysis (multi-model classification)
- Topic modeling (TF-IDF and LDA)
- Demand insights (intensity and correlation analysis)

New in v0.2.0:
- Pydantic-based type-safe configuration
- Structured logging with Loguru
- Automatic sequence numbering for outputs
- Categorized output folders

Example:
    >>> from comment_analyzer import CommentPipeline, Settings
    >>> from comment_analyzer.core.log_manager import init_logging
    >>>
    >>> # Initialize logging
    >>> init_logging()
    >>>
    >>> # Load settings
    >>> settings = Settings()
    >>>
    >>> # Create pipeline with settings
    >>> pipeline = CommentPipeline(settings=settings)
    >>>
    >>> # Load and analyze data
    >>> df = pipeline.load_data("comments.csv")
    >>> results = pipeline.run(df)
    >>>
    >>> # Save results to categorized folders
    >>> results.save()
    >>>
    >>> # Access output manager for custom saves
    >>> from comment_analyzer.core.output_manager import OutputManager
    >>> manager = OutputManager()
    >>> manager.save_dataframe(df, "custom.csv", category="demand")
"""

from comment_analyzer.core.config import Config

# New Pydantic-based settings
from comment_analyzer.core.settings import (
    Settings,
    PathConfig,
    DataConfig,
    PreprocessingConfig,
    SentimentConfig,
    TopicConfig,
    DemandConfig,
    OutputConfig,
    LoggingConfig,
    VisualizationConfig,
    get_settings,
    init_settings,
)

# Managers
from comment_analyzer.core.output_manager import OutputManager, SavedFileInfo
from comment_analyzer.core.log_manager import LogManager, get_log_manager, init_logging

__version__ = "0.2.0"
__author__ = "Comment Analyzer Team"

__all__ = [
    # Legacy
    "Config",
    "CommentPipeline",
    "PipelineResults",
    # New Settings
    "Settings",
    "PathConfig",
    "DataConfig",
    "PreprocessingConfig",
    "SentimentConfig",
    "TopicConfig",
    "DemandConfig",
    "OutputConfig",
    "LoggingConfig",
    "VisualizationConfig",
    "get_settings",
    "init_settings",
    # Managers
    "OutputManager",
    "SavedFileInfo",
    "LogManager",
    "get_log_manager",
    "init_logging",
]


def __getattr__(name: str):
    if name in {"CommentPipeline", "PipelineResults"}:
        from comment_analyzer.core.pipeline import CommentPipeline, PipelineResults

        exports = {
            "CommentPipeline": CommentPipeline,
            "PipelineResults": PipelineResults,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
