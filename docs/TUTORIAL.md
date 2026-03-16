# Tutorial: Using Comment Analyzer

A comprehensive guide from basic usage to advanced techniques.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Basic Usage](#basic-usage)
4. [Configuration](#configuration)
5. [Working with Different Platforms](#working-with-different-platforms)
6. [Advanced Techniques](#advanced-techniques)
7. [Interpreting Results](#interpreting-results)
8. [Troubleshooting](#troubleshooting)

---

## Installation

### From PyPI

```bash
pip install comment-analyzer
```

### From Source

```bash
git clone https://github.com/yourusername/comment-analyzer.git
cd comment-analyzer
pip install -e .
```

### Verify Installation

```python
from comment_analyzer import CommentPipeline
print("Installation successful!")
```

---

## Quick Start

### Complete Example in 5 Lines

```python
from comment_analyzer import CommentPipeline

pipeline = CommentPipeline()
df = pipeline.load_data("comments.csv")
results = pipeline.run(df)
print(results.summary())
```

---

## Basic Usage

### Loading Data

```python
from comment_analyzer import CommentPipeline

pipeline = CommentPipeline()

# Load CSV
df = pipeline.load_data("comments.csv")

# Load with platform auto-detection
df = pipeline.load_data("jd_comments.csv", platform="jd")

# Load Excel
df = pipeline.load_data("comments.xlsx")

# Load JSON
df = pipeline.load_data("comments.json")
```

### Running Analysis

```python
# Basic run
results = pipeline.run(df)

# Specify text column explicitly
results = pipeline.run(df, text_column="review_content")

# Quiet mode (no progress output)
results = pipeline.run(df, verbose=False)
```

### Accessing Results

```python
# Sentiment distribution
print(results.sentiment_distribution)
# {'positive': 150, 'negative': 50, 'neutral': 30}

# Top keywords
for word, score in results.top_keywords[:10]:
    print(f"{word}: {score:.4f}")

# Topics
for topic in results.topics:
    words = [w for w, _ in topic['words'][:5]]
    print(f"Topic {topic['id']}: {', '.join(words)}")

# Demand intensity
print(results.demand_intensity.head())

# Demand correlation
print(results.demand_correlation)
```

### Saving Results

```python
# Save all results to directory
results.save("output/")

# This creates:
# - output/processed_data.csv
# - output/sentiment_distribution.csv
# - output/top_keywords.csv
# - output/topics.csv
# - output/demand_intensity.csv
# - output/demand_correlation.csv
```

---

## Configuration

### Using Default Configuration

```python
from comment_analyzer import CommentPipeline

# Uses config/default.yaml
pipeline = CommentPipeline()
```

### Loading Custom Configuration

```python
from comment_analyzer import Config, CommentPipeline

# Load from file
config = Config.from_yaml("my_config.yaml")
pipeline = CommentPipeline(config)
```

### Programmatic Configuration

```python
from comment_analyzer import Config, CommentPipeline

config = Config()

# Modify sentiment settings
config.sentiment.models.svm.C = 2.0
config.sentiment.models.svm.enabled = True

# Modify TF-IDF settings
config.sentiment.tfidf.max_features = 10000
config.sentiment.tfidf.ngram_range = [1, 3]

# Modify LDA settings
config.topic.lda.num_topics = 10

pipeline = CommentPipeline(config)
```

### Configuration File Example

Create `my_config.yaml`:

```yaml
data:
  platform: generic
  text_column_keywords:
    - content
    - comment
    - review
    - 评论
    - 评价

preprocessing:
  clean:
    remove_urls: true
    remove_emails: true
    remove_html: true
  segmentation:
    mode: precise
  stopwords:
    use_default: true
    extra_words:
      - 商品
      - 店铺
      - 卖家

sentiment:
  labeling_method: snownlp
  snownlp:
    threshold_positive: 0.6
    threshold_negative: 0.4
  tfidf:
    max_features: 5000
    min_df: 2
    max_df: 0.95
  models:
    naive_bayes:
      enabled: true
      alpha: 1.0
    svm:
      enabled: true
      C: 1.0
    logistic_regression:
      enabled: false

topic:
  keywords:
    method: tfidf
    top_k: 30
  lda:
    num_topics: 5
    passes: 15
    iterations: 100

demand:
  intensity:
    method: tfidf_weighted
    normalization: minmax
  correlation:
    method: cooccurrence
    min_cooccurrence: 3
```

---

## Working with Different Platforms

### JD.com Data

```python
from comment_analyzer import CommentPipeline

pipeline = CommentPipeline()

# Platform auto-detection for column mapping
df = pipeline.load_data("jd_comments.csv", platform="jd")

# JD-specific columns:
# - content / 评论内容 → standardized to "content"
# - score / 评分 → standardized to "rating"
# - creationTime / 时间 → standardized to "date"

results = pipeline.run(df)
```

### Taobao/Tmall Data

```python
# Taobao platform mapping
df = pipeline.load_data("taobao_comments.csv", platform="taobao")

# Taobao-specific columns:
# - rateContent / 评论内容 → "content"
# - rate / 评分 → "rating"
# - rateDate / 时间 → "date"
```

### Bilibili Comments

```python
# Bilibili platform mapping
df = pipeline.load_data("bilibili_comments.csv", platform="bilibili")

# Bilibili-specific columns:
# - content / message / 评论 → "content"
# - ctime / 时间 → "date"
```

### Generic CSV

```python
# Works with any CSV format
# Auto-detects text column based on column name keywords

df = pipeline.load_data("my_data.csv", platform="generic")

# Or specify text column explicitly
results = pipeline.run(df, text_column="my_comment_column")
```

---

## Advanced Techniques

### Step-by-Step Processing

```python
from comment_analyzer.preprocessing import TextCleaner, JiebaSegmenter, StopwordFilter
from comment_analyzer.sentiment import SentimentLabeler

# Custom preprocessing chain
cleaner = TextCleaner(remove_urls=True)
segmenter = JiebaSegmenter(mode='search')
filter = StopwordFilter(min_word_length=2)
labeler = SentimentLabeler()

# Process step by step
df['cleaned'] = df['comment'].apply(cleaner.clean)
df['segmented'] = df['cleaned'].apply(segmenter.segment)
df['filtered'] = df['segmented'].apply(filter.filter)
df['sentiment'] = df['cleaned'].apply(labeler.label)

# Join tokens for vectorization
df['processed'] = df['filtered'].apply(lambda x: ' '.join(x))
```

### Custom Stopwords

```python
from comment_analyzer.preprocessing import StopwordFilter

# Load default + custom stopwords
filter = StopwordFilter(
    extra_words=['品牌名', '店铺名', '特定词']
)

# Save custom stopwords list
filter.save_stopwords("my_stopwords.txt")

# Use custom stopwords file
filter = StopwordFilter(stopwords_path="my_stopwords.txt")
```

### Custom Dictionary for Segmentation

```python
from comment_analyzer.preprocessing import JiebaSegmenter

# Load custom dictionary
segmenter = JiebaSegmenter(
    custom_dict_path="custom_dict.txt"
)

# Or add words programmatically
segmenter.add_word("新词", freq=1000, tag='n')
```

### Training Custom Classifier

```python
from comment_analyzer.sentiment import TFIDFVectorizer, Classifier

# Prepare data
vectorizer = TFIDFVectorizer(max_features=5000)
X = vectorizer.fit_transform(df['processed_text'])
y = df['sentiment_label']

# Train classifier
clf = Classifier('svm', C=1.5, kernel='linear')
results = clf.train(X, y, cross_validate=True, cv=5)

print(results.summary())
print(results.classification_report)

# Save model
clf.save("my_model.pkl")

# Load model
clf.load("my_model.pkl")
predictions = clf.predict(X_test)
```

### Topic Modeling Tuning

```python
from comment_analyzer.topic import LDAModel

# Try different numbers of topics
for num_topics in [3, 5, 7, 10]:
    lda = LDAModel(
        num_topics=num_topics,
        passes=20,
        iterations=200,
    )
    topics = lda.fit_transform(documents)
    coherence = lda.get_coherence_score(documents)
    print(f"Topics: {num_topics}, Coherence: {coherence:.4f}")
```

### Custom Demand Categories

Create `my_demand_keywords.json`:

```json
{
  "categories": {
    "appearance": {
      "name": "外观",
      "name_en": "Appearance",
      "keywords": ["外观", "颜值", "漂亮", "好看", "设计", "颜色"]
    },
    "usability": {
      "name": "易用性",
      "name_en": "Usability",
      "keywords": ["简单", "容易", "方便", "便捷", "好用", "操作"]
    }
  }
}
```

Use in pipeline:

```python
from comment_analyzer.demand import DemandIntensityCalculator

calculator = DemandIntensityCalculator(
    keywords_path="my_demand_keywords.json",
    method='tfidf_weighted'
)
```

---

## Interpreting Results

### Sentiment Distribution

```python
results = pipeline.run(df)

# View distribution
distribution = results.sentiment_distribution
total = sum(distribution.values())

for label, count in distribution.items():
    pct = count / total * 100
    print(f"{label}: {count} ({pct:.1f}%)")

# Typical healthy distribution:
# - Positive: 60-80%
# - Neutral: 10-30%
# - Negative: 5-20%
```

### Keywords Analysis

```python
# Top keywords indicate main discussion topics
for word, score in results.top_keywords[:20]:
    print(f"{word}: {score:.4f}")

# High TF-IDF scores indicate distinctive terms
# Low scores indicate common terms
```

### Topic Interpretation

```python
for topic in results.topics:
    topic_id = topic['id']
    weight = topic['weight']
    words = [w for w, _ in topic['words'][:10]]

    print(f"\nTopic {topic_id} (weight: {weight:.2%}):")
    print(f"  Words: {', '.join(words)}")

    # Interpret topics based on top words
    # Example:
    # Topic 0 (quality): 质量, 做工, 材料, 耐用
    # Topic 1 (service): 客服, 态度, 售后, 服务
    # Topic 2 (logistics): 物流, 快递, 发货, 速度
```

### Demand Intensity

```python
# Average intensity by category
avg_intensity = results.demand_intensity.mean()
print(avg_intensity.sort_values(ascending=False))

# Find documents with high demand for specific category
high_quality = results.demand_intensity['quality'].nlargest(10)
print("Documents with highest quality mentions:")
print(high_quality.index.tolist())
```

### Demand Correlation

```python
# Highly correlated demand pairs
correlation = results.demand_correlation

# Find strong correlations (>0.3)
for cat1 in correlation.columns:
    for cat2 in correlation.columns:
        if cat1 < cat2:  # Avoid duplicates
            corr = correlation.loc[cat1, cat2]
            if corr > 0.3:
                print(f"{cat1} ↔ {cat2}: {corr:.3f}")

# Interpretation:
# High correlation means demands often mentioned together
# Example: "price" ↔ "quality" means customers compare them
```

---

## Troubleshooting

### Common Issues

#### Issue: "Could not detect text column"

**Solution:**
```python
# Specify text column explicitly
results = pipeline.run(df, text_column="your_column_name")

# Or configure column detection
config = Config()
config.data.text_column_keywords.append("your_column_keyword")
```

#### Issue: "Not enough valid samples for model training"

**Solution:**
```python
# Ensure you have sufficient data
print(f"Total samples: {len(df)}")

# Check for empty processed text
print(f"Non-empty samples: {df['processed_text'].str.len().gt(0).sum()}")

# May need to adjust filtering
config = Config()
config.preprocessing.stopwords.extra_words = []  # Reduce filtering
```

#### Issue: Memory Error with Large Datasets

**Solution:**
```python
# Process in chunks
chunksize = 1000
for chunk in pd.read_csv("large_file.csv", chunksize=chunksize):
    results = pipeline.run(chunk)
    # Save intermediate results
    results.save(f"output/chunk_{i}/")
```

#### Issue: Poor Classification Accuracy

**Solution:**
```python
# Check class balance
print(df['sentiment'].value_counts())

# Enable sample balancing
config = Config()
config.sentiment.balance.enabled = True
config.sentiment.balance.method = 'oversample'  # or 'undersample'

# Try different models
config.sentiment.models.svm.enabled = True
config.sentiment.models.svm.C = 2.0
```

#### Issue: Chinese Characters Not Displaying

**Solution:**
```python
# Save with proper encoding
results.save("output/", encoding='utf-8-sig')  # UTF-8 with BOM for Excel

# Or convert manually
results.processed_data.to_csv(
    "output.csv",
    index=False,
    encoding='utf-8-sig'
)
```

### Performance Optimization

```python
# Disable verbose output for faster processing
results = pipeline.run(df, verbose=False)

# Reduce max features for faster training
config.sentiment.tfidf.max_features = 3000

# Use fewer LDA passes
config.topic.lda.passes = 10
```

### Getting Help

```python
# Check docstrings
help(CommentPipeline.run)

# Check configuration
print(config.to_yaml())

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Best Practices

### 1. Data Quality
- Clean your data before analysis
- Remove duplicates
- Handle missing values

### 2. Configuration Management
- Use version-controlled config files
- Document custom settings
- Test different configurations

### 3. Result Validation
- Always review a sample of results
- Compare with manual analysis
- Check for outliers

### 4. Iterative Improvement
- Start with default settings
- Adjust based on results
- Document what works

### 5. Scalability
- Process large datasets in chunks
- Cache intermediate results
- Use appropriate hardware

---

## Next Steps

- Explore [API Documentation](API.md) for detailed reference
- Read [Architecture Documentation](ARCHITECTURE.md) for implementation details
- Check examples in the `examples/` directory
- Contribute improvements on GitHub
