"""Tests for visualization generator and Hub integration points."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from comment_analyzer.core.settings import PathConfig, Settings
from comment_analyzer.visualization import gallery
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
    """Tests for Hub server bootstrap behavior."""

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

    def test_workspace_and_manifest_routes_use_run_registry(self, tmp_path: Path):
        settings = Settings(
            paths=PathConfig(
                output_base=tmp_path / "outputs",
                visualization_base=tmp_path / "vis_outputs",
                upload_dir=tmp_path / "uploads",
            )
        )

        fastapi_available = importlib.util.find_spec("fastapi") is not None
        if not fastapi_available:
            pytest.skip("fastapi is required for route tests")

        run_registry = settings.paths.get_visualization_path() / "run_registry.json"
        run_registry.parent.mkdir(parents=True, exist_ok=True)
        run_registry.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "runs": [
                        {
                            "run_id": "demo-run",
                            "source_file": "sample_comments.csv",
                            "created_at": "2026-03-18T09:12:00",
                            "status": "completed",
                            "derived_tables": [],
                            "logs": [],
                            "charts": [],
                            "user_message": "上传成功，已生成派生表格、日志和图表。",
                            "summary": {"chart_count": 0},
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        from fastapi.testclient import TestClient

        client = TestClient(create_app(settings=settings))

        home = client.get("/")
        assert home.status_code == 200
        assert "选择评论文件" in home.text
        assert "sample_comments.csv" in home.text

        workspace = client.get("/workspace")
        assert workspace.status_code == 200
        assert "历史文件与分析运行工作台" in workspace.text
        assert "sample_comments.csv" in workspace.text

        manifest = client.get("/api/manifest")
        assert manifest.status_code == 200
        payload = manifest.json()
        assert payload["version"] == "2.0"
        assert payload["total_runs"] == 1
        assert payload["runs"][0]["run_id"] == "demo-run"

        detail = client.get("/api/runs/demo-run")
        assert detail.status_code == 200
        assert detail.json()["source_file"] == "sample_comments.csv"

    def test_upload_failure_reports_category(self, tmp_path: Path, monkeypatch):
        settings = Settings(
            paths=PathConfig(
                output_base=tmp_path / "outputs",
                visualization_base=tmp_path / "vis_outputs",
                upload_dir=tmp_path / "uploads",
            )
        )

        class BrokenPipeline:
            def __init__(self, settings=None):
                self.settings = settings

            def load_data(self, path):
                raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")

        fastapi_available = importlib.util.find_spec("fastapi") is not None
        if not fastapi_available:
            pytest.skip("fastapi is required for upload endpoint tests")

        monkeypatch.setattr(gallery, "CommentPipeline", BrokenPipeline)

        from fastapi.testclient import TestClient

        app = create_app(settings=settings)
        client = TestClient(app)

        response = client.post(
            "/upload",
            files={"file": ("bad.csv", b"\xff", "text/csv")},
        )

        assert response.status_code == 422
        assert "UTF-8" in response.json()["detail"]

    def test_upload_success_registers_run_and_artifacts(self, tmp_path: Path, monkeypatch):
        settings = Settings(
            paths=PathConfig(
                output_base=tmp_path / "outputs",
                visualization_base=tmp_path / "vis_outputs",
                upload_dir=tmp_path / "uploads",
            )
        )

        fastapi_available = importlib.util.find_spec("fastapi") is not None
        if not fastapi_available:
            pytest.skip("fastapi is required for upload endpoint tests")

        class DummySavedFileInfo:
            def __init__(self, category: str, original_name: str, final_path: Path):
                self.category = category
                self.original_name = original_name
                self.final_path = final_path

        class FakeLogManager:
            def export_log_entries(self, output_path):
                output = Path(output_path)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps({"entries": [{"message": "processed"}]}, ensure_ascii=False), encoding="utf-8")
                return output

            def get_log_entries(self):
                return [{"type": "important", "category": "pipeline", "message": "processed"}]

        class FakeResults:
            def __init__(self, app_settings: Settings):
                self.settings = app_settings
                self.run_id = "run123"
                self.saved_files = []
                self.log_manager = FakeLogManager()

            def save(self, output_dir=None):
                target_dir = Path(output_dir)
                target_dir.mkdir(parents=True, exist_ok=True)
                table = target_dir / "processed_data.csv"
                table.write_text("comment,label\nhello,pos\n", encoding="utf-8")
                self.saved_files = [DummySavedFileInfo("derived", "processed_data.csv", table)]

            def summary(self):
                return "Summary line 1\nSummary line 2"

            def visualize(self, source_name="analysis", run_id=None):
                chart_dir = self.settings.paths.get_visualization_path() / "sample_20260318"
                chart_dir.mkdir(parents=True, exist_ok=True)
                chart_path = chart_dir / "sentiment_donut_101010.html"
                chart_path.write_text("<html><body>chart</body></html>", encoding="utf-8")
                manifest = {
                    "version": "1.0",
                    "entries": [
                        {
                            "id": "chart1234",
                            "run_id": run_id or self.run_id,
                            "source_file": source_name,
                            "chart_type": "sentiment_donut",
                            "chart_title": "Sentiment donut",
                            "output_path": str(chart_path.relative_to(self.settings.paths.get_visualization_path())).replace("\\", "/"),
                            "created_at": "2026-03-18T10:10:10",
                        }
                    ],
                }
                (self.settings.paths.get_visualization_path() / "manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return [str(chart_path)]

        class FakePipeline:
            def __init__(self, settings=None):
                self.settings = settings

            def load_data(self, path):
                return [{"comment": "hello"}]

            def run(self, dataframe, verbose=False):
                return FakeResults(self.settings)

        monkeypatch.setattr(gallery, "CommentPipeline", FakePipeline)

        from fastapi.testclient import TestClient

        client = TestClient(create_app(settings=settings))
        response = client.post(
            "/upload",
            files={"file": ("comments.csv", b"comment\nhello\n", "text/csv")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["run_id"] == "run123"
        assert payload["artifacts"]["derived_tables"] == 1
        assert payload["artifacts"]["logs"] >= 1
        assert payload["artifacts"]["charts"] == 1
        assert "CSV" in " ".join(payload["how_to_upload"])

        manifest = client.get("/api/runs/run123")
        assert manifest.status_code == 200
        run_payload = manifest.json()
        assert run_payload["source_file"].endswith("comments.csv")
        assert len(run_payload["derived_tables"]) == 1
        assert len(run_payload["charts"]) == 1

        detail_page = client.get("/runs/run123")
        assert detail_page.status_code == 200
        assert "派生表格" in detail_page.text
        assert "日志" in detail_page.text
        assert "图表" in detail_page.text
