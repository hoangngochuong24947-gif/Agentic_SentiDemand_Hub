"""Tests for the stable /api/v1 FastAPI contract."""

from __future__ import annotations

import zipfile
from datetime import datetime

from fastapi.testclient import TestClient

from comment_analyzer.api import main as api_main
from comment_analyzer.api.store import clear_jobs
from comment_analyzer.core.settings import PathConfig, Settings
from comment_analyzer.visualization import gallery
from comment_analyzer.visualization.run_registry import RunRegistry


def _settings(tmp_path):
    return Settings(
        paths=PathConfig(
            output_base=tmp_path / "outputs",
            visualization_base=tmp_path / "visualizations",
            upload_dir=tmp_path / "uploads",
            config_dir=tmp_path / "config",
        )
    )


def _record(run_id: str = "run-001"):
    return {
        "run_id": run_id,
        "source_file": "comments.csv",
        "created_at": datetime.now().isoformat(),
        "status": "completed",
        "derived_tables": [
            {"name": "processed_data", "rows": 2},
            {
                "name": "sentiment_distribution",
                "rows": 3,
                "values": {"positive": 7, "neutral": 2, "negative": 1},
            },
            {
                "name": "top_keywords",
                "rows": 2,
                "preview": {"rows": [{"word": "battery", "score": 0.8}, {"word": "shipping", "score": 0.6}]},
            },
            {
                "name": "feature_mentions",
                "rows": 2,
                "preview": {"rows": [{"feature": "price", "count": 5}, {"feature": "quality", "count": 4}]},
            },
            {
                "name": "topics",
                "rows": 2,
                "preview": {"rows": [{"topic_id": "Topic 1", "words": "battery, charge", "weight": 0.7}]},
            },
            {
                "name": "demand_intensity",
                "rows": 1,
                "preview": {"rows": [{"category": "delivery", "intensity": 0.9}, {"category": "support", "intensity": 0.4}]},
            },
        ],
        "charts": [
            {"name": "sentiment_donut", "status": "ready", "path": "sentiment.html"},
            {"name": "features_lollipop", "status": "ready", "path": "features.html"},
            {"name": "topics_nightingale", "status": "ready", "path": "topics.html"},
            {"name": "demand_dashboard", "status": "ready", "path": "demand.html"},
        ],
        "logs": [{"category": "pipeline", "message": "done"}],
        "summary": {"saved_file_count": 1, "chart_count": 1, "log_file_count": 1},
        "user_message": "done",
    }


def _client_with_run(tmp_path, record=None):
    settings = _settings(tmp_path)
    settings.paths.ensure_directories()
    registry = RunRegistry(settings.paths.get_visualization_path() / "run_registry.json")
    registry.record(record or _record())
    clear_jobs()
    gallery._SESSION_KEYS.clear()
    return TestClient(api_main.create_app(settings)), settings


def test_health_and_run_artifact_contract(tmp_path):
    client, _ = _client_with_run(tmp_path)

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    runs = client.get("/api/v1/runs")
    assert runs.status_code == 200
    assert runs.json()["total"] == 1
    assert runs.json()["runs"][0]["run_id"] == "run-001"

    detail = client.get("/api/v1/runs/run-001")
    assert detail.status_code == 200
    assert detail.json()["derived_tables"][0]["name"] == "processed_data"

    for suffix, expected_name in [
        ("tables", "processed_data"),
        ("charts", "sentiment_donut"),
        ("logs", None),
        ("insights", None),
    ]:
        response = client.get(f"/api/v1/runs/run-001/{suffix}")
        assert response.status_code == 200
        assert response.json()["run_id"] == "run-001"
        if expected_name:
            assert response.json()["items"][0]["name"] == expected_name


def test_chart_data_endpoint_returns_structured_candidates(tmp_path):
    client, _ = _client_with_run(tmp_path)

    response = client.get("/api/v1/runs/run-001/chart-data")
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-001"
    assert payload["total"] >= 5

    charts = {item["id"]: item for item in payload["charts"]}
    assert set(charts) >= {"sentiment_donut", "keyword_lollipop", "feature_bars", "topic_rose", "demand_radar"}
    assert charts["sentiment_donut"]["kind"] == "donut"
    assert charts["sentiment_donut"]["status"] == "ready"
    assert charts["sentiment_donut"]["data"]["total"] == 10
    assert charts["sentiment_donut"]["legacy_artifact"]["name"] == "sentiment_donut"
    assert charts["keyword_lollipop"]["data"]["items"][0] == {"label": "battery", "value": 0.8}
    assert charts["demand_radar"]["data"]["axes"][0] == {"label": "delivery", "value": 0.9}


def test_chart_data_endpoint_returns_missing_states_without_previews(tmp_path):
    sparse = {
        **_record("run-sparse"),
        "derived_tables": [{"name": "processed_data", "rows": 2}],
        "charts": [{"name": "sentiment_donut", "status": "ready"}],
    }
    client, _ = _client_with_run(tmp_path, sparse)

    response = client.get("/api/v1/runs/run-sparse/chart-data")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 5
    assert any(item["status"] == "missing" and item["reason"] for item in payload["charts"])


def test_analysis_job_stub_tracks_in_memory_status(tmp_path):
    client, _ = _client_with_run(tmp_path)

    created = client.post("/api/v1/analysis/run", json={"run_id": "run-001", "parameters": {"mode": "fast"}})
    assert created.status_code == 200
    payload = created.json()
    assert payload["status"] == "completed"
    assert payload["run_id"] == "run-001"
    assert payload["result"]["parameters"] == {"mode": "fast"}

    fetched = client.get(f"/api/v1/analysis/jobs/{payload['job_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["job_id"] == payload["job_id"]


def test_cancel_job_endpoint_handles_queued_and_completed_states(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    clear_jobs()

    def capture_schedule(background_tasks, job_id, upload_path, app_settings):
        return None

    monkeypatch.setattr(api_main, "_schedule_upload_job", capture_schedule)
    client = TestClient(api_main.create_app(settings))

    queued = client.post(
        "/api/v1/data/upload",
        files={"file": ("comments.csv", b"comment\nhello\n", "text/csv")},
    )
    assert queued.status_code == 200
    queued_payload = queued.json()

    canceled = client.post(f"/api/v1/analysis/jobs/{queued_payload['job_id']}/cancel")
    assert canceled.status_code == 200
    canceled_payload = canceled.json()
    assert canceled_payload["status"] == "canceled"
    assert canceled_payload["cancellation_requested"] is True

    completed = client.post("/api/v1/analysis/run", json={})
    assert completed.status_code == 200
    completed_payload = completed.json()

    completed_cancel = client.post(f"/api/v1/analysis/jobs/{completed_payload['job_id']}/cancel")
    assert completed_cancel.status_code == 200
    assert completed_cancel.json()["status"] == "completed"
    assert completed_cancel.json()["cancellation_requested"] is False


def test_export_results_endpoint_builds_zip_manifest(tmp_path):
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    table_path = artifact_dir / "processed.csv"
    chart_path = artifact_dir / "sentiment.html"
    table_path.write_text("comment,sentiment\nhello,positive\n", encoding="utf-8")
    chart_path.write_text("<html>chart</html>", encoding="utf-8")

    record = {
        **_record("run-export"),
        "derived_tables": [{"name": "processed_data", "rows": 1, "path": str(table_path)}],
        "charts": [{"name": "sentiment_donut", "status": "ready", "path": str(chart_path)}],
        "logs": [{"category": "pipeline", "message": "done"}],
        "insights": [],
    }
    client, _ = _client_with_run(tmp_path, record)

    response = client.post(
        "/api/v1/export/results",
        json={"run_id": "run-export", "artifact_groups": ["tables", "charts", "logs"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["run_id"] == "run-export"
    assert payload["download_url"].endswith(f"{payload['export_id']}/download")
    assert payload["included_counts"] == {"derived_tables": 1, "charts": 1, "logs": 0}

    zip_path = tmp_path / "outputs" / "exports" / f"run-export_{payload['export_id']}.zip"
    assert payload["path"] == str(zip_path)
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert any(name.startswith("derived_tables/") for name in names)
        assert any(name.startswith("charts/") for name in names)
        manifest = archive.read("manifest.json").decode("utf-8")
        assert "run-export" in manifest

    download = client.get(payload["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"


def test_generate_insights_without_api_key_writes_fallback_artifacts(tmp_path):
    client, settings = _client_with_run(tmp_path)

    response = client.post("/api/v1/runs/run-001/insights/generate", json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["insight_status"] == "generated"
    assert "run-001" in payload["advice_markdown"]
    assert payload["structured_advice"]["findings"]
    assert payload["structured_advice"]["actions"]
    assert payload["structured_advice"]["risks"]
    assert payload["structured_advice"]["context"]["provider"] == "local-fallback"
    assert "sentiment_donut" in payload["structured_advice"]["context"]["ready_structured_charts"]

    advice_path = settings.paths.output_base / "workspace_runs" / "run-001" / "insights" / "advice.md"
    assert advice_path.exists()
    metadata_path = settings.paths.output_base / "workspace_runs" / "run-001" / "insights" / "advice.json"
    assert "structured_advice" in metadata_path.read_text(encoding="utf-8")

    insights = client.get("/api/v1/runs/run-001/insights")
    assert insights.status_code == 200
    assert insights.json()["total"] == 2


def test_generate_insights_uses_backend_session_key_and_prompt(monkeypatch, tmp_path):
    client, settings = _client_with_run(tmp_path)
    captured = {}
    session_id = "session-001"
    gallery._SESSION_KEYS[session_id] = {"api_key": "sk-session-secret", "updated_at": "now"}

    def fake_call(api_key, prompt):
        captured["api_key"] = api_key
        captured["prompt"] = prompt
        return {
            "content": "## Findings\n- 评价情绪以正向为主。\n## Actions\n- 优先修复配送体验。\n## Risks\n- 样本量有限。\n## Context\n- run-001",
            "response": {"id": "mocked"},
        }

    monkeypatch.setattr(api_main, "_call_deepseek_advice", fake_call)

    response = client.post("/api/v1/runs/run-001/insights/generate", json={"session_id": session_id})
    assert response.status_code == 200
    payload = response.json()
    assert captured["api_key"] == "sk-session-secret"
    assert "结构化分析结果 JSON" in captured["prompt"]
    assert "comments.csv" in captured["prompt"]
    assert payload["structured_advice"]["context"]["provider"] == "deepseek"
    assert payload["structured_advice"]["findings"]

    metadata_path = settings.paths.output_base / "workspace_runs" / "run-001" / "insights" / "advice.json"
    metadata = metadata_path.read_text(encoding="utf-8")
    assert "structured_advice" in metadata
    assert "mocked" in metadata

    detail = client.get("/api/v1/runs/run-001")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert "评价情绪" in detail_payload["advice_markdown"]
    assert detail_payload["structured_advice"]["context"]["provider"] == "deepseek"


def test_upload_endpoint_returns_queued_job_and_background_completion(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    clear_jobs()

    def fake_upload_pipeline(upload_path, app_settings, job_id):
        assert app_settings is settings
        record = {
            **_record("run-uploaded"),
            "source_file": upload_path.name,
            "insights": [],
        }
        api_main.update_job_step(job_id, "Clean", "completed")
        api_main.update_job_step(job_id, "Sentiment", "completed")
        api_main.update_job_step(job_id, "Topics", "completed")
        api_main.update_job_step(job_id, "Demand", "completed")
        api_main.update_job_step(job_id, "Charts", "completed")
        api_main.update_job(
            job_id,
            status="completed",
            run_id="run-uploaded",
            progress=100,
            result={"artifacts": {"derived_tables": 1, "charts": 1, "logs": 1, "insights": 0}},
        )
        return record

    monkeypatch.setattr(api_main, "_run_upload_pipeline", fake_upload_pipeline)
    client = TestClient(api_main.create_app(settings))

    response = client.post(
        "/api/v1/data/upload",
        files={"file": ("comments.csv", b"comment\nhello\n", "text/csv")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"]
    assert payload["run_id"] == ""
    assert payload["status"] == "queued"

    job = client.get(f"/api/v1/analysis/jobs/{payload['job_id']}")
    assert job.status_code == 200
    job_payload = job.json()
    assert job_payload["status"] == "completed"
    assert job_payload["run_id"] == "run-uploaded"
    assert job_payload["progress"] == 100
    assert [step["name"] for step in job_payload["steps"]] == [
        "Upload",
        "Clean",
        "Sentiment",
        "Topics",
        "Demand",
        "Charts",
    ]
    assert job_payload["result"]["artifacts"]["derived_tables"] == 1


def test_upload_job_can_remain_queued_for_polling(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    clear_jobs()
    scheduled = []

    def capture_schedule(background_tasks, job_id, upload_path, app_settings):
        scheduled.append((job_id, upload_path, app_settings))

    monkeypatch.setattr(api_main, "_schedule_upload_job", capture_schedule)
    client = TestClient(api_main.create_app(settings))

    response = client.post(
        "/api/v1/data/upload",
        files={"file": ("comments.csv", b"comment\nhello\n", "text/csv")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert scheduled

    job = client.get(f"/api/v1/analysis/jobs/{payload['job_id']}")
    assert job.status_code == 200
    job_payload = job.json()
    assert job_payload["status"] == "queued"
    assert job_payload["progress"] > 0
    assert job_payload["steps"][0] == {"name": "Upload", "status": "completed", "message": "File saved"}
    assert job_payload["steps"][-1]["name"] == "Charts"
