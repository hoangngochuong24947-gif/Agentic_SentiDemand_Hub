"""Local gallery server for visualization outputs.

Serves generated chart files, exposes a manifest API, and supports
upload-triggered analysis + visualization generation.

Run:
    python -m comment_analyzer.visualization.gallery
"""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from comment_analyzer.core.pipeline import CommentPipeline
from comment_analyzer.core.settings import Settings, get_settings

_ALLOWED_UPLOAD_SUFFIXES = {".csv", ".xlsx", ".xls", ".json"}


def _import_fastapi() -> Tuple[Any, Any, Any, Any, Any, Any, Any, Any]:
    """Import FastAPI stack lazily so base package stays lightweight."""
    try:
        from fastapi import FastAPI, File, HTTPException, UploadFile
        from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "Gallery requires optional dependencies. "
            "Install with: pip install 'comment-analyzer[viz]'"
        ) from exc

    return FastAPI, File, HTTPException, UploadFile, FileResponse, HTMLResponse, JSONResponse, uvicorn


def _manifest_path(settings: Settings) -> Path:
    return settings.paths.get_visualization_path() / "manifest.json"


def _load_manifest(settings: Settings) -> Dict[str, Any]:
    path = _manifest_path(settings)
    if not path.exists():
        return {"version": "1.0", "entries": []}

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Manifest file is invalid, using empty manifest")
        return {"version": "1.0", "entries": []}

    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    entries = [e for e in entries if isinstance(e, dict)]
    entries.sort(key=lambda e: str(e.get("created_at", "")), reverse=True)
    manifest["entries"] = entries
    return manifest


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("_")
    return cleaned or "upload.csv"


def _resolve_entry_path(settings: Settings, entry: Dict[str, Any]) -> Path:
    vis_root = settings.paths.get_visualization_path().resolve()
    rel_path = Path(str(entry.get("output_path", "")))
    target = (vis_root / rel_path).resolve()
    if vis_root not in target.parents and target != vis_root:
        raise ValueError("Invalid output_path outside visualization directory")
    return target


def _build_index_html(settings: Settings, entries: List[Dict[str, Any]]) -> str:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        key = str(entry.get("source_file", "unknown"))
        grouped.setdefault(key, []).append(entry)

    sections: List[str] = []
    for source in sorted(grouped.keys()):
        cards = []
        for e in grouped[source]:
            entry_id = html.escape(str(e.get("id", "")))
            title = html.escape(str(e.get("chart_title", e.get("chart_type", "chart"))))
            chart_type = html.escape(str(e.get("chart_type", "")))
            created_at = html.escape(str(e.get("created_at", "")))
            cards.append(
                f"""
                <a class="card" href="/chart/{entry_id}" target="_blank" rel="noopener noreferrer">
                  <div class="card-title">{title}</div>
                  <div class="card-meta">{chart_type}</div>
                  <div class="card-time">{created_at}</div>
                </a>
                """
            )
        section = f"""
        <section class="group">
          <h2>{html.escape(source)}</h2>
          <div class="grid">
            {''.join(cards)}
          </div>
        </section>
        """
        sections.append(section)

    if not sections:
        sections.append(
            """
            <section class="empty">
              暂无可视化记录。请先运行 Pipeline 并调用 results.visualize(source_name="...")。
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>SentiDemand Visualization Gallery</title>
  <style>
    :root {{
      --bg:#0a0e1a; --card:#142033; --border:#334155; --text:#e2e8f0; --muted:#94a3b8; --accent:#3b82f6;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family: "Segoe UI", "PingFang SC", sans-serif; background: var(--bg); color: var(--text); }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 1.8rem; }}
    .sub {{ color: var(--muted); margin-bottom: 20px; }}
    .actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 22px; }}
    button {{
      border: 1px solid var(--border); background: #1e293b; color: var(--text);
      border-radius: 8px; padding: 8px 12px; cursor: pointer;
    }}
    button:hover {{ border-color: var(--accent); }}
    #upload-status {{ color: var(--muted); font-size: .92rem; }}
    .group {{ margin-bottom: 28px; }}
    .group h2 {{ margin: 0 0 12px; font-size: 1.15rem; color: #bfdbfe; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }}
    .card {{
      display: block; text-decoration: none; color: inherit;
      border: 1px solid var(--border); border-radius: 12px; padding: 12px;
      background: linear-gradient(180deg, rgba(51,65,85,.35), rgba(20,32,51,.8));
    }}
    .card:hover {{ border-color: var(--accent); transform: translateY(-1px); transition: .15s; }}
    .card-title {{ font-weight: 600; margin-bottom: 6px; }}
    .card-meta, .card-time {{ color: var(--muted); font-size: .86rem; }}
    .empty {{
      border: 1px dashed var(--border); border-radius: 12px; padding: 16px; color: var(--muted);
    }}
    .footer {{ margin-top: 24px; color: var(--muted); font-size: .85rem; }}
  </style>
</head>
<body>
  <main class="wrap">
    <h1>SentiDemand Hub · 可视化画廊</h1>
    <p class="sub">输出目录：{html.escape(str(settings.paths.get_visualization_path()))}</p>

    <div class="actions">
      <button onclick="location.reload()">刷新画廊</button>
      <button onclick="document.getElementById('upload').click()">上传并分析</button>
      <input id="upload" type="file" accept=".csv,.xlsx,.xls,.json" hidden />
      <span id="upload-status"></span>
    </div>

    {''.join(sections)}
    <div class="footer">API: <code>/api/manifest</code></div>
  </main>

  <script>
    const uploadInput = document.getElementById('upload');
    const statusNode = document.getElementById('upload-status');
    uploadInput.addEventListener('change', async () => {{
      if (!uploadInput.files.length) return;
      const file = uploadInput.files[0];
      statusNode.textContent = `正在上传并分析: ${{file.name}} ...`;
      const form = new FormData();
      form.append('file', file);
      try {{
        const res = await fetch('/upload', {{ method: 'POST', body: form }});
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'upload failed');
        statusNode.textContent = `完成：生成 ${{data.charts_generated}} 张图`;
        setTimeout(() => location.reload(), 800);
      }} catch (err) {{
        statusNode.textContent = `失败：${{err.message}}`;
      }}
    }});
  </script>
</body>
</html>
"""


def create_app(settings: Optional[Settings] = None) -> Any:
    """Create FastAPI app for gallery endpoints."""
    FastAPI, File, HTTPException, UploadFile, FileResponse, HTMLResponse, JSONResponse, _ = _import_fastapi()

    app_settings = settings or get_settings()
    app_settings.paths.ensure_directories()

    app = FastAPI(
        title="SentiDemand Visualization Gallery",
        version="1.0.0",
    )

    @app.get("/", response_class=HTMLResponse)
    def index() -> Any:
        manifest = _load_manifest(app_settings)
        return HTMLResponse(_build_index_html(app_settings, manifest["entries"]))

    @app.get("/api/manifest", response_class=JSONResponse)
    def api_manifest() -> Any:
        return JSONResponse(_load_manifest(app_settings))

    @app.get("/chart/{entry_id}")
    def chart(entry_id: str) -> Any:
        manifest = _load_manifest(app_settings)
        entry = next((e for e in manifest["entries"] if str(e.get("id")) == entry_id), None)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Chart id '{entry_id}' not found")

        try:
            path = _resolve_entry_path(app_settings, entry)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Chart file does not exist: {path.name}")

        return FileResponse(path, media_type="text/html; charset=utf-8")

    @app.post("/upload", response_class=JSONResponse)
    async def upload(file: UploadFile = File(...)) -> Any:
        original_name = getattr(file, "filename", None) or "upload.csv"
        suffix = Path(original_name).suffix.lower()
        if suffix not in _ALLOWED_UPLOAD_SUFFIXES:
            allowed = ", ".join(sorted(_ALLOWED_UPLOAD_SUFFIXES))
            raise HTTPException(status_code=400, detail=f"Unsupported file type '{suffix}'. Allowed: {allowed}")

        upload_dir = app_settings.paths.get_upload_path()
        upload_dir.mkdir(parents=True, exist_ok=True)
        target = upload_dir / f"{datetime.now():%Y%m%d_%H%M%S}_{_safe_filename(Path(original_name).name)}"

        content = await file.read()
        target.write_bytes(content)
        logger.info(f"Uploaded file saved to {target}")

        try:
            pipeline = CommentPipeline(settings=app_settings)
            df = pipeline.load_data(target)
            results = pipeline.run(df, verbose=False)
            generated = results.visualize(source_name=target.stem)
        except Exception as exc:
            logger.exception("Failed to process uploaded file")
            raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc

        return JSONResponse(
            {
                "uploaded_file": target.name,
                "charts_generated": len(generated),
                "generated_files": generated,
            }
        )

    return app


def run_gallery_server(
    host: str = "127.0.0.1",
    port: Optional[int] = None,
    settings: Optional[Settings] = None,
) -> None:
    """Run the visualization gallery server."""
    *_, uvicorn = _import_fastapi()
    app_settings = settings or get_settings()
    app = create_app(app_settings)
    server_port = port or app_settings.visualization.gallery_port
    logger.info(f"Starting gallery server on http://{host}:{server_port}")
    uvicorn.run(app, host=host, port=server_port)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run SentiDemand visualization gallery server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Bind port (default: visualization.gallery_port)")
    args = parser.parse_args(argv)
    run_gallery_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
