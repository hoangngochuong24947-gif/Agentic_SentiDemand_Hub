"""Core components for comment_analyzer."""

from comment_analyzer.core.config import Config
from comment_analyzer.core.pipeline import CommentPipeline, PipelineResults

__all__ = ["Config", "CommentPipeline", "PipelineResults"]
