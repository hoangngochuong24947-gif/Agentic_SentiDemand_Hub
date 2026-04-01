"""Demo script for async orchestration and profile-enhanced analysis."""

from __future__ import annotations

import asyncio

import pandas as pd

from comment_analyzer import CommentPipeline


def build_demo_dataframe() -> pd.DataFrame:
    """Create a compact demo dataset with profile fields."""
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


async def main() -> None:
    """Run the demo pipeline and print a concise result digest."""
    pipeline = CommentPipeline()
    results = await pipeline.run_async(build_demo_dataframe(), text_column="comment", verbose=False)

    print("analysis_strategy:", results.analysis_strategy)
    print("detected_dimensions:", results.profile_analysis.get("detected_dimensions", []))
    print("top_segment:", results.profile_analysis.get("segment_insights", [])[:1])
    print("progress_messages:", results.progress_messages[:2])
    print("top_keywords:", results.top_keywords[:5])


if __name__ == "__main__":
    asyncio.run(main())
