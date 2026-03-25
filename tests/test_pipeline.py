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
        assert (output_dir / "derived_columns" / "001_processed_data.csv").exists()
        assert (output_dir / "derived_columns" / "002_ai_briefing.json").exists()


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

    def test_preprocessing_filters_punctuation_tokens(self):
        pipeline = CommentPipeline()
        df = pd.DataFrame({
            "comment": ["很好，真的很好！！！, ,", "包装不错，，物流很快。。。", "味道一般，但服务可以"] * 4,
        })
        results = pipeline.run(df, text_column="comment", verbose=False)
        flattened = [token for row in results.processed_data["filtered_text"] for token in row]
        assert "," not in flattened
        assert "，" not in flattened
        assert "。" not in flattened

    def test_build_ai_briefing(self):
        pipeline = CommentPipeline()
        df = pd.DataFrame({
            "comment": ["产品做工很好，包装也不错", "物流偏慢，希望快一点", "整体满意，但希望价格更稳"] * 4,
        })
        results = pipeline.run(df, text_column="comment", verbose=False)
        briefing = results.build_ai_briefing(source_name="unit_test")
        assert briefing.payload["source_name"] == "unit_test"
        assert "评论洞察分析师" in briefing.system_prompt
        assert "sentiment_distribution" in briefing.payload
