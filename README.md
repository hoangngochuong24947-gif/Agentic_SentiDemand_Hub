# Comment Analyzer

<p align="center">
  <strong>A generic, reusable NLP analysis toolkit for e-commerce comments and reviews</strong>
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#examples">Examples</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## Overview

**Comment Analyzer** is a powerful, modular Python toolkit designed for analyzing e-commerce comments and reviews. Originally inspired by brand-specific analysis workflows, it has been redesigned as a generic, configurable, and extensible framework that works with any product or platform.

### Key Features

- **📊 Data Preprocessing**: Text cleaning, Chinese segmentation (jieba), stopword filtering
- **😊 Sentiment Analysis**: Multi-model classification (Naive Bayes, SVM, Logistic Regression)
- **🔍 Topic Modeling**: TF-IDF keyword extraction and LDA topic discovery
- **💡 Demand Insights**: Demand intensity calculation and co-occurrence analysis
- **⚙️ Fully Configurable**: YAML-based configuration for all parameters
- **🔌 Platform Agnostic**: Works with JD, Taobao, Bilibili, or any CSV data
- **🧪 Well Tested**: Comprehensive test suite with >80% coverage

## Installation

### From PyPI (Recommended)

```bash
pip install comment-analyzer
```

### From Source

```bash
git clone https://github.com/yourusername/comment-analyzer.git
cd comment-analyzer
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/yourusername/comment-analyzer.git
cd comment-analyzer
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```python
from comment_analyzer import CommentPipeline

# Initialize pipeline with default configuration
pipeline = CommentPipeline()

# Load your data (supports JD, Taobao, generic CSV)
df = pipeline.load_data("path/to/comments.csv")

# Run complete analysis pipeline
results = pipeline.run(df)

# Access results
print(results.sentiment_distribution)
print(results.top_keywords)
print(results.topics)
```

### Using Custom Configuration

```python
from comment_analyzer import CommentPipeline, Config

# Load custom configuration
config = Config.from_yaml("path/to/custom_config.yaml")

# Or create configuration programmatically
config = Config()
config.sentiment.models.svm.enabled = True
config.sentiment.models.svm.C = 2.0

# Initialize pipeline with custom config
pipeline = CommentPipeline(config=config)
results = pipeline.run(df)
```

### Step-by-Step Processing

```python
from comment_analyzer.preprocessing import TextCleaner, JiebaSegmenter, StopwordFilter
from comment_analyzer.sentiment import SentimentLabeler, TFIDFVectorizer, Classifier

# Preprocessing
cleaner = TextCleaner()
segmenter = JiebaSegmenter()
filter_ = StopwordFilter()

# Clean and segment text
df['cleaned'] = df['comment'].apply(cleaner.clean)
df['segmented'] = df['cleaned'].apply(segmenter.segment)
df['filtered'] = df['segmented'].apply(filter_.filter)

# Sentiment analysis
labeler = SentimentLabeler()
df['sentiment'] = labeler.label(df['comment'])

# Train classifier
vectorizer = TFIDFVectorizer()
X = vectorizer.fit_transform(df['filtered'])
y = df['sentiment']

classifier = Classifier('svm')
classifier.train(X, y)
predictions = classifier.predict(X)
```

## Documentation

- [API Documentation](docs/API.md) - Detailed API reference
- [Architecture Overview](docs/ARCHITECTURE.md) - System design and data flow
- [Tutorial](docs/TUTORIAL.md) - Step-by-step guide from beginner to advanced

## Configuration

Comment Analyzer uses YAML-based configuration. See [config/default.yaml](config/default.yaml) for all available options.

### Key Configuration Sections

| Section | Description |
|---------|-------------|
| `data` | Platform detection, column mapping |
| `preprocessing` | Text cleaning, segmentation, stopwords |
| `sentiment` | Labeling methods, model parameters |
| `topic` | LDA settings, keyword extraction |
| `demand` | Demand intensity and correlation settings |

## Examples

Check the [examples/](examples/) directory for:

- `basic_usage.py` - Complete basic workflow
- `custom_config.py` - Advanced configuration examples
- `jd_analysis.py` - JD.com specific analysis
- `cross_platform.py` - Multi-platform comparison

## Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Generic CSV | ✅ Supported | Auto-detects text columns |
| JD.com | ✅ Supported | Optimized for JD format |
| Taobao/Tmall | ✅ Supported | Optimized for Taobao format |
| Bilibili | ✅ Supported | Optimized for B站 format |
| Custom | ✅ Supported | Define custom column mappings |

## Project Structure

```
comment-analyzer/
├── config/                    # Configuration files
│   ├── default.yaml          # Default configuration
│   ├── stopwords.txt         # Chinese stopwords
│   └── demand_keywords.json  # Demand analysis keywords
├── src/comment_analyzer/     # Main package
│   ├── core/                 # Core components
│   ├── preprocessing/        # Text preprocessing
│   ├── sentiment/            # Sentiment analysis
│   ├── topic/                # Topic modeling
│   └── demand/               # Demand insights
├── tests/                    # Test suite
├── examples/                 # Usage examples
└── docs/                     # Documentation
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/comment_analyzer

# Run specific test file
pytest tests/test_sentiment.py
```

### Code Style

```bash
# Format code
black src tests

# Type checking
mypy src

# Linting
flake8 src tests
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [jieba](https://github.com/fxsjy/jieba) - Chinese text segmentation
- [SnowNLP](https://github.com/isnowfy/snownlp) - Chinese sentiment analysis
- [Gensim](https://radimrehurek.com/gensim/) - Topic modeling
- [scikit-learn](https://scikit-learn.org/) - Machine learning

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

<p align="center">
  Made with ❤️ for the NLP community
</p>

---

## 中文简介

**Comment Analyzer** 是一个通用、可复用的电商评论 NLP 分析工具包。

### 主要特性

- **📊 数据预处理**: 文本清洗、结巴分词、停用词过滤
- **😊 情感分析**: 多模型情感分类（朴素贝叶斯、SVM、逻辑回归）
- **🔍 主题建模**: TF-IDF 关键词提取和 LDA 主题发现
- **💡 需求洞察**: 需求强度计算和共现分析
- **⚙️ 完全可配置**: 基于 YAML 的配置管理
- **🔌 平台无关**: 支持京东、淘宝、B站或任意 CSV 数据

### 快速开始

```python
from comment_analyzer import CommentPipeline

# 初始化流水线
pipeline = CommentPipeline()

# 加载数据
df = pipeline.load_data("评论数据.csv")

# 运行完整分析
results = pipeline.run(df)

# 查看结果
print(results.sentiment_distribution)  # 情感分布
print(results.top_keywords)            # 关键词
print(results.topics)                  # 主题
```
