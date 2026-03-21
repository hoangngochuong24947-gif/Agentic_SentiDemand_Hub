"""Visualization module for Comment Analyzer.

Generates standalone, interactive HTML charts using ECharts
that can be opened in any browser.

Usage:
    >>> results = pipeline.run(df)
    >>> files = results.visualize(source_name="jd_comments")
    >>> # Or use the generator directly
    >>> from comment_analyzer.visualization import VisualizationGenerator
    >>> gen = VisualizationGenerator(settings, results)
    >>> gen.generate_all("jd_comments")
"""

from comment_analyzer.visualization.generator import VisualizationGenerator
from comment_analyzer.visualization.pages import (
    DEFAULT_CRAWLER_GUIDANCE,
    CrawlerGuideCard,
    render_detail_page,
    render_homepage_page,
    render_workspace_page,
)

__all__ = [
    "VisualizationGenerator",
    "create_app",
    "run_gallery_server",
    "DEFAULT_CRAWLER_GUIDANCE",
    "CrawlerGuideCard",
    "render_detail_page",
    "render_homepage_page",
    "render_workspace_page",
]


def __getattr__(name: str):
    if name in {"create_app", "run_gallery_server"}:
        from comment_analyzer.visualization.gallery import create_app, run_gallery_server

        exports = {
            "create_app": create_app,
            "run_gallery_server": run_gallery_server,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
