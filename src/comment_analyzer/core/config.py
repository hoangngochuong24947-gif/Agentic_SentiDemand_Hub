"""Configuration management for comment_analyzer.

This module provides a flexible configuration system using YAML files
with support for programmatic overrides.

Note: This module is maintained for backward compatibility.
New code should use the Settings class from settings.py which provides
type-safe Pydantic-based configuration.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

# Import new settings system for migration path
from comment_analyzer.core.settings import (
    Settings,
    PathConfig,
    get_settings,
    init_settings,
)


class Config:
    """Configuration manager for comment analysis pipeline.

    Provides a hierarchical configuration system with defaults,
    file-based configuration, and programmatic overrides.

    Note: This class is maintained for backward compatibility.
    For new code, use Settings from comment_analyzer.core.settings.

    Attributes:
        data (ConfigSection): Data loading configuration
        preprocessing (ConfigSection): Preprocessing settings
        sentiment (ConfigSection): Sentiment analysis settings
        topic (ConfigSection): Topic modeling settings
        demand (ConfigSection): Demand analysis settings
        output (ConfigSection): Output settings
        paths (PathConfig): Path configuration (new in v0.2.0)

    Example:
        >>> # Load from YAML file
        >>> config = Config.from_yaml("config/default.yaml")
        >>>
        >>> # Programmatic configuration
        >>> config = Config()
        >>> config.sentiment.models.svm.C = 2.0
        >>>
        >>> # Access nested values
        >>> max_features = config.get("sentiment.tfidf.max_features")
        >>>
        >>> # Get the new Settings object (migration path)
        >>> settings = config.to_settings()
    """

    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "default.yaml"

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize configuration.

        Args:
            config_dict: Optional configuration dictionary to use as base.
                        If None, uses built-in defaults.
        """
        if config_dict is None:
            self._config = self._load_default_config()
        else:
            self._config = config_dict

        # Initialize new path config
        self.paths = PathConfig(**self._config.get("paths", {}))

        # Set up attribute accessors for common sections
        self._setup_accessors()

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration from file."""
        if self.DEFAULT_CONFIG_PATH.exists():
            with open(self.DEFAULT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return self._get_builtin_defaults()

    def _get_builtin_defaults(self) -> Dict[str, Any]:
        """Return built-in default configuration."""
        return {
            "data": {
                "platform": "generic",
                "text_column_keywords": ["content", "comment", "review", "text", "评论", "内容"],
                "rating_column_keywords": ["rating", "score", "star", "评分", "星级"],
                "date_column_keywords": ["date", "time", "created", "时间", "日期"],
            },
            "preprocessing": {
                "clean": {
                    "remove_urls": True,
                    "remove_emails": True,
                    "remove_html": True,
                    "remove_extra_spaces": True,
                    "normalize_whitespace": True,
                },
                "segmentation": {
                    "mode": "precise",
                    "custom_dict_path": None,
                },
                "stopwords": {
                    "use_default": True,
                    "custom_path": None,
                    "extra_words": [],
                },
            },
            "sentiment": {
                "labeling_method": "snownlp",
                "snownlp": {
                    "threshold_positive": 0.6,
                    "threshold_negative": 0.4,
                },
                "balance": {
                    "enabled": True,
                    "method": "undersample",
                    "random_state": 42,
                },
                "tfidf": {
                    "max_features": 5000,
                    "min_df": 2,
                    "max_df": 0.95,
                    "ngram_range": [1, 2],
                },
                "models": {
                    "naive_bayes": {"enabled": True, "alpha": 1.0},
                    "svm": {"enabled": True, "kernel": "linear", "C": 1.0},
                    "logistic_regression": {"enabled": True, "C": 1.0, "max_iter": 1000},
                },
            },
            "topic": {
                "keywords": {
                    "method": "tfidf",
                    "top_k": 20,
                },
                "lda": {
                    "num_topics": 5,
                    "passes": 15,
                    "iterations": 100,
                    "alpha": "auto",
                    "eta": "auto",
                    "random_state": 42,
                },
            },
            "demand": {
                "intensity": {
                    "method": "tfidf_weighted",
                    "normalization": "minmax",
                },
                "correlation": {
                    "method": "cooccurrence",
                    "min_cooccurrence": 2,
                    "window_size": 50,
                },
            },
            "output": {
                "save_intermediate": False,
                "encoding": "utf-8",
                "float_format": "%.4f",
                "use_sequence_numbers": True,
                "sequence_padding": 3,
            },
            "paths": {
                "output_base": "./outputs",
                "visualization_base": "~/.sentidemand/outputs",
                "upload_dir": "~/.sentidemand/uploads",
            },
            "visualization": {
                "theme": "dark",
                "locale": "zh-CN",
                "auto_open_browser": True,
                "gallery_port": 8765,
                "charts": {
                    "sentiment_donut": True,
                    "sentiment_wordcloud": True,
                    "sentiment_distribution": True,
                    "sentiment_scatter": True,
                    "features_bidirectional": True,
                    "features_lollipop": True,
                    "features_heatmap": True,
                    "features_tfidf_scatter": True,
                    "topics_nightingale": True,
                    "topics_bubble": True,
                    "topics_radar": True,
                    "demand_funnel": True,
                    "demand_network": True,
                    "demand_dashboard": True,
                },
            },
        }

    def _setup_accessors(self):
        """Set up attribute accessors for common configuration sections."""
        # These allow dot-notation access like config.sentiment.models.svm.C
        self.data = ConfigSection(self._config.get("data", {}))
        self.preprocessing = ConfigSection(self._config.get("preprocessing", {}))
        self.sentiment = ConfigSection(self._config.get("sentiment", {}))
        self.topic = ConfigSection(self._config.get("topic", {}))
        self.demand = ConfigSection(self._config.get("demand", {}))
        self.output = ConfigSection(self._config.get("output", {}))
        self.visualization = ConfigSection(self._config.get("visualization", {}))

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "Config":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file.

        Returns:
            Config instance loaded from file.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the file is not valid YAML.
        """
        path = Path(path)
        with open(path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        return cls(config_dict)

    def to_yaml(self, path: Union[str, Path]) -> None:
        """Save configuration to YAML file.

        Args:
            path: Path to save the configuration file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.

        Args:
            key: Dot-separated key path (e.g., "sentiment.tfidf.max_features")
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation.

        Args:
            key: Dot-separated key path.
            value: Value to set.
        """
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._setup_accessors()  # Re-setup accessors after modification

    def get_stopwords_path(self) -> Optional[Path]:
        """Get the path to stopwords file.

        Returns:
            Path to stopwords file or None if not using default.
        """
        custom_path = self.preprocessing.stopwords.custom_path
        if custom_path:
            return Path(custom_path)
        if self.preprocessing.stopwords.use_default:
            return self.paths.config_dir / "stopwords.txt"
        return None

    def get_demand_keywords_path(self) -> Path:
        """Get the path to demand keywords file.

        Returns:
            Path to demand_keywords.json file.
        """
        return self.paths.config_dir / "demand_keywords.json"

    def to_settings(self) -> Settings:
        """Convert this Config to the new Settings object.

        This is a migration path for transitioning from Config to Settings.

        Returns:
            Settings instance with equivalent configuration.
        """
        warnings.warn(
            "Config.to_settings() is deprecated. Use Settings directly.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Convert the internal dict to a Settings object
        return Settings(**self._config)

    def __repr__(self) -> str:
        return f"Config(platform={self.data.platform})"


class ConfigSection:
    """Helper class for accessing nested configuration sections.

    Allows dot-notation access to dictionary values.
    """

    def __init__(self, data: Dict[str, Any]):
        """Initialize with configuration dictionary.

        Args:
            data: Configuration dictionary for this section.
        """
        self._data = data

        # Recursively create ConfigSections for nested dicts
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigSection(value))
            else:
                setattr(self, key, value)

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        """Check if key exists in this section."""
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        """Get value with default."""
        return self._data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert back to dictionary."""
        return self._data
