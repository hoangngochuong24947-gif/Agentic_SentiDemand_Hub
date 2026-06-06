# Architecture Documentation

This document describes the system architecture, module relationships, and data flow of the Comment Analyzer project.

## Overview

Comment Analyzer is designed as a modular, pipeline-based system for analyzing e-commerce comments. The architecture follows these principles:

1. **Modularity**: Each component is independent and replaceable
2. **Configuration-driven**: All behavior controlled via YAML configuration
3. **Extensibility**: Easy to add new preprocessing methods, models, or analysis types
4. **Reusability**: Generic design works with any e-commerce platform

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CommentPipeline                                    │
│                    (Main Orchestrator)                                       │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┬───────────────┐
       ▼               ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│Preprocessing│ │   Sentiment │ │    Topic    │ │   Demand    │
│   Module    │ │   Module    │ │   Module    │ │   Module    │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

## Module Structure

### 1. Core Module (`core/`)

#### Config (`core/config.py`)
- **Purpose**: Centralized configuration management
- **Features**:
  - YAML-based configuration loading
  - Dot notation access (`config.sentiment.models.svm.C`)
  - Programmatic configuration modification
  - Default configuration fallbacks

#### CommentPipeline (`core/pipeline.py`)
- **Purpose**: Main orchestrator for the analysis workflow
- **Responsibilities**:
  - Data loading (CSV, Excel, JSON)
  - Column auto-detection
  - Workflow orchestration
  - Results compilation

#### PipelineResults (`core/pipeline.py`)
- **Purpose**: Container for all analysis results
- **Features**:
  - Structured result storage
  - Summary generation
  - Export capabilities

### 2. Preprocessing Module (`preprocessing/`)

```
Raw Text → TextCleaner → JiebaSegmenter → StopwordFilter → Clean Tokens
```

#### TextCleaner (`preprocessing/cleaner.py`)
- URL removal
- Email removal
- HTML tag stripping
- Whitespace normalization

#### JiebaSegmenter (`preprocessing/segmenter.py`)
- Chinese word segmentation
- Part-of-speech tagging
- Noun/verb/adjective extraction
- Custom dictionary support

#### StopwordFilter (`preprocessing/filter.py`)
- Stopword removal
- Configurable stopword lists
- Minimum word length filtering

### 3. Sentiment Module (`sentiment/`)

```
Clean Text → SentimentLabeler → TFIDFVectorizer → Classifier → Predictions
```

#### SentimentLabeler (`sentiment/labeler.py`)
- SnowNLP-based sentiment scoring
- Rating-based labeling
- Threshold-based classification (positive/neutral/negative)

#### TFIDFVectorizer (`sentiment/vectorizer.py`)
- Text vectorization using TF-IDF
- N-gram support
- Feature selection

#### Classifier (`sentiment/classifier.py`)
- Multiple model support (Naive Bayes, SVM, Logistic Regression)
- Cross-validation
- Feature importance extraction

### 4. Topic Module (`topic/`)

```
Tokens → KeywordExtractor → LDAModel → Topics
```

#### KeywordExtractor (`topic/keywords.py`)
- TF-IDF based keyword extraction
- Document-level keyword ranking

#### LDAModel (`topic/lda.py`)
- Latent Dirichlet Allocation
- Topic discovery
- Coherence scoring

### 5. Demand Module (`demand/`)

```
Tokens → DemandIntensityCalculator → DemandCorrelationAnalyzer → Insights
```

#### DemandIntensityCalculator (`demand/intensity.py`)
- Category-based intensity scoring
- TF-IDF weighted calculation
- Normalization options

#### DemandCorrelationAnalyzer (`demand/correlation.py`)
- Co-occurrence analysis
- PMI calculation
- Demand clustering

## Data Flow

### Complete Pipeline Flow

```
┌─────────────┐
│  Input CSV  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐     ┌─────────────────┐
│  Data Loading   │────▶│ Column Detection│
└─────────────────┘     └─────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────┐
│                  Preprocessing Phase                  │
├─────────────┬─────────────┬──────────────────────────┤
│Text Cleaning│ Segmentation│   Stopword Filtering     │
└─────────────┴─────────────┴──────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────┐
│                Sentiment Analysis Phase               │
├─────────────────┬─────────────────┬──────────────────┤
│  Label Generation│ TF-IDF Vector   │  Model Training  │
└─────────────────┴─────────────────┴──────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────┐
│                Topic Modeling Phase                   │
├───────────────────────┬──────────────────────────────┤
│   Keyword Extraction  │        LDA Modeling          │
└───────────────────────┴──────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────┐
│                Demand Analysis Phase                  │
├───────────────────────┬──────────────────────────────┤
│   Intensity Calc      │    Correlation Analysis      │
└───────────────────────┴──────────────────────────────┘
                               │
                               ▼
┌─────────────────┐
│ PipelineResults │
└─────────────────┘
```

## Configuration System

### Configuration Hierarchy

```
Built-in Defaults  <──  YAML Config File  <──  Programmatic Overrides
```

### Configuration Sections

| Section | Purpose | Key Settings |
|---------|---------|--------------|
| `data` | Data loading | platform, column_keywords |
| `preprocessing` | Text cleaning | clean, segmentation, stopwords |
| `sentiment` | Sentiment analysis | labeling_method, models, tfidf |
| `topic` | Topic modeling | lda, keywords |
| `demand` | Demand analysis | intensity, correlation |

## Extension Points

### Adding a New Classifier

1. Create model wrapper class
2. Add configuration schema
3. Register in Classifier factory

```python
class MyCustomClassifier:
    def train(self, X, y):
        # Implementation
        pass

    def predict(self, X):
        # Implementation
        pass
```

### Adding a New Preprocessor

1. Implement preprocessing class
2. Add to pipeline initialization
3. Update configuration

### Adding a New Platform Support

1. Add platform mapping to `CommentPipeline.PLATFORM_MAPPINGS`
2. Define column name mappings

```python
PLATFORM_MAPPINGS = {
    "new_platform": {
        "content": ["comment", "review"],
        "rating": ["score", "stars"],
    }
}
```

## Testing Strategy

### Unit Tests
- Individual component testing
- Mock external dependencies

### Integration Tests
- Full pipeline testing
- End-to-end workflows

### Test Coverage
- Preprocessing: >90%
- Sentiment: >85%
- Topic: >85%
- Pipeline: >80%

## Performance Considerations

### Optimization Strategies

1. **Batch Processing**: All components support batch operations
2. **Lazy Loading**: Models loaded on demand
3. **Caching**: Vectorizers cache fitted state
4. **Parallelization**: Potential for parallel model training

### Memory Management

- Sparse matrices for TF-IDF
- Streaming for large datasets
- Optional intermediate result saving

## Deployment Considerations

### Installation Methods

1. **PyPI**: `pip install comment-analyzer`
2. **Source**: `pip install -e .`
3. **Docker**: Container with all dependencies

### Environment Requirements

- Python 3.8+
- 2GB+ RAM for large datasets
- Optional: GPU for deep learning extensions

## Future Enhancements

### Planned Features

1. **Deep Learning Models**: BERT-based sentiment analysis
2. **Real-time Processing**: Streaming analysis support
3. **Visualization**: Built-in chart generation
4. **API Server**: RESTful API for integration
5. **Web UI**: Browser-based interface

### Architecture Improvements

1. **Plugin System**: Dynamic model loading
2. **Distributed Processing**: Spark/Dask integration
3. **Model Registry**: Versioned model management
4. **A/B Testing**: Multiple model comparison
