#!/usr/bin/env python
"""
Custom Configuration Example for Comment Analyzer

This example demonstrates how to customize the analysis pipeline
using configuration files and programmatic configuration.

Requirements:
    pip install comment-analyzer pandas

Usage:
    python custom_config.py
"""

import json
import tempfile
from pathlib import Path

import pandas as pd
from comment_analyzer import CommentPipeline, Config


def create_sample_data():
    """Create sample comment data."""
    return pd.DataFrame({
        "review_content": [
            "产品质量非常好，做工精细，用料考究",
            "包装精美，物流快速，服务态度好",
            "性价比很高，比实体店便宜很多",
            "质量一般，做工有待改进",
            "物流太慢，等了一周才到",
            "客服态度很好，解决问题及时",
            "外观漂亮，功能齐全，推荐购买",
            "不好用，用了几天就出问题了",
            "价格便宜，质量也不错，好评",
            "整体满意，会继续回购的",
        ] * 10,
        "rating": [5, 5, 5, 3, 2, 5, 5, 1, 4, 5] * 10,
    })


def example_programmatic_config():
    """Example 1: Programmatic configuration."""
    print("\n" + "=" * 60)
    print("Example 1: Programmatic Configuration")
    print("=" * 60)

    # Create configuration from defaults
    config = Config()

    # Modify preprocessing settings
    config.preprocessing.clean.remove_urls = True
    config.preprocessing.segmentation.mode = "precise"
    config.preprocessing.stopwords.extra_words = ["商品", "店铺", "卖家"]

    # Modify sentiment analysis settings
    config.sentiment.tfidf.max_features = 3000
    config.sentiment.models.svm.enabled = True
    config.sentiment.models.svm.C = 2.0
    config.sentiment.models.logistic_regression.enabled = False

    # Modify topic modeling settings
    config.topic.lda.num_topics = 3
    config.topic.lda.passes = 10

    # Create pipeline with custom config
    pipeline = CommentPipeline(config)

    # Run analysis
    df = create_sample_data()
    results = pipeline.run(df, text_column="review_content", verbose=False)

    print("\nResults with custom programmatic configuration:")
    print(f"- Topics discovered: {len(results.topics)}")
    print(f"- Sentiment distribution: {results.sentiment_distribution}")


def example_yaml_config():
    """Example 2: Loading configuration from YAML."""
    print("\n" + "=" * 60)
    print("Example 2: YAML Configuration")
    print("=" * 60)

    # Create a temporary YAML config file
    yaml_content = """
data:
  platform: generic
  text_column_keywords:
    - review_content
    - comment
    - 评论

preprocessing:
  segmentation:
    mode: search
  stopwords:
    use_default: true
    extra_words:
      - 快递
      - 物流
      - 发货

sentiment:
  labeling_method: snownlp
  tfidf:
    max_features: 2000
  models:
    naive_bayes:
      enabled: true
    svm:
      enabled: false

topic:
  lda:
    num_topics: 4
    passes: 8
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        config_path = f.name

    try:
        # Load configuration from YAML
        config = Config.from_yaml(config_path)
        pipeline = CommentPipeline(config)

        # Run analysis
        df = create_sample_data()
        results = pipeline.run(df, text_column="review_content", verbose=False)

        print(f"\nResults with YAML configuration:")
        print(f"- Topics discovered: {len(results.topics)}")
        print(f"- Top keywords: {[w for w, _ in results.top_keywords[:5]]}")

    finally:
        # Clean up
        Path(config_path).unlink()


def example_custom_keywords():
    """Example 3: Custom demand keywords."""
    print("\n" + "=" * 60)
    print("Example 3: Custom Demand Keywords")
    print("=" * 60)

    # Create custom demand keywords
    custom_keywords = {
        "categories": {
            "quality": {
                "name": "质量",
                "name_en": "Quality",
                "keywords": ["质量", "品质", "做工", "材料", "耐用"]
            },
            "appearance": {
                "name": "外观",
                "name_en": "Appearance",
                "keywords": ["外观", "颜值", "漂亮", "好看", "设计", "颜色"]
            },
            "value": {
                "name": "性价比",
                "name_en": "Value",
                "keywords": ["性价比", "划算", "值得", "物美价廉", "实惠"]
            }
        }
    }

    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(custom_keywords, f, ensure_ascii=False, indent=2)
        keywords_path = f.name

    try:
        from comment_analyzer.demand import DemandIntensityCalculator

        # Use custom keywords
        calculator = DemandIntensityCalculator(
            keywords_path=keywords_path,
            method='tfidf_weighted',
            normalization='minmax'
        )

        # Sample documents
        documents = [
            ["质量", "很好", "外观", "漂亮", "性价比", "高"],
            ["外观", "一般", "质量", "不错"],
            ["性价比", "很高", "值得", "购买"],
        ]

        intensity = calculator.calculate(documents)

        print("\nCustom demand intensity analysis:")
        print(intensity.to_string())

        print("\nCategory distribution:")
        distribution = calculator.get_category_distribution(intensity)
        for cat, value in distribution.items():
            print(f"  {cat}: {value:.4f}")

    finally:
        Path(keywords_path).unlink()


def example_custom_stopwords():
    """Example 4: Custom stopwords."""
    print("\n" + "=" * 60)
    print("Example 4: Custom Stopwords")
    print("=" * 60)

    from comment_analyzer.preprocessing import StopwordFilter

    # Create custom stopwords file
    stopwords_content = """# Custom stopwords
京东
淘宝
天猫
店家
客服小哥
快递小哥
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(stopwords_content)
        stopwords_path = f.name

    try:
        # Use custom stopwords
        filter_ = StopwordFilter(stopwords_path=stopwords_path)

        # Test filtering
        words = ["京东", "产品", "质量很好", "客服小哥", "态度好"]
        filtered = filter_.filter(words)

        print("\nOriginal words:", words)
        print("Filtered words:", filtered)
        print(f"\nRemoved: {set(words) - set(filtered)}")

    finally:
        Path(stopwords_path).unlink()


def main():
    """Run all examples."""
    print("=" * 60)
    print("Comment Analyzer - Custom Configuration Examples")
    print("=" * 60)

    example_programmatic_config()
    example_yaml_config()
    example_custom_keywords()
    example_custom_stopwords()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
