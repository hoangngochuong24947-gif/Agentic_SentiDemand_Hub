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
from comment_analyzer.visualization.gallery import create_app, run_gallery_server

__all__ = ["VisualizationGenerator", "create_app", "run_gallery_server"]
