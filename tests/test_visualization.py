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

    def test_routes_use_new_information_architecture(self, tmp_path: Path):
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

        run_id = "demo-run"
        run_dir = settings.paths.output_base / "workspace_runs" / run_id
        charts_dir = run_dir / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)
        chart_file = charts_dir / "sentiment_donut_101010.html"
        chart_file.write_text("<html><body>chart</body></html>", encoding="utf-8")

        run_registry = settings.paths.get_visualization_path() / "run_registry.json"
        run_registry.parent.mkdir(parents=True, exist_ok=True)
        run_registry.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "runs": [
                        {
                            "run_id": run_id,
                            "source_file": "sample_comments.csv",
                            "created_at": "2026-03-18T09:12:00",
                            "status": "completed",
                            "derived_tables": [],
                            "logs": [],
                            "charts": [
                                {
                                    "type": "chart",
                                    "name": "sentiment_donut",
                                    "title": "Sentiment donut",
                                    "summary": "Chart ready",
                                    "status": "ready",
                                    "reason": "",
                                    "path": str(chart_file),
                                    "downloadable": True,
                                }
                            ],
                            "chart_failures": ["demand_network"],
                            "insight_status": "not_generated",
                            "insight_updated_at": "",
                            "insights": [],
                            "user_message": "上传成功，分析完成。",
                            "summary": {"chart_count": 1, "saved_file_count": 0, "log_file_count": 0},
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
        assert "上传并分析" in home.text
        assert "sample_comments.csv" in home.text

        workspace = client.get("/workspace")
        assert workspace.status_code == 200
        assert "表格工作台" in workspace.text

        workspace_run = client.get(f"/workspace/{run_id}")
        assert workspace_run.status_code == 200
        assert "sample_comments.csv" in workspace_run.text

        dashboard = client.get(f"/dashboard/{run_id}")
        assert dashboard.status_code == 200
        assert "chart-iframe" in dashboard.text

        insights = client.get(f"/insights/{run_id}")
        assert insights.status_code == 200
        assert "DeepSeek API Key" in insights.text

        legacy = client.get("/legacy")
        assert legacy.status_code == 200
        assert "旧版入口" in legacy.text

        manifest = client.get("/api/manifest")
        assert manifest.status_code == 200
        payload = manifest.json()
        assert payload["version"] == "3.0"
        assert payload["total_runs"] == 1

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

        client = TestClient(create_app(settings=settings))
        response = client.post("/upload", files={"file": ("bad.csv", b"\xff", "text/csv")})

        assert response.status_code == 422
        assert "UTF-8" in response.json()["detail"]

    def test_upload_success_registers_run_and_chart_audit(self, tmp_path: Path, monkeypatch):
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
        response = client.post("/upload", files={"file": ("comments.csv", b"comment\nhello\n", "text/csv")})

        assert response.status_code == 200
        payload = response.json()
        assert payload["run_id"] == "run123"
        assert payload["artifacts"]["derived_tables"] == 1
        assert payload["artifacts"]["logs"] >= 1
        assert payload["artifacts"]["charts"] == 1
        assert payload["artifacts"]["missing_charts"] >= 1

        run_payload = client.get("/api/runs/run123").json()
        assert run_payload["source_file"].endswith("comments.csv")
        assert len(run_payload["derived_tables"]) == 1
        assert len(run_payload["charts"]) >= 1
        assert "chart_failures" in run_payload
        assert run_payload["summary"]["chart_count"] == 1

    def test_deepseek_session_and_insight_generation(self, tmp_path: Path, monkeypatch):
        settings = Settings(
            paths=PathConfig(
                output_base=tmp_path / "outputs",
                visualization_base=tmp_path / "vis_outputs",
                upload_dir=tmp_path / "uploads",
            )
        )

        fastapi_available = importlib.util.find_spec("fastapi") is not None
        if not fastapi_available:
            pytest.skip("fastapi is required for API tests")

        run_id = "insight-run"
        run_registry = settings.paths.get_visualization_path() / "run_registry.json"
        run_registry.parent.mkdir(parents=True, exist_ok=True)
        run_registry.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "runs": [
                        {
                            "run_id": run_id,
                            "source_file": "insight.csv",
                            "created_at": "2026-03-18T09:12:00",
                            "status": "completed",
                            "derived_tables": [],
                            "logs": [],
                            "charts": [],
                            "chart_failures": [],
                            "insight_status": "not_generated",
                            "insight_updated_at": "",
                            "insights": [],
                            "summary": {"chart_count": 0, "saved_file_count": 0, "log_file_count": 0},
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(
            gallery,
            "_call_deepseek",
            lambda api_key, prompt: {"response": {"id": "mock"}, "content": "## 建议\n- 优先优化物流稳定性"},
        )

        from fastapi.testclient import TestClient

        client = TestClient(create_app(settings=settings))

        key_resp = client.post("/api/session/deepseek-key", json={"api_key": "sk-test-deepseek-123456789"})
        assert key_resp.status_code == 200
        session_id = key_resp.json()["session_id"]

        insight_resp = client.post(f"/api/runs/{run_id}/insights/generate", json={"session_id": session_id})
        assert insight_resp.status_code == 200
        payload = insight_resp.json()
        assert payload["insight_status"] == "generated"
        assert "物流稳定性" in payload["advice_markdown"]

        run_payload = client.get(f"/api/runs/{run_id}").json()
        assert run_payload["insight_status"] == "generated"
        assert len(run_payload["insights"]) == 2
