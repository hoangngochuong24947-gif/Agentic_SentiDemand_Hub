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

## 6. 内存占用与资源控制（小服务器部署）
- 服务进程启动时**不会**加载 pandas / scikit-learn / gensim / jieba / snownlp。
  `CommentPipeline` 只在真正处理上传时惰性加载（`gallery._pipeline_class`），
  因此空闲基线内存约 60 MB（此前约 640 MB）。
- 若需手动触发分析栈，可访问 `comment_analyzer.CommentPipeline` 或直接
  `import comment_analyzer.core.pipeline`。
- 数值库线程数默认被限制为 1（见 `comment_analyzer/_limits.py`，可被环境变量覆盖），
  避免在小内存机器上因多线程 BLAS/OpenMP 造成内存峰值过高。
- 运行记录（`run_registry.json`）与图表清单（`manifest.json`）按 mtime 做进程内缓存，
  避免每次请求重复解析大 JSON。
- 验证命令（在本仓库）：
  - `uv sync --extra dev --extra viz`
  - `.venv/bin/python -m pytest tests/ -q -p no:cacheprovider --no-cov`
  - `.venv/bin/python -m pytest tests/test_import_footprint.py -v -p no:cacheprovider --no-cov`
- 启动命令不变：`python -m comment_analyzer.visualization.gallery --host 0.0.0.0 --port 8765`
