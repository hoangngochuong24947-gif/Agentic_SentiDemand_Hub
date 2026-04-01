"""User-facing progress copy for long-running analysis tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass
class ProgressMessage:
    """A compact user-facing progress payload."""

    stage: str
    label: str
    encouragement: str
    analysis_tip: str
    delivery_copy: str

    def to_dict(self) -> Dict[str, str]:
        """Return a JSON-friendly representation."""
        return asdict(self)


class ProgressMessageCenter:
    """Build reusable progress messages for CLI or future API streaming."""

    _COPY = {
        "preprocessing": ProgressMessage(
            stage="preprocessing",
            label="数据预处理",
            encouragement="先把评论洗干净，后面的判断才会更稳，我们在帮结果打基础。",
            analysis_tip="小技巧：先看清洗后的高频词，再判断情绪和需求，误判会少很多。",
            delivery_copy="当前正在整理评论文本、分词和去噪，马上进入分析阶段。",
        ),
        "sentiment": ProgressMessage(
            stage="sentiment",
            label="情绪分析",
            encouragement="情绪分布正在成形，越靠近真实用户感受，后面的结论就越有价值。",
            analysis_tip="小技巧：别只盯正负面比例，负面评论的集中主题更值得优先处理。",
            delivery_copy="当前正在提取情绪信号，稍后会给出情绪结构和重点风险点。",
        ),
        "topic": ProgressMessage(
            stage="topic",
            label="主题建模",
            encouragement="评论里的共性主题正在浮现，杂乱反馈很快会变成可读结构。",
            analysis_tip="小技巧：把主题词和原评论一起看，能更快分辨“真需求”和“偶发抱怨”。",
            delivery_copy="当前正在聚合高频主题，稍后会输出用户反复提到的关注点。",
        ),
        "demand": ProgressMessage(
            stage="demand",
            label="需求分析",
            encouragement="需求强度和共现关系正在拼起来，这一步最容易长出行动建议。",
            analysis_tip="小技巧：需求共现高，不代表都要一起做，先看是否同时影响转化和满意度。",
            delivery_copy="当前正在计算需求强度与关联关系，稍后会给出优先处理方向。",
        ),
        "profile": ProgressMessage(
            stage="profile",
            label="画像增强",
            encouragement="有用户基础画像时，分析会更接近“谁在说什么”，而不只是“大家在说什么”。",
            analysis_tip="小技巧：分群样本量先过线，再解读差异；小样本差异更适合当假设，不适合当结论。",
            delivery_copy="当前正在比对不同用户画像的反馈差异，稍后会补充人群洞察。",
        ),
    }

    def build(self, stages: List[str]) -> List[Dict[str, str]]:
        """Create ordered progress payloads for a set of stages."""
        messages: List[Dict[str, str]] = []
        for stage in stages:
            payload = self._COPY.get(stage)
            if payload is not None:
                messages.append(payload.to_dict())
        return messages
