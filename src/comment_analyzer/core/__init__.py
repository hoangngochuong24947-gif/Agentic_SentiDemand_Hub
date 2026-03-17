"""Core components for comment_analyzer."""

# Legacy config (for backward compatibility)
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
    get_settings,
    init_settings,
    reset_settings,
)

# Output and log managers
from comment_analyzer.core.output_manager import OutputManager, SavedFileInfo
from comment_analyzer.core.log_manager import LogManager, get_log_manager, init_logging

# Pipeline
from comment_analyzer.core.pipeline import CommentPipeline, PipelineResults

__all__ = [
    # Legacy
    "Config",
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
    "get_settings",
    "init_settings",
    "reset_settings",
    # Managers
    "OutputManager",
    "SavedFileInfo",
    "LogManager",
    "get_log_manager",
    "init_logging",
    # Pipeline
    "CommentPipeline",
    "PipelineResults",
]
