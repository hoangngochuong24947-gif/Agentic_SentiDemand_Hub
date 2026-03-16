# API Documentation

Complete API reference for the Comment Analyzer package.

## Table of Contents

- [Core Components](#core-components)
  - [Config](#config)
  - [CommentPipeline](#commentpipeline)
  - [PipelineResults](#pipelineresults)
- [Preprocessing](#preprocessing)
  - [TextCleaner](#textcleaner)
  - [JiebaSegmenter](#jiebasegmenter)
  - [StopwordFilter](#stopwordfilter)
- [Sentiment Analysis](#sentiment-analysis)
  - [SentimentLabeler](#sentimentlabeler)
  - [TFIDFVectorizer](#tfidfvectorizer)
  - [Classifier](#classifier)
- [Topic Modeling](#topic-modeling)
  - [KeywordExtractor](#keywordextractor)
  - [LDAModel](#ldamodel)
- [Demand Analysis](#demand-analysis)
  - [DemandIntensityCalculator](#demandintensitycalculator)
  - [DemandCorrelationAnalyzer](#demandcorrelationanalyzer)

---

## Core Components

### Config

Configuration management for the comment analysis pipeline.

```python
from comment_analyzer import Config

# Load from YAML
config = Config.from_yaml("config/default.yaml")

# Access configuration values
platform = config.data.platform
max_features = config.sentiment.tfidf.max_features

# Get values with dot notation
value = config.get("sentiment.models.svm.C", default=1.0)

# Set values programmatically
config.set("sentiment.models.svm.C", 2.0)
```

#### Methods

##### `from_yaml(path)`

Load configuration from a YAML file.

**Parameters:**
- `path` (str | Path): Path to YAML configuration file

**Returns:** Config instance

**Raises:**
- `FileNotFoundError`: If file does not exist
- `yaml.YAMLError`: If file is not valid YAML

##### `to_yaml(path)`

Save configuration to a YAML file.

**Parameters:**
- `path` (str | Path): Path to save configuration file

##### `get(key, default=None)`

Get a configuration value using dot notation.

**Parameters:**
- `key` (str): Dot-separated key path (e.g., "sentiment.tfidf.max_features")
- `default`: Default value if key not found

**Returns:** Configuration value or default

##### `set(key, value)`

Set a configuration value using dot notation.

**Parameters:**
- `key` (str): Dot-separated key path
- `value`: Value to set

---

### CommentPipeline

Main pipeline orchestrator for comment analysis.

```python
from comment_analyzer import CommentPipeline, Config

# Basic usage
pipeline = CommentPipeline()
df = pipeline.load_data("comments.csv")
results = pipeline.run(df)

# With custom configuration
config = Config.from_yaml("custom_config.yaml")
pipeline = CommentPipeline(config)
results = pipeline.run(df, text_column="review_text")

# Save results
results.save("output/")
```

#### Methods

##### `__init__(config=None)`

Initialize the pipeline.

**Parameters:**
- `config` (Config, optional): Configuration object. If None, uses default configuration.

##### `load_data(path, platform=None, encoding="utf-8", **kwargs)`

Load comment data from file.

**Parameters:**
- `path` (str | Path): Path to data file (CSV, Excel, JSON)
- `platform` (str, optional): Platform type ("jd", "taobao", "bilibili", "generic")
- `encoding` (str): File encoding (default: "utf-8")
- `**kwargs`: Additional arguments passed to pandas read function

**Returns:** pandas.DataFrame with loaded data

**Supported Platforms:**
| Platform | Description |
|----------|-------------|
| `generic` | Auto-detects text columns |
| `jd` | JD.com format |
| `taobao` | Taobao/Tmall format |
| `bilibili` | Bilibili format |

##### `detect_text_column(df)`

Automatically detect the text content column.

**Parameters:**
- `df` (pandas.DataFrame): Input dataframe

**Returns:** str - Name of detected text column

**Raises:**
- `ValueError`: If no suitable text column is found

##### `run(df, text_column=None, verbose=True)`

Run the complete analysis pipeline.

**Parameters:**
- `df` (pandas.DataFrame): Input dataframe with comments
- `text_column` (str, optional): Name of text column. If None, auto-detects.
- `verbose` (bool): Whether to show progress information

**Returns:** [PipelineResults](#pipelineresults)

---

### PipelineResults

Container for pipeline analysis results.

```python
# Access results
results.sentiment_distribution  # {'positive': 100, 'negative': 50}
results.top_keywords           # [('word', 0.5234), ...]
results.topics                 # [{'id': 0, 'words': [...], 'weight': 0.3}, ...]

# Generate summary
print(results.summary())

# Save to disk
results.save("output_directory/")
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `original_data` | pd.DataFrame | Original input dataframe |
| `processed_data` | pd.DataFrame | Processed dataframe with all transformations |
| `sentiment_distribution` | dict | Sentiment label counts |
| `sentiment_models` | dict | Model names to ModelResults |
| `top_keywords` | list | (word, score) tuples |
| `topics` | list | Topic dictionaries |
| `demand_intensity` | pd.DataFrame | Demand category intensities |
| `demand_correlation` | pd.DataFrame | Demand correlation matrix |

#### Methods

##### `summary()`

Generate a text summary of the analysis results.

**Returns:** str - Formatted summary

##### `save(output_dir)`

Save all results to the specified directory.

**Parameters:**
- `output_dir` (str | Path): Directory path where results will be saved

---

## Preprocessing

### TextCleaner

Text cleaner for preprocessing comments and reviews.

```python
from comment_analyzer.preprocessing import TextCleaner

cleaner = TextCleaner(
    remove_urls=True,
    remove_emails=True,
    remove_html=True,
    remove_extra_spaces=True,
    normalize_whitespace=True,
)

text = "Check https://example.com <b>great</b> product!!!"
cleaned = cleaner.clean(text)
# Result: "Check great product!!!"
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `remove_urls` | bool | True | Remove URLs from text |
| `remove_emails` | bool | True | Remove email addresses |
| `remove_html` | bool | True | Strip HTML tags |
| `remove_extra_spaces` | bool | True | Collapse multiple spaces |
| `normalize_whitespace` | bool | True | Normalize whitespace characters |

#### Methods

##### `clean(text)`

Clean the input text.

**Parameters:**
- `text` (str | None): Input text to clean

**Returns:** str - Cleaned text

##### `clean_batch(texts)`

Clean a batch of texts.

**Parameters:**
- `texts` (list): List of texts to clean

**Returns:** list - List of cleaned texts

---

### JiebaSegmenter

Chinese text segmenter using jieba.

```python
from comment_analyzer.preprocessing import JiebaSegmenter

# Precise mode (default)
segmenter = JiebaSegmenter(mode='precise')
words = segmenter.segment("产品质量很好")
# Result: ['产品', '质量', '很', '好']

# With POS tagging
pos_tags = segmenter.segment_with_pos("产品质量很好")
# Result: [('产品', 'n'), ('质量', 'n'), ('很', 'd'), ('好', 'a')]

# Extract nouns only
nouns = segmenter.extract_nouns("产品质量很好")
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mode` | str | 'precise' | Segmentation mode: 'precise', 'full', 'search' |
| `custom_dict_path` | str | None | Path to custom dictionary file |

**Modes:**
- `precise`: Accurate segmentation, suitable for text analysis
- `full`: All possible words, high recall
- `search`: Search engine mode with long word re-segmentation

#### Methods

##### `segment(text)`

Segment text into words.

**Parameters:**
- `text` (str): Input text to segment

**Returns:** list - List of segmented words

##### `segment_with_pos(text)`

Segment text with part-of-speech tagging.

**Parameters:**
- `text` (str): Input text

**Returns:** list - List of (word, pos_tag) tuples

##### `extract_nouns(text)`

Extract nouns from text.

**Parameters:**
- `text` (str): Input text

**Returns:** list - List of nouns

##### `load_custom_dict(path)`

Load a custom dictionary.

**Parameters:**
- `path` (str): Path to dictionary file

---

### StopwordFilter

Stopword filter for text processing.

```python
from comment_analyzer.preprocessing import StopwordFilter

# With default stopwords
filter = StopwordFilter()
words = filter.filter(['的', '产品', '是', '好'])
# Result: ['产品', '好']

# With custom stopwords
filter = StopwordFilter(extra_words=['非常'])
words = filter.filter(['非常', '好', '产品'])
# Result: ['好', '产品']

# Check if word is stopword
is_stop = filter.is_stopword('的')  # True
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stopwords_path` | str | None | Path to stopwords file |
| `extra_words` | list | None | Additional words to filter |
| `min_word_length` | int | 1 | Minimum word length to keep |

#### Methods

##### `filter(words)`

Filter stopwords from word list.

**Parameters:**
- `words` (list): List of words to filter

**Returns:** list - Filtered list of words

##### `add_stopwords(words)`

Add words to the stopword list.

**Parameters:**
- `words` (list): Words to add

---

## Sentiment Analysis

### SentimentLabeler

Sentiment labeler for Chinese text.

```python
from comment_analyzer.sentiment import SentimentLabeler

labeler = SentimentLabeler(
    method='snownlp',
    threshold_positive=0.6,
    threshold_negative=0.4,
)

# Label single text
sentiment = labeler.label("这个产品非常好！")
# Result: 'positive'

# Get raw score
score = labeler.get_score("质量一般")
# Result: 0.5 (neutral)

# Batch processing
sentiments = labeler.label_batch(["很好", "很差", "一般"])
# Result: ['positive', 'negative', 'neutral']

# From ratings
sentiments = labeler.label_from_rating([5.0, 3.0, 1.0], max_rating=5.0)
# Result: ['positive', 'neutral', 'negative']
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `method` | str | 'snownlp' | Labeling method: 'snownlp', 'rating' |
| `threshold_positive` | float | 0.6 | Score threshold for positive |
| `threshold_negative` | float | 0.4 | Score threshold for negative |

#### Methods

##### `label(text)`

Label text with sentiment category.

**Parameters:**
- `text` (str): Input text

**Returns:** str - Sentiment label ('positive', 'negative', 'neutral')

##### `get_score(text)`

Get sentiment score for text.

**Parameters:**
- `text` (str): Input text

**Returns:** float - Score between 0 and 1

---

### TFIDFVectorizer

TF-IDF vectorizer for text classification.

```python
from comment_analyzer.sentiment import TFIDFVectorizer

vectorizer = TFIDFVectorizer(
    max_features=5000,
    min_df=2,
    max_df=0.95,
    ngram_range=(1, 2),
)

texts = ["产品很好", "服务不错", "质量一般"]
X = vectorizer.fit_transform(texts)

# Get feature names
features = vectorizer.get_feature_names()

# Get IDF scores
idf_scores = vectorizer.get_idf_scores()

# Transform new texts
X_new = vectorizer.transform(["质量很好"])
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_features` | int | 5000 | Maximum number of features |
| `min_df` | int/float | 2 | Minimum document frequency |
| `max_df` | int/float | 0.95 | Maximum document frequency |
| `ngram_range` | tuple | (1, 2) | Range of n-grams (min_n, max_n) |

#### Methods

##### `fit(texts)`

Fit the vectorizer to the texts.

**Parameters:**
- `texts` (list): List of texts to fit on

**Returns:** self

##### `transform(texts)`

Transform texts to TF-IDF matrix.

**Parameters:**
- `texts` (list): List of texts to transform

**Returns:** sparse matrix - TF-IDF features

##### `fit_transform(texts)`

Fit and transform in one step.

**Parameters:**
- `texts` (list): List of texts

**Returns:** sparse matrix - TF-IDF features

---

### Classifier

Machine learning classifier for sentiment analysis.

```python
from comment_analyzer.sentiment import Classifier

# Train Naive Bayes
clf = Classifier('naive_bayes', alpha=1.0)
results = clf.train(X_train, y_train)

# Train SVM
clf = Classifier('svm', C=1.0, kernel='linear')
results = clf.train(X_train, y_train)

# Train Logistic Regression
clf = Classifier('logistic_regression', C=1.0, max_iter=1000)
results = clf.train(X_train, y_train)

# Make predictions
predictions = clf.predict(X_test)

# Get feature importance
importance = clf.get_feature_importance(feature_names)
```

#### Supported Models

- `naive_bayes`: Multinomial Naive Bayes
- `svm`: Linear Support Vector Machine
- `logistic_regression`: Logistic Regression

#### Methods

##### `train(X, y, test_size=0.2, cross_validate=False, cv=5)`

Train the classifier.

**Parameters:**
- `X`: Feature matrix
- `y`: Target labels
- `test_size` (float): Fraction for testing (default: 0.2)
- `cross_validate` (bool): Perform cross-validation
- `cv` (int): Number of CV folds

**Returns:** ModelResults

##### `predict(X)`

Make predictions on new data.

**Parameters:**
- `X`: Feature matrix

**Returns:** array - Predicted labels

---

## Topic Modeling

### KeywordExtractor

TF-IDF based keyword extractor.

```python
from comment_analyzer.topic import KeywordExtractor

extractor = KeywordExtractor(
    method='tfidf',
    top_k=20,
)

texts = ["产品质量很好", "服务不错"] * 10
keywords = extractor.extract(texts)
# Result: [('质量', 0.5234), ('服务', 0.4892), ...]

# Keywords for specific document
doc_keywords = extractor.extract_for_document("产品质量")
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `method` | str | 'tfidf' | Extraction method |
| `top_k` | int | 20 | Number of top keywords |
| `max_features` | int | 10000 | Maximum features for TF-IDF |

---

### LDAModel

Latent Dirichlet Allocation (LDA) topic model.

```python
from comment_analyzer.topic import LDAModel

lda = LDAModel(
    num_topics=5,
    passes=15,
    iterations=100,
)

documents = [
    ['产品', '质量', '很好'],
    ['服务', '态度', '不错'],
    ['物流', '速度', '快'],
]

# Fit and get topics
topics = lda.fit_transform(documents)

# Get topic words
for topic in topics:
    print(f"Topic {topic['id']}: {topic['words'][:5]}")

# Get document topics
doc_topics = lda.get_document_topics(['质量', '很好'])
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_topics` | int | 5 | Number of topics to discover |
| `passes` | int | 15 | Number of training passes |
| `iterations` | int | 100 | Maximum iterations |
| `alpha` | str/float | 'auto' | Document-topic prior |
| `eta` | str/float | 'auto' | Topic-word prior |
| `random_state` | int | 42 | Random seed |

#### Methods

##### `fit(documents)`

Fit the LDA model.

**Parameters:**
- `documents` (list): List of documents (each is a list of words)

##### `get_topics()`

Get discovered topics.

**Returns:** list - Topic dictionaries with 'id', 'words', 'weight'

##### `get_coherence_score(documents, coherence='c_v')`

Calculate topic coherence score.

**Parameters:**
- `documents` (list): List of documents
- `coherence` (str): Coherence measure

**Returns:** float - Coherence score

---

## Demand Analysis

### DemandIntensityCalculator

Calculate demand intensity for different categories.

```python
from comment_analyzer.demand import DemandIntensityCalculator

calculator = DemandIntensityCalculator(
    keywords_path="config/demand_keywords.json",
    method='tfidf_weighted',
    normalization='minmax',
)

documents = [
    ['味道', '不错', '价格', '便宜'],
    ['服务', '态度', '好', '质量', '不错'],
]

# Calculate intensity
intensity = calculator.calculate(documents)
print(intensity)
#        taste  price  service
#    0   0.5    0.5      0.0
#    1   0.0    0.0      0.7

# Get category distribution
distribution = calculator.get_category_distribution(intensity)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `keywords_path` | str | None | Path to keywords JSON file |
| `method` | str | 'tfidf_weighted' | Calculation method |
| `normalization` | str | 'minmax' | Normalization method |

**Methods:**
- `simple`: Simple keyword count
- `tfidf_weighted`: TF-IDF weighted scores

**Normalization:**
- `minmax`: Min-Max to [0, 1]
- `standard`: Z-score normalization
- `none`: No normalization

---

### DemandCorrelationAnalyzer

Analyze correlations between demand categories.

```python
from comment_analyzer.demand import DemandCorrelationAnalyzer

analyzer = DemandCorrelationAnalyzer(
    method='cooccurrence',
    min_cooccurrence=2,
)

keywords = {
    'taste': ['味道', '口味', '好吃'],
    'price': ['价格', '便宜', '贵'],
    'service': ['服务', '态度'],
}

documents = [
    ['味道', '不错', '价格', '便宜'],
    ['服务', '态度', '好'],
]

correlation = analyzer.analyze(documents, keywords)
print(correlation)

# Find correlated pairs
pairs = analyzer.find_correlated_pairs(correlation, threshold=0.3)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `method` | str | 'cooccurrence' | Correlation method |
| `min_cooccurrence` | int | 2 | Minimum co-occurrence count |
| `window_size` | int | 50 | Window size for co-occurrence |

---

## Configuration File Reference

See [config/default.yaml](../config/default.yaml) for complete example.

```yaml
data:
  platform: generic
  text_column_keywords: [content, comment, review, 评论]

preprocessing:
  clean:
    remove_urls: true
    remove_emails: true
  segmentation:
    mode: precise
  stopwords:
    use_default: true

sentiment:
  labeling_method: snownlp
  tfidf:
    max_features: 5000
  models:
    naive_bayes:
      enabled: true
    svm:
      enabled: true
      C: 1.0

topic:
  lda:
    num_topics: 5
    passes: 15

demand:
  intensity:
    method: tfidf_weighted
  correlation:
    method: cooccurrence
```
