"""Tests for OutputManager module."""

import json
from pathlib import Path

import pandas as pd
import pytest

from comment_analyzer.core.output_manager import OutputManager, SavedFileInfo
from comment_analyzer.core.settings import Settings, PathConfig


class TestSavedFileInfo:
    """Tests for SavedFileInfo dataclass."""

    def test_creation(self):
        """Test creating SavedFileInfo."""
        info = SavedFileInfo(
            category="demand",
            original_name="test.csv",
            sequence_number=1,
            final_path=Path("outputs/demand/001_test.csv")
        )
        assert info.category == "demand"
        assert info.original_name == "test.csv"
        assert info.sequence_number == 1

    def test_string_representation(self):
        """Test string representation."""
        info = SavedFileInfo(
            category="demand",
            original_name="test.csv",
            sequence_number=1,
            final_path=Path("outputs/demand/001_test.csv")
        )
        str_repr = str(info)
        assert "demand" in str_repr
        assert "test.csv" in str_repr


class TestOutputManagerInitialization:
    """Tests for OutputManager initialization."""

    def test_default_initialization(self):
        """Test initialization with default settings."""
        manager = OutputManager()
        assert manager.settings is not None
        assert manager._saved_files == []

    def test_custom_settings(self):
        """Test initialization with custom settings."""
        settings = Settings()
        manager = OutputManager(settings)
        assert manager.settings is settings


class TestOutputManagerSequenceNumbering:
    """Tests for sequence numbering functionality."""

    def test_get_next_sequence_number_empty_folder(self, tmp_path):
        """Test getting sequence number for empty folder."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        folder = tmp_path / "test"
        folder.mkdir()

        seq = manager._get_next_sequence_number(folder)
        assert seq == 1

    def test_get_next_sequence_number_with_files(self, tmp_path):
        """Test getting sequence number with existing files."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        folder = tmp_path / "test"
        folder.mkdir()

        # Create existing files
        (folder / "001_file.csv").touch()
        (folder / "002_file.csv").touch()
        (folder / "005_file.csv").touch()

        seq = manager._get_next_sequence_number(folder)
        assert seq == 6

    def test_generate_filename_with_sequence(self, tmp_path):
        """Test filename generation with sequence."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        folder = tmp_path / "test"
        folder.mkdir()

        filename, seq = manager._generate_filename("test.csv", folder, use_sequence=True)
        assert filename == "001_test.csv"
        assert seq == 1

    def test_generate_filename_without_sequence(self, tmp_path):
        """Test filename generation without sequence."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        folder = tmp_path / "test"
        folder.mkdir()

        filename, seq = manager._generate_filename("test.csv", folder, use_sequence=False)
        assert filename == "test.csv"
        assert seq == 0

    def test_sequence_padding(self, tmp_path):
        """Test sequence number padding."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        settings.output.sequence_padding = 5
        manager = OutputManager(settings)

        folder = tmp_path / "test"
        folder.mkdir()

        filename, seq = manager._generate_filename("test.csv", folder, use_sequence=True)
        assert filename == "00001_test.csv"


class TestOutputManagerSaveDataFrame:
    """Tests for saving DataFrames."""

    def test_save_dataframe_with_sequence(self, tmp_path):
        """Test saving DataFrame with sequence numbering."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

        info = manager.save_dataframe(df, "data.csv", category="demand", use_sequence=True)

        assert info.sequence_number == 1
        assert info.final_path.exists()
        assert info.final_path.name == "001_data.csv"

    def test_save_dataframe_without_sequence(self, tmp_path):
        """Test saving DataFrame without sequence numbering."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        df = pd.DataFrame({"col1": [1, 2, 3]})

        info = manager.save_dataframe(df, "data.csv", category="demand", use_sequence=False)

        assert info.sequence_number == 0
        assert info.final_path.name == "data.csv"

    def test_save_multiple_dataframes_increments_sequence(self, tmp_path):
        """Test that saving multiple files increments sequence."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        df = pd.DataFrame({"col1": [1, 2, 3]})

        info1 = manager.save_dataframe(df, "data.csv", category="demand", use_sequence=True)
        info2 = manager.save_dataframe(df, "data.csv", category="demand", use_sequence=True)
        info3 = manager.save_dataframe(df, "data.csv", category="demand", use_sequence=True)

        assert info1.sequence_number == 1
        assert info2.sequence_number == 2
        assert info3.sequence_number == 3

        assert info1.final_path.name == "001_data.csv"
        assert info2.final_path.name == "002_data.csv"
        assert info3.final_path.name == "003_data.csv"

    def test_save_dataframe_different_categories(self, tmp_path):
        """Test saving DataFrames to different categories."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        df = pd.DataFrame({"col1": [1, 2, 3]})

        info1 = manager.save_dataframe(df, "data.csv", category="demand", use_sequence=True)
        info2 = manager.save_dataframe(df, "data.csv", category="sentiment", use_sequence=True)

        assert info1.sequence_number == 1
        assert info2.sequence_number == 1
        assert "demand" in str(info1.final_path)
        assert "sentiment" in str(info2.final_path)


class TestOutputManagerSaveText:
    """Tests for saving text files."""

    def test_save_text_with_sequence(self, tmp_path):
        """Test saving text with sequence numbering."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        content = "This is a test report."

        info = manager.save_text(content, "report.txt", category="sentiment", use_sequence=True)

        assert info.sequence_number == 1
        assert info.final_path.exists()
        # Handle BOM if present
        raw_content = info.final_path.read_bytes()
        if raw_content.startswith(b'\xef\xbb\xbf'):
            saved_content = raw_content[3:].decode('utf-8')
        else:
            saved_content = raw_content.decode('utf-8')
        assert saved_content == content


class TestOutputManagerSaveJSON:
    """Tests for saving JSON files."""

    def test_save_json_with_sequence(self, tmp_path):
        """Test saving JSON with sequence numbering."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        data = {"key": "value", "number": 42}

        info = manager.save_json(data, "data.json", category="demand", use_sequence=True)

        assert info.sequence_number == 1
        assert info.final_path.exists()

        loaded = json.loads(info.final_path.read_text(encoding='utf-8'))
        assert loaded == data


class TestOutputManagerSaveExcel:
    """Tests for saving Excel files."""

    @pytest.mark.skip(reason="openpyxl not installed")
    def test_save_excel_with_sequence(self, tmp_path):
        """Test saving Excel with sequence numbering."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

        info = manager.save_excel(df, "data.xlsx", category="derived", use_sequence=True)

        assert info.sequence_number == 1
        assert info.final_path.exists()

        # Verify it can be read back
        df_read = pd.read_excel(info.final_path)
        assert len(df_read) == 3


class TestOutputManagerFileTracking:
    """Tests for file tracking functionality."""

    def test_get_saved_files(self, tmp_path):
        """Test getting saved files list."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        df = pd.DataFrame({"col1": [1, 2, 3]})
        manager.save_dataframe(df, "data.csv", category="demand")
        manager.save_dataframe(df, "data.csv", category="sentiment")

        all_files = manager.get_saved_files()
        assert len(all_files) == 2

        demand_files = manager.get_saved_files(category="demand")
        assert len(demand_files) == 1

    def test_get_latest_file(self, tmp_path):
        """Test getting latest file in category."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        df = pd.DataFrame({"col1": [1, 2, 3]})
        manager.save_dataframe(df, "data1.csv", category="demand")
        import time
        time.sleep(0.01)
        manager.save_dataframe(df, "data2.csv", category="demand")

        latest = manager.get_latest_file("demand")
        assert latest is not None
        assert "data2" in latest.final_path.name

    def test_list_category_files(self, tmp_path):
        """Test listing files in category."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        df = pd.DataFrame({"col1": [1, 2, 3]})
        manager.save_dataframe(df, "data.csv", category="demand")

        files = manager.list_category_files("demand")
        assert len(files) == 1


class TestOutputManagerSummary:
    """Tests for summary generation."""

    def test_generate_summary(self, tmp_path):
        """Test generating summary."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        df = pd.DataFrame({"col1": [1, 2, 3]})
        manager.save_dataframe(df, "data.csv", category="demand")
        manager.save_dataframe(df, "data.csv", category="sentiment")

        summary = manager.generate_summary()
        assert "Output Summary" in summary
        assert "Total files saved: 2" in summary
        assert "demand" in summary
        assert "sentiment" in summary


class TestOutputManagerClear:
    """Tests for clearing categories."""

    def test_clear_category_without_confirm(self, tmp_path):
        """Test clearing category without confirm does nothing."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        df = pd.DataFrame({"col1": [1, 2, 3]})
        manager.save_dataframe(df, "data.csv", category="demand")

        count = manager.clear_category("demand", confirm=False)
        assert count == 0

        files = manager.list_category_files("demand")
        assert len(files) == 1

    def test_clear_category_with_confirm(self, tmp_path):
        """Test clearing category with confirm."""
        settings = Settings()
        settings.paths.output_base = tmp_path
        manager = OutputManager(settings)

        df = pd.DataFrame({"col1": [1, 2, 3]})
        manager.save_dataframe(df, "data1.csv", category="demand")
        manager.save_dataframe(df, "data2.csv", category="demand")

        count = manager.clear_category("demand", confirm=True)
        assert count == 2

        files = manager.list_category_files("demand")
        assert len(files) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
