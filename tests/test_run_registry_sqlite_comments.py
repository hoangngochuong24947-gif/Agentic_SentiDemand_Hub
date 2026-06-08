"""Tests for SQLite-based comment storage, retrieval, updating, and preview overriding."""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
from fastapi.testclient import TestClient

from comment_analyzer.visualization.run_registry import RunRegistry
from comment_analyzer.api.main import create_app


def test_sqlite_comments_persistence_and_editing(tmp_path):
    registry_json_path = tmp_path / "run_registry.json"
    registry = RunRegistry(registry_json_path)

    # 1. Create a dummy dataframe resembling processed comments
    data = {
        "content": ["I love this product!", "Worst purchase ever.", "It is okay."],
        "cleaned_text": ["love product", "worst purchase", "okay"],
        "segmented_text": [["love", "product"], ["worst", "purchase"], ["okay"]],
        "filtered_text": [["love", "product"], ["worst", "purchase"], ["okay"]],
        "processed_text": ["love product", "worst purchase", "okay"],
        "sentiment": ["positive", "negative", "neutral"],
        "sentiment_score": [0.95, 0.05, 0.50]
    }
    df = pd.DataFrame(data)

    # 2. Record a run
    run_record = {
        "run_id": "test-run-comments-123",
        "source_file": "user_comments.csv",
        "status": "completed",
        "derived_tables": [
            {
                "name": "processed_data.csv",
                "title": "processed_data.csv",
                "preview": {
                    "columns": ["content", "cleaned_text", "sentiment"],
                    "rows": [
                        {"content": "I love this product!", "cleaned_text": "love product", "sentiment": "positive"},
                        {"content": "Worst purchase ever.", "cleaned_text": "worst purchase", "sentiment": "negative"},
                        {"content": "It is okay.", "cleaned_text": "okay", "sentiment": "neutral"}
                    ]
                }
            }
        ],
        "logs": [],
        "charts": [],
    }
    registry.record(run_record)

    # 3. Save comments to the database
    registry.save_comments("test-run-comments-123", df, "content")

    # 4. Verify comments were stored
    comments = registry.get_comments("test-run-comments-123")
    assert len(comments) == 3
    assert comments[0]["raw_content"] == "I love this product!"
    assert comments[0]["sentiment"] == "positive"
    assert comments[0]["sentiment_score"] == 0.95

    # 5. Edit a comment
    target_comment_id = comments[1]["comment_id"]
    registry.update_comment(target_comment_id, {
        "raw_content": "Worst purchase ever. (Updated)",
        "sentiment": "neutral",
        "sentiment_score": 0.45
    })

    # 6. Verify edited comment has updated values
    updated_comments = registry.get_comments("test-run-comments-123")
    assert updated_comments[1]["raw_content"] == "Worst purchase ever. (Updated)"
    assert updated_comments[1]["sentiment"] == "neutral"
    assert updated_comments[1]["sentiment_score"] == 0.45

    # 7. Verify dynamic preview overriding in get_run
    run_detail = registry.get_run("test-run-comments-123")
    assert run_detail is not None
    
    tables = run_detail.get("derived_tables", [])
    assert len(tables) == 1
    
    preview_rows = tables[0]["preview"]["rows"]
    assert len(preview_rows) == 3
    # Verify the edited content is reflected in the preview!
    assert preview_rows[1]["content"] == "Worst purchase ever. (Updated)"
    assert preview_rows[1]["sentiment"] == "neutral"
    assert preview_rows[1]["sentiment_score"] == "0.4500"


def test_api_comments_endpoints(tmp_path):
    # Setup test app with custom settings (to write database to tmp_path)
    from comment_analyzer.core.settings import get_settings
    settings = get_settings().model_copy()
    settings.paths.visualization_base = tmp_path
    
    app = create_app(settings)
    client = TestClient(app)

    # 1. Create a run and upload data via test data
    run_record = {
        "run_id": "api-run-abc",
        "source_file": "api_data.csv",
        "status": "completed",
        "derived_tables": [
            {
                "name": "processed_data.csv",
                "title": "processed_data.csv",
                "preview": {
                    "columns": ["content", "cleaned_text", "sentiment"],
                    "rows": []
                }
            }
        ]
    }
    # Initialize run in db
    registry = RunRegistry(tmp_path / "run_registry.json")
    registry.record(run_record)
    
    df = pd.DataFrame({
        "content": ["Awesome product!"],
        "cleaned_text": ["awesome product"],
        "segmented_text": [["awesome", "product"]],
        "filtered_text": [["awesome", "product"]],
        "processed_text": ["awesome product"],
        "sentiment": ["positive"],
        "sentiment_score": [0.99]
    })
    registry.save_comments("api-run-abc", df, "content")

    # 2. Test GET API
    response = client.get("/api/v1/runs/api-run-abc/comments")
    assert response.status_code == 200
    res_data = response.json()
    assert "comments" in res_data
    assert len(res_data["comments"]) == 1
    assert res_data["comments"][0]["raw_content"] == "Awesome product!"

    # 3. Test POST update API
    comment_id = res_data["comments"][0]["comment_id"]
    update_response = client.post(f"/api/v1/comments/{comment_id}/update", json={
        "raw_content": "Awesome product! (Edited)",
        "sentiment": "neutral",
        "sentiment_score": 0.50
    })
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "ok"

    # 4. Verify updated values from GET API
    response = client.get("/api/v1/runs/api-run-abc/comments")
    res_data = response.json()
    assert res_data["comments"][0]["raw_content"] == "Awesome product! (Edited)"
    assert res_data["comments"][0]["sentiment"] == "neutral"
    assert res_data["comments"][0]["sentiment_score"] == 0.50
