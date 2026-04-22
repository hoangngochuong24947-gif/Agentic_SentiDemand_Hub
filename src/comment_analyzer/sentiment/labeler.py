"""Sentiment labeling helpers for Chinese and Korean review text."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
from snownlp import SnowNLP
from tqdm import tqdm


class SentimentLabeler:
    """Label text as positive, negative, or neutral."""

    def __init__(
        self,
        method: str = "auto",
        threshold_positive: float = 0.6,
        threshold_negative: float = 0.4,
        language: str = "zh",
        lexicon_path: Optional[Union[str, Path]] = None,
    ):
        if method not in ("auto", "snownlp", "rating", "lexicon"):
            raise ValueError("Invalid method: choose from 'auto', 'snownlp', 'rating', 'lexicon'")

        self.method = method
        self.threshold_positive = threshold_positive
        self.threshold_negative = threshold_negative
        self.language = language
        self.lexicon_path = Path(lexicon_path) if lexicon_path else None
        self.lexicon = self._load_lexicon(self.lexicon_path)

    def _resolve_method(self) -> str:
        if self.method != "auto":
            return self.method
        return "lexicon" if self.language == "ko" else "snownlp"

    @staticmethod
    def _default_lexicon() -> Dict[str, List[str]]:
        return {
            "positive": ["좋", "만족", "추천", "빠르", "훌륭", "예쁘", "편하", "부드럽", "깔끔", "가성비"],
            "negative": ["별로", "불만", "실망", "느리", "최악", "환불", "문제", "불편", "아쉽", "늦"],
            "negations": ["안", "못", "없", "아니"],
        }

    def _load_lexicon(self, path: Optional[Path]) -> Dict[str, List[str]]:
        if path and path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            return {
                "positive": loaded.get("positive", []),
                "negative": loaded.get("negative", []),
                "negations": loaded.get("negations", []),
            }
        return self._default_lexicon()

    def _lexicon_score(self, text: str) -> float:
        tokens = re.findall(r"[가-힣A-Za-z]+", text.lower())
        if not tokens:
            return 0.5

        positive = 0
        negative = 0
        negations = set(self.lexicon.get("negations", []))

        for index, token in enumerate(tokens):
            window = tokens[max(0, index - 2):index]
            negated = any(neg in window for neg in negations)
            if any(keyword in token for keyword in self.lexicon.get("positive", [])):
                if negated:
                    negative += 1
                else:
                    positive += 1
            if any(keyword in token for keyword in self.lexicon.get("negative", [])):
                if negated:
                    positive += 1
                else:
                    negative += 1

        total = positive + negative
        if total == 0:
            return 0.5
        return positive / total

    def get_score(self, text: str) -> float:
        if not text or not isinstance(text, str):
            return 0.5

        resolved_method = self._resolve_method()
        if resolved_method == "snownlp":
            try:
                return SnowNLP(text).sentiments
            except Exception:
                return 0.5
        if resolved_method == "lexicon":
            return self._lexicon_score(text)
        return 0.5

    def label(self, text: str) -> str:
        score = self.get_score(text)
        if score >= self.threshold_positive:
            return "positive"
        if score <= self.threshold_negative:
            return "negative"
        return "neutral"

    def label_batch(self, texts: Union[List[str], pd.Series], verbose: bool = False) -> List[str]:
        iterator = tqdm(texts, desc="Labeling sentiment") if verbose else texts
        return [self.label(text) for text in iterator]

    def label_from_rating(
        self,
        ratings: Union[List[float], pd.Series],
        max_rating: float = 5.0,
        positive_threshold: float = 0.6,
        negative_threshold: float = 0.4,
    ) -> List[str]:
        labels: List[str] = []
        for rating in ratings:
            if pd.isna(rating):
                labels.append("neutral")
                continue
            normalized = float(rating) / max_rating
            if normalized >= positive_threshold:
                labels.append("positive")
            elif normalized <= negative_threshold:
                labels.append("negative")
            else:
                labels.append("neutral")
        return labels

    def get_sentiment_distribution(self, labels: List[str]) -> dict:
        total = len(labels)
        if total == 0:
            return {}

        counts = {}
        for label in ("positive", "negative", "neutral"):
            count = labels.count(label)
            counts[label] = {"count": count, "percentage": count / total * 100}
        return counts
