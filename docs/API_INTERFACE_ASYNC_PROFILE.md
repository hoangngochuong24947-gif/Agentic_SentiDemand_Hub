# Async Profile Analysis API Contract

> Version: v0.3.0-draft  
> Updated: 2026-04-01  
> Purpose: Backend/frontend contract for async comment analysis, progress feedback, and profile-enhanced insight output.

## Scope

This contract prepares the next frontend/backend integration round without requiring a frontend upgrade right now.

New capabilities covered here:

- Async orchestration after preprocessing
- Auto strategy selection: `generic` or `profile_enhanced`
- Progress copy for long-running tasks
- Demographic/profile insight payloads when input data contains fields such as gender, age, or region

## Recommended Flow

1. Frontend uploads or submits review data.
2. Backend creates an analysis task and immediately returns `task_id`.
3. Frontend polls task status and displays `encouragement`, `analysis_tip`, and `delivery_copy`.
4. Backend returns the final analysis payload with both generic insight results and optional profile-enhanced summaries.

## Endpoint 1: Create Analysis Task

`POST /api/v1/analysis/tasks`

### Request

```json
{
  "source_name": "demo_comments_batch",
  "records": [
    {
      "comment": "物流非常快，包装很完整，体验很好",
      "gender": "女",
      "age": 22,
      "region": "华东"
    }
  ],
  "text_column": "comment",
  "analysis_mode": "auto",
  "profile_fields": {
    "gender": "gender",
    "age": "age",
    "region": "region"
  }
}
```

### Field Notes

- `analysis_mode`: `auto | generic | profile_enhanced`
- `profile_fields` is optional.
- If `analysis_mode=auto`, backend should inspect the payload and choose:
  - `generic`: no usable profile columns detected
  - `profile_enhanced`: at least one usable profile column detected

### Response

```json
{
  "code": 202,
  "message": "task accepted",
  "data": {
    "task_id": "task_20260401_001",
    "status": "queued",
    "analysis_mode": "auto"
  }
}
```

## Endpoint 2: Poll Task Status

`GET /api/v1/analysis/tasks/{task_id}`

### Response While Running

```json
{
  "code": 200,
  "message": "running",
  "data": {
    "task_id": "task_20260401_001",
    "status": "running",
    "current_stage": "topic",
    "progress_messages": [
      {
        "stage": "preprocessing",
        "label": "数据预处理",
        "encouragement": "先把评论洗干净，后面的判断才会更稳，我们在帮结果打基础。",
        "analysis_tip": "小技巧：先看清洗后的高频词，再判断情绪和需求，误判会少很多。",
        "delivery_copy": "当前正在整理评论文本、分词和去噪，马上进入分析阶段。"
      },
      {
        "stage": "topic",
        "label": "主题建模",
        "encouragement": "评论里的共性主题正在浮现，杂乱反馈很快会变成可读结构。",
        "analysis_tip": "小技巧：把主题词和原评论一起看，能更快分辨“真需求”和“偶发抱怨”。",
        "delivery_copy": "当前正在聚合高频主题，稍后会输出用户反复提到的关注点。"
      }
    ]
  }
}
```

## Endpoint 3: Get Final Result

`GET /api/v1/analysis/tasks/{task_id}/result`

### Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "task_20260401_001",
    "analysis_strategy": "profile_enhanced",
    "sentiment_distribution": {
      "positive": 18,
      "negative": 4,
      "neutral": 2
    },
    "top_keywords": [
      ["物流", 0.84],
      ["包装", 0.71],
      ["价格", 0.68]
    ],
    "topics": [
      {
        "id": 0,
        "weight": 0.32,
        "words": [["物流", 0.21], ["包装", 0.18], ["体验", 0.13]]
      }
    ],
    "demand": {
      "intensity": [
        {
          "quality": 0.81,
          "logistics": 0.74,
          "price": 0.63
        }
      ],
      "correlation": [
        {
          "left": "quality",
          "right": "logistics",
          "score": 0.42
        }
      ]
    },
    "profile_analysis": {
      "strategy": "profile_enhanced",
      "detected_dimensions": ["gender", "age", "region"],
      "coverage": {
        "gender": 1.0,
        "age": 1.0,
        "region": 1.0
      },
      "dimension_summaries": [
        {
          "dimension": "gender",
          "field": "gender",
          "value_count": 2,
          "top_values": [
            {
              "dimension": "gender",
              "value": "女",
              "sample_size": 12,
              "dominant_sentiment": "positive",
              "top_keywords": ["物流", "包装", "体验"]
            }
          ]
        }
      ],
      "segment_insights": [
        {
          "segment": "gender=女, age=18-24岁, region=华东",
          "sample_size": 4,
          "dominant_sentiment": "positive",
          "top_keywords": ["物流", "包装", "体验"],
          "focus_hint": "该分群更常提到 物流、包装、体验，适合在交付中单独说明。"
        }
      ]
    },
    "progress_messages": [
      {
        "stage": "sentiment",
        "label": "情绪分析",
        "encouragement": "情绪分布正在成形，越靠近真实用户感受，后面的结论就越有价值。",
        "analysis_tip": "小技巧：别只盯正负面比例，负面评论的集中主题更值得优先处理。",
        "delivery_copy": "当前正在提取情绪信号，稍后会给出情绪结构和重点风险点。"
      }
    ]
  }
}
```

## Frontend Rendering Suggestions

- If `analysis_strategy=generic`, hide profile tabs and show only generic charts/cards.
- If `analysis_strategy=profile_enhanced`, add:
  - `DimensionSummaryCard`
  - `SegmentInsightTable`
  - `ProfileFocusHintList`
- Polling UI can render one message block:
  - `encouragement` as warm feedback
  - `analysis_tip` as expert hint
  - `delivery_copy` as operational status text

## Backward Compatibility

- Existing generic analysis pages only need to read the original result fields.
- New fields are additive:
  - `analysis_strategy`
  - `profile_analysis`
  - `progress_messages`

## Implementation Notes

- The current Python pipeline already supports:
  - sync `run(...)`
  - async `run_async(...)`
  - automatic progress message generation
  - profile-enhanced summaries when demographic columns are present
- This document is contract-ready even if the REST layer is added in a later phase.
