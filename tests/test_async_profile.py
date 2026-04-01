"""Tests for async orchestration, profile-aware analysis, and progress copy."""

from __future__ import annotations

import asyncio
import time

import pandas as pd

from comment_analyzer.core.pipeline import CommentPipeline, PipelineResults


def _build_profiled_comments() -> pd.DataFrame:
    """Create a compact demo dataset with demographic attributes."""
    return pd.DataFrame(
        {
            "comment": [
                "物流非常快，包装很完整，体验很好",
                "价格有点高，希望活动再多一些",
                "续航不错，但是外观颜色选择太少",
                "客服回复很耐心，不过发货再快一点更好",
                "很适合通勤使用，安装也简单",
                "功能比较全，但说明书还不够清楚",
            ]
            * 4,
            "gender": ["女", "男", "女", "男", "女", "男"] * 4,
            "age": [22, 31, 27, 36, 24, 42] * 4,
            "region": ["华东", "华南", "华东", "华北", "西南", "华南"] * 4,
        }
    )


class TestAsyncProfilePipeline:
    """Coverage for profile-enhanced analysis and async orchestration."""

    def test_profile_enhanced_strategy_is_selected_with_demographics(self):
        pipeline = CommentPipeline()
        results = pipeline.run(_build_profiled_comments(), text_column="comment", verbose=False)

        assert results.analysis_strategy == "profile_enhanced"
        assert results.profile_analysis is not None
        assert set(results.profile_analysis["detected_dimensions"]) == {"gender", "age", "region"}
        assert results.profile_analysis["dimension_summaries"]
        assert results.profile_analysis["segment_insights"]

    def test_generic_strategy_is_used_without_demographics(self):
        pipeline = CommentPipeline()
        df = pd.DataFrame(
            {
                "comment": [
                    "整体满意，做工不错",
                    "物流偏慢，希望改进",
                    "价格合理，性价比高",
                ]
                * 4
            }
        )

        results = pipeline.run(df, text_column="comment", verbose=False)

        assert results.analysis_strategy == "generic"
        assert results.profile_analysis is not None
        assert results.profile_analysis["detected_dimensions"] == []
        assert results.profile_analysis["segment_insights"] == []

    def test_progress_messages_include_wait_copy_tips_and_delivery_phrases(self):
        pipeline = CommentPipeline()
        results = pipeline.run(_build_profiled_comments(), text_column="comment", verbose=False)

        assert results.progress_messages
        assert len(results.progress_messages) >= 4
        assert all(item["encouragement"] for item in results.progress_messages)
        assert all(item["analysis_tip"] for item in results.progress_messages)
        assert all(item["delivery_copy"] for item in results.progress_messages)

    def test_run_async_executes_independent_analysis_tasks_concurrently(self, monkeypatch):
        pipeline = CommentPipeline()
        df = _build_profiled_comments()

        def fake_preprocessing(input_df, text_column, verbose):
            staged = input_df.copy()
            staged["cleaned_text"] = staged[text_column]
            staged["normalized_text"] = staged[text_column]
            staged["analysis_text"] = staged[text_column]
            staged["segmented_text"] = [["示例", "评论"]] * len(staged)
            staged["filtered_text"] = [["示例", "评论"]] * len(staged)
            staged["processed_text"] = ["示例 评论"] * len(staged)
            return staged

        def fake_sentiment(input_df, verbose):
            time.sleep(0.2)
            return {"distribution": {"positive": len(input_df)}, "models": {}}

        def fake_topic(input_df, verbose):
            time.sleep(0.2)
            return {"keywords": [("示例", 1.0)], "topics": [{"id": 0, "words": [("示例", 1.0)]}]}

        def fake_demand(input_df, verbose):
            time.sleep(0.2)
            return {
                "intensity": pd.DataFrame([{"quality": 0.8}]),
                "correlation": pd.DataFrame([[1.0]], columns=["quality"], index=["quality"]),
            }

        def fake_profile(input_df, verbose):
            time.sleep(0.2)
            return {
                "strategy": "profile_enhanced",
                "detected_dimensions": ["gender"],
                "coverage": {"gender": 1.0},
                "dimension_summaries": [{"dimension": "gender", "value": "女", "sample_size": 2}],
                "segment_insights": [{"segment": "gender=女", "sample_size": 2}],
            }

        monkeypatch.setattr(pipeline, "_run_preprocessing", fake_preprocessing)
        monkeypatch.setattr(pipeline, "_run_sentiment_analysis", fake_sentiment)
        monkeypatch.setattr(pipeline, "_run_topic_modeling", fake_topic)
        monkeypatch.setattr(pipeline, "_run_demand_analysis", fake_demand)
        monkeypatch.setattr(pipeline, "_run_profile_analysis", fake_profile)

        started = time.perf_counter()
        results = asyncio.run(pipeline.run_async(df, text_column="comment", verbose=False))
        elapsed = time.perf_counter() - started

        assert isinstance(results, PipelineResults)
        assert elapsed < 0.55
        assert results.analysis_strategy == "profile_enhanced"
