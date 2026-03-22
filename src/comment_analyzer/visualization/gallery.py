"""Hub server for visualization outputs, uploads, and run history."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import shutil
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from loguru import logger

from comment_analyzer.core.log_manager import get_log_manager
from comment_analyzer.core.pipeline import CommentPipeline
from comment_analyzer.core.settings import Settings, get_settings
from comment_analyzer.visualization.generator import VisualizationGenerator
from comment_analyzer.visualization.pages import (
    DEFAULT_CRAWLER_GUIDANCE,
    render_dashboard_page,
    render_detail_page,
    render_homepage_page,
    render_insights_page,
    render_legacy_page,
    render_workspace_page,
)
from comment_analyzer.visualization.run_registry import (
    RunRegistry,
    build_run_record,
    classify_upload_failure,
)

_ALLOWED_UPLOAD_SUFFIXES = {".csv", ".xlsx", ".xls", ".json"}
_RUNS_VERSION = "3.0"
_DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
_SESSION_KEYS: Dict[str, Dict[str, str]] = {}

_UPLOAD_HELP_LINES = (
    "支持 CSV / XLSX / XLS / JSON 四种格式。",
    "文件中至少保留一列评论文本（如：评论、内容、comment、review）。",
    "若 CSV 打开乱码，请先另存为 UTF-8 后再上传。",
    "上传成功后可在工作台查看表格，在仪表盘看图表，在建议页生成结论。",
)

_FAILURE_GUIDANCE = {
    "unsupported_file_type": "文件格式不支持，请上传 CSV / XLSX / XLS / JSON。",
    "missing_input": "没有检测到上传文件，请重新选择。",
    "permission_denied": "文件正在被其他程序占用，请关闭后重试。",
    "encoding_error": "文件编码无法识别，建议另存为 UTF-8。",
    "missing_column": "缺少关键字段，请确认评论文本列存在。",
    "missing_text_column": "未识别到评论文本列，请检查列名。",
    "empty_input": "文件为空或没有可分析内容。",
    "preprocessing_failed": "预处理失败，建议先用小样本验证。",
    "analysis_failed": "分析失败，请检查原始数据质量后重试。",
    "visualization_failed": "可视化生成失败，请查看日志定位原因。",
    "processing_error": "上传后处理失败，请检查数据后重试。",
}


def _import_fastapi() -> Tuple[Any, Any, Any, Any, Any, Any, Any, Any, Any, Any]:
    """Import FastAPI stack lazily so base package stays lightweight."""

    try:
        from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
        from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "Gallery requires optional dependencies. Install with: pip install 'comment-analyzer[viz]'"
        ) from exc

    return Body, FastAPI, File, HTTPException, Query, UploadFile, FileResponse, HTMLResponse, JSONResponse, uvicorn


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("_")
    return cleaned or "upload.csv"


def _chart_manifest_path(settings: Settings) -> Path:
    return settings.paths.get_visualization_path() / "manifest.json"


def _run_registry_path(settings: Settings) -> Path:
    return settings.paths.get_visualization_path() / "run_registry.json"


def _run_artifact_dir(settings: Settings, run_id: str) -> Path:
    path = settings.paths.output_base / "workspace_runs" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _artifact_dir(settings: Settings, run_id: str, folder: str) -> Path:
    path = _run_artifact_dir(settings, run_id) / folder
    path.mkdir(parents=True, exist_ok=True)
    return path


def _registry(settings: Settings) -> RunRegistry:
    return RunRegistry(_run_registry_path(settings))


def _load_chart_manifest(settings: Settings) -> Dict[str, Any]:
    path = _chart_manifest_path(settings)
    if not path.exists():
        return {"version": "1.0", "entries": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": "1.0", "entries": []}
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    payload["entries"] = [entry for entry in entries if isinstance(entry, Mapping)]
    return payload


def _resolve_chart_entry_path(settings: Settings, entry: Mapping[str, Any]) -> Path:
    vis_root = settings.paths.get_visualization_path().resolve()
    rel_path = Path(str(entry.get("output_path", "")))
    target = (vis_root / rel_path).resolve()
    if vis_root not in target.parents and target != vis_root:
        raise ValueError("Invalid output_path outside visualization directory")
    return target


def _failure_status_code(category: str) -> int:
    if category in {"unsupported_file_type", "missing_input"}:
        return 400
    if category in {"encoding_error", "missing_column", "missing_text_column", "empty_input", "permission_denied"}:
        return 422
    return 500


def _friendly_failure_message(category: str, error: Exception) -> str:
    prefix = _FAILURE_GUIDANCE.get(category, _FAILURE_GUIDANCE["processing_error"])
    return f"{prefix} 原始错误：{error}"


def _allowed_roots(settings: Settings) -> List[Path]:
    return [
        settings.paths.output_base.resolve(),
        settings.paths.get_visualization_path().resolve(),
        settings.paths.get_upload_path().resolve(),
    ]


def _ensure_safe_path(settings: Settings, raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("Artifact path is empty")

    path = Path(raw_path)
    resolved = path.resolve() if path.is_absolute() else (settings.paths.output_base / path).resolve()
    for root in _allowed_roots(settings):
        if resolved == root or root in resolved.parents:
            return resolved
    raise ValueError("Artifact path is outside the allowed directories")


def _mask_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"


def _infer_chart_type_from_path(path: Path) -> str:
    stem = path.stem
    if re.search(r"_\d{6}$", stem):
        return re.sub(r"_\d{6}$", "", stem)
    return stem


def _table_preview_from_path(path: Path, *, category: str, title: str) -> Dict[str, Any]:
    preview = {
        "columns": ["field", "value"],
        "rows": [
            {"field": "file", "value": path.name},
            {"field": "category", "value": category},
        ],
    }

    try:
        import pandas as pd
    except Exception:
        return {"title": title, "summary": f"{category} / {path.name}", "preview": preview}

    try:
        if path.suffix.lower() == ".csv":
            frame = pd.read_csv(path, nrows=5)
        elif path.suffix.lower() in {".xlsx", ".xls"}:
            frame = pd.read_excel(path, nrows=5)
        elif path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                frame = pd.DataFrame(data[:5])
            elif isinstance(data, dict):
                frame = pd.DataFrame([data])
            else:
                frame = pd.DataFrame([{"value": str(data)}])
        else:
            frame = None
    except Exception:
        frame = None

    if frame is None or frame.empty:
        return {"title": title, "summary": f"{category} / {path.name}", "preview": preview}

    rows = frame.fillna("").astype(str).to_dict(orient="records")
    return {
        "title": title,
        "summary": f"{category} / {path.name}",
        "preview": {
            "columns": list(frame.columns),
            "rows": rows,
        },
    }


def _serialize_table_artifacts(results: Any) -> List[Dict[str, Any]]:
    artifacts: List[Dict[str, Any]] = []
    for saved in getattr(results, "saved_files", []):
        path = Path(saved.final_path)
        metadata = _table_preview_from_path(path, category=str(saved.category), title=str(saved.original_name))
        artifacts.append(
            {
                "type": "table",
                "name": str(saved.original_name),
                "title": metadata["title"],
                "summary": metadata["summary"],
                "status": "ready",
                "reason": "",
                "path": str(path),
                "downloadable": True,
                "preview": metadata["preview"],
            }
        )
    return artifacts


def _serialize_log_artifacts(summary_path: Path, exported_log_path: Optional[Path], results: Any) -> List[Dict[str, Any]]:
    artifacts: List[Dict[str, Any]] = []
    if summary_path.exists():
        preview_lines = summary_path.read_text(encoding="utf-8").splitlines()[:6]
        artifacts.append(
            {
                "type": "log",
                "name": "run_summary.txt",
                "title": "运行摘要",
                "summary": " / ".join(preview_lines[:2]) if preview_lines else "运行摘要",
                "status": "ready",
                "reason": "",
                "path": str(summary_path),
                "downloadable": True,
                "preview": {"lines": preview_lines},
            }
        )

    if exported_log_path and exported_log_path.exists():
        artifacts.append(
            {
                "type": "log",
                "name": exported_log_path.name,
                "title": "结构化日志",
                "summary": "包含关键过程日志和错误信息。",
                "status": "ready",
                "reason": "",
                "path": str(exported_log_path),
                "downloadable": True,
                "preview": {"lines": []},
            }
        )

    preview_entries = getattr(getattr(results, "log_manager", None), "get_log_entries", lambda: [])()
    for index, entry in enumerate(preview_entries[:4], start=1):
        if not isinstance(entry, Mapping):
            continue
        artifacts.append(
            {
                "type": "log",
                "name": f"log_preview_{index}",
                "title": f"日志摘要 {index}",
                "summary": str(entry.get("message") or entry.get("analysis_type") or entry.get("type") or "log"),
                "status": "ready",
                "reason": "",
                "path": "",
                "downloadable": False,
                "preview": {"lines": [str(entry)]},
            }
        )

    return artifacts


def _materialize_generated_charts(generated: Sequence[str], charts_dir: Path) -> List[Path]:
    materialized: List[Path] = []
    for raw in generated:
        src = Path(raw)
        if not src.exists():
            continue
        dst = charts_dir / src.name
        try:
            shutil.copy2(src, dst)
            materialized.append(dst.resolve())
        except Exception:
            logger.exception(f"Failed to copy chart file: {src}")
    return materialized


def _serialize_chart_artifacts(settings: Settings, run_id: str, chart_files: Sequence[Path]) -> Tuple[List[Dict[str, Any]], List[str]]:
    manifest = _load_chart_manifest(settings)
    by_chart_type: Dict[str, Mapping[str, Any]] = {}
    for entry in manifest.get("entries", []):
        if str(entry.get("run_id") or "") != str(run_id):
            continue
        chart_type = str(entry.get("chart_type") or "")
        if chart_type and chart_type not in by_chart_type:
            by_chart_type[chart_type] = entry

    artifacts: List[Dict[str, Any]] = []
    generated_types: set[str] = set()
    for chart_file in chart_files:
        chart_type = _infer_chart_type_from_path(chart_file)
        generated_types.add(chart_type)
        manifest_entry = by_chart_type.get(chart_type, {})
        artifacts.append(
            {
                "type": "chart",
                "name": chart_type,
                "title": str(manifest_entry.get("chart_title") or chart_type),
                "summary": f"图表文件：{chart_file.name}",
                "status": "ready",
                "reason": "",
                "path": str(chart_file),
                "downloadable": True,
                "preview": {"file": chart_file.name},
                "chart_id": str(manifest_entry.get("id") or ""),
                "chart_type": chart_type,
            }
        )

    enabled_chart_types = [
        chart_type
        for chart_type in VisualizationGenerator.CHART_REGISTRY
        if settings.visualization.charts.get(chart_type, True)
    ]
    missing_types = [chart_type for chart_type in enabled_chart_types if chart_type not in generated_types]
    for chart_type in missing_types:
        _, _, title = VisualizationGenerator.CHART_REGISTRY[chart_type]
        artifacts.append(
            {
                "type": "chart",
                "name": chart_type,
                "title": title,
                "summary": "图表未生成",
                "status": "missing",
                "reason": "数据不足或该图表在当前数据条件下被跳过。",
                "path": "",
                "downloadable": False,
                "preview": {},
                "chart_id": "",
                "chart_type": chart_type,
            }
        )
    return artifacts, missing_types


def _read_existing_insight(run_id: str, settings: Settings) -> Dict[str, Any]:
    run_dir = _run_artifact_dir(settings, run_id)
    insights_dir = run_dir / "insights"
    md_path = insights_dir / "advice.md"
    json_path = insights_dir / "advice.json"
    payload: Dict[str, Any] = {
        "status": "not_generated",
        "updated_at": "",
        "markdown": "",
        "json_path": str(json_path),
        "md_path": str(md_path),
    }
    if md_path.exists():
        payload["markdown"] = md_path.read_text(encoding="utf-8")
        payload["status"] = "generated"
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        payload["updated_at"] = str(data.get("generated_at") or "")
        payload["status"] = str(data.get("status") or payload["status"])
    return payload


def _extract_insight_metrics(record: Mapping[str, Any]) -> Dict[str, Any]:
    summary = record.get("summary") or {}
    metrics: Dict[str, Any] = {
        "run_id": record.get("run_id"),
        "source_file": record.get("source_file"),
        "created_at": record.get("created_at"),
        "chart_count": summary.get("chart_count"),
        "table_count": summary.get("saved_file_count"),
        "log_count": summary.get("log_file_count"),
        "chart_failures": record.get("chart_failures", []),
    }

    sentiment_table = next(
        (
            item
            for item in record.get("derived_tables", [])
            if isinstance(item, Mapping) and "sentiment" in str(item.get("name") or "").lower()
        ),
        None,
    )
    if sentiment_table and isinstance(sentiment_table.get("preview"), Mapping):
        metrics["sentiment_preview"] = sentiment_table["preview"].get("rows", [])[:5]

    keyword_table = next(
        (
            item
            for item in record.get("derived_tables", [])
            if isinstance(item, Mapping) and "keyword" in str(item.get("name") or "").lower()
        ),
        None,
    )
    if keyword_table and isinstance(keyword_table.get("preview"), Mapping):
        metrics["keyword_preview"] = keyword_table["preview"].get("rows", [])[:10]

    return metrics


def _build_insight_prompt(record: Mapping[str, Any]) -> str:
    metrics = _extract_insight_metrics(record)
    metrics_json = json.dumps(metrics, ensure_ascii=False, indent=2)
    return (
        "你是电商评论分析顾问。请基于以下结构化指标输出中文建议，要求：\n"
        "1) 先给三条关键发现。\n"
        "2) 给出三条可执行动作，按优先级排序。\n"
        "3) 给出两个风险点与监控指标。\n"
        "4) 语言简洁，避免空话，保留数据引用。\n\n"
        f"数据摘要:\n{metrics_json}"
    )


def _call_deepseek(api_key: str, prompt: str) -> Dict[str, Any]:
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是资深数据分析与商业策略顾问。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        _DEEPSEEK_ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"DeepSeek API error {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"DeepSeek request failed: {exc}") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("DeepSeek response is not valid JSON") from exc

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if not content:
        raise RuntimeError("DeepSeek returned empty content")
    return {"response": data, "content": content}


def _write_insight_files(settings: Settings, run_id: str, markdown: str, metadata: Dict[str, Any]) -> Dict[str, str]:
    insights_dir = _artifact_dir(settings, run_id, "insights")
    md_path = insights_dir / "advice.md"
    json_path = insights_dir / "advice.json"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"markdown_path": str(md_path), "json_path": str(json_path)}


def _build_rich_run_record(
    settings: Settings,
    *,
    run_id: str,
    source_file: str,
    results: Any,
    summary_path: Path,
    exported_log_path: Optional[Path],
    chart_files: Sequence[Path],
) -> Dict[str, Any]:
    record = build_run_record(
        run_id=run_id,
        source_file=source_file,
        results=results,
        charts=[str(path) for path in chart_files],
        status="completed",
        user_message="上传成功，分析完成。可查看表格、仪表盘和建议页。",
    ).to_dict()

    tables = _serialize_table_artifacts(results)
    logs = _serialize_log_artifacts(summary_path, exported_log_path, results)
    charts, chart_failures = _serialize_chart_artifacts(settings, run_id, chart_files)
    insight = _read_existing_insight(run_id, settings)

    record["derived_tables"] = tables
    record["logs"] = logs
    record["charts"] = charts
    record["chart_failures"] = chart_failures
    record["insight_status"] = insight["status"]
    record["insight_updated_at"] = insight["updated_at"]
    record["insights"] = []

    ready_chart_count = sum(1 for item in charts if item.get("status") == "ready")
    record["summary"] = {
        **record.get("summary", {}),
        "saved_file_count": len(tables),
        "log_file_count": len(logs),
        "chart_count": ready_chart_count,
        "total_chart_slots": len(charts),
    }
    return record


def _run_card_payload(record: Mapping[str, Any]) -> Dict[str, Any]:
    summary = record.get("summary") or {}
    table_count = int(summary.get("saved_file_count") or len(record.get("derived_tables", [])))
    log_count = int(summary.get("log_file_count") or len(record.get("logs", [])))
    chart_count = int(summary.get("chart_count") or 0)
    summary_text = (
        str(record.get("user_message") or "").strip()
        or f"{table_count} 个表格 / {log_count} 条日志 / {chart_count} 个图表"
    )
    run_id = str(record.get("run_id") or "")
    return {
        "run_id": run_id,
        "title": record.get("source_file") or run_id or "未命名运行",
        "status": record.get("status") or "unknown",
        "created_at": record.get("created_at") or "",
        "source_name": record.get("source_file") or "source",
        "summary": summary_text,
        "href": f"/workspace/{run_id}",
    }


def _with_links(record: Mapping[str, Any], artifact_type: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    source_items = record.get(artifact_type, [])
    if not isinstance(source_items, list):
        return items
    file_index = 0
    for entry in source_items:
        if not isinstance(entry, Mapping):
            continue
        payload = dict(entry)
        path = str(payload.get("path") or "")
        if path:
            short_type = artifact_type
            if artifact_type == "derived_tables":
                short_type = "tables"
            payload["open_url"] = f"/runs/{record.get('run_id')}/artifacts/{short_type}/{file_index}"
            payload["download_url"] = f"/runs/{record.get('run_id')}/artifacts/{short_type}/{file_index}?download=true"
            file_index += 1
        else:
            payload["open_url"] = ""
            payload["download_url"] = ""
        items.append(payload)
    return items


def _artifact_collection(record: Mapping[str, Any], artifact_type: str) -> List[Mapping[str, Any]]:
    if artifact_type not in {"derived_tables", "logs", "charts"}:
        raise ValueError(f"Unknown artifact type: {artifact_type}")
    items = record.get(artifact_type, [])
    return [item for item in items if isinstance(item, Mapping) and item.get("path")]


def create_app(settings: Optional[Settings] = None) -> Any:
    """Create FastAPI app for Hub endpoints."""

    Body, FastAPI, File, HTTPException, Query, UploadFile, FileResponse, HTMLResponse, JSONResponse, _ = _import_fastapi()
    app_settings = settings or get_settings()
    app_settings.paths.ensure_directories()
    run_registry = _registry(app_settings)
    app = FastAPI(title="SentiDemand Visualization Gallery", version=_RUNS_VERSION)

    @app.get("/", response_class=HTMLResponse)
    def index() -> Any:
        runs = [_run_card_payload(record) for record in run_registry.list_runs()]
        return HTMLResponse(
            render_homepage_page(
                runs=runs,
                crawler_guidance=DEFAULT_CRAWLER_GUIDANCE,
                page_title="SentiDemand Hub - Home",
            )
        )

    @app.get("/workspace", response_class=HTMLResponse)
    def workspace() -> Any:
        records = run_registry.list_runs()
        runs = [_run_card_payload(record) for record in records]
        selected_record = records[0] if records else {}
        selected_payload = _run_card_payload(selected_record) if selected_record else {}
        return HTMLResponse(
            render_workspace_page(
                runs=runs,
                selected_run=selected_payload,
                tables=_with_links(selected_record, "derived_tables"),
                page_title="SentiDemand Hub - Workspace",
            )
        )

    @app.get("/workspace/{run_id}", response_class=HTMLResponse)
    def workspace_run(run_id: str) -> Any:
        record = run_registry.get_run(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run id '{run_id}' not found")
        runs = [_run_card_payload(item) for item in run_registry.list_runs()]
        return HTMLResponse(
            render_workspace_page(
                runs=runs,
                selected_run=_run_card_payload(record),
                tables=_with_links(record, "derived_tables"),
                page_title=f"SentiDemand Hub - Workspace - {record.get('source_file', run_id)}",
            )
        )

    @app.get("/dashboard/{run_id}", response_class=HTMLResponse)
    def dashboard(run_id: str) -> Any:
        record = run_registry.get_run(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run id '{run_id}' not found")
        return HTMLResponse(
            render_dashboard_page(
                _run_card_payload(record),
                charts=_with_links(record, "charts"),
                page_title=f"SentiDemand Hub - Dashboard - {record.get('source_file', run_id)}",
            )
        )

    @app.get("/insights/{run_id}", response_class=HTMLResponse)
    def insights(run_id: str) -> Any:
        record = run_registry.get_run(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run id '{run_id}' not found")
        insight = _read_existing_insight(run_id, app_settings)
        return HTMLResponse(
            render_insights_page(
                _run_card_payload(record),
                insight_markdown=str(insight.get("markdown") or ""),
                insight_status=str(record.get("insight_status") or insight.get("status") or "not_generated"),
                page_title=f"SentiDemand Hub - Insights - {record.get('source_file', run_id)}",
            )
        )

    @app.get("/legacy", response_class=HTMLResponse)
    def legacy() -> Any:
        runs = [_run_card_payload(record) for record in run_registry.list_runs()]
        return HTMLResponse(render_legacy_page(runs=runs, page_title="SentiDemand Hub - Legacy"))

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def run_detail(run_id: str) -> Any:
        record = run_registry.get_run(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run id '{run_id}' not found")
        return HTMLResponse(
            render_detail_page(
                _run_card_payload(record),
                derived_tables=_with_links(record, "derived_tables"),
                logs=_with_links(record, "logs"),
                charts=_with_links(record, "charts"),
                page_title=f"SentiDemand Hub - Legacy Detail - {record.get('source_file', run_id)}",
            )
        )

    @app.get("/api/manifest", response_class=JSONResponse)
    def api_manifest() -> Any:
        payload = run_registry.to_dict()
        payload["version"] = _RUNS_VERSION
        payload["total_runs"] = len(payload.get("runs", []))
        return JSONResponse(payload)

    @app.get("/api/runs/{run_id}", response_class=JSONResponse)
    def api_run_detail(run_id: str) -> Any:
        record = run_registry.get_run(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run id '{run_id}' not found")
        return JSONResponse(record)

    @app.post("/api/session/deepseek-key", response_class=JSONResponse)
    async def save_deepseek_key(payload: Dict[str, Any] = Body(...)) -> Any:
        api_key = str(payload.get("api_key") or "").strip()
        if len(api_key) < 10:
            raise HTTPException(status_code=422, detail="DeepSeek API Key 无效。")
        session_id = uuid.uuid4().hex
        _SESSION_KEYS[session_id] = {
            "api_key": api_key,
            "updated_at": datetime.now().isoformat(),
        }
        return JSONResponse(
            {
                "session_id": session_id,
                "masked_key": _mask_key(api_key),
                "status": "saved",
            }
        )

    @app.post("/api/runs/{run_id}/insights/generate", response_class=JSONResponse)
    async def generate_insight(run_id: str, payload: Dict[str, Any] = Body(default={})) -> Any:
        record = run_registry.get_run(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run id '{run_id}' not found")

        session_id = str(payload.get("session_id") or "").strip()
        inline_key = str(payload.get("api_key") or "").strip()
        api_key = inline_key or _SESSION_KEYS.get(session_id, {}).get("api_key", "")
        if not api_key:
            raise HTTPException(status_code=422, detail="未找到 DeepSeek 密钥，请先保存会话密钥。")

        prompt = _build_insight_prompt(record)
        try:
            deepseek_result = _call_deepseek(api_key, prompt)
        except Exception as exc:
            record["insight_status"] = "failed"
            record["insight_updated_at"] = datetime.now().isoformat()
            record["user_message"] = f"建议生成失败：{exc}"
            run_registry.record(record)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        now_iso = datetime.now().isoformat()
        advice_markdown = str(deepseek_result["content"]).strip()
        metadata = {
            "status": "generated",
            "generated_at": now_iso,
            "model": "deepseek-chat",
            "metrics": _extract_insight_metrics(record),
            "response": deepseek_result["response"],
        }
        files = _write_insight_files(app_settings, run_id, advice_markdown, metadata)

        record["insight_status"] = "generated"
        record["insight_updated_at"] = now_iso
        record["insights"] = [
            {
                "type": "insight",
                "name": "advice.md",
                "title": "建议文档",
                "summary": "DeepSeek 生成的建议内容。",
                "status": "ready",
                "reason": "",
                "path": files["markdown_path"],
                "downloadable": True,
                "preview": {"lines": advice_markdown.splitlines()[:12]},
            },
            {
                "type": "insight",
                "name": "advice.json",
                "title": "建议元数据",
                "summary": "建议生成参数、时间与结构化数据。",
                "status": "ready",
                "reason": "",
                "path": files["json_path"],
                "downloadable": True,
                "preview": {"lines": []},
            },
        ]
        run_registry.record(record)
        return JSONResponse(
            {
                "run_id": run_id,
                "insight_status": "generated",
                "insight_updated_at": now_iso,
                "advice_markdown": advice_markdown,
                "artifacts": record["insights"],
            }
        )

    @app.get("/chart/{entry_id}")
    def chart(entry_id: str) -> Any:
        manifest = _load_chart_manifest(app_settings)
        entry = next((item for item in manifest.get("entries", []) if str(item.get("id")) == entry_id), None)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Chart id '{entry_id}' not found")
        try:
            path = _resolve_chart_entry_path(app_settings, entry)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Chart file does not exist: {path.name}")
        return FileResponse(path, media_type="text/html; charset=utf-8")

    @app.get("/runs/{run_id}/artifacts/{artifact_type}/{artifact_index}")
    def artifact_file(run_id: str, artifact_type: str, artifact_index: int, download: bool = Query(False)) -> Any:
        mapping = {
            "tables": "derived_tables",
            "logs": "logs",
            "charts": "charts",
        }
        internal_type = mapping.get(artifact_type, artifact_type)
        record = run_registry.get_run(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run id '{run_id}' not found")
        try:
            collection = _artifact_collection(record, internal_type)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if artifact_index < 0 or artifact_index >= len(collection):
            raise HTTPException(status_code=404, detail="Artifact index out of range")

        entry = collection[artifact_index]
        try:
            path = _ensure_safe_path(app_settings, str(entry.get("path") or ""))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Artifact file does not exist: {path.name}")

        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        filename = path.name if download else None
        return FileResponse(path, media_type=media_type, filename=filename)

    @app.post("/upload", response_class=JSONResponse)
    async def upload(file: Any = File(...)) -> Any:
        original_name = getattr(file, "filename", None) or "upload.csv"
        suffix = Path(original_name).suffix.lower()
        if suffix not in _ALLOWED_UPLOAD_SUFFIXES:
            allowed = ", ".join(sorted(_ALLOWED_UPLOAD_SUFFIXES))
            raise HTTPException(status_code=400, detail=f"文件格式不支持：{suffix}，允许格式：{allowed}")

        upload_dir = app_settings.paths.get_upload_path()
        upload_dir.mkdir(parents=True, exist_ok=True)
        target = upload_dir / f"{datetime.now():%Y%m%d_%H%M%S}_{_safe_filename(Path(original_name).name)}"
        content = await file.read()
        if not content:
            raise HTTPException(status_code=422, detail=_FAILURE_GUIDANCE["empty_input"])

        target.write_bytes(content)
        logger.info(f"Uploaded file saved to {target}")

        run_id = uuid.uuid4().hex[:12]
        get_log_manager().clear_entries()
        try:
            pipeline = CommentPipeline(settings=app_settings)
            dataframe = pipeline.load_data(target)
            results = pipeline.run(dataframe, verbose=False)
            results.run_id = results.run_id or run_id

            tables_dir = _artifact_dir(app_settings, results.run_id, "tables")
            logs_dir = _artifact_dir(app_settings, results.run_id, "logs")
            charts_dir = _artifact_dir(app_settings, results.run_id, "charts")
            _artifact_dir(app_settings, results.run_id, "insights")

            results.save(output_dir=tables_dir)
            summary_path = logs_dir / "run_summary.txt"
            summary_path.write_text(results.summary(), encoding="utf-8")

            exported_log_path: Optional[Path] = None
            if getattr(results, "log_manager", None) is not None:
                exported_log_path = Path(results.log_manager.export_log_entries(logs_dir / "log_entries.json"))

            generated = results.visualize(source_name=target.stem, run_id=results.run_id)
            materialized_charts = _materialize_generated_charts(generated, charts_dir)

            record = _build_rich_run_record(
                app_settings,
                run_id=results.run_id,
                source_file=target.name,
                results=results,
                summary_path=summary_path,
                exported_log_path=exported_log_path,
                chart_files=materialized_charts,
            )
            run_registry.record(record)
        except Exception as exc:
            logger.exception("Failed to process uploaded file")
            failure_category = classify_upload_failure(exc)
            run_registry.record(
                build_run_record(
                    run_id=run_id,
                    source_file=target.name,
                    status="failed",
                    user_message=_friendly_failure_message(failure_category, exc),
                    failure_category=failure_category,
                    failure_message=str(exc),
                ).to_dict()
            )
            raise HTTPException(
                status_code=_failure_status_code(failure_category),
                detail=_friendly_failure_message(failure_category, exc),
            ) from exc

        ready_chart_count = sum(1 for item in record["charts"] if item.get("status") == "ready")
        return JSONResponse(
            {
                "uploaded_file": target.name,
                "run_id": record["run_id"],
                "status": record["status"],
                "user_message": record["user_message"],
                "how_to_upload": list(_UPLOAD_HELP_LINES),
                "artifacts": {
                    "derived_tables": len(record["derived_tables"]),
                    "logs": len(record["logs"]),
                    "charts": ready_chart_count,
                    "missing_charts": len(record.get("chart_failures", [])),
                },
                "routes": {
                    "tables": f"/workspace/{record['run_id']}",
                    "dashboard": f"/dashboard/{record['run_id']}",
                    "insights": f"/insights/{record['run_id']}",
                    "legacy": f"/runs/{record['run_id']}",
                },
            }
        )

    return app


def run_gallery_server(
    host: str = "127.0.0.1",
    port: Optional[int] = None,
    settings: Optional[Settings] = None,
) -> None:
    """Run the Hub server."""

    *_, uvicorn = _import_fastapi()
    app_settings = settings or get_settings()
    app = create_app(app_settings)
    server_port = port or app_settings.visualization.gallery_port
    logger.info(f"Starting gallery server on http://{host}:{server_port}")
    uvicorn.run(app, host=host, port=server_port)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run SentiDemand Hub server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Bind port (default: visualization.gallery_port)")
    args = parser.parse_args(argv)
    run_gallery_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
