"""FastAPI application for the stable /api/v1 contract."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from fastapi import BackgroundTasks, Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from comment_analyzer.api.schemas import (
    AnalysisRunRequest,
    ArtifactListResponse,
    ChartDataRecord,
    ChartDataResponse,
    ExportResultsRequest,
    ExportResultsResponse,
    HealthResponse,
    InsightGenerateRequest,
    InsightGenerateResponse,
    JobCancelResponse,
    JobResponse,
    RunDetailResponse,
    RunListResponse,
    RunSummary,
    UploadResponse,
)
from comment_analyzer.api.storage import JsonRunStorage, RunStorage
from comment_analyzer.api.store import cancel_job, create_job, get_job, now_iso, update_job, update_job_step
from comment_analyzer.core.settings import Settings, get_settings

API_VERSION = "1.0"
ALLOWED_UPLOAD_SUFFIXES = {".csv", ".xlsx", ".xls", ".json"}
EXPORT_ARTIFACT_GROUPS = ("derived_tables", "charts", "logs", "insights")
EXPORT_GROUP_ALIASES = {
    "tables": "derived_tables",
    "derived_tables": "derived_tables",
    "charts": "charts",
    "logs": "logs",
    "insights": "insights",
}
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"


def _registry_path(settings: Settings) -> Path:
    return settings.paths.get_visualization_path() / "run_registry.json"


def _registry(settings: Settings) -> RunStorage:
    settings.paths.ensure_directories()
    return JsonRunStorage(_registry_path(settings))


def _record_or_404(registry: RunStorage, run_id: str) -> Dict[str, Any]:
    record = registry.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Run id '{run_id}' not found")
    return record


def _run_summary(record: Mapping[str, Any]) -> RunSummary:
    return RunSummary(
        run_id=str(record.get("run_id") or ""),
        source_file=str(record.get("source_file") or ""),
        created_at=str(record.get("created_at") or ""),
        status=str(record.get("status") or "unknown"),
        summary=dict(record.get("summary") or {}),
        user_message=str(record.get("user_message") or ""),
    )


def _run_detail(record: Mapping[str, Any], settings: Settings) -> RunDetailResponse:
    insight = _read_existing_insight(str(record.get("run_id") or ""), settings)
    stored_insights = record.get("insights", [])
    return RunDetailResponse(
        run_id=str(record.get("run_id") or ""),
        source_file=str(record.get("source_file") or ""),
        created_at=str(record.get("created_at") or ""),
        status=str(record.get("status") or "unknown"),
        derived_tables=list(record.get("derived_tables") or []),
        charts=list(record.get("charts") or []),
        logs=list(record.get("logs") or []),
        insights=list(stored_insights or insight.get("artifacts") or []),
        summary=dict(record.get("summary") or {}),
        user_message=str(record.get("user_message") or ""),
        failure_category=record.get("failure_category"),
        failure_message=record.get("failure_message"),
        insight_status=str(record.get("insight_status") or insight.get("status") or "not_generated"),
        insight_updated_at=str(record.get("insight_updated_at") or insight.get("updated_at") or ""),
        advice_markdown=str(insight.get("markdown") or ""),
        structured_advice=dict(insight.get("structured_advice") or {}),
    )


def _artifact_items(record: Mapping[str, Any], key: str) -> list[Dict[str, Any]]:
    items = record.get(key, [])
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, Mapping)]


def _name_matches(item: Mapping[str, Any], *needles: str) -> bool:
    haystack = " ".join(str(item.get(key) or "") for key in ("name", "title", "summary", "chart_type")).lower()
    return any(needle.lower() in haystack for needle in needles)


def _find_table(record: Mapping[str, Any], *needles: str) -> Optional[Dict[str, Any]]:
    for item in _artifact_items(record, "derived_tables"):
        if _name_matches(item, *needles):
            return item
    return None


def _find_chart_artifact(record: Mapping[str, Any], *needles: str) -> Optional[Dict[str, Any]]:
    for item in _artifact_items(record, "charts"):
        if _name_matches(item, *needles):
            return item
    return None


def _preview_rows(table: Optional[Mapping[str, Any]]) -> list[Dict[str, Any]]:
    if not table:
        return []
    preview = table.get("preview")
    if isinstance(preview, Mapping) and isinstance(preview.get("rows"), list):
        return [dict(row) for row in preview["rows"] if isinstance(row, Mapping)]
    values = table.get("values")
    if isinstance(values, Mapping):
        return [{"label": key, "value": value} for key, value in values.items()]
    return []


def _to_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1].strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _first_text(row: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    lowered = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        value = lowered.get(key)
        if value not in (None, ""):
            return str(value)
    for value in row.values():
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _first_number(row: Mapping[str, Any], keys: tuple[str, ...] = ()) -> Optional[float]:
    lowered = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        number = _to_number(lowered.get(key))
        if number is not None:
            return number
    for value in row.values():
        number = _to_number(value)
        if number is not None:
            return number
    return None


def _chart_record(
    *,
    chart_id: str,
    title: str,
    kind: str,
    data: Dict[str, Any],
    legacy_artifact: Optional[Dict[str, Any]],
    reason: str,
) -> ChartDataRecord:
    has_data = any(bool(value) for value in data.values())
    return ChartDataRecord(
        id=chart_id,
        title=title,
        kind=kind,
        status="ready" if has_data else "missing",
        data=data if has_data else {},
        legacy_artifact=legacy_artifact,
        reason="" if has_data else reason,
    )


def _sentiment_chart(record: Mapping[str, Any]) -> ChartDataRecord:
    table = _find_table(record, "sentiment")
    rows = _preview_rows(table)
    segments = []
    for row in rows:
        label = _first_text(row, ("sentiment", "label", "name", "category"))
        value = _first_number(row, ("count", "value", "total"))
        if label and value is not None:
            segments.append({"label": label, "value": value})
    return _chart_record(
        chart_id="sentiment_donut",
        title="Sentiment Distribution",
        kind="donut",
        data={"segments": segments, "total": sum(item["value"] for item in segments)} if segments else {},
        legacy_artifact=_find_chart_artifact(record, "sentiment_donut", "sentiment"),
        reason="No sentiment distribution table preview or values were found.",
    )


def _keyword_chart(record: Mapping[str, Any]) -> ChartDataRecord:
    table = _find_table(record, "keyword", "word_frequency", "top_words")
    rows = _preview_rows(table)
    items = []
    for row in rows[:12]:
        label = _first_text(row, ("word", "keyword", "term", "label", "name"))
        value = _first_number(row, ("score", "weight", "count", "value", "frequency"))
        if label and value is not None:
            items.append({"label": label, "value": value})
    return _chart_record(
        chart_id="keyword_lollipop",
        title="Top Keywords",
        kind="lollipop",
        data={"items": items} if items else {},
        legacy_artifact=_find_chart_artifact(record, "keyword", "wordcloud", "features_lollipop"),
        reason="No keyword ranking preview was found.",
    )


def _feature_chart(record: Mapping[str, Any]) -> ChartDataRecord:
    table = _find_table(record, "feature", "aspect")
    rows = _preview_rows(table)
    items = []
    for row in rows[:12]:
        label = _first_text(row, ("feature", "aspect", "label", "name", "word"))
        value = _first_number(row, ("count", "score", "weight", "value", "frequency"))
        if label and value is not None:
            items.append({"label": label, "value": value})
    return _chart_record(
        chart_id="feature_bars",
        title="Feature Mentions",
        kind="bar",
        data={"items": items} if items else {},
        legacy_artifact=_find_chart_artifact(record, "features", "feature"),
        reason="No feature/aspect table preview was found.",
    )


def _topic_chart(record: Mapping[str, Any]) -> ChartDataRecord:
    table = _find_table(record, "topic")
    rows = _preview_rows(table)
    items = []
    for index, row in enumerate(rows[:8], start=1):
        label = _first_text(row, ("topic", "topic_id", "label", "name", "words")) or f"Topic {index}"
        value = _first_number(row, ("count", "weight", "score", "value")) or 1.0
        words = _first_text(row, ("words", "keywords", "top_words"))
        item: Dict[str, Any] = {"label": label, "value": value}
        if words and words != label:
            item["keywords"] = [part.strip() for part in re.split(r"[,，|/]", words) if part.strip()][:8]
        items.append(item)
    return _chart_record(
        chart_id="topic_rose",
        title="Topic Overview",
        kind="rose",
        data={"items": items} if items else {},
        legacy_artifact=_find_chart_artifact(record, "topic", "topics_nightingale", "topics"),
        reason="No topic table preview was found.",
    )


def _demand_chart(record: Mapping[str, Any]) -> ChartDataRecord:
    table = _find_table(record, "demand_intensity", "demand")
    rows = _preview_rows(table)
    axes = []
    if rows:
        for row in rows[:12]:
            label = _first_text(row, ("demand", "category", "dimension", "label", "name"))
            value = _first_number(row, ("intensity", "mean", "score", "value", "count"))
            if label and value is not None:
                axes.append({"label": label, "value": value})
        if not axes and len(rows) == 1:
            for key, value in rows[0].items():
                number = _to_number(value)
                if number is not None:
                    axes.append({"label": str(key), "value": number})
    return _chart_record(
        chart_id="demand_radar",
        title="Demand Intensity",
        kind="radar",
        data={"axes": axes} if axes else {},
        legacy_artifact=_find_chart_artifact(record, "demand", "radar", "dashboard", "funnel"),
        reason="No demand intensity preview was found.",
    )


def _chart_data_records(record: Mapping[str, Any]) -> list[ChartDataRecord]:
    return [
        _sentiment_chart(record),
        _keyword_chart(record),
        _feature_chart(record),
        _topic_chart(record),
        _demand_chart(record),
    ]


def _read_existing_insight(run_id: str, settings: Settings) -> Dict[str, Any]:
    insights_dir = settings.paths.output_base / "workspace_runs" / run_id / "insights"
    md_path = insights_dir / "advice.md"
    json_path = insights_dir / "advice.json"
    payload: Dict[str, Any] = {
        "status": "not_generated",
        "updated_at": "",
        "markdown": "",
        "structured_advice": {},
        "artifacts": [],
    }
    if md_path.exists():
        payload["markdown"] = md_path.read_text(encoding="utf-8")
        payload["status"] = "generated"
        payload["artifacts"].append(
            {
                "type": "insight",
                "name": md_path.name,
                "path": str(md_path),
                "status": "ready",
                "downloadable": True,
            }
        )
    if json_path.exists():
        try:
            metadata = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            metadata = {}
        payload["updated_at"] = str(metadata.get("generated_at") or "")
        payload["status"] = str(metadata.get("status") or payload["status"])
        if isinstance(metadata.get("structured_advice"), Mapping):
            payload["structured_advice"] = dict(metadata["structured_advice"])
        payload["artifacts"].append(
            {
                "type": "insight",
                "name": json_path.name,
                "path": str(json_path),
                "status": "ready",
                "downloadable": True,
            }
        )
    return payload


def _write_insight(settings: Settings, run_id: str, markdown: str, metadata: Dict[str, Any]) -> list[Dict[str, Any]]:
    insights_dir = settings.paths.output_base / "workspace_runs" / run_id / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)
    md_path = insights_dir / "advice.md"
    json_path = insights_dir / "advice.json"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return [
        {
            "type": "insight",
            "name": "advice.md",
            "title": "Insight advice",
            "summary": "Generated insight markdown.",
            "status": "ready",
            "path": str(md_path),
            "downloadable": True,
            "preview": {"lines": markdown.splitlines()[:12]},
        },
        {
            "type": "insight",
            "name": "advice.json",
            "title": "Insight metadata",
            "summary": "Generated insight metadata.",
            "status": "ready",
            "path": str(json_path),
            "downloadable": True,
            "preview": {"lines": []},
        },
    ]


def _fallback_insight_markdown(record: Mapping[str, Any]) -> str:
    summary = record.get("summary") or {}
    table_count = summary.get("saved_file_count") or len(record.get("derived_tables", []))
    chart_count = summary.get("chart_count") or len(record.get("charts", []))
    log_count = summary.get("log_file_count") or len(record.get("logs", []))
    return "\n".join(
        [
            "# Analysis Insight",
            "",
            f"- Run: {record.get('run_id')}",
            f"- Source: {record.get('source_file')}",
            f"- Status: {record.get('status')}",
            f"- Artifacts: {table_count} tables, {chart_count} charts, {log_count} logs.",
            "",
            "Review the highest-signal tables and charts before making product decisions.",
        ]
    )


def _structured_item(text: str, **extra: Any) -> Dict[str, Any]:
    payload = {"text": text.strip()}
    payload.update({key: value for key, value in extra.items() if value not in (None, "")})
    return payload


def _local_structured_advice(record: Mapping[str, Any]) -> Dict[str, Any]:
    summary = record.get("summary") or {}
    table_count = int(summary.get("saved_file_count") or summary.get("derived_table_count") or len(record.get("derived_tables", [])))
    chart_count = int(summary.get("chart_count") or len(record.get("charts", [])))
    log_count = int(summary.get("log_file_count") or summary.get("log_count") or len(record.get("logs", [])))
    ready_charts = [chart for chart in _chart_data_records(record) if chart.status == "ready"]
    missing_charts = [chart for chart in _chart_data_records(record) if chart.status != "ready"]

    findings = [
        _structured_item(
            f"Run {record.get('run_id')} is {record.get('status') or 'unknown'} for source {record.get('source_file') or 'unknown'}.",
            source="run_registry",
        ),
        _structured_item(
            f"Available artifacts include {table_count} tables, {chart_count} charts, and {log_count} logs.",
            source="artifact_summary",
        ),
    ]
    if ready_charts:
        findings.append(
            _structured_item(
                "Structured chart data is available for: "
                + ", ".join(chart.id for chart in ready_charts[:5])
                + ".",
                source="chart_data",
            )
        )

    actions = [
        _structured_item("Review ready structured charts first, then open the legacy artifact for visual fallback.", priority="high"),
        _structured_item("Validate the top sentiment, keyword, topic, and demand signals against source comments before committing roadmap changes.", priority="medium"),
    ]
    if missing_charts:
        actions.append(
            _structured_item(
                "Regenerate or inspect input data for missing chart sections: "
                + ", ".join(chart.id for chart in missing_charts[:5])
                + ".",
                priority="medium",
            )
        )

    risks = [
        _structured_item("Some charts may be unavailable when the underlying preview tables are absent.", monitor="missing_chart_count"),
        _structured_item("Artifact counts describe generated outputs, not statistical confidence.", monitor="source_sample_quality"),
    ]
    if record.get("failure_message"):
        risks.append(_structured_item(str(record.get("failure_message")), monitor="run_failure"))

    return {
        "findings": findings,
        "actions": actions,
        "risks": risks,
        "context": {
            "run_id": record.get("run_id"),
            "source_file": record.get("source_file"),
            "status": record.get("status"),
            "table_count": table_count,
            "chart_count": chart_count,
            "log_count": log_count,
            "ready_structured_charts": [chart.id for chart in ready_charts],
            "missing_structured_charts": [chart.id for chart in missing_charts],
        },
    }


def _markdown_structured_advice(markdown: str) -> Dict[str, Any]:
    buckets: Dict[str, list[Dict[str, Any]]] = {"findings": [], "actions": [], "risks": []}
    current: Optional[str] = None
    heading_patterns = {
        "findings": ("finding", "insight", "observation", "??", "??", "??"),
        "actions": ("action", "recommend", "next step", "??", "??", "??"),
        "risks": ("risk", "monitor", "watch", "??", "??", "??"),
    }

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = re.sub(r"^[#>*\-\d.\s]+", "", line).strip().lower()
        matched_heading = next(
            (bucket for bucket, needles in heading_patterns.items() if any(needle in heading for needle in needles)),
            None,
        )
        if line.startswith("#") and matched_heading:
            current = matched_heading
            continue
        if matched_heading and len(heading) <= 24:
            current = matched_heading
            continue
        if re.match(r"^[-*]|\d+[.)]\s+", line) and current:
            text = re.sub(r"^[-*]\s*|\d+[.)]\s+", "", line).strip()
            if text:
                buckets[current].append(_structured_item(text, source="markdown"))
            continue
        if current and len(line) > 12:
            buckets[current].append(_structured_item(line, source="markdown"))

    if not any(buckets.values()):
        lines = [line.strip("-*# 0123456789.") for line in markdown.splitlines() if line.strip()]
        buckets["findings"] = [_structured_item(line, source="markdown") for line in lines[:3] if line]

    return {**buckets, "context": {"source": "markdown"}}


def _structured_advice(record: Mapping[str, Any], markdown: str, *, provider: str) -> Dict[str, Any]:
    local = _local_structured_advice(record)
    if provider == "local-fallback":
        local["context"]["provider"] = provider
        return local

    parsed = _markdown_structured_advice(markdown)
    for key in ("findings", "actions", "risks"):
        if not parsed.get(key):
            parsed[key] = local[key]
    context = dict(local.get("context") or {})
    context.update(parsed.get("context") or {})
    context["provider"] = provider
    parsed["context"] = context
    return parsed


def _advice_metrics(record: Mapping[str, Any]) -> Dict[str, Any]:
    summary = record.get("summary") if isinstance(record.get("summary"), Mapping) else {}
    sentiment_table = _find_table(record, "sentiment")
    keyword_table = _find_table(record, "keyword", "word_frequency", "top_words")
    topic_table = _find_table(record, "topic")
    demand_table = _find_table(record, "demand_intensity", "demand")

    return {
        "run_id": record.get("run_id"),
        "source_file": record.get("source_file"),
        "created_at": record.get("created_at"),
        "status": record.get("status"),
        "summary": dict(summary or {}),
        "artifact_counts": _artifact_counts(record),
        "sentiment_preview": _preview_rows(sentiment_table)[:8],
        "keyword_preview": _preview_rows(keyword_table)[:12],
        "topic_preview": _preview_rows(topic_table)[:8],
        "demand_preview": _preview_rows(demand_table)[:8],
        "structured_charts": [
            {
                "id": chart.id,
                "title": chart.title,
                "kind": chart.kind,
                "status": chart.status,
                "reason": chart.reason,
                "data": chart.data,
            }
            for chart in _chart_data_records(record)
        ],
        "failure_category": record.get("failure_category"),
        "failure_message": record.get("failure_message"),
    }


def _build_advice_prompt(record: Mapping[str, Any]) -> str:
    metrics_json = json.dumps(_advice_metrics(record), ensure_ascii=False, indent=2)
    return (
        "你是电商评论分析顾问。请只基于下面的结构化分析结果生成中文决策建议。\n"
        "输出要求：\n"
        "1. 使用 Markdown。\n"
        "2. 必须包含四个二级标题：## Findings、## Actions、## Risks、## Context。\n"
        "3. Findings 给 3 条关键发现，每条要引用可见数据或 artifact 状态。\n"
        "4. Actions 给 3 条可执行动作，按优先级排序，避免空泛建议。\n"
        "5. Risks 给 2 条风险或监控点，说明为什么要关注。\n"
        "6. Context 简要说明 run、数据源、表格/图表/日志数量。\n"
        "7. 不要编造没有出现在 JSON 中的数据；数据缺失时要明确说明缺失。\n\n"
        f"结构化分析结果 JSON：\n{metrics_json}"
    )


def _resolve_deepseek_api_key(payload: InsightGenerateRequest) -> str:
    inline_key = str(payload.api_key or "").strip()
    if inline_key:
        return inline_key

    session_id = str(payload.session_id or "").strip()
    if session_id:
        from comment_analyzer.visualization import gallery

        stored = gallery._SESSION_KEYS.get(session_id, {})
        stored_key = str(stored.get("api_key") or "").strip()
        if stored_key:
            return stored_key

    return os.getenv("DEEPSEEK_API_KEY", "").strip()


def _call_deepseek_advice(api_key: str, prompt: str) -> Dict[str, Any]:
    request_payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是资深数据分析与商业策略顾问，擅长把评论分析结果转成可执行建议。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        DEEPSEEK_ENDPOINT,
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"DeepSeek API error {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"DeepSeek request failed: {exc}") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("DeepSeek response is not valid JSON") from exc

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("DeepSeek returned empty content")
    return {"response": data, "content": content}


async def _save_upload_file(file: UploadFile, settings: Settings) -> Path:
    from comment_analyzer.visualization import gallery

    original_name = file.filename or "upload.csv"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_SUFFIXES))
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}. Allowed: {allowed}")

    upload_dir = settings.paths.get_upload_path()
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"{now_iso().replace(':', '').replace('.', '')}_{gallery._safe_filename(Path(original_name).name)}"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    target.write_bytes(content)
    return target


def _artifact_counts(record: Mapping[str, Any]) -> Dict[str, int]:
    return {
        "derived_tables": len(record.get("derived_tables", [])),
        "charts": len(record.get("charts", [])),
        "logs": len(record.get("logs", [])),
        "insights": len(record.get("insights", [])),
    }


def _export_dir(settings: Settings) -> Path:
    path = settings.paths.output_base / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_export_groups(groups: Optional[list[str]]) -> list[str]:
    if not groups:
        return list(EXPORT_ARTIFACT_GROUPS)

    normalized = []
    for group in groups:
        key = EXPORT_GROUP_ALIASES.get(str(group).strip().lower())
        if key is None:
            allowed = ", ".join(sorted(EXPORT_GROUP_ALIASES))
            raise HTTPException(status_code=422, detail=f"Unsupported artifact group '{group}'. Allowed: {allowed}")
        if key not in normalized:
            normalized.append(key)
    return normalized


def _safe_archive_name(value: str, fallback: str) -> str:
    name = Path(value).name or fallback
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or fallback


def _artifact_file_path(item: Mapping[str, Any]) -> Optional[Path]:
    value = item.get("path") or item.get("file") or item.get("output_path")
    if value in (None, ""):
        return None
    path = Path(str(value))
    return path if path.exists() and path.is_file() else None


def _build_results_export(settings: Settings, record: Mapping[str, Any], groups: Optional[list[str]]) -> ExportResultsResponse:
    run_id = str(record.get("run_id") or "")
    export_id = uuid.uuid4().hex
    selected_groups = _normalize_export_groups(groups)
    zip_path = _export_dir(settings) / f"{run_id or 'run'}_{export_id}.zip"
    included_counts = {group: 0 for group in selected_groups}
    manifest_items = []

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for group in selected_groups:
            for index, item in enumerate(_artifact_items(record, group)):
                path = _artifact_file_path(item)
                if path is None:
                    continue
                artifact_name = _safe_archive_name(str(item.get("name") or path.name), f"artifact_{index}")
                archive_name = f"{group}/{index:03d}_{artifact_name}"
                archive.write(path, archive_name)
                included_counts[group] += 1
                manifest_items.append(
                    {
                        "group": group,
                        "name": str(item.get("name") or path.name),
                        "source_path": str(path),
                        "archive_path": archive_name,
                    }
                )

        manifest = {
            "export_id": export_id,
            "run_id": run_id,
            "created_at": now_iso(),
            "artifact_groups": selected_groups,
            "included_counts": included_counts,
            "artifacts": manifest_items,
        }
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    return ExportResultsResponse(
        export_id=export_id,
        status="ready",
        run_id=run_id,
        download_url=f"/api/v1/export/results/{export_id}/download",
        path=str(zip_path),
        included_counts=included_counts,
    )


def _run_upload_pipeline(upload_path: Path, settings: Settings, job_id: str) -> Dict[str, Any]:
    from comment_analyzer.core.log_manager import get_log_manager
    from comment_analyzer.core.pipeline import CommentPipeline
    from comment_analyzer.visualization import gallery
    from comment_analyzer.visualization.run_registry import build_run_record, classify_upload_failure

    run_id = uuid.uuid4().hex[:12]
    run_registry = _registry(settings)
    current_step = "Upload"

    try:
        update_job(job_id, status="running", message="Upload job running")
        update_job_step(job_id, "Upload", "completed", message="File saved")

        current_step = "Clean"
        update_job_step(job_id, current_step, "running")
        get_log_manager().clear_entries()
        pipeline = CommentPipeline(settings=settings)
        dataframe = pipeline.load_data(upload_path)
        update_job_step(job_id, current_step, "completed")

        current_step = "Sentiment"
        update_job_step(job_id, current_step, "running")
        results = pipeline.run(dataframe, verbose=False)
        results.run_id = results.run_id or run_id
        update_job_step(job_id, "Sentiment", "completed")
        update_job_step(job_id, "Topics", "completed")
        update_job_step(job_id, "Demand", "completed")

        current_step = "Charts"
        update_job_step(job_id, current_step, "running")
        tables_dir = gallery._artifact_dir(settings, results.run_id, "tables")
        logs_dir = gallery._artifact_dir(settings, results.run_id, "logs")
        charts_dir = gallery._artifact_dir(settings, results.run_id, "charts")
        gallery._artifact_dir(settings, results.run_id, "insights")

        results.save(output_dir=tables_dir)
        summary_path = logs_dir / "run_summary.txt"
        summary_path.write_text(results.summary(), encoding="utf-8")

        exported_log_path: Optional[Path] = None
        if getattr(results, "log_manager", None) is not None:
            exported_log_path = Path(results.log_manager.export_log_entries(logs_dir / "log_entries.json"))

        generated = results.visualize(source_name=upload_path.stem, run_id=results.run_id)
        materialized_charts = gallery._materialize_generated_charts(generated, charts_dir)
        record = gallery._build_rich_run_record(
            settings,
            run_id=results.run_id,
            source_file=upload_path.name,
            results=results,
            summary_path=summary_path,
            exported_log_path=exported_log_path,
            chart_files=materialized_charts,
        )
        run_registry.record(record)
        if hasattr(dataframe, "columns"):
            text_column = pipeline.detect_text_column(dataframe)
            run_registry.save_comments(results.run_id, results.processed_data, text_column)
        update_job_step(job_id, current_step, "completed")
        update_job(
            job_id,
            status="completed",
            run_id=str(record.get("run_id") or ""),
            progress=100,
            result={"artifacts": _artifact_counts(record), "run_id": str(record.get("run_id") or "")},
            message=str(record.get("user_message") or "Upload analysis completed"),
        )
        return record
    except Exception as exc:
        try:
            update_job_step(job_id, current_step, "failed", message=str(exc))
        except Exception:
            pass
        failure_category = classify_upload_failure(exc)
        record = build_run_record(
            run_id=run_id,
            source_file=upload_path.name,
            status="failed",
            user_message=str(exc),
            failure_category=failure_category,
            failure_message=str(exc),
        ).to_dict()
        run_registry.record(record)
        update_job(
            job_id,
            status="failed",
            run_id=run_id,
            error=str(exc),
            result={"failure_category": failure_category},
            message="Upload analysis failed",
        )
        return record


def _schedule_upload_job(background_tasks: BackgroundTasks, job_id: str, upload_path: Path, settings: Settings) -> None:
    background_tasks.add_task(_run_upload_pipeline, upload_path, settings, job_id)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    app_settings = settings or get_settings()
    app_settings.paths.ensure_directories()
    app = FastAPI(title="Comment Analyzer API", version=API_VERSION)

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(version=API_VERSION)

    @app.get("/api/v1/runs", response_model=RunListResponse)
    def list_runs() -> RunListResponse:
        records = _registry(app_settings).list_runs()
        runs = [_run_summary(record) for record in records]
        return RunListResponse(runs=runs, total=len(runs))

    @app.get("/api/v1/runs/{run_id}", response_model=RunDetailResponse)
    def get_run(run_id: str) -> RunDetailResponse:
        record = _record_or_404(_registry(app_settings), run_id)
        return _run_detail(record, app_settings)

    @app.get("/api/v1/runs/{run_id}/tables", response_model=ArtifactListResponse)
    def get_run_tables(run_id: str) -> ArtifactListResponse:
        record = _record_or_404(_registry(app_settings), run_id)
        items = _artifact_items(record, "derived_tables")
        return ArtifactListResponse(run_id=run_id, items=items, total=len(items))

    @app.get("/api/v1/runs/{run_id}/charts", response_model=ArtifactListResponse)
    def get_run_charts(run_id: str) -> ArtifactListResponse:
        record = _record_or_404(_registry(app_settings), run_id)
        items = _artifact_items(record, "charts")
        return ArtifactListResponse(run_id=run_id, items=items, total=len(items))

    @app.get("/api/v1/runs/{run_id}/chart-data", response_model=ChartDataResponse)
    def get_run_chart_data(run_id: str) -> ChartDataResponse:
        record = _record_or_404(_registry(app_settings), run_id)
        charts = _chart_data_records(record)
        return ChartDataResponse(run_id=run_id, charts=charts, total=len(charts))

    @app.get("/api/v1/runs/{run_id}/logs", response_model=ArtifactListResponse)
    def get_run_logs(run_id: str) -> ArtifactListResponse:
        record = _record_or_404(_registry(app_settings), run_id)
        items = _artifact_items(record, "logs")
        return ArtifactListResponse(run_id=run_id, items=items, total=len(items))

    @app.get("/api/v1/runs/{run_id}/insights", response_model=ArtifactListResponse)
    def get_run_insights(run_id: str) -> ArtifactListResponse:
        record = _record_or_404(_registry(app_settings), run_id)
        detail = _run_detail(record, app_settings)
        return ArtifactListResponse(run_id=run_id, items=detail.insights, total=len(detail.insights))

    @app.post("/api/v1/data/upload", response_model=UploadResponse)
    async def upload_data(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> UploadResponse:
        upload_path = await _save_upload_file(file, app_settings)
        job = create_job("upload", message="Upload queued")
        update_job_step(job["job_id"], "Upload", "completed", message="File saved")
        update_job(job["job_id"], status="queued", message="Upload queued")
        _schedule_upload_job(background_tasks, job["job_id"], upload_path, app_settings)
        return UploadResponse(
            job_id=job["job_id"],
            status="queued",
            uploaded_file=upload_path.name,
            user_message="Upload accepted and queued for analysis",
        )

    @app.post("/api/v1/analysis/run", response_model=JobResponse)
    def run_analysis(payload: AnalysisRunRequest = Body(default_factory=AnalysisRunRequest)) -> JobResponse:
        registry = _registry(app_settings)
        run_id = payload.run_id
        if run_id is not None:
            _record_or_404(registry, run_id)
        else:
            latest = registry.latest()
            run_id = str(latest.get("run_id")) if latest else None

        job = create_job("analysis", run_id=run_id, message="Analysis job completed by compatibility stub")
        result = {"parameters": payload.parameters}
        if run_id:
            result["run_id"] = run_id
        return JobResponse(**update_job(job["job_id"], status="completed", progress=100, result=result))

    @app.get("/api/v1/analysis/jobs/{job_id}", response_model=JobResponse)
    def get_analysis_job(job_id: str) -> JobResponse:
        job = get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job id '{job_id}' not found")
        return JobResponse(**job)

    @app.post("/api/v1/analysis/jobs/{job_id}/cancel", response_model=JobCancelResponse)
    def cancel_analysis_job(job_id: str) -> JobCancelResponse:
        job = cancel_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job id '{job_id}' not found")
        return JobCancelResponse(**job)

    @app.post("/api/v1/export/results", response_model=ExportResultsResponse)
    def export_results(payload: ExportResultsRequest) -> ExportResultsResponse:
        record = _record_or_404(_registry(app_settings), payload.run_id)
        return _build_results_export(app_settings, record, payload.artifact_groups)

    @app.get("/api/v1/export/results/{export_id}/download")
    def download_results_export(export_id: str) -> Any:
        if not re.fullmatch(r"[a-f0-9]{32}", export_id):
            raise HTTPException(status_code=404, detail="Export not found")
        matches = list(_export_dir(app_settings).glob(f"*_{export_id}.zip"))
        if not matches:
            raise HTTPException(status_code=404, detail="Export not found")
        path = matches[0]
        return FileResponse(path, media_type="application/zip", filename=path.name)

    @app.post("/api/v1/runs/{run_id}/insights/generate", response_model=InsightGenerateResponse)
    def generate_insights(
        run_id: str,
        payload: InsightGenerateRequest = Body(default_factory=InsightGenerateRequest),
    ) -> InsightGenerateResponse:
        registry = _registry(app_settings)
        record = _record_or_404(registry, run_id)
        job = create_job("insight", run_id=run_id, message="Insight generation started")

        try:
            api_key = _resolve_deepseek_api_key(payload)
            if api_key:
                prompt = _build_advice_prompt(record)
                deepseek_result = _call_deepseek_advice(api_key, prompt)
                markdown = str(deepseek_result["content"]).strip()
                response_payload = deepseek_result.get("response", {})
                provider = "deepseek"
            else:
                markdown = _fallback_insight_markdown(record)
                response_payload = {"provider": "local-fallback"}
                provider = "local-fallback"

            timestamp = now_iso()
            structured_advice = _structured_advice(record, markdown, provider=provider)
            artifacts = _write_insight(
                app_settings,
                run_id,
                markdown,
                {
                    "status": "generated",
                    "generated_at": timestamp,
                    "response": response_payload,
                    "structured_advice": structured_advice,
                },
            )
            record["insight_status"] = "generated"
            record["insight_updated_at"] = timestamp
            record["insights"] = artifacts
            registry.record(record)
            update_job(
                job["job_id"],
                status="completed",
                progress=100,
                result={"artifacts": artifacts},
                message="Insight generated",
            )
        except Exception as exc:
            update_job(job["job_id"], status="failed", error=str(exc), message="Insight generation failed")
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return InsightGenerateResponse(
            run_id=run_id,
            job_id=job["job_id"],
            status="completed",
            insight_status="generated",
            insight_updated_at=str(record.get("insight_updated_at") or ""),
            advice_markdown=markdown,
            structured_advice=structured_advice,
            artifacts=artifacts,
        )

    @app.get("/api/v1/runs/{run_id}/artifacts/{artifact_type}/{artifact_index}")
    def get_artifact_file(run_id: str, artifact_type: str, artifact_index: int) -> Any:
        mapping = {"tables": "derived_tables", "logs": "logs", "charts": "charts", "insights": "insights"}
        key = mapping.get(artifact_type, artifact_type)
        record = _record_or_404(_registry(app_settings), run_id)
        items = _artifact_items(record, key)
        if artifact_index < 0 or artifact_index >= len(items):
            raise HTTPException(status_code=404, detail="Artifact index out of range")
        path = Path(str(items[artifact_index].get("path") or ""))
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="Artifact file not found")
        return JSONResponse(
            {
                "path": str(path),
                "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            }
        )

    @app.get("/api/v1/runs/{run_id}/comments")
    def get_run_comments(run_id: str) -> Any:
        registry = _registry(app_settings)
        _record_or_404(registry, run_id)
        comments = registry.get_comments(run_id)
        return JSONResponse({"comments": comments})

    @app.post("/api/v1/comments/{comment_id}/update")
    async def update_run_comment(comment_id: int, payload: Dict[str, Any] = Body(...)) -> Any:
        registry = _registry(app_settings)
        registry.update_comment(comment_id, payload)
        return JSONResponse({"status": "ok", "message": "Comment updated successfully"})

    return app


app = create_app()
