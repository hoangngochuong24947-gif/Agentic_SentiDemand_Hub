"""Tests for LogManager module."""

import json
from pathlib import Path

import pytest

from comment_analyzer.core.log_manager import LogManager, get_log_manager, init_logging
from comment_analyzer.core.settings import Settings, LoggingConfig


class TestLogManagerInitialization:
    """Tests for LogManager initialization."""

    def test_default_initialization(self):
        """Test initialization with default settings."""
        manager = LogManager()
        assert manager.settings is not None
        assert manager._log_entries == []

    def test_custom_settings(self):
        """Test initialization with custom settings."""
        settings = Settings()
        manager = LogManager(settings)
        assert manager.settings is settings


class TestLogManagerAnalysisLogging:
    """Tests for analysis logging functionality."""

    def test_log_analysis(self, tmp_path):
        """Test logging analysis results."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        data = {"positive": 100, "negative": 50}
        manager.log_analysis("sentiment", data, extra={"source": "test"})

        entries = manager.get_log_entries(entry_type="analysis")
        assert len(entries) == 1
        assert entries[0]["analysis_type"] == "sentiment"
        assert entries[0]["data"] == data

    def test_log_important(self, tmp_path):
        """Test logging important messages."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        manager.log_important("Test message", category="test", data={"key": "value"})

        entries = manager.get_log_entries(entry_type="important")
        assert len(entries) == 1
        assert entries[0]["message"] == "Test message"
        assert entries[0]["category"] == "test"

    def test_log_model_result(self, tmp_path):
        """Test logging model results."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        metrics = {"accuracy": 0.95, "f1": 0.94}
        params = {"C": 1.0, "kernel": "linear"}
        manager.log_model_result("svm", metrics, params)

        entries = manager.get_log_entries(entry_type="model_result")
        assert len(entries) == 1
        assert entries[0]["model_name"] == "svm"
        assert entries[0]["metrics"] == metrics


class TestLogManagerPipelineLogging:
    """Tests for pipeline logging."""

    def test_log_pipeline_start(self, tmp_path):
        """Test logging pipeline start."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        config = {"platform": "test", "rows": 100}
        manager.log_pipeline_start(config)

        # Should not throw exception

    def test_log_pipeline_end(self, tmp_path):
        """Test logging pipeline end."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        results = {"total_comments": 100, "sentiment": {"pos": 50}}
        manager.log_pipeline_end(10.5, results)

        entries = manager.get_log_entries(entry_type="important")
        assert len(entries) == 1
        assert entries[0]["data"]["duration_seconds"] == 10.5


class TestLogManagerDataLogging:
    """Tests for data logging."""

    def test_log_data_info(self, tmp_path):
        """Test logging data information."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        column_info = {"text": "object", "label": "int64"}
        manager.log_data_info("test_data", 1000, column_info)

        # Should not throw exception

    def test_log_error(self, tmp_path):
        """Test logging errors."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        error = ValueError("Test error")
        context = {"stage": "preprocessing"}
        manager.log_error(error, context, category="runtime")

        # Should not throw exception


class TestLogManagerEntryManagement:
    """Tests for log entry management."""

    def test_get_log_entries_by_type(self, tmp_path):
        """Test getting log entries filtered by type."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        manager.log_analysis("test1", {})
        manager.log_important("msg1", category="cat1")
        manager.log_analysis("test2", {})

        analysis_entries = manager.get_log_entries(entry_type="analysis")
        assert len(analysis_entries) == 2

        important_entries = manager.get_log_entries(entry_type="important")
        assert len(important_entries) == 1

    def test_get_log_entries_by_category(self, tmp_path):
        """Test getting log entries filtered by category."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        manager.log_important("msg1", category="cat1")
        manager.log_important("msg2", category="cat2")
        manager.log_important("msg3", category="cat1")

        cat1_entries = manager.get_log_entries(entry_type="important", category="cat1")
        assert len(cat1_entries) == 2

    def test_clear_entries(self, tmp_path):
        """Test clearing log entries."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        manager.log_analysis("test", {})
        assert len(manager._log_entries) == 1

        manager.clear_entries()
        assert len(manager._log_entries) == 0


class TestLogManagerExport:
    """Tests for log entry export."""

    def test_export_log_entries_default_path(self, tmp_path):
        """Test exporting log entries to default path."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        manager.log_analysis("test", {"key": "value"})

        path = manager.export_log_entries()

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["total_entries"] == 1
        assert len(data["entries"]) == 1

    def test_export_log_entries_custom_path(self, tmp_path):
        """Test exporting log entries to custom path."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        manager.log_analysis("test", {})

        custom_path = tmp_path / "custom_export.json"
        path = manager.export_log_entries(custom_path)

        assert path == custom_path
        assert path.exists()

    def test_export_log_entries_filtered(self, tmp_path):
        """Test exporting log entries with type filter."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = LogManager(settings)
        manager.configure()

        manager.log_analysis("test", {})
        manager.log_important("msg", category="test")

        path = manager.export_log_entries(entry_type="analysis")

        data = json.loads(path.read_text())
        assert data["total_entries"] == 1
        assert data["entries"][0]["type"] == "analysis"


class TestGlobalLogManager:
    """Tests for global log manager singleton."""

    def test_get_log_manager(self):
        """Test that get_log_manager returns a LogManager."""
        manager = get_log_manager()
        assert isinstance(manager, LogManager)

    def test_init_logging(self, tmp_path):
        """Test initializing logging."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.logging.log_to_file = False
        settings.logging.log_to_console = False

        manager = init_logging(settings)
        assert isinstance(manager, LogManager)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
