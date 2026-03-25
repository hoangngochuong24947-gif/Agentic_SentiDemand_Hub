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
              <div class="empty-kicker">No Signal Yet</div>
              <div class="empty-title">这里还没有形成可阅读的洞察。</div>
              <div class="empty-copy">导入一批评论后，系统会在这里生成图表、证据线索与可直接汇报的分析资产。</div>
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>SentiDemand Desk</title>
  <style>
    :root {{
      --bg:#07111f; --bg-soft:#0f1a2d; --card:#132237; --card-strong:#182a44;
      --border:rgba(148,163,184,.18); --text:#ecf3fb; --muted:#8ea3bb; --accent:#4ea1ff;
      --accent-soft:rgba(78,161,255,.16); --success:#19c37d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin:0; font-family: "Segoe UI", "PingFang SC", sans-serif; color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(78,161,255,.14), transparent 32%),
        radial-gradient(circle at 85% 15%, rgba(25,195,125,.10), transparent 20%),
        linear-gradient(180deg, #07111f 0%, #091423 42%, #0b1626 100%);
    }}
    .wrap {{ max-width: 1260px; margin: 0 auto; padding: 32px 24px 56px; }}
    .hero {{
      padding: 28px; border: 1px solid var(--border); border-radius: 24px; margin-bottom: 24px;
      background: linear-gradient(180deg, rgba(24,42,68,.78), rgba(11,22,38,.92));
      box-shadow: 0 22px 48px rgba(0,0,0,.26);
    }}
    .eyebrow {{
      display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px;
      background: var(--accent-soft); color:#cfe6ff; font-size:.8rem; letter-spacing:.04em;
      text-transform:uppercase; margin-bottom:16px;
    }}
    h1 {{ margin: 0 0 10px; font-size: 2.3rem; letter-spacing: -.03em; }}
    .sub {{ color: var(--muted); margin: 0; max-width: 760px; line-height: 1.7; }}
    .hero-meta {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 22px; }}
    .meta-card {{
      padding: 14px 16px; border: 1px solid var(--border); border-radius: 16px; background: rgba(10,19,33,.45);
    }}
    .meta-label {{ color: var(--muted); font-size: .8rem; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .04em; }}
    .meta-value {{ color: var(--text); font-size: 1rem; line-height: 1.5; }}
    .actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 22px; align-items: center; }}
    button {{
      border: 1px solid var(--border); background: rgba(19,34,55,.9); color: var(--text);
      border-radius: 999px; padding: 10px 16px; cursor: pointer; font-weight: 600;
    }}
    button:hover {{ border-color: var(--accent); background: rgba(24,42,68,.95); }}
    .primary {{
      background: linear-gradient(135deg, #3b82f6, #2563eb); border-color: transparent;
    }}
    #upload-status {{ color: var(--muted); font-size: .92rem; }}
    .group {{ margin-bottom: 28px; }}
    .group h2 {{ margin: 0 0 12px; font-size: 1.15rem; color: #d8e9ff; letter-spacing: -.02em; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }}
    .card {{
      display: block; text-decoration: none; color: inherit;
      border: 1px solid var(--border); border-radius: 18px; padding: 16px;
      background: linear-gradient(180deg, rgba(24,42,68,.75), rgba(15,26,45,.95));
    }}
    .card:hover {{ border-color: var(--accent); transform: translateY(-1px); transition: .15s; box-shadow: 0 18px 30px rgba(0,0,0,.18); }}
    .card-title {{ font-weight: 700; margin-bottom: 8px; line-height: 1.4; }}
    .card-meta, .card-time {{ color: var(--muted); font-size: .86rem; }}
    .empty {{
      border: 1px dashed var(--border); border-radius: 20px; padding: 24px; color: var(--muted);
      background: rgba(10,19,33,.36);
    }}
    .empty-kicker {{ text-transform: uppercase; letter-spacing: .08em; font-size: .78rem; color: #cfe6ff; margin-bottom: 10px; }}
    .empty-title {{ font-size: 1.2rem; color: var(--text); margin-bottom: 8px; }}
    .empty-copy {{ line-height: 1.7; max-width: 680px; }}
    .footer {{ margin-top: 24px; color: var(--muted); font-size: .85rem; }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div class="eyebrow">SentiDemand Desk</div>
      <h1>把评论，变成可执行的判断</h1>
      <p class="sub">从情绪、主题与需求信号中，提炼产品机会、风险预警与下一步动作。这里不只是图表仓库，而是每一次评论分析的决策入口。</p>
      <div class="hero-meta">
        <div class="meta-card">
          <div class="meta-label">Workspace</div>
          <div class="meta-value">{html.escape(str(settings.paths.get_visualization_path()))}</div>
        </div>
        <div class="meta-card">
          <div class="meta-label">What You Get</div>
          <div class="meta-value">Charts, AI briefing package, and evidence-ready artifacts</div>
        </div>
        <div class="meta-card">
          <div class="meta-label">Best For</div>
          <div class="meta-value">产品复盘、用户洞察、管理层摘要</div>
        </div>
      </div>
    </section>

    <div class="actions">
      <button onclick="location.reload()">刷新当前洞察</button>
      <button class="primary" onclick="document.getElementById('upload').click()">导入评论数据</button>
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
      statusNode.textContent = `已接收 ${{file.name}}，正在检查结构并提炼洞察...`;
      const form = new FormData();
      form.append('file', file);
      try {{
        const res = await fetch('/upload', {{ method: 'POST', body: form }});
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'upload failed');
        statusNode.textContent = `分析完成：已生成 ${{data.charts_generated}} 张图表，并同步产出 AI briefing 包。`;
        setTimeout(() => location.reload(), 800);
      }} catch (err) {{
        statusNode.textContent = `本次导入未完成：${{err.message}}`;
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
            briefing = results.build_ai_briefing(source_name=target.stem)
        except Exception as exc:
            logger.exception("Failed to process uploaded file")
            raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc

        return JSONResponse(
            {
                "uploaded_file": target.name,
                "charts_generated": len(generated),
                "generated_files": generated,
                "ai_briefing_preview": {
                    "source_name": briefing.payload.get("source_name"),
                    "keywords": briefing.payload.get("top_keywords", [])[:5],
                },
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
