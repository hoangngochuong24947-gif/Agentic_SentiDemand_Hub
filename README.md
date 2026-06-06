# Agentic SentiDemand Hub / 智能评论需求洞察中枢

> A reusable NLP toolkit for e-commerce comment analysis, topic discovery, demand insights, and standalone visualization generation.
> 一个可复用的电商评论 NLP 分析工具包，支持情感分析、主题发现、需求洞察与独立可视化生成。

---

## English

### React Frontend Rebuild Current Status

The React rebuild is implemented under `frontend/` with Vite + React + TypeScript. The rebuilt app is served by the existing FastAPI Hub at `/app/`; the legacy Python-rendered pages are still kept for compatibility on older routes such as `/`.

Current rebuild status:

- Phase 1: React shell, routes, visual system, and legacy endpoint adapter are complete.
- Phase 2: `/api/v1` is mounted, upload analysis is an async job, and React polls job progress.
- Phase 3: structured chart data and structured advice are implemented, with legacy ECharts HTML and markdown fallback preserved.
- Phase 4: JSON-backed storage adapter, zip export endpoint, job cancel primitives, React export/cancel UI, and Playwright smoke checks are complete enough for handoff.

#### Start The React App Through FastAPI

```bash
cd frontend
npm install
npm run build

cd ..
python -m comment_analyzer.visualization.gallery
```

Open:

- React app: `http://127.0.0.1:8765/app/`
- Legacy compatibility UI: `http://127.0.0.1:8765/`

Use another port when `8765` is busy:

```bash
python -m comment_analyzer.visualization.gallery --port 8893
```

Then open `http://127.0.0.1:8893/app/`.

#### Development Mode

Run the Hub backend first, then run Vite:

```bash
python -m comment_analyzer.visualization.gallery --port 8765

cd frontend
npm install
npm run dev
```

The React API client prefers `/api/v1` and keeps legacy fallback where needed. Set `VITE_USE_API_V1=0` only when testing the old adapter path.

#### Frontend Navigation And Text

The React top navigation uses compact English labels:

- `Upload`: upload and analyze a review/comment file.
- `Runs`: view historical analysis runs.
- `Tables`: inspect generated table previews and open/download artifacts.
- `Charts`: view structured React-native chart cards and legacy chart files.
- `Advice`: save a DeepSeek session key and generate decision advice.

Primary action labels:

- `Analyze`: submit the selected file for analysis.
- `Cancel analysis`: request cancellation for queued/running upload jobs.
- `Export`: create a zip package for the current run.
- `Open export`: open/download the generated export package.
- `Save`: save the DeepSeek key into the backend session.
- `Generate`: generate AI advice for the current run.

#### Upload File Workflow

Supported upload extensions:

- `.csv`
- `.xlsx`
- `.xls`
- `.json`

React upload behavior:

1. Open `/app/`.
2. Select or drop a file in the upload panel.
3. Click `Analyze`.
4. The frontend calls `POST /api/v1/data/upload`.
5. The backend saves the upload, creates a job, and returns immediately with `job_id` and `status="queued"`.
6. React polls `GET /api/v1/analysis/jobs/{job_id}`.
7. The progress UI shows six stages: `Upload`, `Clean`, `Sentiment`, `Topics`, `Demand`, `Charts`.
8. When the job completes, React navigates to `/app/workspace/{run_id}`.

Cancellation note: `Cancel analysis` is cooperative. Queued jobs can be marked canceled; running jobs are marked cancel requested/canceling, but the current Python pipeline is not force-killed.

#### Tables, Charts, Advice, And Export

- Tables: `/app/workspace/{run_id}` shows table previews with horizontal scrolling for wide tables, plus open/download artifact actions.
- Charts: `/app/dashboard/{run_id}` uses `GET /api/v1/runs/{run_id}/chart-data` for native React chart cards, while keeping legacy ECharts HTML artifacts visible.
- Advice: `/app/insights/{run_id}` renders structured `Findings`, `Actions`, `Risks`, and `Context`; markdown remains as fallback/artifact.
- Export: Workspace, Dashboard, and Run Detail include `Export`; it calls `POST /api/v1/export/results` and returns a downloadable zip with `manifest.json`.

#### Key API Endpoints

Current stable `/api/v1` endpoints:

- `GET /api/v1/health`
- `GET /api/v1/runs`
- `GET /api/v1/runs/{run_id}`
- `GET /api/v1/runs/{run_id}/tables`
- `GET /api/v1/runs/{run_id}/charts`
- `GET /api/v1/runs/{run_id}/chart-data`
- `GET /api/v1/runs/{run_id}/logs`
- `GET /api/v1/runs/{run_id}/insights`
- `POST /api/v1/data/upload`
- `POST /api/v1/analysis/run`
- `GET /api/v1/analysis/jobs/{job_id}`
- `POST /api/v1/analysis/jobs/{job_id}/cancel`
- `POST /api/v1/runs/{run_id}/insights/generate`
- `POST /api/v1/export/results`
- `GET /api/v1/export/results/{export_id}/download`

Legacy compatibility endpoints still available:

- `GET /api/manifest`
- `GET /api/runs/{run_id}`
- `POST /upload`
- `GET /runs/{run_id}/artifacts/{artifact_type}/{artifact_index}`
- `GET /chart/{entry_id}`
- `POST /api/session/deepseek-key`
- `POST /api/runs/{run_id}/insights/generate`

#### Verification

Recommended verification after frontend/API changes:

```bash
python scripts/check_frontend_rebuild_docs.py
PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py
cd frontend && npm run typecheck
cd frontend && npm run build
```

Recent Playwright smoke screenshots are written under:

- `docs/frontend_rebuild_screenshots/playwright-upload-smoke.png`
- `docs/frontend_rebuild_screenshots/playwright-workspace-smoke.png`
- `docs/frontend_rebuild_screenshots/playwright-dashboard-smoke.png`
- `docs/frontend_rebuild_screenshots/playwright-insights-mobile-smoke.png`
- `docs/frontend_rebuild_screenshots/playwright-detail-smoke.png`

## 中文使用教程（React 重构版）

当前新版前端已经重构为 Vite + React + TypeScript，代码在 `frontend/`。FastAPI Hub 会在 `/app/` 挂载新版 React 前端；旧版 Python 页面仍保留在 `/` 等旧路由，作为兼容入口。

### 1. 启动新版前端

先构建 React，再启动 Hub：

```bash
cd frontend
npm install
npm run build

cd ..
python -m comment_analyzer.visualization.gallery
```

打开：

- 新版 React 前端：`http://127.0.0.1:8765/app/`
- 旧版兼容页面：`http://127.0.0.1:8765/`

如果 `8765` 端口被占用，可以指定其他端口：

```bash
python -m comment_analyzer.visualization.gallery --port 8893
```

然后打开 `http://127.0.0.1:8893/app/`。

开发模式：

```bash
python -m comment_analyzer.visualization.gallery --port 8765

cd frontend
npm install
npm run dev
```

React 默认优先调用 `/api/v1`。只有测试旧接口适配时，才需要设置 `VITE_USE_API_V1=0`。

### 2. 前端页面与按钮说明

顶部导航：

- `Upload`：上传评论/评价文件并开始分析。
- `Runs`：查看历史分析任务。
- `Tables`：查看生成表格、预览数据、打开或下载 artifact。
- `Charts`：查看结构化 React 图表，并保留旧 ECharts HTML 图表文件。
- `Advice`：保存 DeepSeek session key，并生成决策建议。

主要按钮：

- `Analyze`：提交当前选择的文件并开始分析。
- `Cancel analysis`：请求取消排队中或运行中的分析任务。
- `Export`：把当前 run 的结果打包成 zip。
- `Open export`：打开或下载已经生成的导出包。
- `Save`：把 DeepSeek key 保存到后端 session。
- `Generate`：为当前 run 生成 AI 建议。

### 3. 上传文件处理流程

支持上传：

- `.csv`
- `.xlsx`
- `.xls`
- `.json`

操作步骤：

1. 打开 `/app/`。
2. 在上传区域选择或拖入文件。
3. 点击 `Analyze`。
4. 前端调用 `POST /api/v1/data/upload`。
5. 后端保存文件，创建后台 job，并立即返回 `job_id` 和 `status="queued"`。
6. 前端轮询 `GET /api/v1/analysis/jobs/{job_id}`。
7. 上传进度会显示六个阶段：`Upload`、`Clean`、`Sentiment`、`Topics`、`Demand`、`Charts`。
8. 分析完成后，页面自动跳转到 `/app/workspace/{run_id}`。

取消说明：`Cancel analysis` 目前是协作式取消。排队中的任务可以标记为 canceled；已经运行中的任务会标记为 cancel requested/canceling，但不会强制杀掉正在执行的 Python pipeline。

### 4. 表格、图表、建议与导出

- 表格页：`/app/workspace/{run_id}`，用于查看表格预览。宽表会横向滚动，避免内容被挤成竖排。
- 图表页：`/app/dashboard/{run_id}`，优先使用 `GET /api/v1/runs/{run_id}/chart-data` 渲染 React 原生图表，同时保留旧 HTML 图表文件。
- 建议页：`/app/insights/{run_id}`，优先显示结构化 `Findings`、`Actions`、`Risks`、`Context`，markdown 仍作为 fallback/artifact 保留。
- 导出：Workspace、Dashboard、Run Detail 页面都有 `Export`。点击后调用 `POST /api/v1/export/results`，生成包含 `manifest.json` 的 zip 包。

### 5. 关键接口

当前稳定 `/api/v1` 接口：

- `GET /api/v1/health`
- `GET /api/v1/runs`
- `GET /api/v1/runs/{run_id}`
- `GET /api/v1/runs/{run_id}/tables`
- `GET /api/v1/runs/{run_id}/charts`
- `GET /api/v1/runs/{run_id}/chart-data`
- `GET /api/v1/runs/{run_id}/logs`
- `GET /api/v1/runs/{run_id}/insights`
- `POST /api/v1/data/upload`
- `POST /api/v1/analysis/run`
- `GET /api/v1/analysis/jobs/{job_id}`
- `POST /api/v1/analysis/jobs/{job_id}/cancel`
- `POST /api/v1/runs/{run_id}/insights/generate`
- `POST /api/v1/export/results`
- `GET /api/v1/export/results/{export_id}/download`

旧接口仍保留兼容：

- `GET /api/manifest`
- `GET /api/runs/{run_id}`
- `POST /upload`
- `GET /runs/{run_id}/artifacts/{artifact_type}/{artifact_index}`
- `GET /chart/{entry_id}`
- `POST /api/session/deepseek-key`
- `POST /api/runs/{run_id}/insights/generate`

### 6. 验证命令

前端或 API 改动后建议运行：

```bash
python scripts/check_frontend_rebuild_docs.py
PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py
cd frontend && npm run typecheck
cd frontend && npm run build
```

最近的 Playwright 截图保存在：

- `docs/frontend_rebuild_screenshots/playwright-upload-smoke.png`
- `docs/frontend_rebuild_screenshots/playwright-workspace-smoke.png`
- `docs/frontend_rebuild_screenshots/playwright-dashboard-smoke.png`
- `docs/frontend_rebuild_screenshots/playwright-insights-mobile-smoke.png`
- `docs/frontend_rebuild_screenshots/playwright-detail-smoke.png`

### 1. What This Project Is

**Agentic SentiDemand Hub** is built on `comment_analyzer`, a modular Python pipeline for analyzing review/comment datasets.

It provides:

- Text preprocessing (cleaning, segmentation, stopword filtering)
- Sentiment labeling + ML classification
- Keyword extraction + LDA topic modeling
- Demand intensity and co-occurrence analysis
- Standalone HTML visualizations (ECharts)
- Optional local gallery server for browsing historical charts and uploading files

---

### 2. Core Features

- **Typed configuration** with Pydantic (`Settings`, env override support)
- **Structured logging** with Loguru
- **Output management** with categorized folders and sequence-safe saving
- **Visualization module** with 14 chart generators:
  - Sentiment: donut, wordcloud-style dual bars, distribution, scatter
  - Features: bidirectional bar, lollipop, heatmap, TF-IDF scatter
  - Topics: nightingale rose, bubble matrix, radar
  - Demand: funnel, network graph, dashboard
- **Gallery server (optional deps)**:
  - `GET /` gallery UI
  - `GET /api/manifest` manifest JSON
  - `GET /chart/{id}` chart file view
  - `POST /upload` upload + run pipeline + generate charts

---

### 3. Installation

#### Base install

```bash
pip install -e .
```

#### Development dependencies

```bash
pip install -e ".[dev]"
```

#### Visualization gallery dependencies (optional)

```bash
pip install -e ".[viz]"
```

Python requirement: **3.8+**

---

### 4. Quick Start

```python
from comment_analyzer import CommentPipeline

pipeline = CommentPipeline()
df = pipeline.load_data("data/comments.csv")
results = pipeline.run(df)

print(results.sentiment_distribution)
print(results.top_keywords[:10])
print(results.topics[:3])
```

---

### 5. Generate Visualizations

```python
# Generate all enabled charts to local HTML files
files = results.visualize(source_name="comments_batch_01")
print(files[:3])
```

Default visualization output path:

- `~/.sentidemand/outputs/{source}_{YYYYMMDD}/`
- Global index: `~/.sentidemand/outputs/manifest.json`

---

### 6. Run Local Gallery

```bash
python -m comment_analyzer.visualization.gallery
```

Default URL:

- `http://127.0.0.1:8765`

If optional deps are missing, install:

```bash
pip install -e ".[viz]"
```

---

### 7. Configuration

Default config file:

- `config/default.yaml`

Main sections:

- `data`
- `preprocessing`
- `sentiment`
- `topic`
- `demand`
- `output`
- `paths`
- `visualization`

Environment variables:

- Prefix: `COMMENT_ANALYZER_`
- Nested delimiter: `__`

Example:

```bash
COMMENT_ANALYZER_PATHS__VISUALIZATION_BASE=/custom/vis/path
COMMENT_ANALYZER_VISUALIZATION__AUTO_OPEN_BROWSER=false
```

---

### 8. Output Structure

Analysis outputs (default):

- `./outputs/demand_analysis/`
- `./outputs/sentiment_models/`
- `./outputs/word_frequency/`
- `./outputs/derived_columns/`
- `./outputs/logs/`

Visualization outputs (default):

- `~/.sentidemand/outputs/`
- `~/.sentidemand/uploads/`

---

### 9. Development

Run tests:

```bash
pytest
```

Format / lint / typing:

```bash
black src tests
flake8 src tests
mypy src
```

#### Korean validation dataset

This repository includes a synthetic Korean review dataset generator for
language-specific validation:

```bash
python scripts/generate_korean_test_dataset.py
python scripts/validate_korean_pipeline.py
```

Generated files:

- `data/korean_reviews_mock.csv`
- `data/korean_reviews_mock.json`
- `outputs/korean_validation_report.json`

The Korean pipeline currently supports a regex fallback segmenter. If `konlpy`
is installed, `Okt` can be selected through:

```bash
COMMENT_ANALYZER_DATA__LANGUAGE=ko
COMMENT_ANALYZER_PREPROCESSING__SEGMENTATION__BACKEND=okt
COMMENT_ANALYZER_SENTIMENT__LABELING_METHOD=lexicon
```

#### README update policy

Keep this README updated with every meaningful project change. Commits that
change source code, configuration, scripts, tests, or data should include a
staged `README.md` update explaining the user-facing workflow, validation
steps, or operational impact.

Install the repository hooks after cloning or when hook templates change:

```bash
python scripts/install_hooks.py
```

The pre-commit hook enforces this README policy before running the focused
verification tests.

---

### 10. Project Layout

```text
Agentic_SentiDemand_Hub/
├─ config/
├─ data/
├─ docs/
├─ examples/
├─ src/comment_analyzer/
│  ├─ core/
│  ├─ preprocessing/
│  ├─ sentiment/
│  ├─ topic/
│  ├─ demand/
│  └─ visualization/
│     ├─ charts/
│     ├─ templates/
│     ├─ generator.py
│     └─ gallery.py
└─ tests/
```

---

## 中文

### 1. 项目简介

**Agentic SentiDemand Hub** 基于 `comment_analyzer`，是一个模块化的评论数据分析流水线。

它提供：

- 文本预处理（清洗、分词、停用词过滤）
- 情感打标与机器学习分类
- 关键词提取与 LDA 主题建模
- 需求强度与共现关系分析
- 独立 HTML 可视化（ECharts）
- 可选本地画廊服务（浏览历史图表、上传文件自动分析）

---

### 2. 核心能力

- **强类型配置**（Pydantic，支持环境变量覆盖）
- **结构化日志**（Loguru）
- **输出管理**（分类目录 + 序号安全保存）
- **可视化模块**（14 种图表生成器）
- **画廊服务（可选依赖）**
  - `GET /` 画廊页面
  - `GET /api/manifest` 注册表 JSON
  - `GET /chart/{id}` 图表查看
  - `POST /upload` 上传并自动跑分析 + 生成图表

---

### 3. 安装

#### 基础安装

```bash
pip install -e .
```

#### 开发依赖

```bash
pip install -e ".[dev]"
```

#### 可视化画廊依赖（可选）

```bash
pip install -e ".[viz]"
```

Python 版本要求：**3.8+**

---

### 4. 快速开始

```python
from comment_analyzer import CommentPipeline

pipeline = CommentPipeline()
df = pipeline.load_data("data/comments.csv")
results = pipeline.run(df)

print(results.sentiment_distribution)
print(results.top_keywords[:10])
print(results.topics[:3])
```

---

### 5. 生成可视化

```python
files = results.visualize(source_name="comments_batch_01")
print(files[:3])
```

默认可视化输出路径：

- `~/.sentidemand/outputs/{数据源}_{YYYYMMDD}/`
- 全局索引：`~/.sentidemand/outputs/manifest.json`

---

### 6. 启动画廊

```bash
python -m comment_analyzer.visualization.gallery
```

默认地址：

- `http://127.0.0.1:8765`

若提示缺依赖，请安装：

```bash
pip install -e ".[viz]"
```

---

### 7. 配置说明

默认配置文件：

- `config/default.yaml`

主要配置节：

- `data`
- `preprocessing`
- `sentiment`
- `topic`
- `demand`
- `output`
- `paths`
- `visualization`

环境变量规则：

- 前缀：`COMMENT_ANALYZER_`
- 嵌套分隔符：`__`

示例：

```bash
COMMENT_ANALYZER_PATHS__VISUALIZATION_BASE=/custom/vis/path
COMMENT_ANALYZER_VISUALIZATION__AUTO_OPEN_BROWSER=false
```

---

### 8. 输出目录

分析输出（默认）：

- `./outputs/demand_analysis/`
- `./outputs/sentiment_models/`
- `./outputs/word_frequency/`
- `./outputs/derived_columns/`
- `./outputs/logs/`

可视化输出（默认）：

- `~/.sentidemand/outputs/`
- `~/.sentidemand/uploads/`

---

### 9. 开发命令

运行测试：

```bash
pytest
```

格式化 / 检查：

```bash
black src tests
flake8 src tests
mypy src
```

---

### 10. 开源协议

本项目采用 **MIT License**，详见 `LICENSE`。
