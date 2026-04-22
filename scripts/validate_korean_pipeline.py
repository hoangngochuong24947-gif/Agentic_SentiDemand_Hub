"""Validate Korean preprocessing and pipeline behavior on synthetic data."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from comment_analyzer.core.pipeline import CommentPipeline
from comment_analyzer.core.settings import init_settings, reset_settings


def detect_okt() -> dict:
    try:
        from konlpy.tag import Okt

        tokens = Okt().morphs("배송이 빠르고 품질도 만족스러워요", norm=True, stem=True)
        return {"available": True, "backend": "okt", "tokens": tokens}
    except Exception as exc:
        return {"available": False, "backend": "regex", "tokens": [], "error": str(exc)}


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    dataset_path = repo_root / "data" / "korean_reviews_mock.csv"
    report_path = repo_root / "outputs" / "korean_validation_report.json"

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}. Run generate_korean_test_dataset.py first.")

    reset_settings()
    init_settings(
        **{
            "data": {"language": "ko"},
            "preprocessing": {"segmentation": {"backend": "okt"}},
            "sentiment": {"labeling_method": "lexicon"},
        }
    )

    df = pd.read_csv(dataset_path)
    okt_probe = detect_okt()
    pipeline = CommentPipeline()
    results = pipeline.run(df, text_column="comment", verbose=False)

    report = {
        "dataset_rows": len(df),
        "segmenter_backend": pipeline.segmenter.resolved_backend,
        "sentiment_method": pipeline.sentiment_labeler._resolve_method(),
        "okt_probe": okt_probe,
        "sentiment_distribution": results.sentiment_distribution,
        "top_keywords": results.top_keywords[:10],
        "sample_tokens": results.processed_data[["comment", "filtered_text"]].head(5).to_dict(orient="records"),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
