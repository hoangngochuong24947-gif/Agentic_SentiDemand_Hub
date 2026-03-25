# Agentic_SentiDemand_Hub 项目结构分析

## 1. 项目定位

`Agentic_SentiDemand_Hub` 是一个面向电商评论数据的通用 NLP 分析工具包，核心能力包括：

- 文本预处理（清洗、分词、停用词）
- 情感分析（规则标注 + 传统 ML 分类）
- 主题建模（TF-IDF 关键词 + LDA）
- 需求洞察（需求强度 + 共现相关性）
- 可视化（14 个 ECharts 图 + 本地 Gallery 服务）

---

## 2. 目录结构总览

```text
Agentic_SentiDemand_Hub/
├─ config/                 # 默认配置、停用词、需求词典
├─ data/                   # 示例/输入数据
├─ docs/                   # 设计与 API 文档
├─ examples/               # 端到端示例与演示脚本
├─ outputs/                # 分析输出目录（本地运行产物）
├─ src/
│  └─ comment_analyzer/
│     ├─ core/             # 配置、日志、输出管理、Pipeline 编排
│     ├─ preprocessing/    # cleaner / segmenter / stopword filter
│     ├─ sentiment/        # labeler / vectorizer / classifier
│     ├─ topic/            # keyword extractor / LDA
│     ├─ demand/           # intensity / correlation
│     └─ visualization/    # 图表生成器、图表模板、Gallery 服务
├─ tests/                  # 单测与集成测试
├─ pyproject.toml          # 包配置、依赖、pytest/mypy/black 配置
└─ README.md               # 项目说明与快速开始
```

---

## 3. 关键入口文件

- `src/comment_analyzer/__init__.py`  
  对外导出 `CommentPipeline`、`Settings`、`OutputManager`、`LogManager` 等统一 API。

- `src/comment_analyzer/core/pipeline.py`  
  主入口：负责加载数据、自动识别文本列、执行 4 阶段分析并汇总结果。

- `src/comment_analyzer/core/settings.py`  
  Pydantic 配置中心，支持环境变量覆盖（`COMMENT_ANALYZER_` 前缀）。

- `src/comment_analyzer/visualization/generator.py`  
  将 `PipelineResults` 生成独立 HTML 图表，并写入 `manifest.json`。

- `src/comment_analyzer/visualization/gallery.py`  
  提供 FastAPI 本地可视化画廊和上传即分析接口。

---

## 4. 技术栈识别

- 语言与构建：Python 3.8+、setuptools
- 数据与建模：pandas、numpy、scikit-learn、gensim、SnowNLP、jieba
- 配置与日志：pydantic/pydantic-settings、loguru
- 可视化与服务：ECharts（前端）、FastAPI + Uvicorn（可选）
- 测试与质量：pytest、pytest-cov、black、flake8、mypy

---

## 5. 架构风格

项目采用“单进程 pipeline 编排 + 模块化分析器 + 可插拔可视化”的结构：

- 编排层：`CommentPipeline` 负责统一流程
- 能力层：preprocessing/sentiment/topic/demand 各子模块职责单一
- 输出层：`PipelineResults` + `OutputManager` + `VisualizationGenerator`
- 运维层：`Settings`（配置）+ `LogManager`（日志）

