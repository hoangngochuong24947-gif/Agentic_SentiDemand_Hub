"""Tests for Pydantic-based settings module."""

import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from comment_analyzer.core.settings import (
    Settings,
    PathConfig,
    DataConfig,
    SentimentConfig,
    SnowNLPConfig,
    TFIDFConfig,
    get_settings,
    init_settings,
    reset_settings,
)


class TestPathConfig:
    """Tests for PathConfig model."""

    def test_default_paths(self):
        """Test default path configuration."""
        config = PathConfig()
        assert config.output_base == Path("./outputs")
        assert config.demand_folder == "demand_analysis"
        assert config.sentiment_folder == "sentiment_models"
        assert config.word_frequency_folder == "word_frequency"
        assert config.derived_columns_folder == "derived_columns"
        assert config.logs_folder == "logs"

    def test_custom_paths(self):
        """Test custom path configuration."""
        config = PathConfig(
            output_base=Path("/custom/output"),
            demand_folder="custom_demand"
        )
        assert config.output_base == Path("/custom/output")
        assert config.demand_folder == "custom_demand"

    def test_expanduser_paths(self):
        """Test '~' paths are expanded to user home."""
        config = PathConfig(
            visualization_base="~/.sentidemand/outputs",
            upload_dir="~/.sentidemand/uploads",
        )
        assert str(config.visualization_base).startswith(str(Path.home()))
        assert str(config.upload_dir).startswith(str(Path.home()))

    def test_path_getters(self):
        """Test path getter methods."""
        config = PathConfig()
        assert config.get_demand_path() == Path("./outputs/demand_analysis")
        assert config.get_sentiment_path() == Path("./outputs/sentiment_models")
        assert config.get_word_frequency_path() == Path("./outputs/word_frequency")
        assert config.get_derived_columns_path() == Path("./outputs/derived_columns")
        assert config.get_logs_path() == Path("./outputs/logs")

    def test_ensure_directories(self, tmp_path):
        """Test directory creation."""
        config = PathConfig(
            output_base=tmp_path / "test_outputs",
            visualization_base=tmp_path / "vis_outputs",
            upload_dir=tmp_path / "uploads",
        )
        config.ensure_directories()

        assert (tmp_path / "test_outputs" / "demand_analysis").exists()
        assert (tmp_path / "test_outputs" / "sentiment_models").exists()
        assert (tmp_path / "test_outputs" / "word_frequency").exists()
        assert (tmp_path / "test_outputs" / "derived_columns").exists()
        assert (tmp_path / "test_outputs" / "logs").exists()
        assert (tmp_path / "vis_outputs").exists()
        assert (tmp_path / "uploads").exists()


class TestSnowNLPConfig:
    """Tests for SnowNLPConfig model."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        config = SnowNLPConfig()
        assert config.threshold_positive == 0.6
        assert config.threshold_negative == 0.4

    def test_valid_thresholds(self):
        """Test valid threshold configuration."""
        config = SnowNLPConfig(threshold_positive=0.7, threshold_negative=0.3)
        assert config.threshold_positive == 0.7
        assert config.threshold_negative == 0.3

    def test_invalid_thresholds_range(self):
        """Test invalid threshold values (out of range)."""
        with pytest.raises(ValidationError):
            SnowNLPConfig(threshold_positive=1.5)

        with pytest.raises(ValidationError):
            SnowNLPConfig(threshold_negative=-0.1)

    def test_invalid_thresholds_order(self):
        """Test invalid threshold values (positive <= negative)."""
        with pytest.raises(ValidationError):
            SnowNLPConfig(threshold_positive=0.4, threshold_negative=0.6)


class TestTFIDFConfig:
    """Tests for TFIDFConfig model."""

    def test_default_ngram_range(self):
        """Test default ngram range."""
        config = TFIDFConfig()
        assert config.ngram_range == [1, 2]

    def test_valid_ngram_range(self):
        """Test valid ngram range."""
        config = TFIDFConfig(ngram_range=[2, 3])
        assert config.ngram_range == [2, 3]

    def test_invalid_ngram_range_length(self):
        """Test invalid ngram range (wrong length)."""
        with pytest.raises(ValidationError):
            TFIDFConfig(ngram_range=[1, 2, 3])

    def test_invalid_ngram_range_order(self):
        """Test invalid ngram range (wrong order)."""
        with pytest.raises(ValidationError):
            TFIDFConfig(ngram_range=[3, 2])


class TestSettings:
    """Tests for main Settings model."""

    def test_default_settings(self):
        """Test default settings creation."""
        settings = Settings()
        assert settings.app_name == "comment-analyzer"
        assert settings.app_version == "0.2.0"
        assert settings.debug is False

    def test_nested_config_access(self):
        """Test accessing nested configuration."""
        settings = Settings()
        assert settings.data.platform == "generic"
        assert settings.sentiment.labeling_method == "snownlp"
        assert settings.topic.lda.num_topics == 5

    def test_get_stopwords_path_default(self, tmp_path):
        """Test getting default stopwords path."""
        settings = Settings()
        settings.paths.config_dir = tmp_path

        path = settings.get_stopwords_path()
        assert path == tmp_path / "stopwords.txt"

    def test_get_stopwords_path_disabled(self):
        """Test getting stopwords path when disabled."""
        settings = Settings()
        settings.preprocessing.stopwords.use_default = False

        path = settings.get_stopwords_path()
        assert path is None

    def test_get_demand_keywords_path(self, tmp_path):
        """Test getting demand keywords path."""
        settings = Settings()
        settings.paths.config_dir = tmp_path

        path = settings.get_demand_keywords_path()
        assert path == tmp_path / "demand_keywords.json"

    def test_to_dict(self):
        """Test converting settings to dictionary."""
        settings = Settings()
        data = settings.to_dict()

        assert "app_name" in data
        assert "data" in data
        assert "preprocessing" in data

    def test_to_yaml_file(self, tmp_path):
        """Test saving settings to YAML file."""
        settings = Settings()
        yaml_path = tmp_path / "config.yaml"

        settings.to_yaml_file(yaml_path)

        assert yaml_path.exists()
        content = yaml_path.read_text(encoding='utf-8')
        assert "app_name" in content


class TestSettingsEnvironmentVariables:
    """Tests for settings loading from environment variables."""

    def test_env_var_string(self, monkeypatch):
        """Test loading string from environment variable."""
        monkeypatch.setenv("COMMENT_ANALYZER_APP_NAME", "test-app")

        settings = Settings()
        assert settings.app_name == "test-app"

    def test_env_var_boolean(self, monkeypatch):
        """Test loading boolean from environment variable."""
        monkeypatch.setenv("COMMENT_ANALYZER_DEBUG", "true")

        settings = Settings()
        assert settings.debug is True

    def test_env_var_nested(self, monkeypatch):
        """Test loading nested config from environment variable."""
        monkeypatch.setenv("COMMENT_ANALYZER_DATA__PLATFORM", "jd")

        settings = Settings()
        assert settings.data.platform == "jd"


class TestGlobalSettings:
    """Tests for global settings singleton."""

    def test_get_settings_singleton(self):
        """Test that get_settings returns singleton."""
        reset_settings()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_reset_settings(self):
        """Test resetting global settings."""
        reset_settings()
        settings1 = get_settings()
        reset_settings()
        settings2 = get_settings()
        assert settings1 is not settings2

    def test_init_settings(self):
        """Test initializing settings."""
        reset_settings()
        settings = init_settings()
        assert isinstance(settings, Settings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
