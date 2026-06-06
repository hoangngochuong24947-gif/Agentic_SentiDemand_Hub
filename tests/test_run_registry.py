"""Tests for visualization run registry helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from comment_analyzer.visualization.run_registry import (
    RunRegistry,
    classify_upload_failure,
)


def test_run_registry_persists_grouped_runs(tmp_path):
    registry_path = tmp_path / "runs.json"
    registry = RunRegistry(registry_path)

    record = {
        "run_id": "run-001",
        "source_file": "comments.csv",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "derived_tables": [{"name": "processed_data.csv", "rows": 2}],
        "logs": [{"category": "pipeline", "message": "done"}],
        "charts": [{"name": "sentiment_donut", "path": "charts/sentiment_donut.html"}],
        "user_message": "Upload completed",
    }

    registry.record(record)
    reloaded = RunRegistry(registry_path)
    payload = reloaded.to_dict()

    assert payload["runs"][0]["run_id"] == "run-001"
    assert payload["runs"][0]["source_file"] == "comments.csv"
    assert payload["runs"][0]["derived_tables"][0]["name"] == "processed_data.csv"
    assert reloaded.group_by_source()["comments.csv"][0]["run_id"] == "run-001"


def test_upload_failure_classification():
    assert classify_upload_failure(ValueError("unsupported file type")) == "unsupported_file_type"
    assert classify_upload_failure(FileNotFoundError("missing file")) == "missing_input"
    assert classify_upload_failure(UnicodeDecodeError("utf-8", b"", 0, 1, "bad")) == "encoding_error"
