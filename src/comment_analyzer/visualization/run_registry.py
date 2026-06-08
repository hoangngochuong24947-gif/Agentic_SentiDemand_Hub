"""Run registry and summary helpers for upload-triggered analysis runs."""

from __future__ import annotations

import json
import sqlite3
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
    """SQLite-backed run registry that persists and groups run records for upload history."""

    def __init__(self, registry_path: Path):
        self.json_path = Path(registry_path)
        self.db_path = self.json_path.with_suffix(".db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._migrate_if_needed()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    source_file TEXT,
                    created_at TEXT,
                    status TEXT,
                    user_message TEXT,
                    failure_category TEXT,
                    failure_message TEXT,
                    insight_status TEXT,
                    insight_updated_at TEXT,
                    summary TEXT,
                    derived_tables TEXT,
                    logs TEXT,
                    charts TEXT,
                    insights TEXT,
                    advice_markdown TEXT,
                    chart_failures TEXT
                )
            """)
            try:
                conn.execute("ALTER TABLE runs ADD COLUMN chart_failures TEXT")
            except sqlite3.OperationalError:
                pass
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    raw_content TEXT,
                    cleaned_text TEXT,
                    segmented_text TEXT,
                    filtered_text TEXT,
                    processed_text TEXT,
                    sentiment TEXT,
                    sentiment_score REAL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                )
            """)

    def _migrate_if_needed(self) -> None:
        if not self.json_path.exists() or self.json_path.stat().st_size == 0:
            return

        try:
            logger.info(f"Migrating run registry from JSON to SQLite: {self.json_path} -> {self.db_path}")
            data = json.loads(self.json_path.read_text(encoding="utf-8"))
            runs = data.get("runs", [])
            for run in runs:
                if isinstance(run, dict):
                    self.record(run)
            
            # Rename JSON registry to prevent re-migration
            backup_path = self.json_path.with_suffix(".json.bak")
            self.json_path.rename(backup_path)
            logger.info(f"JSON registry migrated and backed up to: {backup_path}")
        except Exception as exc:
            logger.error(f"Failed to migrate JSON registry to SQLite: {exc}")

    def to_dict(self) -> Dict[str, Any]:
        return {"version": "3.0", "runs": self.list_runs()}

    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        (
            run_id,
            source_file,
            created_at,
            status,
            user_message,
            failure_category,
            failure_message,
            insight_status,
            insight_updated_at,
            summary_str,
            derived_tables_str,
            logs_str,
            charts_str,
            insights_str,
            advice_markdown,
            chart_failures_str
        ) = row

        def _safe_json_loads(val: str, default: Any) -> Any:
            if not val:
                return default
            try:
                return json.loads(val)
            except Exception:
                return default

        return {
            "run_id": run_id,
            "source_file": source_file,
            "created_at": created_at,
            "status": status,
            "user_message": user_message or "",
            "failure_category": failure_category,
            "failure_message": failure_message,
            "insight_status": insight_status or "not_generated",
            "insight_updated_at": insight_updated_at or "",
            "summary": _safe_json_loads(summary_str, {}),
            "derived_tables": _safe_json_loads(derived_tables_str, []),
            "logs": _safe_json_loads(logs_str, []),
            "charts": _safe_json_loads(charts_str, []),
            "insights": _safe_json_loads(insights_str, []),
            "advice_markdown": advice_markdown or "",
            "chart_failures": _safe_json_loads(chart_failures_str, []),
        }

    def list_runs(self) -> List[Dict[str, Any]]:
        """Return all recorded runs in reverse chronological order."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT run_id, source_file, created_at, status, user_message, 
                       failure_category, failure_message, insight_status, 
                       insight_updated_at, summary, derived_tables, logs, 
                       charts, insights, advice_markdown, chart_failures 
                FROM runs ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Return a run by id if it exists."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT run_id, source_file, created_at, status, user_message, 
                       failure_category, failure_message, insight_status, 
                       insight_updated_at, summary, derived_tables, logs, 
                       charts, insights, advice_markdown, chart_failures 
                FROM runs WHERE run_id = ?
                """,
                (run_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            run_dict = self._row_to_dict(row)
            
            # Override preview for processed_data.csv dynamically if comments exist in db
            try:
                cursor.execute(
                    """
                    SELECT comment_id, raw_content, cleaned_text, segmented_text, 
                           filtered_text, processed_text, sentiment, sentiment_score 
                    FROM comments WHERE run_id = ? ORDER BY comment_id ASC LIMIT 5
                    """,
                    (run_id,)
                )
                db_comments = cursor.fetchall()
                if db_comments:
                    for table in run_dict.get("derived_tables", []):
                        if table.get("name") == "processed_data.csv":
                            preview_rows = []
                            columns = table.get("preview", {}).get("columns", [])
                            text_col = "content"
                            for col in columns:
                                if col.lower() in {"content", "comment", "review", "text", "评论", "内容", "评价", "리뷰", "후기"}:
                                    text_col = col
                                    break
                            
                            if "comment_id" not in columns:
                                columns.insert(0, "comment_id")
                            if "sentiment_score" not in columns:
                                columns.append("sentiment_score")
                            
                            table["preview"]["columns"] = columns
                            
                            for c in db_comments:
                                row_dict = {
                                    "comment_id": str(c[0]),
                                    text_col: str(c[1]),
                                    "cleaned_text": str(c[2]),
                                    "segmented_text": str(c[3]),
                                    "filtered_text": str(c[4]),
                                    "processed_text": str(c[5]),
                                    "sentiment": str(c[6]),
                                    "sentiment_score": f"{c[7]:.4f}" if c[7] is not None else "0.5000"
                                }
                                preview_rows.append(row_dict)
                            table["preview"]["rows"] = preview_rows
            except Exception as exc:
                logger.error(f"Failed to override preview from database: {exc}")
                
            return run_dict

    def record(self, record: RunRecord | Mapping[str, Any]) -> Dict[str, Any]:
        if isinstance(record, RunRecord):
            record_dict = record.to_dict()
        else:
            record_dict = dict(record)

        run_id = str(record_dict.get("run_id", ""))
        source_file = record_dict.get("source_file", "")
        created_at = record_dict.get("created_at") or datetime.now().isoformat()
        status = record_dict.get("status", "unknown")
        user_message = record_dict.get("user_message", "")
        failure_category = record_dict.get("failure_category")
        failure_message = record_dict.get("failure_message")
        insight_status = record_dict.get("insight_status", "not_generated")
        insight_updated_at = record_dict.get("insight_updated_at", "")
        advice_markdown = record_dict.get("advice_markdown", "")

        summary_str = json.dumps(record_dict.get("summary", {}), ensure_ascii=False)
        derived_tables_str = json.dumps(record_dict.get("derived_tables", []), ensure_ascii=False)
        logs_str = json.dumps(record_dict.get("logs", []), ensure_ascii=False)
        charts_str = json.dumps(record_dict.get("charts", []), ensure_ascii=False)
        insights_str = json.dumps(record_dict.get("insights", []), ensure_ascii=False)
        chart_failures_str = json.dumps(record_dict.get("chart_failures", []), ensure_ascii=False)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, source_file, created_at, status, user_message, 
                    failure_category, failure_message, insight_status, 
                    insight_updated_at, summary, derived_tables, logs, 
                    charts, insights, advice_markdown, chart_failures
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, source_file, created_at, status, user_message,
                    failure_category, failure_message, insight_status,
                    insight_updated_at, summary_str, derived_tables_str, logs_str,
                    charts_str, insights_str, advice_markdown, chart_failures_str
                )
            )
        return record_dict

    def group_by_source(self) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for record in self.list_runs():
            source = str(record.get("source_file", "unknown"))
            grouped.setdefault(source, []).append(record)
        return grouped

    def latest(self) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT run_id, source_file, created_at, status, user_message, 
                       failure_category, failure_message, insight_status, 
                       insight_updated_at, summary, derived_tables, logs, 
                       charts, insights, advice_markdown, chart_failures 
                FROM runs ORDER BY created_at DESC LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
        return None

    def save_comments(self, run_id: str, df: pd.DataFrame, text_column: str) -> None:
        """Save dataframe comments to SQLite database."""
        if df is None or not hasattr(df, "iterrows"):
            return
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                raw_content = str(row.get(text_column) or "")
                cleaned_text = str(row.get("cleaned_text") or "")
                
                seg = row.get("segmented_text")
                if isinstance(seg, str):
                    try:
                        seg = json.loads(seg)
                    except Exception:
                        seg = [s.strip() for s in seg.split(",") if s.strip()]
                segmented_text = json.dumps(list(seg or []))
                
                fil = row.get("filtered_text")
                if isinstance(fil, str):
                    try:
                        fil = json.loads(fil)
                    except Exception:
                        fil = [s.strip() for s in fil.split(",") if s.strip()]
                filtered_text = json.dumps(list(fil or []))
                
                processed_text = str(row.get("processed_text") or "")
                sentiment = str(row.get("sentiment") or "neutral")
                
                sentiment_score = row.get("sentiment_score")
                if sentiment_score is None:
                    from comment_analyzer.sentiment.labeler import SentimentLabeler
                    labeler = SentimentLabeler()
                    sentiment_score = labeler.get_score(cleaned_text)
                sentiment_score = float(sentiment_score)

                cursor.execute(
                    """
                    INSERT INTO comments (
                        run_id, raw_content, cleaned_text, segmented_text, 
                        filtered_text, processed_text, sentiment, sentiment_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id, raw_content, cleaned_text, segmented_text,
                        filtered_text, processed_text, sentiment, sentiment_score
                    )
                )
            conn.commit()

    def get_comments(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieve all comments associated with a run."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT comment_id, run_id, raw_content, cleaned_text, segmented_text, 
                       filtered_text, processed_text, sentiment, sentiment_score 
                FROM comments WHERE run_id = ? ORDER BY comment_id ASC
                """,
                (run_id,)
            )
            rows = cursor.fetchall()
            comments = []
            for r in rows:
                def _safe_json_loads(val: str, default: Any) -> Any:
                    if not val:
                        return default
                    try:
                        return json.loads(val)
                    except Exception:
                        return default

                comments.append({
                    "comment_id": r[0],
                    "run_id": r[1],
                    "raw_content": r[2],
                    "cleaned_text": r[3],
                    "segmented_text": _safe_json_loads(r[4], []),
                    "filtered_text": _safe_json_loads(r[5], []),
                    "processed_text": r[6],
                    "sentiment": r[7],
                    "sentiment_score": r[8]
                })
            return comments

    def update_comment(self, comment_id: int, updates: Dict[str, Any]) -> None:
        """Update comment content or sentiment properties in database."""
        allowed_keys = {"raw_content", "cleaned_text", "sentiment", "sentiment_score"}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_keys}
        if not filtered_updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in filtered_updates.keys())
        params = list(filtered_updates.values())
        params.append(comment_id)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                f"UPDATE comments SET {set_clause} WHERE comment_id = ?",
                params
            )


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
