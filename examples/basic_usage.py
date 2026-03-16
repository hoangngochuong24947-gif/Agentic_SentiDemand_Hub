#!/usr/bin/env python
"""
Basic Usage Example for Comment Analyzer

This example demonstrates the simplest way to use the comment analyzer
for processing e-commerce comments.

Requirements:
    pip install comment-analyzer pandas

Usage:
    python basic_usage.py
"""

import pandas as pd
from comment_analyzer import CommentPipeline, Config


def create_sample_data():
    """Create sample comment data for demonstration."""
    data = {
        "comment": [
            "产品质量非常好，物流也很快，下次还会购买！",
            "一般般吧，没什么特别的，价格还可以",
            "包装破损了，客服态度也不好，很失望",
            "味道不错，价格便宜，性价比很高",
            "物流太慢了，等了一个星期才到",
            "质量很好，做工精细，非常满意",
            "服务态度很好，有问题及时解决",
            "外观漂亮，功能齐全，推荐购买",
            "不好用，用了几天就坏了，退货",
            "性价比很高，朋友推荐买的，确实不错",
        ] * 10,  # Create 100 comments for better analysis
        "rating": [5, 3, 1, 4, 2, 5, 5, 4, 1, 4] * 10,
    }
    return pd.DataFrame(data)


def main():
    """Run the basic usage example."""
    print("=" * 60)
    print("Comment Analyzer - Basic Usage Example")
    print("=" * 60)

    # Step 1: Create or load data
    print("\n[Step 1] Creating sample data...")
    df = create_sample_data()
    print(f"Created {len(df)} sample comments")
    print(f"Columns: {list(df.columns)}")

    # Step 2: Initialize pipeline with default configuration
    print("\n[Step 2] Initializing pipeline...")
    pipeline = CommentPipeline()
    print("Pipeline initialized with default configuration")

    # Step 3: Run the analysis pipeline
    print("\n[Step 3] Running analysis pipeline...")
    print("This may take a moment...\n")
    results = pipeline.run(df, text_column="comment")

    # Step 4: Display results
    print("\n[Step 4] Analysis Results:")
    print("-" * 60)

    # Sentiment distribution
    print("\n1. Sentiment Distribution:")
    for label, count in results.sentiment_distribution.items():
        pct = count / len(df) * 100
        bar = "█" * int(pct / 2)
        print(f"   {label:10s}: {count:3d} ({pct:5.1f}%) {bar}")

    # Top keywords
    print("\n2. Top 10 Keywords:")
    for i, (word, score) in enumerate(results.top_keywords[:10], 1):
        print(f"   {i:2d}. {word:10s} (score: {score:.4f})")

    # Topics
    print("\n3. Discovered Topics:")
    for topic in results.topics:
        words = [w for w, _ in topic["words"][:5]]
        print(f"   Topic {topic['id']}: {', '.join(words)}")

    # Sample of processed data
    print("\n4. Sample Processed Data:")
    print("-" * 60)
    sample = results.processed_data[["cleaned_text", "sentiment"]].head(3)
    for idx, row in sample.iterrows():
        print(f"\n   Original: {row['cleaned_text'][:50]}...")
        print(f"   Sentiment: {row['sentiment']}")

    # Step 5: Save results
    print("\n[Step 5] Saving results...")
    # results.save("output/basic_example/")
    # print("Results saved to: output/basic_example/")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
