# Agentic SentiDemand Hub / 智能评论需求洞察中枢

> A reusable NLP toolkit for e-commerce comment analysis, topic discovery, demand insights, and standalone visualization generation.  
> 一个可复用的电商评论 NLP 分析工具包，支持情感分析、主题发现、需求洞察与独立可视化生成。

---

## English

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

