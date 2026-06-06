"""Run registry and summary helpers for upload-triggered analysis runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from loguru import logger


def classify_upload_failure(error: Exception) -> str:
    """Map upload/processing exceptions to readable failure categories."""

    message = str(error).lower()
    name = type(error).__name__

    if isinstance(error, FileNotFoundError):
        return "missing_input"
    if isinstance(error, PermissionError):
        return "permission_denied"
    if isinstance(error, UnicodeDecodeError) or "encoding" in message:
        return "encoding_error"
    if isinstance(error, KeyError) or "column" in message:
        return "missing_column"
    if "unsupported" in message and "file" in message:
        return "unsupported_file_type"
    if name in {"EmptyDataError"} or "empty" in message:
        return "empty_input"
    if "no text" in message or "detect text column" in message:
        return "missing_text_column"
    if "preprocess" in message or "segment" in message:
        return "preprocessing_failed"
    if "train" in message or "sentiment" in message:
        return "analysis_failed"
    if "visual" in message or "chart" in message:
        return "visualization_failed"
    return "processing_error"


def _now_iso() -> str:
    return datetime.now().isoformat()


def _safe_list(values: Optional[Iterable[Any]]) -> List[Any]:
    return list(values or [])


def summarize_processed_data(results: Any) -> List[Dict[str, Any]]:
    """Summarize in-memory analysis outputs as logical tables."""

    tables: List[Dict[str, Any]] = []

    processed = getattr(results, "processed_data", None)
    if processed is not None and not getattr(processed, "empty", True):
        tables.append(
            {
                "name": "processed_data",
                "rows": len(processed),
                "columns": list(processed.columns),
                "kind": "dataframe",
            }
        )

    sentiment_distribution = getattr(results, "sentiment_distribution", None)
    if sentiment_distribution:
        tables.append(
            {
                "name": "sentiment_distribution",
                "rows": len(sentiment_distribution),
                "columns": ["sentiment", "count"],
                "kind": "summary",
                "values": dict(sentiment_distribution),
            }
        )

    top_keywords = getattr(results, "top_keywords", None)
    if top_keywords:
        tables.append(
            {
                "name": "top_keywords",
                "rows": len(top_keywords),
                "columns": ["word", "score"],
                "kind": "ranking",
            }
        )

    topics = getattr(results, "topics", None)
    if topics:
        tables.append(
            {
                "name": "topics",
                "rows": len(topics),
                "columns": ["topic_id", "words"],
                "kind": "model_output",
            }
        )

    demand_intensity = getattr(results, "demand_intensity", None)
    if demand_intensity is not None and not getattr(demand_intensity, "empty", True):
        tables.append(
            {
                "name": "demand_intensity",
                "rows": len(demand_intensity),
                "columns": list(demand_intensity.columns),
                "kind": "dataframe",
            }
        )

    demand_correlation = getattr(results, "demand_correlation", None)
    if demand_correlation is not None and not getattr(demand_correlation, "empty", True):
        tables.append(
            {
                "name": "demand_correlation",
                "rows": len(demand_correlation),
                "columns": list(demand_correlation.columns),
                "kind": "matrix",
            }
        )

    return tables


def summarize_logs(log_manager: Any) -> List[Dict[str, Any]]:
    """Summarize structured log entries for a run record."""

    if log_manager is None:
        return []

    if hasattr(log_manager, "get_log_entries"):
        entries = log_manager.get_log_entries()
    else:
        entries = []

    summaries: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        summary = {
            "type": entry.get("type", "log"),
            "category": entry.get("category", "general"),
        }
        if "message" in entry:
            summary["message"] = entry.get("message")
        if "analysis_type" in entry:
            summary["analysis_type"] = entry.get("analysis_type")
        if "model_name" in entry:
            summary["model_name"] = entry.get("model_name")
        summaries.append(summary)
    return summaries


def summarize_charts(chart_paths: Sequence[Any], source_file: str) -> List[Dict[str, Any]]:
    """Summarize generated chart files."""

    charts: List[Dict[str, Any]] = []
    for path in chart_paths:
        if isinstance(path, Mapping):
            chart_name = str(path.get("name") or path.get("chart_type") or "chart")
            chart_path_value = path.get("path") or path.get("output_path") or path.get("file")
            chart_path = Path(str(chart_path_value)) if chart_path_value is not None else Path(chart_name)
        else:
            chart_path = Path(path)
            chart_name = chart_path.stem
        charts.append(
            {
                "name": chart_name,
                "path": str(chart_path),
                "source_file": source_file,
            }
        )
    return charts


@dataclass
class RunRecord:
    """Structured representation of a single analysis run."""

    run_id: str
    source_file: str
    created_at: str
    status: str
    derived_tables: List[Dict[str, Any]] = field(default_factory=list)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    charts: List[Dict[str, Any]] = field(default_factory=list)
    user_message: str = ""
    failure_category: Optional[str] = None
    failure_message: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "source_file": self.source_file,
            "created_at": self.created_at,
            "status": self.status,
            "derived_tables": list(self.derived_tables),
            "logs": list(self.logs),
            "charts": list(self.charts),
            "user_message": self.user_message,
            "failure_category": self.failure_category,
            "failure_message": self.failure_message,
            "summary": dict(self.summary),
        }


class RunRegistry:
    """Persist and group run records for upload history."""

    def __init__(self, registry_path: Path):
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        if not self.registry_path.exists():
            return {"version": "1.0", "runs": []}

        try:
            import json

            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Invalid run registry at {self.registry_path}: {exc}")
            return {"version": "1.0", "runs": []}

        runs = data.get("runs", [])
        if not isinstance(runs, list):
            runs = []
        data["runs"] = [run for run in runs if isinstance(run, dict)]
        return data

    def _save(self, payload: Dict[str, Any]) -> None:
        import json

        self.registry_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def to_dict(self) -> Dict[str, Any]:
        return self._load()

    def list_runs(self) -> List[Dict[str, Any]]:
        """Return all recorded runs in stored order."""

        return list(self._load().get("runs", []))

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Return a run by id if it exists."""

        for record in self._load().get("runs", []):
            if str(record.get("run_id")) == str(run_id):
                return record
        return None

    def record(self, record: RunRecord | Mapping[str, Any]) -> Dict[str, Any]:
        payload = self._load()
        runs = list(payload.get("runs", []))

        if isinstance(record, RunRecord):
            record_dict = record.to_dict()
        else:
            record_dict = dict(record)

        run_id = str(record_dict.get("run_id", ""))
        runs = [item for item in runs if str(item.get("run_id")) != run_id]
        runs.append(record_dict)
        runs.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)

        payload["runs"] = runs
        self._save(payload)
        return record_dict

    def group_by_source(self) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for record in self._load().get("runs", []):
            source = str(record.get("source_file", "unknown"))
            grouped.setdefault(source, []).append(record)
        for records in grouped.values():
            records.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return grouped

    def latest(self) -> Optional[Dict[str, Any]]:
        runs = self._load().get("runs", [])
        return runs[0] if runs else None


def build_run_record(
    *,
    run_id: str,
    source_file: str,
    results: Any = None,
    charts: Optional[Sequence[str]] = None,
    status: str = "completed",
    user_message: str = "",
    failure_category: Optional[str] = None,
    failure_message: Optional[str] = None,
    summary: Optional[Dict[str, Any]] = None,
) -> RunRecord:
    """Build a run record from pipeline results and generated charts."""

    derived_tables = summarize_processed_data(results) if results is not None else []
    log_entries = summarize_logs(getattr(results, "log_manager", None)) if results is not None else []
    chart_entries = summarize_charts(charts or [], source_file)

    if not log_entries and results is not None:
        log_entries = [
            {
                "type": "summary",
                "category": "pipeline",
                "message": "Structured logs were not captured; using run summary only.",
            }
        ]

    inferred_summary = {
        "run_id": run_id,
        "source_file": source_file,
        "status": status,
        "derived_table_count": len(derived_tables),
        "log_count": len(log_entries),
        "chart_count": len(chart_entries),
    }
    if summary:
        inferred_summary.update(summary)

    return RunRecord(
        run_id=run_id,
        source_file=source_file,
        created_at=_now_iso(),
        status=status,
        derived_tables=derived_tables,
        logs=log_entries,
        charts=chart_entries,
        user_message=user_message,
        failure_category=failure_category,
        failure_message=failure_message,
        summary=inferred_summary,
    )
