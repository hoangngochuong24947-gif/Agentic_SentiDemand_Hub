"""Hub server for visualization outputs, uploads, and run history."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from loguru import logger

from comment_analyzer.core.log_manager import get_log_manager
from comment_analyzer.core.pipeline import CommentPipeline
from comment_analyzer.core.settings import Settings, get_settings
from comment_analyzer.visualization.pages import (
    DEFAULT_CRAWLER_GUIDANCE,
    render_detail_page,
    render_homepage_page,
    render_workspace_page,
)
from comment_analyzer.visualization.run_registry import (
    RunRegistry,
    build_run_record,
    classify_upload_failure,
)

_ALLOWED_UPLOAD_SUFFIXES = {".csv", ".xlsx", ".xls", ".json"}
_RUNS_VERSION = "2.0"
_UPLOAD_HELP_LINES = (
    "支持 CSV、XLSX、XLS、JSON 四种格式。",
    "文件里至少需要一列真实的评论文本，建议列名为 评论、内容、comment、review 等。",
    "如果 CSV 打开后是乱码，请先另存为 UTF-8 编码再上传。",
    "上传成功后，可在工作台查看这次运行生成的表格、日志和图表。",
)
_FAILURE_GUIDANCE = {
    "unsupported_file_type": "文件格式不支持。请上传 CSV、XLSX、XLS 或 JSON。",
    "missing_input": "没有找到上传文件，请重新选择文件后再试。",
    "permission_denied": "当前文件无法读取，可能正被其它程序占用。请关闭占用后重试。",
    "encoding_error": "文件编码无法识别。建议将文件另存为 UTF-8 编码后再上传。",
    "missing_column": "文件里缺少分析所需字段。请确认评论文本列已经保留。",
    "missing_text_column": "系统没有识别到评论文本列。请把评论内容放在清晰的列名下再上传。",
    "empty_input": "文件为空，或没有可分析的评论内容。请检查导出结果后再上传。",
    "preprocessing_failed": "文本预处理阶段失败。建议先上传一份字段更简单的小样本确认格式。",
    "analysis_failed": "分析阶段失败。建议先用较小文件测试，并检查评论列是否为纯文本。",
    "visualization_failed": "图表生成失败，但原始分析可能已完成。请先查看日志面板确认原因。",
    "processing_error": "上传后处理失败。请先检查文件格式、编码和评论列，再重新上传。",
}


def _import_fastapi() -> Tuple[Any, Any, Any, Any, Any, Any, Any, Any]:
    """Import FastAPI stack lazily so base package stays lightweight."""

    try:
        from fastapi import FastAPI, File, HTTPException, Query, UploadFile
        from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "Gallery requires optional dependencies. "
            "Install with: pip install 'comment-analyzer[viz]'"
        ) from exc

    return FastAPI, File, HTTPException, Query, UploadFile, FileResponse, HTMLResponse, JSONResponse, uvicorn


def _chart_manifest_path(settings: Settings) -> Path:
    return settings.paths.get_visualization_path() / "manifest.json"


def _load_chart_manifest(settings: Settings) -> Dict[str, Any]:
    path = _chart_manifest_path(settings)
    if not path.exists():
        return {"version": "1.0", "entries": []}

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Chart manifest is invalid, using empty manifest")
        return {"version": "1.0", "entries": []}

    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    entries = [entry for entry in entries if isinstance(entry, dict)]
    entries.sort(key=lambda entry: str(entry.get("created_at", "")), reverse=True)
    manifest["entries"] = entries
    return manifest


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("_")
    return cleaned or "upload.csv"


def _run_registry_path(settings: Settings) -> Path:
    return settings.paths.get_visualization_path() / "run_registry.json"


def _run_artifact_dir(settings: Settings, run_id: str) -> Path:
    path = settings.paths.output_base / "workspace_runs" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


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
    roots = [
        settings.paths.output_base.resolve(),
        settings.paths.get_visualization_path().resolve(),
        settings.paths.get_upload_path().resolve(),
    ]
    return roots


def _ensure_safe_path(settings: Settings, raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("Artifact path is empty")

    path = Path(raw_path)
    resolved = path.resolve() if path.is_absolute() else (settings.paths.output_base / path).resolve()
    for root in _allowed_roots(settings):
        if resolved == root or root in resolved.parents:
            return resolved
    raise ValueError("Artifact path is outside the allowed directories")


def _resolve_chart_entry_path(settings: Settings, entry: Mapping[str, Any]) -> Path:
    vis_root = settings.paths.get_visualization_path().resolve()
    rel_path = Path(str(entry.get("output_path", "")))
    target = (vis_root / rel_path).resolve()
    if vis_root not in target.parents and target != vis_root:
        raise ValueError("Invalid output_path outside visualization directory")
    return target


def _registry(settings: Settings) -> RunRegistry:
    return RunRegistry(_run_registry_path(settings))


def _table_preview_from_path(path: Path, *, category: str, title: str) -> Dict[str, Any]:
    preview = {
        "title": title,
        "summary": f"{category} · {path.name}",
        "columns": ["field", "value"],
        "rows": [
            {"field": "file", "value": path.name},
            {"field": "category", "value": category},
        ],
    }

    try:
        import pandas as pd
    except Exception:
        return preview

    try:
        if path.suffix.lower() == ".csv":
            frame = pd.read_csv(path, nrows=4)
        elif path.suffix.lower() in {".xlsx", ".xls"}:
            frame = pd.read_excel(path, nrows=4)
        elif path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                if "entries" in data and isinstance(data["entries"], list):
                    frame = pd.DataFrame(data["entries"][:4])
                else:
                    frame = pd.DataFrame([data])
            elif isinstance(data, list):
                frame = pd.DataFrame(data[:4])
            else:
                frame = pd.DataFrame([{"value": data}])
        else:
            return preview
    except Exception:
        return preview

    if frame.empty:
        return preview

    rows = frame.fillna("").astype(str).to_dict(orient="records")
    return {
        "title": title,
        "summary": f"{category} · {path.name}",
        "columns": list(frame.columns),
        "rows": rows[:4],
    }


def _serialize_table_artifacts(results: Any) -> List[Dict[str, Any]]:
    artifacts: List[Dict[str, Any]] = []
    for saved in getattr(results, "saved_files", []):
        path = Path(saved.final_path)
        preview = _table_preview_from_path(path, category=str(saved.category), title=str(saved.original_name))
        preview["path"] = str(path)
        preview["category"] = str(saved.category)
        artifacts.append(preview)
    return artifacts


def _serialize_log_artifacts(summary_path: Path, exported_log_path: Optional[Path], results: Any) -> List[Dict[str, Any]]:
    artifacts: List[Dict[str, Any]] = []

    if summary_path.exists():
        summary_text = summary_path.read_text(encoding="utf-8").splitlines()
        artifacts.append(
            {
                "title": "run_summary.txt",
                "message": " | ".join(summary_text[:3]) or "本次分析摘要",
                "path": str(summary_path),
                "category": "summary",
            }
        )

    if exported_log_path and exported_log_path.exists():
        artifacts.append(
            {
                "title": exported_log_path.name,
                "message": "结构化日志导出，可用于回看处理过程和错误信息。",
                "path": str(exported_log_path),
                "category": "structured_logs",
            }
        )

    for index, entry in enumerate(getattr(getattr(results, "log_manager", None), "get_log_entries", lambda: [])()[:4], start=1):
        if not isinstance(entry, Mapping):
            continue
        artifacts.append(
            {
                "title": f"日志摘要 {index}",
                "message": str(entry.get("message") or entry.get("analysis_type") or entry.get("type") or "log entry"),
                "category": str(entry.get("category") or entry.get("type") or "log"),
            }
        )

    return artifacts


def _serialize_chart_artifacts(settings: Settings, run_id: str, generated: Sequence[str]) -> List[Dict[str, Any]]:
    manifest = _load_chart_manifest(settings)
    entries = [
        entry for entry in manifest.get("entries", [])
        if str(entry.get("run_id") or "") == str(run_id)
    ]

    artifacts: List[Dict[str, Any]] = []
    if entries:
        for entry in entries:
            try:
                chart_path = _resolve_chart_entry_path(settings, entry)
            except ValueError:
                continue
            artifacts.append(
                {
                    "title": str(entry.get("chart_title") or entry.get("chart_type") or chart_path.stem),
                    "type": str(entry.get("chart_type") or "chart"),
                    "summary": f"图表文件：{chart_path.name}",
                    "path": str(chart_path),
                    "chart_id": str(entry.get("id") or ""),
                }
            )
        return artifacts

    for raw_path in generated:
        path = Path(raw_path)
        artifacts.append(
            {
                "title": path.stem,
                "type": "chart",
                "summary": f"图表文件：{path.name}",
                "path": str(path),
            }
        )
    return artifacts


def _build_rich_run_record(
    settings: Settings,
    *,
    run_id: str,
    source_file: str,
    results: Any,
    generated: Sequence[str],
    summary_path: Path,
    exported_log_path: Optional[Path],
) -> Dict[str, Any]:
    record = build_run_record(
        run_id=run_id,
        source_file=source_file,
        results=results,
        charts=generated,
        status="completed",
        user_message="上传成功，已生成派生表格、日志和图表。",
    ).to_dict()
    record["derived_tables"] = _serialize_table_artifacts(results)
    record["logs"] = _serialize_log_artifacts(summary_path, exported_log_path, results)
    record["charts"] = _serialize_chart_artifacts(settings, run_id, generated)
    record["summary"] = {
        **record.get("summary", {}),
        "saved_file_count": len(record["derived_tables"]),
        "log_file_count": len(record["logs"]),
        "chart_count": len(record["charts"]),
    }
    return record


def _run_card_payload(record: Mapping[str, Any]) -> Dict[str, Any]:
    summary = record.get("summary") or {}
    table_count = int(summary.get("saved_file_count") or len(record.get("derived_tables", [])))
    log_count = int(summary.get("log_file_count") or len(record.get("logs", [])))
    chart_count = int(summary.get("chart_count") or len(record.get("charts", [])))
    user_message = str(record.get("user_message") or "").strip()
    summary_text = user_message or f"{table_count} 个表格 · {log_count} 条日志 · {chart_count} 张图表"
    return {
        "title": record.get("source_file") or record.get("run_id") or "未命名运行",
        "status": record.get("status") or "unknown",
        "created_at": record.get("created_at") or "",
        "source_name": record.get("source_file") or "source",
        "summary": summary_text,
        "href": f"/runs/{record.get('run_id')}",
    }


def _tables_for_detail(record: Mapping[str, Any]) -> List[Dict[str, Any]]:
    tables: List[Dict[str, Any]] = []
    for index, entry in enumerate(record.get("derived_tables", [])):
        if not isinstance(entry, Mapping):
            continue
        tables.append(
            {
                **entry,
                "open_url": f"/runs/{record.get('run_id')}/artifacts/tables/{index}",
                "download_url": f"/runs/{record.get('run_id')}/artifacts/tables/{index}?download=true",
            }
        )
    return tables


def _logs_for_detail(record: Mapping[str, Any]) -> List[Dict[str, Any]]:
    logs: List[Dict[str, Any]] = []
    file_index = 0
    for entry in record.get("logs", []):
        if not isinstance(entry, Mapping):
            logs.append({"title": "日志", "message": str(entry)})
            continue

        payload = dict(entry)
        if payload.get("path"):
            payload["open_url"] = f"/runs/{record.get('run_id')}/artifacts/logs/{file_index}"
            payload["download_url"] = f"/runs/{record.get('run_id')}/artifacts/logs/{file_index}?download=true"
            file_index += 1
        logs.append(payload)
    return logs


def _charts_for_detail(record: Mapping[str, Any]) -> List[Dict[str, Any]]:
    charts: List[Dict[str, Any]] = []
    for index, entry in enumerate(record.get("charts", [])):
        if not isinstance(entry, Mapping):
            continue
        chart_id = str(entry.get("chart_id") or "")
        payload = dict(entry)
        if chart_id:
            payload["open_url"] = f"/chart/{chart_id}"
        elif payload.get("path"):
            payload["open_url"] = f"/runs/{record.get('run_id')}/artifacts/charts/{index}"
        if payload.get("path"):
            payload["download_url"] = f"/runs/{record.get('run_id')}/artifacts/charts/{index}?download=true"
        charts.append(payload)
    return charts


def _artifact_collection(record: Mapping[str, Any], artifact_type: str) -> List[Mapping[str, Any]]:
    if artifact_type == "tables":
        return [entry for entry in record.get("derived_tables", []) if isinstance(entry, Mapping) and entry.get("path")]
    if artifact_type == "logs":
        return [entry for entry in record.get("logs", []) if isinstance(entry, Mapping) and entry.get("path")]
    if artifact_type == "charts":
        return [entry for entry in record.get("charts", []) if isinstance(entry, Mapping) and entry.get("path")]
    raise ValueError(f"Unknown artifact type: {artifact_type}")


def create_app(settings: Optional[Settings] = None) -> Any:
    """Create FastAPI app for Hub endpoints."""

    FastAPI, File, HTTPException, Query, UploadFile, FileResponse, HTMLResponse, JSONResponse, _ = _import_fastapi()

    app_settings = settings or get_settings()
    app_settings.paths.ensure_directories()
    run_registry = _registry(app_settings)

    app = FastAPI(
        title="SentiDemand Visualization Gallery",
        version=_RUNS_VERSION,
    )

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
        runs = [_run_card_payload(record) for record in run_registry.list_runs()]
        return HTMLResponse(render_workspace_page(runs=runs, page_title="SentiDemand Hub - Workspace"))

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def run_detail(run_id: str) -> Any:
        record = run_registry.get_run(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run id '{run_id}' not found")

        return HTMLResponse(
            render_detail_page(
                _run_card_payload(record),
                derived_tables=_tables_for_detail(record),
                logs=_logs_for_detail(record),
                charts=_charts_for_detail(record),
                page_title=f"SentiDemand Hub - {record.get('source_file', run_id)}",
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

    @app.get("/chart/{entry_id}")
    def chart(entry_id: str) -> Any:
        manifest = _load_chart_manifest(app_settings)
        entry = next((item for item in manifest["entries"] if str(item.get("id")) == entry_id), None)
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
        record = run_registry.get_run(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run id '{run_id}' not found")

        try:
            collection = _artifact_collection(record, artifact_type)
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
            raise HTTPException(
                status_code=400,
                detail=f"文件格式不支持。当前后缀为 {suffix}，可上传格式为：{allowed}。",
            )

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

            run_dir = _run_artifact_dir(app_settings, results.run_id)
            tables_dir = run_dir / "tables"
            logs_dir = run_dir / "logs"
            tables_dir.mkdir(parents=True, exist_ok=True)
            logs_dir.mkdir(parents=True, exist_ok=True)

            results.save(output_dir=tables_dir)
            summary_path = logs_dir / "run_summary.txt"
            summary_path.write_text(results.summary(), encoding="utf-8")

            exported_log_path: Optional[Path] = None
            if getattr(results, "log_manager", None) is not None:
                exported_log_path = Path(results.log_manager.export_log_entries(logs_dir / "log_entries.json"))

            generated = results.visualize(source_name=target.stem, run_id=results.run_id)
            record = _build_rich_run_record(
                app_settings,
                run_id=results.run_id,
                source_file=target.name,
                results=results,
                generated=generated,
                summary_path=summary_path,
                exported_log_path=exported_log_path,
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
                    "charts": len(record["charts"]),
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
