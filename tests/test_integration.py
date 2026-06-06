"""Integration tests for the complete system."""

import json
from pathlib import Path

import pandas as pd
import pytest

from comment_analyzer import CommentPipeline, Settings
from comment_analyzer.core.log_manager import init_logging
from comment_analyzer.core.output_manager import OutputManager


class TestEndToEndPipeline:
    """End-to-end integration tests."""

    @pytest.fixture
    def sample_data(self):
        """Create sample comment data for testing."""
        return pd.DataFrame({
            "id": range(1, 21),
            "content": [
                "这个产品非常好用，很喜欢！",
                "质量一般，性价比不高",
                "发货速度快，包装完好",
                "客服态度差，不满意",
                "价格实惠，推荐购买",
                "产品有问题，需要退货",
                "使用效果不错，会回购",
                "物流太慢了，等了很久",
                "质量很好，物超所值",
                "外观设计漂亮，功能齐全",
                "操作复杂，不太会用",
                "售后服务很好，解决问题快",
                "颜色不喜欢，想换货",
                "功能强大，满足需求",
                "电池续航短，需要改进",
                "屏幕清晰，显示效果好",
                "声音太小，听不清楚",
                "安装简单，使用方便",
                "配件齐全，性价比很高",
                "整体满意，五星好评",
            ]
        })

    @pytest.fixture
    def temp_settings(self, tmp_path):
        """Create temporary settings for testing."""
        settings = Settings()
        settings.paths.output_base = tmp_path / "test_outputs"
        settings.logging.log_to_file = True
        settings.logging.log_to_console = False
        settings.topic.lda.num_topics = 3  # Reduce for faster tests
        settings.sentiment.tfidf.max_features = 100  # Reduce for faster tests
        return settings

    def test_full_pipeline_execution(self, sample_data, temp_settings):
        """Test full pipeline execution with new system."""
        # Initialize logging
        init_logging(temp_settings)

        # Create pipeline
        pipeline = CommentPipeline(settings=temp_settings)

        # Run pipeline
        results = pipeline.run(sample_data, verbose=False)

        # Verify results
        assert results is not None
        assert len(results.processed_data) == len(sample_data)
        assert results.sentiment_distribution is not None
        assert len(results.top_keywords) > 0
        assert len(results.topics) > 0

    def test_pipeline_results_save_with_categories(self, sample_data, temp_settings):
        """Test that pipeline results are saved to categorized folders."""
        init_logging(temp_settings)

        pipeline = CommentPipeline(settings=temp_settings)
        results = pipeline.run(sample_data, verbose=False)

        # Save results
        results.save()

        # Verify categorized folders exist
        output_base = temp_settings.paths.output_base
        assert (output_base / "demand_analysis").exists()
        assert (output_base / "sentiment_models").exists()
        assert (output_base / "word_frequency").exists()
        assert (output_base / "derived_columns").exists()
        assert (output_base / "logs").exists()

        # Verify files were created
        demand_files = list((output_base / "demand_analysis").glob("*.csv"))
        sentiment_files = list((output_base / "sentiment_models").glob("*.csv"))
        wordfreq_files = list((output_base / "word_frequency").glob("*.csv"))
        derived_files = list((output_base / "derived_columns").glob("*.csv"))

        assert len(demand_files) > 0
        assert len(sentiment_files) > 0
        assert len(wordfreq_files) > 0
        assert len(derived_files) > 0

        # Verify sequence numbering - at least one file should have 001_
        assert any(f.name.startswith("001_") for f in demand_files)

    def test_multiple_runs_increment_sequences(self, sample_data, temp_settings):
        """Test that multiple runs increment sequence numbers."""
        init_logging(temp_settings)

        pipeline = CommentPipeline(settings=temp_settings)

        # Run twice
        results1 = pipeline.run(sample_data, verbose=False)
        results1.save()

        results2 = pipeline.run(sample_data, verbose=False)
        results2.save()

        # Verify sequence numbers
        output_base = temp_settings.paths.output_base
        demand_files = sorted((output_base / "demand_analysis").glob("*.csv"))

        assert len(demand_files) >= 2
        assert "001_" in demand_files[0].name
        assert "002_" in demand_files[1].name

    def test_log_entries_created(self, sample_data, temp_settings):
        """Test that important log entries are created."""
        log_manager = init_logging(temp_settings)

        pipeline = CommentPipeline(settings=temp_settings, log_manager=log_manager)
        results = pipeline.run(sample_data, verbose=False)
        results.save()

        # Export and verify log entries
        log_path = log_manager.export_log_entries()

        assert log_path.exists()
        data = json.loads(log_path.read_text(encoding='utf-8'))

        # Should have multiple log entries
        assert data["total_entries"] > 0

        # Check for important entries
        important_entries = [
            e for e in data["entries"]
            if e.get("type") == "important"
        ]
        assert len(important_entries) > 0

    def test_saved_files_tracking(self, sample_data, temp_settings):
        """Test that saved files are tracked correctly."""
        init_logging(temp_settings)

        pipeline = CommentPipeline(settings=temp_settings)
        results = pipeline.run(sample_data, verbose=False)
        results.save()

        # Verify saved files are tracked
        assert len(results.saved_files) > 0

        # Verify each saved file has correct info
        for info in results.saved_files:
            assert info.final_path.exists()
            assert info.category in ["demand", "sentiment", "word_frequency", "derived"]
            assert info.sequence_number > 0

    def test_custom_output_directory(self, sample_data, temp_settings, tmp_path):
        """Test saving to custom output directory."""
        init_logging(temp_settings)

        pipeline = CommentPipeline(settings=temp_settings)
        results = pipeline.run(sample_data, verbose=False)

        # Save to custom directory
        custom_dir = tmp_path / "custom_output"
        results.save(custom_dir)

        # Verify files in custom directory
        assert (custom_dir / "demand_analysis").exists()
        assert (custom_dir / "sentiment_models").exists()


class TestConfigurationIntegration:
    """Tests for configuration system integration."""

    def test_settings_from_environment(self, monkeypatch, tmp_path):
        """Test loading settings from environment variables."""
        monkeypatch.setenv("COMMENT_ANALYZER_PATHS__OUTPUT_BASE", str(tmp_path / "env_output"))
        monkeypatch.setenv("COMMENT_ANALYZER_DATA__PLATFORM", "jd")
        monkeypatch.setenv("COMMENT_ANALYZER_TOPIC__LDA__NUM_TOPICS", "10")

        from comment_analyzer.core.settings import Settings
        settings = Settings()

        assert str(settings.paths.output_base) == str(tmp_path / "env_output")
        assert settings.data.platform == "jd"
        assert settings.topic.lda.num_topics == 10

    def test_output_manager_with_custom_settings(self, tmp_path):
        """Test OutputManager with custom settings."""
        settings = Settings()
        settings.paths.output_base = tmp_path / "custom"
        settings.output.sequence_padding = 4

        manager = OutputManager(settings)

        df = pd.DataFrame({"col": [1, 2, 3]})
        info = manager.save_dataframe(df, "test.csv", category="demand")

        assert info.final_path.name.startswith("0001_")

    def test_legacy_config_compatibility(self, tmp_path):
        """Test that legacy Config still works."""
        from comment_analyzer.core.config import Config

        config = Config()

        # Should be able to access nested values
        assert config.data.platform == "generic"
        assert config.sentiment.labeling_method == "snownlp"

        # Should be able to use with pipeline
        from comment_analyzer import CommentPipeline

        pipeline = CommentPipeline(config=config)
        assert pipeline.settings is not None


class TestErrorHandling:
    """Tests for error handling in the new system."""

    @pytest.fixture
    def temp_settings(self, tmp_path):
        """Create temporary settings for testing."""
        from comment_analyzer.core.settings import Settings
        settings = Settings()
        settings.paths.output_base = tmp_path / "test_outputs"
        settings.logging.log_to_file = True
        settings.logging.log_to_console = False
        settings.topic.lda.num_topics = 3
        settings.sentiment.tfidf.max_features = 100
        return settings

    def test_invalid_settings_validation(self):
        """Test that invalid settings raise validation errors."""
        from comment_analyzer.core.settings import SnowNLPConfig
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SnowNLPConfig(threshold_positive=0.3, threshold_negative=0.7)

    def test_pipeline_with_empty_data(self, temp_settings):
        """Test pipeline behavior with empty data."""
        init_logging(temp_settings)

        empty_data = pd.DataFrame({"content": []})

        pipeline = CommentPipeline(settings=temp_settings)

        # Should handle empty data gracefully
        results = pipeline.run(empty_data, verbose=False)

        assert results is not None
        assert len(results.processed_data) == 0

    def test_output_manager_with_invalid_category(self, tmp_path):
        """Test OutputManager with invalid category creates folder."""
        settings = Settings()
        settings.paths.output_base = tmp_path

        manager = OutputManager(settings)

        df = pd.DataFrame({"col": [1, 2, 3]})
        info = manager.save_dataframe(df, "test.csv", category="invalid_category")

        # Should create the folder anyway
        assert (tmp_path / "invalid_category").exists()
        assert info.final_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
