"""Profile-aware analysis helpers for demographic-enhanced review insights."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class ProfileAnalysisReport:
    """Structured demographic analysis output."""

    strategy: str
    detected_dimensions: List[str]
    coverage: Dict[str, float]
    dimension_summaries: List[Dict[str, Any]]
    segment_insights: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-friendly representation."""
        return asdict(self)


class DemographicProfileAnalyzer:
    """Detect demographic fields and build segmented insight summaries."""

    _COLUMN_CANDIDATES = {
        "gender": ["gender", "sex", "性别"],
        "age": ["age", "age_group", "年龄", "年龄段"],
        "region": ["region", "area", "province", "city", "地区", "地域", "省份", "城市"],
    }

    def analyze(self, df: pd.DataFrame) -> ProfileAnalysisReport:
        """Build a demographic summary from processed comments."""
        detected = self._detect_dimensions(df)
        if not detected:
            return ProfileAnalysisReport(
                strategy="generic",
                detected_dimensions=[],
                coverage={},
                dimension_summaries=[],
                segment_insights=[],
            )

        working_df = df.copy()
        if "age" in detected:
            working_df["_age_bucket"] = working_df[detected["age"]].apply(self._normalize_age_bucket)

        coverage = {
            dimension: round(float(working_df[column].notna().mean()), 4)
            if dimension != "age"
            else round(float(working_df["_age_bucket"].notna().mean()), 4)
            for dimension, column in detected.items()
        }

        dimension_summaries = [
            self._build_dimension_summary(working_df, dimension, column)
            for dimension, column in detected.items()
        ]
        segment_insights = self._build_segment_insights(working_df, detected)

        return ProfileAnalysisReport(
            strategy="profile_enhanced",
            detected_dimensions=list(detected.keys()),
            coverage=coverage,
            dimension_summaries=dimension_summaries,
            segment_insights=segment_insights,
        )

    def _detect_dimensions(self, df: pd.DataFrame) -> Dict[str, str]:
        detected: Dict[str, str] = {}
        normalized_columns = {str(column).lower(): str(column) for column in df.columns}
        for dimension, aliases in self._COLUMN_CANDIDATES.items():
            for alias in aliases:
                column = normalized_columns.get(alias.lower())
                if column is not None:
                    detected[dimension] = column
                    break
        return detected

    def _build_dimension_summary(
        self,
        df: pd.DataFrame,
        dimension: str,
        column: str,
    ) -> Dict[str, Any]:
        series = df["_age_bucket"] if dimension == "age" else df[column]
        grouped = (
            df.assign(_dimension_value=series)
            .dropna(subset=["_dimension_value"])
            .groupby("_dimension_value", dropna=True)
        )

        top_values: List[Dict[str, Any]] = []
        for value, group in sorted(grouped, key=lambda item: len(item[1]), reverse=True)[:5]:
            top_values.append(
                {
                    "dimension": dimension,
                    "value": str(value),
                    "sample_size": int(len(group)),
                    "dominant_sentiment": self._dominant_sentiment(group),
                    "top_keywords": self._top_keywords(group),
                }
            )

        return {
            "dimension": dimension,
            "field": column,
            "value_count": int(series.dropna().nunique()),
            "top_values": top_values,
        }

    def _build_segment_insights(self, df: pd.DataFrame, detected: Dict[str, str]) -> List[Dict[str, Any]]:
        segment_columns: List[str] = []
        for dimension, column in detected.items():
            segment_columns.append("_age_bucket" if dimension == "age" else column)

        grouped = (
            df.dropna(subset=segment_columns)
            .groupby(segment_columns, dropna=True)
        )

        insights: List[Dict[str, Any]] = []
        for keys, group in sorted(grouped, key=lambda item: len(item[1]), reverse=True)[:5]:
            if not isinstance(keys, tuple):
                keys = (keys,)
            segment = {}
            for index, dimension in enumerate(detected.keys()):
                segment[dimension] = str(keys[index])
            insights.append(
                {
                    "segment": ", ".join(f"{key}={value}" for key, value in segment.items()),
                    "sample_size": int(len(group)),
                    "dominant_sentiment": self._dominant_sentiment(group),
                    "top_keywords": self._top_keywords(group),
                    "focus_hint": self._build_focus_hint(group),
                }
            )
        return insights

    @staticmethod
    def _dominant_sentiment(group: pd.DataFrame) -> str:
        if "sentiment" not in group.columns:
            return "unknown"
        counts = group["sentiment"].dropna().astype(str).value_counts()
        if counts.empty:
            return "unknown"
        return str(counts.idxmax())

    @staticmethod
    def _top_keywords(group: pd.DataFrame) -> List[str]:
        tokens: Counter[str] = Counter()
        if "filtered_text" not in group.columns:
            return []
        for row in group["filtered_text"]:
            for token in row or []:
                cleaned = str(token).strip()
                if cleaned:
                    tokens[cleaned] += 1
        return [word for word, _ in tokens.most_common(5)]

    def _build_focus_hint(self, group: pd.DataFrame) -> str:
        keywords = self._top_keywords(group)
        if not keywords:
            return "当前分群样本较少，建议结合原始评论进一步核验。"
        lead = "、".join(keywords[:3])
        return f"该分群更常提到 {lead}，适合在交付中单独说明。"

    @staticmethod
    def _normalize_age_bucket(value: Any) -> Optional[str]:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if any(marker in stripped for marker in ["后", "-", "~", "岁"]):
                return stripped
            if stripped.isdigit():
                value = int(stripped)
            else:
                return stripped

        if isinstance(value, (int, float)) and not pd.isna(value):
            age = int(value)
            if age < 18:
                return "18岁以下"
            if age <= 24:
                return "18-24岁"
            if age <= 34:
                return "25-34岁"
            if age <= 44:
                return "35-44岁"
            return "45岁及以上"
        return str(value)
