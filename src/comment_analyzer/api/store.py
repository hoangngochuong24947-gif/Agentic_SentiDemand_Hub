"""Small in-memory job store for API v1 compatibility."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional


_JOBS: Dict[str, Dict[str, Any]] = {}

UPLOAD_STEP_NAMES = ["Upload", "Clean", "Sentiment", "Topics", "Demand", "Charts"]


def now_iso() -> str:
    return datetime.now().isoformat()


def create_job(
    kind: str,
    *,
    run_id: Optional[str] = None,
    message: str = "",
    retry_of: Optional[str] = None,
) -> Dict[str, Any]:
    timestamp = now_iso()
    job = {
        "job_id": uuid.uuid4().hex,
        "status": "pending",
        "run_id": run_id,
        "kind": kind,
        "created_at": timestamp,
        "updated_at": timestamp,
        "message": message,
        "result": {},
        "error": None,
        "steps": _default_steps() if kind == "upload" else [],
        "progress": 0,
        "cancellation_requested": False,
        "retry_of": retry_of,
    }
    _JOBS[job["job_id"]] = job
    return dict(job)


def update_job(job_id: str, **changes: Any) -> Dict[str, Any]:
    job = _JOBS[job_id]
    job.update(changes)
    job["updated_at"] = now_iso()
    return dict(job)


def _default_steps() -> list[Dict[str, Any]]:
    return [{"name": name, "status": "pending"} for name in UPLOAD_STEP_NAMES]


def update_job_step(job_id: str, step_name: str, status: str, *, message: str = "") -> Dict[str, Any]:
    job = _JOBS[job_id]
    steps = list(job.get("steps") or [])
    updated_steps = []
    for step in steps:
        item = dict(step)
        if item.get("name") == step_name:
            item["status"] = status
            if message:
                item["message"] = message
        updated_steps.append(item)

    completed = sum(1 for step in updated_steps if step.get("status") == "completed")
    running = any(step.get("status") == "running" for step in updated_steps)
    failed = any(step.get("status") == "failed" for step in updated_steps)
    progress = int(completed / len(updated_steps) * 100) if updated_steps else int(job.get("progress") or 0)
    if running and updated_steps:
        progress = max(progress, 1)
    if failed:
        progress = min(progress, 99)

    job["steps"] = updated_steps
    job["progress"] = progress
    job["updated_at"] = now_iso()
    return dict(job)


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    job = _JOBS.get(job_id)
    return dict(job) if job else None


def cancel_job(job_id: str) -> Optional[Dict[str, Any]]:
    job = _JOBS.get(job_id)
    if job is None:
        return None

    status = str(job.get("status") or "")
    if status in {"completed", "failed", "canceled"}:
        return dict(job)

    job["cancellation_requested"] = True
    if status in {"pending", "queued"}:
        job["status"] = "canceled"
        job["message"] = "Job canceled before execution"
    else:
        job["status"] = "canceling"
        job["message"] = "Cancellation requested"
    job["updated_at"] = now_iso()
    return dict(job)


def clear_jobs() -> None:
    _JOBS.clear()
