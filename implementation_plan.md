# SentiDemand Hub 可视化架构方案（修订版）

## 背景与核心问题

项目 **Agentic_SentiDemand_Hub** 是一个成熟的 Python NLP 分析工具包，但**完全没有可视化能力**。用户提出了几个关键的架构顾虑：

| 顾虑 | 解决方案 |
|------|---------|
| 可视化文件要保存本地，不能覆盖 | 以 `{数据源名}_{图表类型}_{时间戳}.html` 命名，永不覆盖 |
| 每个可视化要和原始数据绑定 | `manifest.json` 注册表，记录每次生成的完整元数据 |
| 输出目录不能放在项目 repo 里 | 默认输出到 `~/.sentidemand/outputs/`（用户家目录下） |
| 别人 clone 项目后能复刻 | 路径写在 [config/default.yaml](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/config/default.yaml) 里，用 `~` 通配 + 环境变量覆盖 |
| 要有拖拽上传文件的功能 | 轻量 Web 画廊内置拖拽区 |

---

## 设计理念：「先生成，再展示」

**不直接上来建 Vue 网站。** 分两步走：

### Phase 1：可视化生成器（本次实施）
> Python 后端新增一个 `visualization/` 模块，能把分析结果直接渲染为**独立 HTML 文件**（内嵌 ECharts），浏览器双击就能打开。同时启动一个**轻量本地画廊服务器**，可以查看所有历史图表。

### Phase 2：完整 Vue 前端（未来）
> 在 Phase 1 稳定后，再建完整的 Vue SPA。

---

## 文件系统设计

```
项目 repo（git tracked）:
  src/comment_analyzer/
    visualization/            ← [NEW] 可视化生成模块
      __init__.py
      generator.py            ← 核心：读 PipelineResults → 生成 HTML
      templates/              ← ECharts HTML 模板
        base.html             ← 通用模板骨架
      charts/                 ← 各图表类型的配置生成器
        sentiment.py          ← 情感方向（环形图/词云/分布图/散点图）
        features.py           ← 特征方向（双向柱图/棒棒糖/热力图）
        topics.py             ← 主题方向（玫瑰图/气泡矩阵/雷达图）
        demand.py             ← 需求方向（漏斗/共现网络/仪表盘）
      gallery.py              ← 本地画廊 Web 服务器
  config/
    default.yaml              ← 新增 visualization 配置节

用户本地（NOT git tracked）:
  ~/.sentidemand/             ← 用户数据根目录
    outputs/                  ← 可视化输出根目录
      manifest.json           ← 全局注册表
      jd_comments_20260316/   ← 以数据源命名的子文件夹
        sentiment_donut_194902.html
        sentiment_wordcloud_194902.html
        demand_funnel_195003.html
        ...
      taobao_snacks_20260317/
        ...
    uploads/                  ← 拖拽上传的原始文件暂存区
```

### 文件命名规则

```
{chart_type}_{HHmmss}.html
```

例如：`sentiment_donut_194902.html`

- **chart_type**：图表类型英文标识（[sentiment_donut](file:///C:/Users/30847/Desktop/antigravity/Claude%E8%AF%95%E9%AA%8C%E7%94%B0/%E4%B8%89%E5%88%9Bplatform-example/scripts/vis_01_sentiment.py#49-87), [demand_funnel](file:///C:/Users/30847/Desktop/antigravity/Claude%E8%AF%95%E9%AA%8C%E7%94%B0/%E4%B8%89%E5%88%9Bplatform-example/scripts/vis_04_demand.py#52-115) 等）
- **HHmmss**：时间戳精确到秒

文件夹按数据源 + 日期命名：`{数据源文件名去后缀}_{YYYYMMDD}/`

---

## manifest.json 注册表

每次生成可视化后，自动向 `manifest.json` 追加记录：

```json
{
  "version": "1.0",
  "entries": [
    {
      "id": "a1b2c3",
      "source_file": "jd_comments.csv",
      "source_hash": "sha256:abc123...",
      "chart_type": "sentiment_donut",
      "chart_title": "评论情感极性分布",
      "output_path": "jd_comments_20260316/sentiment_donut_194902.html",
      "created_at": "2026-03-16T19:49:02",
      "pipeline_config": { "platform": "jd", "sentiment_method": "snownlp" },
      "data_summary": { "total_comments": 5000, "positive_pct": 62.3 }
    }
  ]
}
```

**关键字段**：
- `source_hash`：原始文件的 SHA256，确保相同数据可溯源
- `output_path`：相对于 `outputs/` 根目录的相对路径
- `pipeline_config`：使用的分析配置快照

---

## 与现有代码的集成方式

> [!IMPORTANT]
> **零侵入现有代码**。只在 `src/comment_analyzer/` 下新增 `visualization/` 包。现有的 [OutputManager](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/core/output_manager.py#34-400)、[Settings](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/core/settings.py#281-342)、[PathConfig](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/core/settings.py#18-107) 全部复用，不修改。

### 复用现有设施

| 现有设施 | 复用方式 |
|---------|---------|
| [PathConfig](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/core/settings.py#18-107) | 新增 `visualization_base` 字段（默认 `~/.sentidemand/outputs`） |
| `OutputManager._get_next_sequence_number()` | 序号自增逻辑直接复用 |
| [Settings](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/core/settings.py#281-342) 环境变量前缀 `COMMENT_ANALYZER_` | 支持 `COMMENT_ANALYZER_PATHS__VISUALIZATION_BASE=xxx` 覆盖 |
| [PipelineResults](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/core/pipeline.py#36-343) | 新增 `.visualize()` 便捷方法，调用 Generator |

### 配置扩展（[config/default.yaml](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/config/default.yaml) 新增节）

```yaml
visualization:
  output_base: "~/.sentidemand/outputs"
  theme: "dark"              # dark / light
  locale: "zh-CN"            # 图表语言
  auto_open_browser: true    # 生成后自动打开浏览器
  charts:
    sentiment_donut: true
    sentiment_wordcloud: true
    sentiment_distribution: true
    sentiment_scatter: true
    features_bidirectional: true
    features_lollipop: true
    features_heatmap: true
    features_tfidf_scatter: true
    topics_nightingale: true
    topics_bubble: true
    topics_radar: true
    demand_funnel: true
    demand_network: true
    demand_dashboard: true
```

---

## Proposed Changes

### 可视化模块

#### [NEW] [generator.py](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/visualization/generator.py)

核心生成器类 `VisualizationGenerator`：

```python
class VisualizationGenerator:
    def __init__(self, settings, results: PipelineResults):
        ...

    def generate_all(self, source_name: str) -> List[str]:
        """一键生成全部图表，返回生成的文件路径列表"""

    def generate_chart(self, chart_type: str, source_name: str) -> str:
        """生成单张图表"""
```

- 读取 [PipelineResults](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/core/pipeline.py#36-343) 数据
- 将数据注入 ECharts HTML 模板
- 保存到用户本地输出目录
- 更新 `manifest.json`

---

#### [NEW] [templates/base.html](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/visualization/templates/base.html)

独立 HTML 模板（内嵌 ECharts CDN）：
- 深空暗色主题 + Glassmorphism 风格
- 零依赖、双击即开
- 响应式自适应

---

#### [NEW] [charts/sentiment.py](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/visualization/charts/sentiment.py)

4 个情感可视化函数，对标 [vis_01_sentiment.py](file:///C:/Users/30847/Desktop/antigravity/Claude%E8%AF%95%E9%AA%8C%E7%94%B0/%E4%B8%89%E5%88%9Bplatform-example/scripts/vis_01_sentiment.py)：
- `gen_sentiment_donut()` → 情感极性环形图
- `gen_sentiment_wordcloud()` → 正/负面词云对决
- `gen_sentiment_distribution()` → 情感得分分布直方图
- `gen_sentiment_scatter()` → 文本长度 vs 情感散点图

---

#### [NEW] [charts/features.py](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/visualization/charts/features.py)

4 个特征可视化函数，对标 [vis_02_features.py](file:///C:/Users/30847/Desktop/antigravity/Claude%E8%AF%95%E9%AA%8C%E7%94%B0/%E4%B8%89%E5%88%9Bplatform-example/scripts/vis_02_features.py)。

---

#### [NEW] [charts/topics.py](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/visualization/charts/topics.py)

3 个主题可视化函数，对标 [vis_03_topics.py](file:///C:/Users/30847/Desktop/antigravity/Claude%E8%AF%95%E9%AA%8C%E7%94%B0/%E4%B8%89%E5%88%9Bplatform-example/scripts/vis_03_topics.py)。

---

#### [NEW] [charts/demand.py](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/visualization/charts/demand.py)

3 个需求可视化函数，对标 [vis_04_demand.py](file:///C:/Users/30847/Desktop/antigravity/Claude%E8%AF%95%E9%AA%8C%E7%94%B0/%E4%B8%89%E5%88%9Bplatform-example/scripts/vis_04_demand.py)。

---

#### [NEW] [gallery.py](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/visualization/gallery.py)

本地画廊 Web 服务器（基于 FastAPI）：

- `GET /` → 画廊首页（中文版，暗色主题）
  - 读取 `manifest.json` 展示所有历史图表，按数据源分组
  - 点击卡片可全屏查看
- `GET /chart/{id}` → 渲染单张图表
- `POST /upload` → 拖拽上传 CSV → 运行 Pipeline → 生成可视化
- `GET /api/manifest` → JSON 格式返回注册表

---

### Settings 扩展

#### [MODIFY] [settings.py](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/core/settings.py)

新增 `VisualizationConfig` Pydantic 模型，加入 `Settings.visualization` 字段。

**改动极小**：只添加一个新的配置类和一个新字段，不触碰任何现有代码。

---

### PipelineResults 扩展

#### [MODIFY] [pipeline.py](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/core/pipeline.py)

给 [PipelineResults](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/src/comment_analyzer/core/pipeline.py#36-343) 添加一个便捷方法：

```python
def visualize(self, source_name: str = "analysis") -> List[str]:
    """一键生成全部可视化，返回输出文件路径"""
    from comment_analyzer.visualization.generator import VisualizationGenerator
    gen = VisualizationGenerator(self.settings, self)
    return gen.generate_all(source_name)
```

**改动极小**：只添加一个方法，不改动任何现有逻辑。

---

## 可复刻性方案

> [!IMPORTANT]
> 别人 clone 这个项目后如何复刻？

1. **[config/default.yaml](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/config/default.yaml) 中的路径使用 `~` 通配符**
   - `~/.sentidemand/outputs` → 自动解析到每个用户的家目录
   - Windows: `C:\Users\xxx\.sentidemand\outputs`
   - macOS: `/Users/xxx/.sentidemand/outputs`
   - Linux: `/home/xxx/.sentidemand/outputs`

2. **环境变量覆盖**
   - `COMMENT_ANALYZER_PATHS__VISUALIZATION_BASE=/custom/path`
   - 写在 `.env` 文件中，[.gitignore](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/.gitignore) 已忽略

3. **首次运行自动创建目录**
   - Gallery 服务器启动时自动检测并创建 `~/.sentidemand/` 目录

4. **[.gitignore](file:///C:/Users/30847/Desktop/antigravity/Agentic_SentiDemand_Hub/.gitignore) 已排除输出文件**
   - `outputs/` 和 `~/.sentidemand/` 不会被提交到 git

---

## 用户使用流程

```python
# Step 1: 正常使用 Pipeline（不变）
from comment_analyzer import CommentPipeline
pipeline = CommentPipeline()
df = pipeline.load_data("jd_comments.csv")
results = pipeline.run(df)

# Step 2: 一键生成全部可视化（新增！）
files = results.visualize(source_name="jd_comments")
# → 生成 14 个 HTML 文件到 ~/.sentidemand/outputs/jd_comments_20260316/
# → 自动打开浏览器展示画廊

# Step 3: 启动画廊服务器浏览历史（可选）
# 命令行: python -m comment_analyzer.visualization.gallery
# 浏览器访问: http://localhost:8765
```

---

## 美学设计：深空观测站暗色主题

| 属性 | 值 |
|------|-----|
| 背景色 | `#0a0e1a` (深空黑) |
| 卡片底色 | `rgba(20, 27, 45, 0.85)` + `backdrop-filter: blur(12px)` |
| 主色 | `#3b82f6` (星蓝) |
| 正面色 | `#10b981` (翠绿) |
| 负面色 | `#ef4444` (珊瑚红) |
| 中性色 | `#6b7280` |
| 字体 | Outfit (标题) + Noto Sans SC (中文正文) |
| 特效 | 卡片发光边框 + 图表入场动画 + 数据源分组折叠 |

---

## Verification Plan

### 自动化验证
```bash
# 1. 运行现有测试确保零破坏
cd C:\Users\30847\Desktop\antigravity\Agentic_SentiDemand_Hub
python -m pytest tests/ -v

# 2. 测试可视化生成（需要有示例数据）
python -c "from comment_analyzer.visualization.generator import VisualizationGenerator; print('✅ 模块导入成功')"

# 3. 启动画廊服务器
python -m comment_analyzer.visualization.gallery
# → 浏览器访问 http://localhost:8765 验证
```

### 浏览器验证
- 用内置浏览器工具打开生成的 HTML 文件验证图表渲染
- 打开画廊页面验证拖拽上传和历史展示
