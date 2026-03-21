"""Tests for core pipeline module."""

import pandas as pd
import pytest

from comment_analyzer.core.config import Config
from comment_analyzer.core.pipeline import CommentPipeline, PipelineResults


class TestConfig:
    """Tests for Config class."""

    def test_default_config(self):
        config = Config()
        assert config.data.platform == "generic"
        assert config.sentiment.tfidf.max_features > 0

    def test_from_yaml(self, tmp_path):
        yaml_content = """
data:
  platform: jd
sentiment:
  tfidf:
    max_features: 1000
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml_content)

        config = Config.from_yaml(config_file)
        assert config.data.platform == "jd"
        assert config.get("sentiment.tfidf.max_features") == 1000

    def test_get_method(self):
        config = Config()
        assert config.get("data.platform") == "generic"
        assert config.get("nonexistent.key", "default") == "default"

    def test_set_method(self):
        config = Config()
        config.set("custom.key", "value")
        assert config.get("custom.key") == "value"

    def test_stopwords_path(self):
        config = Config()
        path = config.get_stopwords_path()
        assert path is not None

    def test_demand_keywords_path(self):
        config = Config()
        path = config.get_demand_keywords_path()
        assert path is not None


class TestPipelineResults:
    """Tests for PipelineResults class."""

    def test_summary(self):
        df = pd.DataFrame({"text": ["test1", "test2"]})
        results = PipelineResults(
            original_data=df,
            processed_data=df,
            sentiment_distribution={"positive": 10, "negative": 5},
            top_keywords=[("word", 0.5)],
            topics=[{"id": 0, "words": [("test", 0.1)], "weight": 0.5}],
        )
        summary = results.summary()
        assert "Total comments" in summary
        assert "Sentiment Distribution" in summary

    def test_save(self, tmp_path):
        df = pd.DataFrame({"text": ["test1", "test2"], "processed": ["p1", "p2"]})
        results = PipelineResults(
            original_data=df,
            processed_data=df,
            sentiment_distribution={"positive": 10},
            top_keywords=[("word", 0.5)],
        )
        output_dir = tmp_path / "output"
        results.save(output_dir)
        assert (output_dir / "processed_data.csv").exists()

    def test_run_record_summary(self):
        df = pd.DataFrame({"text": ["test1", "test2"]})
        results = PipelineResults(
            original_data=df,
            processed_data=df,
            sentiment_distribution={"positive": 1, "negative": 1},
            top_keywords=[("word", 0.5)],
            topics=[{"id": 0, "words": [("test", 0.1)]}],
        )

        record = results.to_run_record(
            run_id="run-123",
            source_file="comments.csv",
            user_message="Upload completed",
            charts=[{"name": "sentiment_donut", "path": "charts/sentiment_donut.html"}],
        )

        assert record["run_id"] == "run-123"
        assert record["source_file"] == "comments.csv"
        assert record["status"] == "completed"
        assert record["derived_tables"]
        assert record["logs"]
        assert record["charts"]
        assert record["user_message"] == "Upload completed"


class TestCommentPipeline:
    """Tests for CommentPipeline class."""

    def test_initialization(self):
        pipeline = CommentPipeline()
        assert pipeline.config is not None
        assert pipeline.cleaner is not None
        assert pipeline.segmenter is not None

    def test_initialization_with_config(self):
        config = Config()
        pipeline = CommentPipeline(config)
        assert pipeline.config == config

    def test_detect_text_column(self):
        pipeline = CommentPipeline()
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "comment": ["很好", "不错", "一般"],
            "rating": [5, 4, 3],
        })
        col = pipeline.detect_text_column(df)
        assert col == "comment"

    def test_detect_text_column_auto(self):
        pipeline = CommentPipeline()
        df = pd.DataFrame({
            "id": [1, 2],
            "review_content": ["This is a very long review text", "Another long review text here"],
        })
        col = pipeline.detect_text_column(df)
        assert col == "review_content"

    def test_detect_text_column_error(self):
        pipeline = CommentPipeline()
        df = pd.DataFrame({"id": [1], "num": [2]})
        with pytest.raises(ValueError):
            pipeline.detect_text_column(df)

    def test_run_pipeline(self):
        pipeline = CommentPipeline()
        df = pd.DataFrame({
            "comment": ["产品质量很好", "服务不错", "物流很快"] * 10,
        })
        results = pipeline.run(df, text_column="comment", verbose=False)
        assert isinstance(results, PipelineResults)
        assert len(results.processed_data) == len(df)

    def test_load_data_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({"comment": ["test1", "test2"], "rating": [5, 4]})
        df.to_csv(csv_file, index=False)

        pipeline = CommentPipeline()
        loaded = pipeline.load_data(csv_file)
        assert len(loaded) == 2
        assert "comment" in loaded.columns

    def test_load_data_not_found(self):
        pipeline = CommentPipeline()
        with pytest.raises(FileNotFoundError):
            pipeline.load_data("nonexistent.csv")
