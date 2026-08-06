"""Core components for comment_analyzer."""

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

_LAZY_IMPORTS = {
    "Config": ("comment_analyzer.core.config", "Config"),
    "Settings": ("comment_analyzer.core.settings", "Settings"),
    "PathConfig": ("comment_analyzer.core.settings", "PathConfig"),
    "DataConfig": ("comment_analyzer.core.settings", "DataConfig"),
    "PreprocessingConfig": ("comment_analyzer.core.settings", "PreprocessingConfig"),
    "SentimentConfig": ("comment_analyzer.core.settings", "SentimentConfig"),
    "TopicConfig": ("comment_analyzer.core.settings", "TopicConfig"),
    "DemandConfig": ("comment_analyzer.core.settings", "DemandConfig"),
    "OutputConfig": ("comment_analyzer.core.settings", "OutputConfig"),
    "LoggingConfig": ("comment_analyzer.core.settings", "LoggingConfig"),
    "get_settings": ("comment_analyzer.core.settings", "get_settings"),
    "init_settings": ("comment_analyzer.core.settings", "init_settings"),
    "reset_settings": ("comment_analyzer.core.settings", "reset_settings"),
    "OutputManager": ("comment_analyzer.core.output_manager", "OutputManager"),
    "SavedFileInfo": ("comment_analyzer.core.output_manager", "SavedFileInfo"),
    "LogManager": ("comment_analyzer.core.log_manager", "LogManager"),
    "get_log_manager": ("comment_analyzer.core.log_manager", "get_log_manager"),
    "init_logging": ("comment_analyzer.core.log_manager", "init_logging"),
    "CommentPipeline": ("comment_analyzer.core.pipeline", "CommentPipeline"),
    "PipelineResults": ("comment_analyzer.core.pipeline", "PipelineResults"),
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
