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

Memory note: this package imports its heavy analysis dependencies
(pandas, scikit-learn, gensim, jieba, snownlp) lazily so that lightweight
consumers such as the visualization gallery server do not pay the ~500 MB
import cost up front. Access ``comment_analyzer.CommentPipeline`` (or import
``comment_analyzer.core.pipeline``) explicitly when analysis is needed.

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

_LAZY_IMPORTS = {
    "Config": ("comment_analyzer.core.config", "Config"),
    "CommentPipeline": ("comment_analyzer.core.pipeline", "CommentPipeline"),
    "PipelineResults": ("comment_analyzer.core.pipeline", "PipelineResults"),
    "Settings": ("comment_analyzer.core.settings", "Settings"),
    "PathConfig": ("comment_analyzer.core.settings", "PathConfig"),
    "DataConfig": ("comment_analyzer.core.settings", "DataConfig"),
    "PreprocessingConfig": ("comment_analyzer.core.settings", "PreprocessingConfig"),
    "SentimentConfig": ("comment_analyzer.core.settings", "SentimentConfig"),
    "TopicConfig": ("comment_analyzer.core.settings", "TopicConfig"),
    "DemandConfig": ("comment_analyzer.core.settings", "DemandConfig"),
    "OutputConfig": ("comment_analyzer.core.settings", "OutputConfig"),
    "LoggingConfig": ("comment_analyzer.core.settings", "LoggingConfig"),
    "VisualizationConfig": ("comment_analyzer.core.settings", "VisualizationConfig"),
    "get_settings": ("comment_analyzer.core.settings", "get_settings"),
    "init_settings": ("comment_analyzer.core.settings", "init_settings"),
    "OutputManager": ("comment_analyzer.core.output_manager", "OutputManager"),
    "SavedFileInfo": ("comment_analyzer.core.output_manager", "SavedFileInfo"),
    "LogManager": ("comment_analyzer.core.log_manager", "LogManager"),
    "get_log_manager": ("comment_analyzer.core.log_manager", "get_log_manager"),
    "init_logging": ("comment_analyzer.core.log_manager", "init_logging"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        import importlib

        module_name, attr = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_name)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
