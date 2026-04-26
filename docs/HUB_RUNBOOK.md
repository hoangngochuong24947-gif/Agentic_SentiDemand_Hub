# SentiDemand Hub 运行手册（v2）

## 1. 一步步上传并得到分析结果
1. 启动服务后打开 `http://127.0.0.1:8765`。
2. 在主页点击“上传并分析”，选择评论文件（`csv/xlsx/xls/json`）。
3. 上传成功后会自动跳转到 `表格工作台`（`/workspace/{run_id}`）。
4. 在 `仪表盘` 页面（`/dashboard/{run_id}`）查看可视化结果。
5. 在 `建议` 页面（`/insights/{run_id}`）先保存 DeepSeek Key，再手动点击“生成建议”。
6. 若想回看旧版整合视图，进入 `/legacy` 或 `/runs/{run_id}`。

## 2. 端口与启动命令
- 默认端口来自 `visualization.gallery_port`，默认值 `8765`。
- 启动命令：
  - `python -m comment_analyzer.visualization.gallery`
- 自定义端口：
  - `python -m comment_analyzer.visualization.gallery --port 9000`

## 3. 页面与文件对应关系
- 主页：`/`
  - 文件：`src/comment_analyzer/visualization/pages.py` -> `render_homepage_page`
- 工作台（表格）：`/workspace`、`/workspace/{run_id}`
  - 文件：`pages.py` -> `render_workspace_page`
- 仪表盘（图表）：`/dashboard/{run_id}`
  - 文件：`pages.py` -> `render_dashboard_page`
- 建议页（DeepSeek）：`/insights/{run_id}`
  - 文件：`pages.py` -> `render_insights_page`
- 旧版入口：`/legacy`、`/runs/{run_id}`
  - 文件：`pages.py` -> `render_legacy_page` / `render_detail_page`
- 路由总入口：`src/comment_analyzer/visualization/gallery.py`

## 4. 输出结果在哪个文件夹
- 每次运行统一落盘到：
  - `outputs/workspace_runs/{run_id}/tables`
  - `outputs/workspace_runs/{run_id}/logs`
  - `outputs/workspace_runs/{run_id}/charts`
  - `outputs/workspace_runs/{run_id}/insights`
- 可视化原始 HTML 仍保留在：
  - `~/.sentidemand/outputs`
- 运行索引：
  - `~/.sentidemand/outputs/run_registry.json`

## 5. 解耦方式（核心原则）
- 页面解耦：
  - 表格、图表、建议拆成独立页面，避免挤在同一界面。
- 路由解耦：
  - 页面路由与 artifact 下载路由分离，交互清晰。
- 数据解耦：
  - Run 记录统一标准字段（`type/name/path/preview/downloadable/status/reason`）。
- 能力解耦：
  - 分析管线仍由 `CommentPipeline` 负责。
  - 展示层由 `pages.py` 负责。
  - Hub API 编排和落盘由 `gallery.py` 负责。
  - LLM 建议由 DeepSeek 独立 API 调用逻辑负责。
# React Phase 1 Frontend

The React rebuild lives in `frontend/`.

Development mode:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies current Hub endpoints to `http://127.0.0.1:8765`.

Production build through the existing Hub:

```bash
cd frontend
npm run build
python -m comment_analyzer.visualization.gallery
```

Open `http://127.0.0.1:8765/app`. The FastAPI Hub serves the built React SPA from `frontend/dist` while the old server-rendered pages remain available at the existing routes.

# React Phase 2 Closure

Phase 2 is complete:

- `/api/v1` is mounted into the existing Hub while legacy routes remain available.
- `/api/v1/data/upload` returns a queued job and React polls `/api/v1/analysis/jobs/{job_id}` before navigating to the completed run.
- Stable JSON exists for runs, artifacts, charts, tables, logs, insights, downloads, and errors, with legacy fallback preserved.

Minimum verification target for Phase 2 changes:

```bash
python scripts/check_frontend_rebuild_docs.py
PYTHONPATH=src pytest tests/test_visualization.py tests/test_run_registry.py
cd frontend && npm run typecheck
cd frontend && npm run build
```

Next: continue Phase 4 storage, export, session hardening prep, and job-control work.

# React Phase 3 Verification

Phase 3 is complete enough for Phase 4 handoff:

- Browser verification covered the built React app and representative desktop/mobile routes.
- Chart payloads expose stable structured data for React-native chart cards while keeping legacy HTML artifact references.
- Generated advice can be presented as Findings, Actions, Risks, and supporting context, with markdown/plain text fallback.
- Documentation/memory worker: keep rebuild docs, README, and this runbook current without changing source.

Verification target:

```bash
python scripts/check_frontend_rebuild_docs.py
PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py
cd frontend && npm run typecheck
cd frontend && npm run build
```

Browser smoke setup:

```bash
python -m comment_analyzer.visualization.gallery
cd frontend && npm run dev
```

Principle: keep iframe fallback for existing ECharts HTML artifacts. Structured chart data should improve React route rendering, but existing chart HTML must remain openable and embeddable until replacement rendering is complete.

# React Phase 4 Active Work

Phase 4 is active:

- Backend/API worker: storage abstraction, `POST /api/v1/export/results`, DeepSeek/session hardening prep, local concurrency limits, cancel status, and retry-friendly failed/canceled job states.
- Frontend worker: export and cancel/control UI once the Phase 4 API contracts are available.
- Documentation/memory worker: record progress and verification only; do not edit frontend/backend source.

Verification is pending for Phase 4 source behavior. Target commands:

```bash
python scripts/check_frontend_rebuild_docs.py
PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py
cd frontend && npm run typecheck
cd frontend && npm run build
```
