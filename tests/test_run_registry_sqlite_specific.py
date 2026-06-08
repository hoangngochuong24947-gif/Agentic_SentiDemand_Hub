"""SQLite-specific tests for RunRegistry, including JSON auto-migration."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from comment_analyzer.visualization.run_registry import RunRegistry


def test_sqlite_auto_migration_from_json(tmp_path):
    json_path = tmp_path / "run_registry.json"
    db_path = tmp_path / "run_registry.db"
    
    # 1. Create a dummy JSON registry file
    legacy_record = {
        "run_id": "run-legacy-001",
        "source_file": "legacy_comments.csv",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "derived_tables": [{"name": "processed_data.csv", "rows": 5}],
        "logs": [{"category": "pipeline", "message": "legacy run logged"}],
        "charts": [],
        "user_message": "Legacy run successfully analyzed",
    }
    
    payload = {
        "version": "1.0",
        "runs": [legacy_record]
    }
    
    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    
    # 2. Initialize RunRegistry - this should trigger migration
    registry = RunRegistry(json_path)
    
    # 3. Verify that the SQLite DB was created and contains the migrated run
    assert db_path.exists()
    
    run_in_db = registry.get_run("run-legacy-001")
    assert run_in_db is not None
    assert run_in_db["source_file"] == "legacy_comments.csv"
    assert run_in_db["derived_tables"][0]["rows"] == 5
    assert run_in_db["logs"][0]["message"] == "legacy run logged"
    
    # 4. Verify that the JSON file was renamed to .json.bak
    assert not json_path.exists()
    backup_path = tmp_path / "run_registry.json.bak"
    assert backup_path.exists()
    
    # 5. Check we can insert new records into the SQLite DB
    new_record = {
        "run_id": "run-sqlite-002",
        "source_file": "new_comments.csv",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "derived_tables": [],
        "logs": [],
        "charts": [],
        "user_message": "New sqlite run logged",
    }
    registry.record(new_record)
    
    runs = registry.list_runs()
    assert len(runs) == 2
    assert runs[0]["run_id"] == "run-sqlite-002" or runs[1]["run_id"] == "run-sqlite-002"
