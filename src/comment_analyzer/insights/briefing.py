"""Build structured AI briefing payloads from pipeline results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from comment_analyzer.core.pipeline import PipelineResults


@dataclass
class BriefingPack:
    """Structured prompt package for downstream LLM execution."""

    system_prompt: str
    developer_prompt: str
    user_prompt: str
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert the prompt package into a JSON-serializable dict."""
        return asdict(self)


class InsightBriefingBuilder:
    """Build a robust prompt-injection package for review insight generation."""

    SYSTEM_PROMPT = """你是一名“评论洞察分析师 + 产品策略顾问”。
你的职责不是复述图表，而是基于评论数据输出可执行的商业判断。

必须遵守：
1. 只基于输入数据分析，不编造外部事实。
2. 先识别证据，再做解释，再给建议。
3. 每条重要结论都要有数据或评论证据支撑。
4. 明确区分：
- 事实：数据直接显示的现象
- 判断：对现象的解释
- 建议：可以执行的动作
- 风险：当前样本的局限或不确定性
5. 禁止空泛表达，例如“用户整体满意但仍有提升空间”或“建议进一步优化用户体验”，除非能说明具体问题、影响对象和业务含义。
6. 优先输出高价值发现：
- 高强度负面痛点
- 被反复提及的需求缺口
- 有增长潜力的卖点
- 可快速改进的产品问题
7. 语言风格应简洁、专业、有判断力，像给管理层汇报，而不是写说明书。
"""

    DEVELOPER_PROMPT = """你将收到以下输入：
- 数据概览：评论数量、有效样本数、时间范围
- 情绪分布
- 高频关键词
- 主题聚类
- 需求强度
- 共现关系
- 若干代表性评论原文

请按以下顺序分析：
1. 判断样本是否足够支持结论，指出明显偏差。
2. 用一句话概括当前用户舆情主旋律。
3. 提炼 3-5 条最重要发现，每条必须包含：
   - 发现标题
   - 现象说明
   - 证据
   - 对业务的意义
4. 提炼 2-4 个增长机会点。
5. 提炼 2-4 个风险点或阻碍转化的问题。
6. 给出一个按优先级排序的行动清单，分为：
   - 立刻可做
   - 下一阶段值得验证
7. 如果数据不足或证据冲突，必须明确说“不足以下结论”。

输出必须为合法 JSON，不要输出 markdown。
JSON 字段如下：
{
  "executive_summary": "",
  "core_findings": [
    {
      "title": "",
      "signal": "",
      "evidence": "",
      "business_impact": "",
      "priority": "high|medium|low"
    }
  ],
  "opportunity_points": [],
  "risk_points": [],
  "action_plan": {
    "immediate": [],
    "next_stage": []
  },
  "confidence_notes": []
}
"""

    def build(self, results: "PipelineResults", source_name: str = "analysis") -> BriefingPack:
        """Build a prompt package from pipeline results."""
        payload = self._build_payload(results, source_name)
        user_prompt = self._build_user_prompt(payload)
        return BriefingPack(
            system_prompt=self.SYSTEM_PROMPT,
            developer_prompt=self.DEVELOPER_PROMPT,
            user_prompt=user_prompt,
            payload=payload,
        )

    def _build_payload(self, results: "PipelineResults", source_name: str) -> Dict[str, Any]:
        df = results.processed_data
        total_comments = len(results.original_data)
        valid_comments = 0
        if df is not None and "processed_text" in df.columns:
            valid_comments = int(df["processed_text"].fillna("").astype(str).str.len().gt(0).sum())

        sentiment_distribution = [
            {"label": label, "count": int(count)}
            for label, count in sorted(
                results.sentiment_distribution.items(), key=lambda item: item[1], reverse=True
            )
        ]

        top_keywords = [
            {"word": word, "score": round(float(score), 4)}
            for word, score in results.top_keywords[:15]
        ]

        topics: List[Dict[str, Any]] = []
        for topic in results.topics[:5]:
            topics.append(
                {
                    "topic_id": int(topic.get("id", 0)),
                    "weight": round(float(topic.get("weight", 0.0)), 4),
                    "keywords": [
                        {"word": word, "weight": round(float(weight), 4)}
                        for word, weight in topic.get("words", [])[:8]
                    ],
                }
            )

        demand_intensity: List[Dict[str, Any]] = []
        if results.demand_intensity is not None and not results.demand_intensity.empty:
            for record in results.demand_intensity.head(20).to_dict(orient="records"):
                demand_intensity.append(
                    {str(key): self._normalize_scalar(value) for key, value in record.items()}
                )

        demand_correlation: List[Dict[str, Any]] = []
        if results.demand_correlation is not None and not results.demand_correlation.empty:
            corr_df = results.demand_correlation.copy()
            columns = corr_df.columns.tolist()
            for i, row_name in enumerate(columns):
                for j in range(i + 1, len(columns)):
                    score = float(corr_df.iloc[i, j])
                    if score > 0:
                        demand_correlation.append(
                            {
                                "left": str(row_name),
                                "right": str(columns[j]),
                                "score": round(score, 4),
                            }
                        )
            demand_correlation.sort(key=lambda item: item["score"], reverse=True)
            demand_correlation = demand_correlation[:12]

        representative_quotes = self._collect_quotes(results)

        return {
            "source_name": source_name,
            "data_overview": {
                "total_comments": total_comments,
                "valid_comments": valid_comments,
                "platform": getattr(results.settings.data, "platform", "generic")
                if results.settings
                else "generic",
                "date_range": self._infer_date_range(df),
            },
            "sentiment_distribution": sentiment_distribution,
            "top_keywords": top_keywords,
            "topics": topics,
            "demand_intensity": demand_intensity,
            "demand_correlation": demand_correlation,
            "representative_quotes": representative_quotes,
        }

    def _build_user_prompt(self, payload: Dict[str, Any]) -> str:
        return (
            "请基于以下评论分析结果，生成管理层可直接阅读的评论洞察结论。\n\n"
            f"[数据概览]\n{payload['data_overview']}\n\n"
            f"[情绪分布]\n{payload['sentiment_distribution']}\n\n"
            f"[高频关键词]\n{payload['top_keywords']}\n\n"
            f"[主题聚类]\n{payload['topics']}\n\n"
            f"[需求强度]\n{payload['demand_intensity']}\n\n"
            f"[共现关系]\n{payload['demand_correlation']}\n\n"
            f"[代表性评论]\n{payload['representative_quotes']}\n"
        )

    def _collect_quotes(self, results: "PipelineResults") -> Dict[str, List[str]]:
        df = results.processed_data
        if df is None or "cleaned_text" not in df.columns:
            return {"positive": [], "negative": [], "neutral": []}

        quote_map: Dict[str, List[str]] = {"positive": [], "negative": [], "neutral": []}
        if "sentiment" not in df.columns:
            return quote_map

        label_map = {
            "positive": {"positive", "正面"},
            "negative": {"negative", "负面"},
            "neutral": {"neutral", "中性"},
        }

        for target_key, labels in label_map.items():
            subset = df[df["sentiment"].isin(labels)]["cleaned_text"].dropna().astype(str)
            cleaned_quotes = []
            for quote in subset.head(5).tolist():
                quote = quote.strip()
                if len(quote) >= 6:
                    cleaned_quotes.append(quote[:140])
            quote_map[target_key] = cleaned_quotes[:3]

        return quote_map

    @staticmethod
    def _infer_date_range(df: Any) -> str:
        if df is None:
            return "unknown"
        for candidate in ("date", "time", "created", "日期", "时间"):
            if candidate in df.columns:
                values = df[candidate].dropna().astype(str)
                if not values.empty:
                    return f"{values.iloc[0]} -> {values.iloc[-1]}"
        return "unknown"

    @staticmethod
    def _normalize_scalar(value: Any) -> Any:
        if hasattr(value, "item") and callable(getattr(value, "item")):
            try:
                return value.item()
            except Exception:
                return value
        return value
