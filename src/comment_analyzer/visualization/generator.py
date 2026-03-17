"""Core visualization generator.

Reads PipelineResults and produces standalone HTML files with embedded ECharts.
Manages the manifest.json registry for tracking all generated visualizations.
"""

from __future__ import annotations

import html
import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from comment_analyzer.core.pipeline import PipelineResults
    from comment_analyzer.core.settings import Settings


class VisualizationGenerator:
    """Generate interactive HTML chart files from pipeline results.

    Each generated file is self-contained (ECharts via CDN) and can be
    opened by double-clicking in any modern browser.

    Files are saved to ``~/.sentidemand/outputs/{source}_{date}/`` by default,
    never overwriting previous runs.

    Example::

        gen = VisualizationGenerator(settings, results)
        paths = gen.generate_all("jd_comments")
    """

    # Registry of chart generators: chart_type -> (module_path, function_name, title)
    CHART_REGISTRY: Dict[str, tuple] = {
        # Sentiment (vis_01)
        "sentiment_donut": ("sentiment", "gen_sentiment_donut", "评论情感极性分布"),
        "sentiment_wordcloud": ("sentiment", "gen_sentiment_wordcloud", "正面 vs 负面高频词云"),
        "sentiment_distribution": ("sentiment", "gen_sentiment_distribution", "情感得分分布"),
        "sentiment_scatter": ("sentiment", "gen_sentiment_scatter", "评论长度 vs 情感得分"),
        # Features (vis_02)
        "features_bidirectional": ("features", "gen_features_bidirectional", "模型特征正负面双向对比"),
        "features_lollipop": ("features", "gen_features_lollipop", "高频核心词汇 Top30"),
        "features_heatmap": ("features", "gen_features_heatmap", "多模型特征权重热力图"),
        "features_tfidf_scatter": ("features", "gen_features_tfidf_scatter", "TF-IDF vs 词频对比"),
        # Topics (vis_03)
        "topics_nightingale": ("topics", "gen_topics_nightingale", "LDA 主题占比玫瑰图"),
        "topics_bubble": ("topics", "gen_topics_bubble", "主题关键词气泡矩阵"),
        "topics_radar": ("topics", "gen_topics_radar", "模型评估雷达图"),
        # Demand (vis_04)
        "demand_funnel": ("demand", "gen_demand_funnel", "需求强度漏斗图"),
        "demand_network": ("demand", "gen_demand_network", "需求共现网络关系图"),
        "demand_dashboard": ("demand", "gen_demand_dashboard", "需求综合仪表盘"),
    }
    _JS_FUNC_PATTERN = re.compile(r'"__JS_FUNC__(.*?)__JS_FUNC__"', re.DOTALL)

    def __init__(self, settings: "Settings", results: "PipelineResults"):
        self.settings = settings
        self.results = results
        self._template = self._load_template()

    # ── Template loading ──────────────────────────────────────────

    def _load_template(self) -> str:
        """Load the base HTML template."""
        tpl_path = Path(__file__).parent / "templates" / "base.html"
        return tpl_path.read_text(encoding="utf-8")

    # ── Public API ────────────────────────────────────────────────

    def generate_all(self, source_name: str) -> List[str]:
        """Generate all enabled charts.

        Args:
            source_name: Name of the data source (used in folder naming).

        Returns:
            List of absolute paths to generated HTML files.
        """
        enabled = self.settings.visualization.charts
        output_dir = self._prepare_output_dir(source_name)
        generated: List[str] = []

        for chart_type, (module, func_name, title) in self.CHART_REGISTRY.items():
            if not enabled.get(chart_type, True):
                continue
            try:
                path = self._generate_one(
                    chart_type, module, func_name, title,
                    source_name, output_dir,
                )
                if path:
                    generated.append(path)
            except Exception as e:
                logger.warning(f"Skipped chart '{chart_type}': {e}")

        logger.info(f"Generated {len(generated)}/{len(self.CHART_REGISTRY)} charts → {output_dir}")

        if self.settings.visualization.auto_open_browser and generated:
            self._open_in_browser(generated[0])

        return generated

    def generate_chart(self, chart_type: str, source_name: str) -> Optional[str]:
        """Generate a single chart by type name.

        Args:
            chart_type: One of the keys in CHART_REGISTRY.
            source_name: Data source name.

        Returns:
            Absolute path to generated HTML file, or None on failure.
        """
        if chart_type not in self.CHART_REGISTRY:
            raise ValueError(f"Unknown chart_type '{chart_type}'. Valid: {list(self.CHART_REGISTRY)}")

        module, func_name, title = self.CHART_REGISTRY[chart_type]
        output_dir = self._prepare_output_dir(source_name)
        return self._generate_one(chart_type, module, func_name, title, source_name, output_dir)

    # ── Internal logic ────────────────────────────────────────────

    def _generate_one(
        self,
        chart_type: str,
        module_name: str,
        func_name: str,
        title: str,
        source_name: str,
        output_dir: Path,
    ) -> Optional[str]:
        """Generate a single chart HTML file."""
        import importlib
        mod = importlib.import_module(f"comment_analyzer.visualization.charts.{module_name}")
        gen_func = getattr(mod, func_name)

        echarts_option = gen_func(self.results)
        if echarts_option is None:
            logger.debug(f"Chart '{chart_type}' returned None (no data), skipping")
            return None

        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{chart_type}_{timestamp}.html"
        filepath = output_dir / filename

        # Render template
        option_json = json.dumps(
            echarts_option,
            ensure_ascii=False,
            indent=2,
            default=self._json_default,
        )
        option_json = self._restore_js_functions(option_json)
        html_doc = self._template
        html_doc = html_doc.replace("{{CHART_TITLE}}", html.escape(title))
        html_doc = html_doc.replace("{{SOURCE_NAME}}", html.escape(source_name))
        html_doc = html_doc.replace("{{CREATED_AT}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        html_doc = html_doc.replace("{{CHART_TYPE}}", html.escape(chart_type))
        html_doc = html_doc.replace("{{CHART_HEIGHT}}", self._get_chart_height(chart_type))
        html_doc = html_doc.replace("{{ECHARTS_OPTION}}", option_json)

        filepath.write_text(html_doc, encoding="utf-8")
        logger.info(f"  ✅ {title} → {filename}")

        # Update manifest
        self._update_manifest(source_name, chart_type, title, filepath)

        return str(filepath)

    def _prepare_output_dir(self, source_name: str) -> Path:
        """Create output directory for this source + date combo."""
        date_str = datetime.now().strftime("%Y%m%d")
        clean_name = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", source_name, flags=re.UNICODE).strip("_")
        if not clean_name:
            clean_name = "analysis"
        folder_name = f"{clean_name}_{date_str}"
        output_dir = self.settings.paths.get_visualization_path() / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    @classmethod
    def _restore_js_functions(cls, option_json: str) -> str:
        """Restore JS function placeholders into raw functions.

        Chart generators can embed formatter/symbol functions using:
        ``__JS_FUNC__function(...) {...}__JS_FUNC__``.
        """

        def _replace(match: re.Match[str]) -> str:
            raw = match.group(1)
            try:
                return json.loads(f'"{raw}"')
            except json.JSONDecodeError:
                return raw

        return cls._JS_FUNC_PATTERN.sub(_replace, option_json)

    @staticmethod
    def _json_default(value: Any) -> Any:
        """JSON serializer fallback for numpy/pandas scalar objects."""
        # numpy scalar values (np.float32, np.int64, etc.)
        if hasattr(value, "item") and callable(getattr(value, "item")):
            try:
                return value.item()
            except Exception:
                pass
        # generic iterable containers that JSON cannot directly encode
        if isinstance(value, (set, tuple)):
            return list(value)
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    def _get_chart_height(self, chart_type: str) -> str:
        """Return preferred chart height CSS value."""
        tall_charts = {"demand_network", "topics_nightingale", "features_bidirectional"}
        if chart_type in tall_charts:
            return "700px"
        return "520px"

    def _get_source_hash(self) -> str:
        """Compute a short hash of the original data for provenance."""
        try:
            data_str = self.results.original_data.head(100).to_csv(index=False)
            return hashlib.sha256(data_str.encode()).hexdigest()[:16]
        except Exception:
            return "unknown"

    # ── Manifest management ───────────────────────────────────────

    def _get_manifest_path(self) -> Path:
        return self.settings.paths.get_visualization_path() / "manifest.json"

    def _load_manifest(self) -> Dict[str, Any]:
        path = self._get_manifest_path()
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"version": "1.0", "entries": []}

    def _update_manifest(
        self,
        source_name: str,
        chart_type: str,
        title: str,
        filepath: Path,
    ) -> None:
        manifest = self._load_manifest()
        vis_root = self.settings.paths.get_visualization_path()
        rel_path = str(filepath.relative_to(vis_root)).replace("\\", "/")

        entry = {
            "id": uuid.uuid4().hex[:8],
            "source_file": source_name,
            "source_hash": self._get_source_hash(),
            "chart_type": chart_type,
            "chart_title": title,
            "output_path": rel_path,
            "created_at": datetime.now().isoformat(),
            "pipeline_config": {
                "platform": self.settings.data.platform,
                "sentiment_method": self.settings.sentiment.labeling_method,
            },
            "data_summary": self._build_data_summary(),
        }
        manifest["entries"].append(entry)

        self._get_manifest_path().write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _build_data_summary(self) -> Dict[str, Any]:
        """Build a compact summary of the analysis results for the manifest."""
        summary: Dict[str, Any] = {
            "total_comments": len(self.results.original_data),
        }
        if self.results.sentiment_distribution:
            total = sum(self.results.sentiment_distribution.values())
            summary["sentiment"] = {
                k: round(v / total * 100, 1) if total > 0 else 0
                for k, v in self.results.sentiment_distribution.items()
            }
        if self.results.top_keywords:
            summary["top_keywords"] = [w for w, _ in self.results.top_keywords[:5]]
        return summary

    # ── Browser ───────────────────────────────────────────────────

    @staticmethod
    def _open_in_browser(filepath: str) -> None:
        """Open generated file in default browser."""
        import webbrowser
        try:
            webbrowser.open(f"file:///{filepath.replace(chr(92), '/')}")
        except Exception:
            pass
