"""Sentiment analysis chart generators (vis_01 direction).

Produces ECharts option dicts for:
  - Donut chart (sentiment polarity)
  - Word cloud (positive vs negative)
  - Histogram (score distribution)
  - Scatter (text length vs sentiment score)
"""

from __future__ import annotations
from typing import Any, Dict, Optional, TYPE_CHECKING
from collections import Counter

if TYPE_CHECKING:
    from comment_analyzer.core.pipeline import PipelineResults

# ── Color palette ────────────────────────────────────────────────
_GREEN = "#10b981"
_RED = "#ef4444"
_GRAY = "#6b7280"
_BLUE = "#3b82f6"
_AMBER = "#f59e0b"

_LABEL_COLORS = {"正面": _GREEN, "负面": _RED, "中性": _GRAY,
                 "positive": _GREEN, "negative": _RED, "neutral": _GRAY}


def _safe_sentiment_col(results: "PipelineResults") -> Optional[str]:
    """Find the sentiment column in processed data."""
    df = results.processed_data
    if df is None:
        return None
    for col in ("sentiment", "sentiment_label"):
        if col in df.columns:
            return col
    return None


# ═══════════════════════════════════════════════════════════════════
# Chart 1: Sentiment Donut
# ═══════════════════════════════════════════════════════════════════
def gen_sentiment_donut(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    dist = results.sentiment_distribution
    if not dist:
        return None

    total = sum(dist.values())
    data = []
    for label, count in dist.items():
        data.append({
            "name": label,
            "value": count,
            "itemStyle": {"color": _LABEL_COLORS.get(label, _BLUE)},
        })

    return {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} 条 ({d}%)"},
        "graphic": [
            {"type": "text", "left": "center", "top": "42%",
             "style": {"text": str(total), "fontSize": 42, "fontWeight": "bold",
                        "fill": "#f1f5f9", "textAlign": "center"}},
            {"type": "text", "left": "center", "top": "54%",
             "style": {"text": "条评论", "fontSize": 14, "fill": "#94a3b8",
                        "textAlign": "center"}},
        ],
        "series": [{
            "type": "pie",
            "radius": ["50%", "72%"],
            "center": ["50%", "50%"],
            "avoidLabelOverlap": True,
            "itemStyle": {"borderRadius": 6, "borderColor": "#0a0e1a", "borderWidth": 3},
            "label": {"show": True, "formatter": "{b}\n{d}%", "color": "#f1f5f9",
                      "fontSize": 13},
            "emphasis": {"label": {"show": True, "fontSize": 16, "fontWeight": "bold"}},
            "data": data,
            "animationType": "scale",
            "animationEasing": "elasticOut",
        }],
    }


# ═══════════════════════════════════════════════════════════════════
# Chart 2: Word Cloud (positive vs negative as dual bar)
# ═══════════════════════════════════════════════════════════════════
def gen_sentiment_wordcloud(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    """Dual horizontal bar showing top-15 words for positive & negative."""
    col = _safe_sentiment_col(results)
    df = results.processed_data
    if col is None or df is None or "filtered_text" not in df.columns:
        return None

    def _top_words(label: str, n: int = 15):
        subset = df[df[col] == label]["filtered_text"].dropna()
        words = []
        for tokens in subset:
            if isinstance(tokens, list):
                words.extend(tokens)
            elif isinstance(tokens, str):
                words.extend(tokens.split())
        return Counter(words).most_common(n)

    pos = _top_words("正面") or _top_words("positive")
    neg = _top_words("负面") or _top_words("negative")
    if not pos and not neg:
        return None

    pos_words = [w for w, _ in reversed(pos)]
    pos_counts = [c for _, c in reversed(pos)]
    neg_words = [w for w, _ in reversed(neg)]
    neg_counts = [-c for _, c in reversed(neg)]

    return {
        "tooltip": {"trigger": "axis",
                     "formatter": "{b}: {c}"},
        "grid": [
            {"left": "5%", "right": "52%", "top": 60, "bottom": 30},
            {"left": "52%", "right": "5%", "top": 60, "bottom": 30},
        ],
        "title": [
            {"text": "👎 负面高频词", "left": "22%", "top": 10,
             "textStyle": {"color": _RED, "fontSize": 15}},
            {"text": "👍 正面高频词", "left": "72%", "top": 10,
             "textStyle": {"color": _GREEN, "fontSize": 15}},
        ],
        "xAxis": [
            {"type": "value", "gridIndex": 0, "inverse": True,
             "axisLabel": {"show": False}, "splitLine": {"show": False}},
            {"type": "value", "gridIndex": 1,
             "axisLabel": {"show": False}, "splitLine": {"show": False}},
        ],
        "yAxis": [
            {"type": "category", "gridIndex": 0, "data": neg_words,
             "position": "right", "axisLabel": {"color": "#f1f5f9", "fontSize": 12},
             "axisLine": {"show": False}, "axisTick": {"show": False}},
            {"type": "category", "gridIndex": 1, "data": pos_words,
             "axisLabel": {"color": "#f1f5f9", "fontSize": 12},
             "axisLine": {"show": False}, "axisTick": {"show": False}},
        ],
        "series": [
            {"type": "bar", "xAxisIndex": 0, "yAxisIndex": 0, "data": neg_counts,
             "itemStyle": {"color": _RED, "borderRadius": [4, 0, 0, 4]},
             "barWidth": "60%", "label": {"show": True, "position": "left",
              "formatter": lambda_abs_str(), "color": "#f1f5f9", "fontSize": 11}},
            {"type": "bar", "xAxisIndex": 1, "yAxisIndex": 1, "data": pos_counts,
             "itemStyle": {"color": _GREEN, "borderRadius": [0, 4, 4, 0]},
             "barWidth": "60%", "label": {"show": True, "position": "right",
              "color": "#f1f5f9", "fontSize": 11}},
        ],
    }


def lambda_abs_str():
    """Return an ECharts JS formatter to show absolute value."""
    return "__JS_FUNC__function(p){return Math.abs(p.value);}__JS_FUNC__"


# ═══════════════════════════════════════════════════════════════════
# Chart 3: Score Distribution Histogram
# ═══════════════════════════════════════════════════════════════════
def gen_sentiment_distribution(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    df = results.processed_data
    if df is None:
        return None

    score_col = None
    for c in ("sentiment_score", "score"):
        if c in df.columns:
            score_col = c
            break
    if score_col is None:
        return None

    scores = df[score_col].dropna().tolist()
    if not scores:
        return None

    import numpy as np
    counts, bin_edges = np.histogram(scores, bins=30)
    bar_data = []
    for i, c in enumerate(counts):
        mid = (bin_edges[i] + bin_edges[i + 1]) / 2
        bar_data.append([round(mid, 3), int(c)])

    mean_val = round(float(np.mean(scores)), 3)

    return {
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "value", "name": "情感得分",
                  "axisLabel": {"color": "#94a3b8"}, "nameTextStyle": {"color": "#94a3b8"}},
        "yAxis": {"type": "value", "name": "评论数量",
                  "axisLabel": {"color": "#94a3b8"}, "nameTextStyle": {"color": "#94a3b8"},
                  "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.1)"}}},
        "series": [
            {"type": "bar", "data": bar_data, "barWidth": "90%",
             "itemStyle": {"color": {
                 "type": "linear", "x": 0, "y": 0, "x2": 1, "y2": 0,
                 "colorStops": [
                     {"offset": 0, "color": _RED},
                     {"offset": 0.5, "color": _AMBER},
                     {"offset": 1, "color": _GREEN},
                 ],
             }, "borderRadius": [3, 3, 0, 0]}},
            {"type": "line", "markLine": {
                "symbol": "none",
                "data": [{"xAxis": mean_val,
                          "label": {"formatter": f"均值={mean_val}", "color": _AMBER},
                          "lineStyle": {"color": _AMBER, "type": "dashed", "width": 2}}],
            }, "data": []},
        ],
    }


# ═══════════════════════════════════════════════════════════════════
# Chart 4: Length vs Sentiment Scatter
# ═══════════════════════════════════════════════════════════════════
def gen_sentiment_scatter(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    df = results.processed_data
    if df is None:
        return None

    col = _safe_sentiment_col(results)
    score_col = None
    for c in ("sentiment_score", "score"):
        if c in df.columns:
            score_col = c
            break
    if col is None or score_col is None:
        return None

    len_col = None
    for c in ("text_len", "content_length"):
        if c in df.columns:
            len_col = c
            break
    if len_col is None and "cleaned_text" in df.columns:
        lengths = df["cleaned_text"].astype(str).str.len()
    elif len_col:
        lengths = df[len_col]
    else:
        return None

    series = []
    for label, color in _LABEL_COLORS.items():
        mask = df[col] == label
        if mask.any():
            subset_len = lengths[mask].tolist()
            subset_score = df.loc[mask, score_col].tolist()
            data = [[round(l, 1), round(s, 3)] for l, s in zip(subset_len, subset_score)]
            if len(data) > 2000:
                import random
                data = random.sample(data, 2000)
            series.append({
                "type": "scatter", "name": label, "data": data,
                "symbolSize": 5,
                "itemStyle": {"color": color, "opacity": 0.5},
            })

    if not series:
        return None

    return {
        "tooltip": {"trigger": "item",
                     "formatter": "长度: {c0}<br/>情感得分: {c1}"},
        "legend": {"data": [s["name"] for s in series], "top": 10,
                   "textStyle": {"color": "#f1f5f9"}},
        "xAxis": {"type": "value", "name": "文本长度",
                  "axisLabel": {"color": "#94a3b8"}, "nameTextStyle": {"color": "#94a3b8"}},
        "yAxis": {"type": "value", "name": "情感得分",
                  "axisLabel": {"color": "#94a3b8"}, "nameTextStyle": {"color": "#94a3b8"},
                  "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.1)"}}},
        "series": series,
    }
