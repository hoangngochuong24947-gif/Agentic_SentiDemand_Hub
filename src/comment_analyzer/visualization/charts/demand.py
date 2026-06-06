"""Demand insight chart generators (vis_04 direction).

Produces ECharts option dicts for:
  - Funnel chart (demand intensity ranking)
  - Force-directed graph (demand co-occurrence network)
  - Dashboard (combined bars + top pairs)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from comment_analyzer.core.pipeline import PipelineResults

_PALETTE = ["#ef4444", "#f97316", "#f59e0b", "#10b981", "#3b82f6",
            "#8b5cf6", "#06b6d4", "#334155"]


# ═══════════════════════════════════════════════════════════════════
# Chart 12: Demand Funnel
# ═══════════════════════════════════════════════════════════════════
def gen_demand_funnel(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    df = results.demand_intensity
    if df is None or df.empty:
        return None

    # Expect columns: demand_type, count (or intensity_pct)
    if "demand_type" not in df.columns:
        return None

    count_col = "count" if "count" in df.columns else "intensity_pct"
    if count_col not in df.columns:
        # Fallback: use first numeric column
        num_cols = df.select_dtypes(include="number").columns
        if len(num_cols) == 0:
            return None
        count_col = num_cols[0]

    sorted_df = df.sort_values(count_col, ascending=False)
    data = []
    for i, (_, row) in enumerate(sorted_df.iterrows()):
        data.append({
            "name": str(row["demand_type"]),
            "value": round(float(row[count_col]), 1),
            "itemStyle": {"color": _PALETTE[i % len(_PALETTE)]},
        })

    return {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c}"},
        "series": [{
            "type": "funnel",
            "left": "15%",
            "width": "70%",
            "top": 40,
            "bottom": 30,
            "min": 0,
            "minSize": "8%",
            "maxSize": "100%",
            "sort": "descending",
            "gap": 4,
            "label": {"show": True, "position": "inside", "color": "#f1f5f9",
                      "fontSize": 14, "fontWeight": "bold"},
            "labelLine": {"show": False},
            "itemStyle": {"borderColor": "#0a0e1a", "borderWidth": 2, "borderRadius": 4},
            "emphasis": {"label": {"fontSize": 16}},
            "data": data,
            "animationType": "scale",
        }],
    }


# ═══════════════════════════════════════════════════════════════════
# Chart 13: Demand Co-occurrence Network (Force Graph)
# ═══════════════════════════════════════════════════════════════════
def gen_demand_network(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    corr_df = results.demand_correlation
    int_df = results.demand_intensity
    if corr_df is None or corr_df.empty:
        return None

    demand_names = corr_df.columns.tolist()
    size_map = {}
    if int_df is not None and "demand_type" in int_df.columns:
        count_col = "count" if "count" in int_df.columns else int_df.select_dtypes(include="number").columns[0]
        size_map = {str(row["demand_type"]): float(row[count_col]) for _, row in int_df.iterrows()}

    max_size = max(size_map.values()) if size_map else 1

    nodes = []
    for i, name in enumerate(demand_names):
        size_val = size_map.get(name, max_size * 0.3)
        nodes.append({
            "id": str(i),
            "name": name,
            "symbolSize": max(20, size_val / max_size * 70),
            "itemStyle": {"color": _PALETTE[i % len(_PALETTE)]},
            "label": {"show": True, "color": "#f1f5f9", "fontSize": 13, "fontWeight": "bold"},
        })

    links = []
    import numpy as np
    vals = corr_df.values.copy()
    np.fill_diagonal(vals, 0)
    max_co = max(float(vals.max()), 1)

    for i in range(len(demand_names)):
        for j in range(i + 1, len(demand_names)):
            w = float(vals[i][j])
            if w > 0:
                links.append({
                    "source": str(i),
                    "target": str(j),
                    "value": round(w, 1),
                    "lineStyle": {
                        "width": max(1, w / max_co * 10),
                        "opacity": min(0.9, w / max_co * 0.8 + 0.1),
                        "color": "#475569",
                        "curveness": 0.1,
                    },
                })

    return {
        "tooltip": {"formatter": "__JS_FUNC__function(p){if(p.dataType==='edge')return p.data.source+' × '+p.data.target+': '+p.data.value;return p.name;}__JS_FUNC__"},
        "animationDuration": 1500,
        "animationEasingUpdate": "quinticInOut",
        "series": [{
            "type": "graph",
            "layout": "force",
            "data": nodes,
            "links": links,
            "roam": True,
            "force": {"repulsion": 300, "gravity": 0.1, "edgeLength": [80, 200]},
            "emphasis": {"focus": "adjacency",
                         "lineStyle": {"width": 6}},
            "lineStyle": {"curveness": 0.1},
        }],
    }


# ═══════════════════════════════════════════════════════════════════
# Chart 14: Demand Dashboard (dual bars)
# ═══════════════════════════════════════════════════════════════════
def gen_demand_dashboard(results: "PipelineResults") -> Optional[Dict[str, Any]]:
    int_df = results.demand_intensity
    corr_df = results.demand_correlation
    if int_df is None or int_df.empty:
        return None

    # Left: demand intensity bar
    if "demand_type" not in int_df.columns:
        return None
    pct_col = "intensity_pct" if "intensity_pct" in int_df.columns else (
        "count" if "count" in int_df.columns else int_df.select_dtypes(include="number").columns[0]
    )
    sorted_df = int_df.sort_values(pct_col, ascending=True)
    dem_names = sorted_df["demand_type"].tolist()
    dem_vals = [round(float(v), 1) for v in sorted_df[pct_col]]
    bar_colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(dem_names))]

    # Right: top co-occurrence pairs
    pairs_data = {"names": [], "vals": []}
    if corr_df is not None and not corr_df.empty:
        import numpy as np
        names = corr_df.columns.tolist()
        cv = corr_df.values.copy()
        np.fill_diagonal(cv, 0)
        pair_list = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if cv[i][j] > 0:
                    pair_list.append((f"{names[i]} × {names[j]}", float(cv[i][j])))
        pair_list.sort(key=lambda x: x[1], reverse=True)
        top8 = pair_list[:8]
        pairs_data["names"] = [p[0] for p in reversed(top8)]
        pairs_data["vals"] = [round(p[1], 1) for p in reversed(top8)]

    series = [{
        "type": "bar", "xAxisIndex": 0, "yAxisIndex": 0,
        "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(dem_vals, bar_colors)],
        "barWidth": "55%", "itemStyle": {"borderRadius": [0, 4, 4, 0]},
        "label": {"show": True, "position": "right", "color": "#94a3b8", "fontSize": 11},
    }]

    grids = [{"left": "12%", "right": "55%", "top": 50, "bottom": 30}]
    x_axes = [{"type": "value", "gridIndex": 0, "axisLabel": {"color": "#94a3b8"},
               "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.1)"}}}]
    y_axes = [{"type": "category", "gridIndex": 0, "data": dem_names,
               "axisLabel": {"color": "#f1f5f9", "fontSize": 12},
               "axisLine": {"show": False}}]
    titles = [{"text": "需求强度排行", "left": "20%", "top": 10,
               "textStyle": {"color": "#f1f5f9", "fontSize": 15}}]

    if pairs_data["names"]:
        grids.append({"left": "55%", "right": "5%", "top": 50, "bottom": 30})
        x_axes.append({"type": "value", "gridIndex": 1, "axisLabel": {"color": "#94a3b8"},
                       "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.1)"}}})
        y_axes.append({"type": "category", "gridIndex": 1, "data": pairs_data["names"],
                       "axisLabel": {"color": "#f1f5f9", "fontSize": 11},
                       "axisLine": {"show": False}})
        series.append({
            "type": "bar", "xAxisIndex": 1, "yAxisIndex": 1,
            "data": pairs_data["vals"],
            "barWidth": "55%",
            "itemStyle": {"color": "#f97316", "borderRadius": [0, 4, 4, 0]},
            "label": {"show": True, "position": "right", "color": "#f97316", "fontSize": 11,
                      "fontWeight": "bold"},
        })
        titles.append({"text": "高频共现组合 Top8", "left": "70%", "top": 10,
                       "textStyle": {"color": "#f1f5f9", "fontSize": 15}})

    return {
        "title": titles,
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": grids,
        "xAxis": x_axes,
        "yAxis": y_axes,
        "series": series,
    }
