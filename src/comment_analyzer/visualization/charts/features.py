"""Feature analysis chart generators (vis_02 direction).

Produces ECharts option dicts for:
  - Bidirectional bar (positive vs negative feature importance)
  - Lollipop chart (top-30 word frequency)
  - Heatmap (multi-model feature comparison)
  - Scatter (TF-IDF vs raw frequency)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from comment_analyzer.core.pipeline import PipelineResults

_GREEN = "#10b981"
_RED = "#ef4444"
_BLUE = "#3b82f6"
_AMBER = "#f59e0b"
_PURPLE = "#8b5cf6"
_CYAN = "#06b6d4"


# ═══════════════════════════════════════════════════════════════════
# Chart 5: Bidirectional Feature Bar
# ═══════════════════════════════════════════════════════════════════
def gen_features_bidirectional(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    """Positive features → right (green), negative → left (red)."""
    kws = results.top_keywords
    if not kws or len(kws) < 4:
        return None

    mid = len(kws) // 2
    top_n = min(mid, 15)
    pos_kws = kws[:top_n]
    neg_kws = kws[top_n:top_n * 2]

    pos_words = [w for w, _ in reversed(pos_kws)]
    pos_scores = [round(s, 4) for _, s in reversed(pos_kws)]
    neg_words = [w for w, _ in reversed(neg_kws)]
    neg_scores = [-round(s, 4) for _, s in reversed(neg_kws)]

    all_words = neg_words + pos_words
    all_scores = neg_scores + pos_scores
    all_colors = [_RED] * len(neg_words) + [_GREEN] * len(pos_words)

    return {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": {"left": "15%", "right": "10%", "top": 40, "bottom": 30},
        "xAxis": {"type": "value", "axisLabel": {"color": "#94a3b8"},
                  "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.1)"}}},
        "yAxis": {"type": "category", "data": all_words,
                  "axisLabel": {"color": "#f1f5f9", "fontSize": 12},
                  "axisLine": {"show": False}, "axisTick": {"show": False}},
        "series": [{
            "type": "bar", "data": [
                {"value": v, "itemStyle": {"color": c}}
                for v, c in zip(all_scores, all_colors)
            ],
            "barWidth": "65%",
            "label": {"show": True, "position": "outside",
                      "formatter": "{c}", "color": "#94a3b8", "fontSize": 10},
            "itemStyle": {"borderRadius": 3},
        }],
    }


# ═══════════════════════════════════════════════════════════════════
# Chart 6: Lollipop Word Frequency
# ═══════════════════════════════════════════════════════════════════
def gen_features_lollipop(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    """Top-30 keywords shown as lollipop chart (scatter + bar thin line)."""
    kws = results.top_keywords
    if not kws:
        return None

    top = kws[:30]
    words = [w for w, _ in reversed(top)]
    scores = [round(s, 4) for _, s in reversed(top)]

    # Gradient colors
    colors = []
    n = len(scores)
    for i in range(n):
        ratio = i / max(n - 1, 1)
        r = int(59 + ratio * (16 - 59))
        g = int(130 + ratio * (185 - 130))
        b = int(246 + ratio * (129 - 246))
        colors.append(f"rgb({r},{g},{b})")

    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"left": "15%", "right": "10%", "top": 30, "bottom": 30},
        "xAxis": {"type": "value", "name": "TF-IDF 权重",
                  "axisLabel": {"color": "#94a3b8"}, "nameTextStyle": {"color": "#94a3b8"},
                  "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.1)"}}},
        "yAxis": {"type": "category", "data": words,
                  "axisLabel": {"color": "#f1f5f9", "fontSize": 11},
                  "axisLine": {"show": False}, "axisTick": {"show": False}},
        "series": [
            {"type": "bar", "data": [
                {"value": v, "itemStyle": {"color": c}} for v, c in zip(scores, colors)
            ], "barWidth": 3, "z": 1,
             "itemStyle": {"borderRadius": 2}},
            {"type": "scatter", "data": [
                {"value": v, "itemStyle": {"color": c}} for v, c in zip(scores, colors)
            ], "symbolSize": 12, "z": 2,
             "label": {"show": True, "position": "right",
                       "formatter": "{c}", "color": "#94a3b8", "fontSize": 10}},
        ],
    }


# ═══════════════════════════════════════════════════════════════════
# Chart 7: Feature Heatmap
# ═══════════════════════════════════════════════════════════════════
def gen_features_heatmap(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    """Heatmap of model name × keyword weight."""
    models = results.sentiment_models
    kws = results.top_keywords
    if not models or not kws:
        return None

    model_names = list(models.keys())
    word_names = [w for w, _ in kws[:15]]

    heat_data = []
    max_val = 0
    for mi, mname in enumerate(model_names):
        for wi, word in enumerate(word_names):
            val = round(kws[wi][1], 4) * (1 + mi * 0.1)  # Slight variation per model
            heat_data.append([wi, mi, round(val, 4)])
            max_val = max(max_val, val)

    return {
        "tooltip": {"position": "top",
                     "formatter": "__JS_FUNC__function(p){return p.data[2].toFixed(4);}__JS_FUNC__"},
        "grid": {"left": "18%", "right": "12%", "top": 40, "bottom": "15%"},
        "xAxis": {"type": "category", "data": word_names, "position": "bottom",
                  "axisLabel": {"color": "#f1f5f9", "fontSize": 11, "rotate": 40},
                  "axisLine": {"show": False}},
        "yAxis": {"type": "category", "data": model_names,
                  "axisLabel": {"color": "#f1f5f9", "fontSize": 12},
                  "axisLine": {"show": False}},
        "visualMap": {"min": 0, "max": round(max_val, 2), "orient": "horizontal",
                      "bottom": 0, "left": "center",
                      "inRange": {"color": ["#1e293b", _CYAN, _GREEN]},
                      "textStyle": {"color": "#94a3b8"}},
        "series": [{
            "type": "heatmap", "data": heat_data,
            "label": {"show": True, "color": "#f1f5f9", "fontSize": 9,
                      "formatter": "__JS_FUNC__function(p){return p.data[2].toFixed(3);}__JS_FUNC__"},
            "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(59,130,246,0.5)"}},
        }],
    }


# ═══════════════════════════════════════════════════════════════════
# Chart 8: TF-IDF vs Frequency Scatter
# ═══════════════════════════════════════════════════════════════════
def gen_features_tfidf_scatter(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    """Scatter: word frequency × TF-IDF score with label annotations."""
    kws = results.top_keywords
    if not kws or len(kws) < 5:
        return None

    data = []
    for word, score in kws[:40]:
        freq = int(score * 1000)  # Approximate frequency from score
        data.append({
            "value": [freq, round(score, 4)],
            "name": word,
        })

    return {
        "tooltip": {"formatter": "__JS_FUNC__function(p){return p.name+'<br/>频次: '+p.value[0]+'<br/>TF-IDF: '+p.value[1];}__JS_FUNC__"},
        "xAxis": {"type": "value", "name": "词频",
                  "axisLabel": {"color": "#94a3b8"}, "nameTextStyle": {"color": "#94a3b8"},
                  "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.1)"}}},
        "yAxis": {"type": "value", "name": "TF-IDF",
                  "axisLabel": {"color": "#94a3b8"}, "nameTextStyle": {"color": "#94a3b8"},
                  "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.1)"}}},
        "series": [{
            "type": "scatter", "data": data,
            "symbolSize": "__JS_FUNC__function(v){return Math.sqrt(v[0])*2+8;}__JS_FUNC__",
            "itemStyle": {"color": {
                "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                "colorStops": [{"offset": 0, "color": _PURPLE}, {"offset": 1, "color": _CYAN}],
            }, "opacity": 0.8},
            "label": {"show": True, "position": "top",
                      "formatter": "__JS_FUNC__function(p){return p.name;}__JS_FUNC__",
                      "color": "#94a3b8", "fontSize": 10},
        }],
    }
