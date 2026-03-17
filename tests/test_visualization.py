"""Tests for visualization generator and gallery integration points."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from comment_analyzer.core.settings import PathConfig, Settings
from comment_analyzer.visualization.gallery import create_app
from comment_analyzer.visualization.generator import VisualizationGenerator


class TestVisualizationGenerator:
    """Unit tests for visualization generator utilities."""

    def test_restore_js_functions(self):
        payload = {
            "tooltip": {
                "formatter": "__JS_FUNC__function(p){return p.value;}__JS_FUNC__",
            }
        }
        dumped = json.dumps(payload, ensure_ascii=False)
        restored = VisualizationGenerator._restore_js_functions(dumped)

        assert "__JS_FUNC__" not in restored
        assert '"formatter": function(p){return p.value;}' in restored

    def test_prepare_output_dir_sanitizes_source_name(self, tmp_path: Path):
        settings = Settings(
            paths=PathConfig(
                output_base=tmp_path / "outputs",
                visualization_base=tmp_path / "vis_outputs",
                upload_dir=tmp_path / "uploads",
            )
        )
        gen = VisualizationGenerator(settings=settings, results=object())

        out_dir = gen._prepare_output_dir("../weird source name.csv")

        assert out_dir.exists()
        assert out_dir.resolve().parent == settings.paths.get_visualization_path().resolve()
        assert ".." not in out_dir.name


class TestVisualizationGallery:
    """Tests for gallery server bootstrap behavior."""

    def test_create_app_dependency_behavior(self, tmp_path: Path):
        settings = Settings(
            paths=PathConfig(
                output_base=tmp_path / "outputs",
                visualization_base=tmp_path / "vis_outputs",
                upload_dir=tmp_path / "uploads",
            )
        )

        fastapi_available = importlib.util.find_spec("fastapi") is not None
        if not fastapi_available:
            with pytest.raises(RuntimeError, match="optional dependencies"):
                create_app(settings=settings)
            return

        app = create_app(settings=settings)
        assert app.title == "SentiDemand Visualization Gallery"
