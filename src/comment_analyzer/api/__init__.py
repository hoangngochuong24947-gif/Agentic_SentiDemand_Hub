"""Stable FastAPI v1 entry points for comment_analyzer."""

from comment_analyzer.api.main import app, create_app

__all__ = ["app", "create_app"]
