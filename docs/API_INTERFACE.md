# Comment Analyzer API 接口文档

> 版本: v0.2.0
> 更新日期: 2026-03-16
> 用途: 前端开发对接参考

---

## 目录

1. [项目现状说明](#1-项目现状说明)
2. [后端架构](#2-后端架构)
3. [API 接口列表](#3-api-接口列表)
4. [数据模型](#4-数据模型)
5. [可视化方案建议](#5-可视化方案建议)

---

## 1. 项目现状说明

### 1.1 当前已实现功能
- ✅ 数据预处理（文本清洗、分词、停用词过滤）
- ✅ 情感分析（SnowNLP + 多模型分类）
- ✅ 主题建模（TF-IDF + LDA）
- ✅ 需求分析（强度计算 + 相关性分析）
- ✅ Pydantic 配置系统
- ✅ 结构化日志（Loguru）
- ✅ 自动递增序号的文件输出

### 1.2 缺失功能（需前端/后端补充）
- ❌ **数据可视化** - 原方案中的图表功能尚未实现
- ❌ RESTful API 接口封装
- ❌ Web 服务框架（FastAPI/Flask）
- ❌ 数据库持久化

### 1.3 可视化需求对照（原方案 vs 现状）

| 原方案可视化 | 当前状态 | 优先级 |
|-------------|---------|--------|
| 情感分布饼图/柱状图 | ❌ 未实现 | P0 |
| 词频词云图 | ❌ 未实现 | P0 |
| 主题分布热力图 | ❌ 未实现 | P1 |
| 需求强度雷达图 | ❌ 未实现 | P1 |
| 相关性矩阵图 | ❌ 未实现 | P1 |
| 时间趋势折线图 | ❌ 未实现 | P2 |
| 情感-需求交叉分析图 | ❌ 未实现 | P2 |

---

## 2. 后端架构

### 2.1 推荐技术栈（补充可视化）

```python
# 新增依赖（建议添加到 pyproject.toml）
[project.optional-dependencies]
web = [
    "fastapi>=0.100.0",      # Web API 框架
    "uvicorn>=0.23.0",       # ASGI 服务器
    "python-multipart>=0.0.6", # 文件上传
]
viz = [
    "plotly>=5.15.0",        # 交互式图表
    "pyecharts>=2.0.0",      # 中文图表（词云）
    "pandas>=2.0.0",         # 数据处理
]
```

### 2.2 建议目录结构扩展

```
src/comment_analyzer/
├── api/                    # 新增: Web API 层
│   ├── __init__.py
│   ├── main.py            # FastAPI 入口
│   ├── routes/            # API 路由
│   │   ├── __init__.py
│   │   ├── analysis.py    # 分析接口
│   │   ├── visualization.py # 可视化接口
│   │   └── export.py      # 导出接口
│   └── schemas/           # Pydantic 请求/响应模型
│       ├── __init__.py
│       ├── request.py
│       └── response.py
├── visualization/          # 新增: 可视化模块
│   ├── __init__.py
│   ├── charts.py          # 图表生成
│   ├── wordcloud.py       # 词云
│   └── exporters.py       # 图表导出
├── core/                   # 现有核心模块
├── preprocessing/
├── sentiment/
├── topic/
└── demand/
```

---

## 3. API 接口列表

### 3.1 基础接口

#### 3.1.1 健康检查
```http
GET /api/v1/health
```

**响应:**
```json
{
  "status": "ok",
  "version": "0.2.0",
  "timestamp": "2026-03-16T10:00:00Z"
}
```

---

### 3.2 数据上传接口

#### 3.2.1 上传评论数据
```http
POST /api/v1/data/upload
Content-Type: multipart/form-data
```

**请求参数:**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | ✅ | CSV/Excel/JSON 文件 |
| platform | String | ❌ | 平台类型: generic/jd/taobao/bilibili |
| text_column | String | ❌ | 文本列名（自动检测） |

**响应:**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "task_20240316100000_abc123",
    "filename": "comments.csv",
    "row_count": 1000,
    "columns": ["id", "content", "rating", "date"],
    "detected_text_column": "content",
    "preview": [
      {"id": 1, "content": "商品很好", "rating": 5},
      {"id": 2, "content": "物流慢", "rating": 3}
    ]
  }
}
```

---

### 3.3 分析接口

#### 3.3.1 执行完整分析
```http
POST /api/v1/analysis/run
Content-Type: application/json
```

**请求体:**
```json
{
  "task_id": "task_20240316100000_abc123",
  "config": {
    "sentiment": {
      "labeling_method": "snownlp",
      "models": ["naive_bayes", "svm", "logistic_regression"]
    },
    "topic": {
      "num_topics": 5,
      "top_k": 20
    },
    "demand": {
      "calculate_intensity": true,
      "calculate_correlation": true
    }
  }
}
```

**响应:**
```json
{
  "code": 200,
  "message": "analysis completed",
  "data": {
    "task_id": "task_20240316100000_abc123",
    "results": {
      "sentiment": {
        "distribution": {
          "positive": 600,
          "negative": 300,
          "neutral": 100
        },
        "model_results": {
          "svm": {"accuracy": 0.95, "f1": 0.94},
          "naive_bayes": {"accuracy": 0.92, "f1": 0.91}
        }
      },
      "topic": {
        "keywords": [
          {"word": "质量", "score": 0.85},
          {"word": "物流", "score": 0.72}
        ],
        "topics": [
          {
            "topic_id": 0,
            "words": ["质量", "产品", "不错"],
            "weights": [0.15, 0.12, 0.10]
          }
        ]
      },
      "demand": {
        "intensity": {
          "quality": 0.85,
          "logistics": 0.72,
          "price": 0.65,
          "service": 0.58
        },
        "correlation": [[1.0, 0.3, 0.2], [0.3, 1.0, 0.4], [0.2, 0.4, 1.0]]
      }
    },
    "output_files": {
      "demand": ["001_demand_intensity.csv", "002_demand_correlation.csv"],
      "sentiment": ["001_sentiment_distribution.csv"],
      "word_frequency": ["001_top_keywords.csv"]
    }
  }
}
```

---

### 3.4 可视化接口（重点）

#### 3.4.1 获取情感分布图
```http
GET /api/v1/visualization/sentiment/distribution?task_id={task_id}&chart_type=pie
```

**请求参数:**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | String | ✅ | 任务ID |
| chart_type | String | ❌ | pie/bar/doughnut, 默认 pie |
| format | String | ❌ | json/html/png, 默认 json |

**响应 (format=json):**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "chart_type": "pie",
    "title": "情感分布",
    "data": [
      {"name": "正面", "value": 600, "color": "#52c41a"},
      {"name": "负面", "value": 300, "color": "#f5222d"},
      {"name": "中性", "value": 100, "color": "#faad14"}
    ],
    "total": 1000,
    "percentages": {
      "positive": 60.0,
      "negative": 30.0,
      "neutral": 10.0
    },
    // ECharts 配置对象（前端可直接使用）
    "echarts_option": {
      "series": [{
        "type": "pie",
        "data": [
          {"name": "正面", "value": 600},
          {"name": "负面", "value": 300},
          {"name": "中性", "value": 100}
        ]
      }]
    }
  }
}
```

**响应 (format=html):**
返回完整 HTML 页面，可直接嵌入 iframe

---

#### 3.4.2 获取词云图
```http
GET /api/v1/visualization/wordcloud?task_id={task_id}&top_n=100
```

**请求参数:**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | String | ✅ | 任务ID |
| top_n | Integer | ❌ | 显示前N个词, 默认 50 |
| format | String | ❌ | json/html/png, 默认 json |

**响应:**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "title": "词频云图",
    "word_count": 100,
    "words": [
      {"name": "质量", "value": 850, "color": "#5470c6"},
      {"name": "物流", "value": 720, "color": "#91cc75"},
      {"name": "服务", "value": 650, "color": "#fac858"}
    ],
    // ECharts wordcloud 配置
    "echarts_option": {
      "series": [{
        "type": "wordCloud",
        "data": [
          {"name": "质量", "value": 850},
          {"name": "物流", "value": 720}
        ]
      }]
    },
    // 图片 Base64 (format=png 时)
    "image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
  }
}
```

---

#### 3.4.3 获取主题分布热力图
```http
GET /api/v1/visualization/topics/heatmap?task_id={task_id}
```

**响应:**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "title": "主题-词语热力图",
    "topics": ["主题1", "主题2", "主题3", "主题4", "主题5"],
    "words": ["质量", "物流", "价格", "服务", "包装"],
    "matrix": [
      [0.85, 0.12, 0.05, 0.08, 0.03],
      [0.10, 0.88, 0.15, 0.22, 0.11],
      [0.20, 0.18, 0.82, 0.14, 0.09]
    ],
    "echarts_option": {
      "xAxis": {"data": ["质量", "物流", "价格", "服务", "包装"]},
      "yAxis": {"data": ["主题1", "主题2", "主题3"]},
      "series": [{
        "type": "heatmap",
        "data": [[0, 0, 0.85], [0, 1, 0.12], ...]
      }]
    }
  }
}
```

---

#### 3.4.4 获取需求强度雷达图
```http
GET /api/v1/visualization/demand/radar?task_id={task_id}
```

**响应:**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "title": "需求强度雷达图",
    "indicators": [
      {"name": "质量", "max": 1.0},
      {"name": "物流", "max": 1.0},
      {"name": "价格", "max": 1.0},
      {"name": "服务", "max": 1.0},
      {"name": "包装", "max": 1.0}
    ],
    "data": [
      {
        "name": "需求强度",
        "value": [0.85, 0.72, 0.65, 0.58, 0.45]
      }
    ],
    "echarts_option": {
      "radar": {
        "indicator": [
          {"name": "质量", "max": 1},
          {"name": "物流", "max": 1}
        ]
      },
      "series": [{
        "type": "radar",
        "data": [{"value": [0.85, 0.72], "name": "需求强度"}]
      }]
    }
  }
}
```

---

#### 3.4.5 获取相关性矩阵图
```http
GET /api/v1/visualization/demand/correlation?task_id={task_id}
```

**响应:**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "title": "需求相关性矩阵",
    "categories": ["质量", "物流", "价格", "服务", "包装"],
    "matrix": [
      [1.00, 0.35, 0.28, 0.42, 0.15],
      [0.35, 1.00, 0.18, 0.25, 0.22],
      [0.28, 0.18, 1.00, 0.38, 0.12]
    ],
    "echarts_option": {...}
  }
}
```

---

#### 3.4.6 获取综合分析仪表板
```http
GET /api/v1/visualization/dashboard?task_id={task_id}
```

**响应:**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "task_20240316100000_abc123",
    "summary": {
      "total_comments": 1000,
      "sentiment_positive_rate": 0.60,
      "top_demand": "质量",
      "topic_count": 5
    },
    "charts": {
      "sentiment_pie": "/api/v1/visualization/sentiment/distribution?task_id=xxx&format=html",
      "wordcloud": "/api/v1/visualization/wordcloud?task_id=xxx&format=html",
      "demand_radar": "/api/v1/visualization/demand/radar?task_id=xxx&format=html",
      "topic_heatmap": "/api/v1/visualization/topics/heatmap?task_id=xxx&format=html"
    },
    // 所有图表的 ECharts 配置
    "echarts_configs": {
      "sentiment_pie": {...},
      "wordcloud": {...},
      "demand_radar": {...}
    }
  }
}
```

---

### 3.5 导出接口

#### 3.5.1 导出分析结果
```http
POST /api/v1/export/results
Content-Type: application/json
```

**请求体:**
```json
{
  "task_id": "task_20240316100000_abc123",
  "formats": ["csv", "excel", "json"],
  "categories": ["sentiment", "topic", "demand"],
  "include_visualizations": true,
  "chart_formats": ["png", "html"]
}
```

**响应:**
```json
{
  "code": 200,
  "message": "export completed",
  "data": {
    "export_id": "exp_20240316100500_xyz789",
    "download_url": "/api/v1/export/download/exp_20240316100500_xyz789",
    "files": {
      "data": [
        "001_sentiment_distribution.csv",
        "002_demand_intensity.csv"
      ],
      "charts": [
        "sentiment_pie.png",
        "wordcloud.html"
      ],
      "report": "analysis_report.pdf"
    },
    "expires_at": "2026-03-17T10:05:00Z"
  }
}
```

---

## 4. 数据模型

### 4.1 核心模型定义

```python
# 请求模型
class AnalysisRequest(BaseModel):
    task_id: str
    config: AnalysisConfig

class AnalysisConfig(BaseModel):
    sentiment: SentimentConfig
    topic: TopicConfig
    demand: DemandConfig

class VisualizationRequest(BaseModel):
    task_id: str
    chart_type: str  # pie, bar, line, radar, heatmap, wordcloud
    format: str = "json"  # json, html, png
    width: int = 800
    height: int = 600

# 响应模型
class APIResponse(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class VisualizationData(BaseModel):
    title: str
    chart_type: str
    data: List[Dict[str, Any]]
    echarts_option: Dict[str, Any]  # 前端直接使用
    metadata: Dict[str, Any]
```

---

## 5. 可视化方案建议

### 5.1 前端推荐方案

| 图表类型 | 推荐库 | 适用场景 |
|---------|-------|---------|
| 情感分布 | ECharts Pie/Bar | 占比展示 |
| 词云 | ECharts WordCloud | 关键词展示 |
| 主题热力图 | ECharts Heatmap | 主题-词关系 |
| 需求雷达图 | ECharts Radar | 多维度对比 |
| 相关性矩阵 | ECharts Heatmap + Scatter | 相关性展示 |
| 时间趋势 | ECharts Line | 时序分析 |

### 5.2 后端可视化生成方案

```python
# 方案1: 纯前端渲染（推荐）
# 后端返回 ECharts 配置，前端渲染

# 方案2: 后端生成图片
# 使用 pyecharts 生成图片/HTML

# 示例代码 (visualization/charts.py)
from pyecharts.charts import Pie, WordCloud, Radar, Heatmap
from pyecharts import options as opts

class ChartGenerator:
    def create_sentiment_pie(self, data: Dict) -> Dict:
        """生成情感分布饼图配置"""
        chart = (
            Pie()
            .add("", [list(z) for z in zip(data.keys(), data.values())])
            .set_global_opts(title_opts=opts.TitleOpts(title="情感分布"))
            .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
        )
        return chart.dump_options()  # 返回 ECharts 配置

    def create_wordcloud(self, words: List[Tuple[str, int]]) -> Dict:
        """生成词云配置"""
        chart = (
            WordCloud()
            .add("", words, word_size_range=[20, 100])
            .set_global_opts(title_opts=opts.TitleOpts(title="词频云图"))
        )
        return chart.dump_options()
```

### 5.3 接口实现优先级

**Phase 1 (MVP):**
- ✅ `/api/v1/analysis/run` - 执行分析
- ✅ `/api/v1/visualization/sentiment/distribution` - 情感分布图
- ✅ `/api/v1/visualization/wordcloud` - 词云图

**Phase 2:**
- ✅ `/api/v1/visualization/demand/radar` - 需求雷达图
- ✅ `/api/v1/visualization/topics/heatmap` - 主题热力图

**Phase 3:**
- ✅ `/api/v1/visualization/dashboard` - 综合仪表板
- ✅ `/api/v1/export/results` - 结果导出

---

## 6. 错误码说明

| 错误码 | 说明 |
|-------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 任务不存在 |
| 422 | 数据验证失败 |
| 500 | 服务器内部错误 |
| 503 | 分析服务繁忙 |

---

## 附录: 快速开始

### 启动后端服务

```bash
# 1. 安装依赖
pip install -e ".[web,viz]"

# 2. 启动服务
uvicorn comment_analyzer.api.main:app --reload --host 0.0.0.0 --port 8000

# 3. 访问文档
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### 前端调用示例

```javascript
// 上传数据
const formData = new FormData();
formData.append('file', file);
const uploadRes = await fetch('/api/v1/data/upload', {
  method: 'POST',
  body: formData
});
const { data: { task_id } } = await uploadRes.json();

// 执行分析
await fetch('/api/v1/analysis/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ task_id })
});

// 获取可视化
const vizRes = await fetch(`/api/v1/visualization/sentiment/distribution?task_id=${task_id}`);
const { data: { echarts_option } } = await vizRes.json();

// 使用 ECharts 渲染
const chart = echarts.init(document.getElementById('chart'));
chart.setOption(echarts_option);
```

---

> 文档维护: Comment Analyzer Team
> 最后更新: 2026-03-16
