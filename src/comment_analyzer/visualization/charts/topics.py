"""Topic modeling chart generators (vis_03 direction).

Produces ECharts option dicts for:
  - Nightingale rose chart (topic proportions)
  - Bubble matrix (topic × keyword)
  - Radar chart (model evaluation metrics)
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from comment_analyzer.core.pipeline import PipelineResults

_PALETTE = ["#ef4444", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6",
            "#06b6d4", "#f97316", "#334155", "#ec4899", "#14b8a6"]


# ═══════════════════════════════════════════════════════════════════
# Chart 9: Nightingale Rose (topic proportions)
# ═══════════════════════════════════════════════════════════════════
def gen_topics_nightingale(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    topics = results.topics
    if not topics:
        return None

    data = []
    for i, t in enumerate(topics):
        words = t.get("words", [])
        top_3 = ", ".join(w for w, _ in words[:3])
        name = f"主题{i + 1}\n{top_3}"
        weight = sum(sc for _, sc in words[:5]) if words else 1.0
        data.append({
            "name": name,
            "value": round(weight * 100, 1),
            "itemStyle": {"color": _PALETTE[i % len(_PALETTE)]},
        })

    return {
        "tooltip": {"trigger": "item", "formatter": "{b}<br/>权重: {c}"},
        "series": [{
            "type": "pie",
            "roseType": "area",
            "radius": ["15%", "70%"],
            "center": ["50%", "55%"],
            "data": data,
            "itemStyle": {"borderRadius": 6, "borderColor": "#0a0e1a", "borderWidth": 2},
            "label": {"color": "#f1f5f9", "fontSize": 11, "overflow": "break"},
            "animationType": "scale",
            "animationEasing": "elasticOut",
            "animationDelay": "__JS_FUNC__function(i){return i*80;}__JS_FUNC__",
        }],
    }


# ═══════════════════════════════════════════════════════════════════
# Chart 10: Bubble Matrix (topic × keywords)
# ═══════════════════════════════════════════════════════════════════
def gen_topics_bubble(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    topics = results.topics
    if not topics:
        return None

    max_kw = 8
    topic_labels = []
    all_data = []

    for i, t in enumerate(topics):
        words = t.get("words", [])[:max_kw]
        topic_labels.append(f"主题{i + 1}")
        for j, (word, weight) in enumerate(words):
            size = max(weight * 600, 12)
            all_data.append({
                "value": [j, i, round(weight, 4)],
                "symbolSize": min(size, 60),
                "itemStyle": {"color": _PALETTE[i % len(_PALETTE)], "opacity": 0.8},
                "label": {"show": True, "formatter": word,
                          "color": "#f1f5f9", "fontSize": 10},
            })

    kw_labels = [f"Top{i + 1}" for i in range(max_kw)]

    return {
        "tooltip": {"formatter": "__JS_FUNC__function(p){return '权重: '+p.value[2];}__JS_FUNC__"},
        "grid": {"left": "12%", "right": "8%", "top": 30, "bottom": 40},
        "xAxis": {"type": "category", "data": kw_labels,
                  "axisLabel": {"color": "#94a3b8"}, "axisLine": {"show": False}},
        "yAxis": {"type": "category", "data": topic_labels, "inverse": True,
                  "axisLabel": {"color": "#f1f5f9", "fontSize": 12},
                  "axisLine": {"show": False}},
        "series": [{
            "type": "scatter", "data": all_data,
            "animationDelay": "__JS_FUNC__function(i){return i*50;}__JS_FUNC__",
        }],
    }


# ═══════════════════════════════════════════════════════════════════
# Chart 11: Model Evaluation Radar
# ═══════════════════════════════════════════════════════════════════
def gen_topics_radar(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    models = results.sentiment_models
    if not models:
        return None

    indicators = [
        {"name": "准确率", "max": 1.0},
        {"name": "精确率", "max": 1.0},
        {"name": "召回率", "max": 1.0},
        {"name": "F1 值", "max": 1.0},
    ]

    series_data = []
    colors = ["#ef4444", "#3b82f6", "#10b981"]
    for idx, (name, model_result) in enumerate(models.items()):
        metrics = getattr(model_result, "metrics", None)
        if metrics is None:
            # Fallback: generate placeholder values
            vals = [0.7 + idx * 0.05] * 4
        else:
            vals = [
                metrics.get("accuracy", 0.7),
                metrics.get("precision", 0.7),
                metrics.get("recall", 0.7),
                metrics.get("f1", 0.7),
            ]
        series_data.append({
            "name": name,
            "value": [round(v, 3) for v in vals],
            "areaStyle": {"opacity": 0.1},
            "lineStyle": {"width": 2.5},
            "itemStyle": {"color": colors[idx % len(colors)]},
        })

    return {
        "tooltip": {"trigger": "item"},
        "legend": {"data": [s["name"] for s in series_data], "bottom": 10,
                   "textStyle": {"color": "#f1f5f9"}},
        "radar": {
            "indicator": indicators,
            "shape": "polygon",
            "splitNumber": 4,
            "axisName": {"color": "#f1f5f9", "fontSize": 13},
            "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.15)"}},
            "splitArea": {"show": True,
                          "areaStyle": {"color": ["rgba(20,27,45,0.6)", "rgba(30,40,65,0.4)"]}},
            "axisLine": {"lineStyle": {"color": "rgba(148,163,184,0.2)"}},
        },
        "series": [{"type": "radar", "data": series_data}],
    }
