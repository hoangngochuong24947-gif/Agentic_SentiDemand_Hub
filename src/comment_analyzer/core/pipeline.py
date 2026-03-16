"""Pipeline orchestrator for comment analysis.

This module provides the main CommentPipeline class that orchestrates
the entire analysis workflow from data loading to result generation.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from tqdm import tqdm

from comment_analyzer.core.config import Config
from comment_analyzer.preprocessing.cleaner import TextCleaner
from comment_analyzer.preprocessing.segmenter import JiebaSegmenter
from comment_analyzer.preprocessing.filter import StopwordFilter
from comment_analyzer.sentiment.labeler import SentimentLabeler
from comment_analyzer.sentiment.vectorizer import TFIDFVectorizer
from comment_analyzer.sentiment.classifier import Classifier, ModelResults
from comment_analyzer.topic.keywords import KeywordExtractor
from comment_analyzer.topic.lda import LDAModel
from comment_analyzer.demand.intensity import DemandIntensityCalculator
from comment_analyzer.demand.correlation import DemandCorrelationAnalyzer


@dataclass
class PipelineResults:
    """Container for pipeline analysis results.

    Attributes:
        original_data: Original input dataframe
        processed_data: Processed dataframe with all transformations
        sentiment_distribution: Dict mapping sentiment labels to counts
        sentiment_models: Dict of model names to ModelResults
        top_keywords: List of (word, score) tuples
        topics: List of topic dictionaries with words and weights
        demand_intensity: DataFrame with demand category intensities
        demand_correlation: DataFrame with demand correlation matrix
        config: Configuration used for the analysis
    """

    original_data: pd.DataFrame = field(repr=False)
    processed_data: pd.DataFrame = field(repr=False)
    sentiment_distribution: Dict[str, int] = field(default_factory=dict)
    sentiment_models: Dict[str, ModelResults] = field(default_factory=dict, repr=False)
    top_keywords: List[Tuple[str, float]] = field(default_factory=list)
    topics: List[Dict[str, Any]] = field(default_factory=list)
    demand_intensity: Optional[pd.DataFrame] = None
    demand_correlation: Optional[pd.DataFrame] = None
    config: Optional[Config] = None

    def summary(self) -> str:
        """Generate a text summary of the analysis results."""
        lines = ["=" * 50]
        lines.append("Comment Analysis Summary")
        lines.append("=" * 50)
        lines.append(f"\nTotal comments: {len(self.original_data)}")

        if self.sentiment_distribution:
            lines.append("\n--- Sentiment Distribution ---")
            total = sum(self.sentiment_distribution.values())
            for label, count in sorted(self.sentiment_distribution.items()):
                pct = count / total * 100 if total > 0 else 0
                lines.append(f"  {label}: {count} ({pct:.1f}%)")

        if self.top_keywords:
            lines.append("\n--- Top Keywords ---")
            for word, score in self.top_keywords[:10]:
                lines.append(f"  {word}: {score:.4f}")

        if self.topics:
            lines.append("\n--- Topics ---")
            for i, topic in enumerate(self.topics[:5], 1):
                words = [w for w, _ in topic.get('words', [])[:5]]
                lines.append(f"  Topic {i}: {', '.join(words)}")

        if self.demand_intensity is not None:
            lines.append("\n--- Demand Intensity ---")
            for col in self.demand_intensity.columns:
                avg = self.demand_intensity[col].mean()
                lines.append(f"  {col}: {avg:.4f}")

        lines.append("\n" + "=" * 50)
        return "\n".join(lines)

    def save(self, output_dir: Union[str, Path]) -> None:
        """Save all results to the specified directory.

        Args:
            output_dir: Directory path where results will be saved.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save processed data
        self.processed_data.to_csv(
            output_dir / "processed_data.csv",
            index=False,
            encoding='utf-8-sig'
        )

        # Save sentiment distribution
        if self.sentiment_distribution:
            pd.Series(self.sentiment_distribution).to_csv(
                output_dir / "sentiment_distribution.csv",
                header=['count']
            )

        # Save model results
        for name, results in self.sentiment_models.items():
            if hasattr(results, 'classification_report'):
                with open(output_dir / f"model_report_{name}.txt", 'w') as f:
                    f.write(results.classification_report)

        # Save keywords
        if self.top_keywords:
            pd.DataFrame(self.top_keywords, columns=['word', 'score']).to_csv(
                output_dir / "top_keywords.csv",
                index=False
            )

        # Save topics
        if self.topics:
            topics_df = []
            for i, topic in enumerate(self.topics):
                for word, weight in topic.get('words', []):
                    topics_df.append({
                        'topic_id': i,
                        'word': word,
                        'weight': weight
                    })
            pd.DataFrame(topics_df).to_csv(
                output_dir / "topics.csv",
                index=False
            )

        # Save demand analysis
        if self.demand_intensity is not None:
            self.demand_intensity.to_csv(output_dir / "demand_intensity.csv")
        if self.demand_correlation is not None:
            self.demand_correlation.to_csv(output_dir / "demand_correlation.csv")


class CommentPipeline:
    """Main pipeline for comment analysis.

    This class orchestrates the entire analysis workflow, from data loading
to generating insights. It uses a configuration-driven approach for
    flexibility and reusability.

    Example:
        >>> pipeline = CommentPipeline()
        >>> df = pipeline.load_data("comments.csv")
        >>> results = pipeline.run(df)
        >>> print(results.summary())
        >>> results.save("output/")

        >>> # With custom config
        >>> config = Config.from_yaml("custom_config.yaml")
        >>> pipeline = CommentPipeline(config)
        >>> results = pipeline.run(df, text_column="review_text")
    """

    # Platform-specific column mappings
    PLATFORM_MAPPINGS = {
        "jd": {
            "content": ["content", "评论内容", "评价内容"],
            "rating": ["score", "rating", "评分"],
            "date": ["creationTime", "时间", "日期"],
        },
        "taobao": {
            "content": ["rateContent", "评论内容", "评价内容"],
            "rating": ["rate", "评分"],
            "date": ["rateDate", "时间", "日期"],
        },
        "bilibili": {
            "content": ["content", "message", "评论", "弹幕"],
            "rating": ["score", "rating"],
            "date": ["ctime", "时间", "日期"],
        },
    }

    def __init__(self, config: Optional[Config] = None):
        """Initialize the pipeline with configuration.

        Args:
            config: Configuration object. If None, uses default configuration.
        """
        self.config = config or Config()

        # Initialize components
        self._init_components()

    def _init_components(self) -> None:
        """Initialize all pipeline components based on configuration."""
        # Preprocessing
        self.cleaner = TextCleaner(
            remove_urls=self.config.preprocessing.clean.remove_urls,
            remove_emails=self.config.preprocessing.clean.remove_emails,
            remove_html=self.config.preprocessing.clean.remove_html,
            remove_extra_spaces=self.config.preprocessing.clean.remove_extra_spaces,
            normalize_whitespace=self.config.preprocessing.clean.normalize_whitespace,
        )

        self.segmenter = JiebaSegmenter(
            mode=self.config.preprocessing.segmentation.mode,
            custom_dict_path=self.config.preprocessing.segmentation.custom_dict_path,
        )

        self.stopword_filter = StopwordFilter(
            stopwords_path=self.config.get_stopwords_path(),
            extra_words=self.config.preprocessing.stopwords.extra_words,
        )

        # Sentiment
        self.sentiment_labeler = SentimentLabeler(
            method=self.config.sentiment.labeling_method,
            threshold_positive=self.config.sentiment.snownlp.threshold_positive,
            threshold_negative=self.config.sentiment.snownlp.threshold_negative,
        )

        self.vectorizer = TFIDFVectorizer(
            max_features=self.config.sentiment.tfidf.max_features,
            min_df=self.config.sentiment.tfidf.min_df,
            max_df=self.config.sentiment.tfidf.max_df,
            ngram_range=tuple(self.config.sentiment.tfidf.ngram_range),
        )

        # Topic
        self.keyword_extractor = KeywordExtractor(
            method=self.config.topic.keywords.method,
            top_k=self.config.topic.keywords.top_k,
        )

        self.lda_model = LDAModel(
            num_topics=self.config.topic.lda.num_topics,
            passes=self.config.topic.lda.passes,
            iterations=self.config.topic.lda.iterations,
            alpha=self.config.topic.lda.alpha,
            eta=self.config.topic.lda.eta,
            random_state=self.config.topic.lda.random_state,
        )

        # Demand
        self.demand_calculator = DemandIntensityCalculator(
            keywords_path=self.config.get_demand_keywords_path(),
            method=self.config.demand.intensity.method,
            normalization=self.config.demand.intensity.normalization,
        )

        self.demand_correlator = DemandCorrelationAnalyzer(
            keywords=self.demand_calculator.keywords,
            method=self.config.demand.correlation.method,
            min_cooccurrence=self.config.demand.correlation.min_cooccurrence,
            window_size=self.config.demand.correlation.window_size,
        )

    def load_data(
        self,
        path: Union[str, Path],
        platform: Optional[str] = None,
        encoding: str = "utf-8",
        **kwargs
    ) -> pd.DataFrame:
        """Load comment data from file.

        Automatically detects file type and platform format.

        Args:
            path: Path to data file (CSV, Excel, JSON).
            platform: Platform type ("jd", "taobao", "bilibili", "generic").
                     If None, uses platform from config.
            encoding: File encoding.
            **kwargs: Additional arguments passed to pandas read function.

        Returns:
            DataFrame with loaded data.

        Raises:
            ValueError: If file format is not supported.
            FileNotFoundError: If file does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # Detect file type
        suffix = path.suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(path, encoding=encoding, **kwargs)
        elif suffix in [".xlsx", ".xls"]:
            df = pd.read_excel(path, **kwargs)
        elif suffix == ".json":
            df = pd.read_json(path, **kwargs)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        # Standardize column names based on platform
        platform = platform or self.config.data.platform
        if platform in self.PLATFORM_MAPPINGS:
            df = self._standardize_columns(df, platform)

        return df

    def _standardize_columns(self, df: pd.DataFrame, platform: str) -> pd.DataFrame:
        """Standardize column names based on platform mapping."""
        mapping = self.PLATFORM_MAPPINGS[platform]
        reverse_map = {}

        for standard, variants in mapping.items():
            for variant in variants:
                reverse_map[variant.lower()] = standard

        # Rename columns
        new_columns = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in reverse_map:
                new_columns[col] = reverse_map[col_lower]

        return df.rename(columns=new_columns)

    def detect_text_column(self, df: pd.DataFrame) -> str:
        """Automatically detect the text content column.

        Args:
            df: Input dataframe.

        Returns:
            Name of the detected text column.

        Raises:
            ValueError: If no suitable text column is found.
        """
        keywords = self.config.data.text_column_keywords

        # First try exact matches (case-insensitive)
        for col in df.columns:
            col_lower = col.lower()
            for kw in keywords:
                if kw.lower() == col_lower:
                    return col

        # Then try partial matches
        for col in df.columns:
            col_lower = col.lower()
            for kw in keywords:
                if kw.lower() in col_lower:
                    return col

        # Finally, try to find the longest string column
        text_lengths = {}
        for col in df.columns:
            if df[col].dtype == object:
                avg_len = df[col].astype(str).str.len().mean()
                text_lengths[col] = avg_len

        if text_lengths:
            return max(text_lengths, key=text_lengths.get)

        raise ValueError(
            f"Could not detect text column. Please specify manually. "
            f"Available columns: {list(df.columns)}"
        )

    def run(
        self,
        df: pd.DataFrame,
        text_column: Optional[str] = None,
        verbose: bool = True,
    ) -> PipelineResults:
        """Run the complete analysis pipeline.

        Args:
            df: Input dataframe with comments.
            text_column: Name of the column containing text content.
                        If None, auto-detects the column.
            verbose: Whether to show progress information.

        Returns:
            PipelineResults containing all analysis results.
        """
        original_df = df.copy()

        # Detect text column if not specified
        if text_column is None:
            text_column = self.detect_text_column(df)

        if verbose:
            print(f"Using text column: '{text_column}'")
            print(f"Processing {len(df)} comments...")

        # ==================== Phase 1: Preprocessing ====================
        if verbose:
            print("\n[1/4] Preprocessing...")

        df = self._run_preprocessing(df, text_column, verbose)

        # ==================== Phase 2: Sentiment Analysis ====================
        if verbose:
            print("\n[2/4] Sentiment Analysis...")

        sentiment_results = self._run_sentiment_analysis(df, verbose)

        # ==================== Phase 3: Topic Modeling ====================
        if verbose:
            print("\n[3/4] Topic Modeling...")

        topic_results = self._run_topic_modeling(df, verbose)

        # ==================== Phase 4: Demand Analysis ====================
        if verbose:
            print("\n[4/4] Demand Analysis...")

        demand_results = self._run_demand_analysis(df, verbose)

        # Compile results
        results = PipelineResults(
            original_data=original_df,
            processed_data=df,
            sentiment_distribution=sentiment_results['distribution'],
            sentiment_models=sentiment_results['models'],
            top_keywords=topic_results['keywords'],
            topics=topic_results['topics'],
            demand_intensity=demand_results.get('intensity'),
            demand_correlation=demand_results.get('correlation'),
            config=self.config,
        )

        if verbose:
            print("\n" + results.summary())

        return results

    def _run_preprocessing(
        self,
        df: pd.DataFrame,
        text_column: str,
        verbose: bool
    ) -> pd.DataFrame:
        """Run preprocessing phase."""
        df = df.copy()

        # Text cleaning
        if verbose:
            print("  Cleaning text...")
        tqdm.pandas(disable=not verbose)
        df['cleaned_text'] = df[text_column].astype(str).progress_apply(self.cleaner.clean)

        # Segmentation
        if verbose:
            print("  Segmenting text...")
        df['segmented_text'] = df['cleaned_text'].progress_apply(self.segmenter.segment)

        # Stopword filtering
        if verbose:
            print("  Filtering stopwords...")
        df['filtered_text'] = df['segmented_text'].progress_apply(self.stopword_filter.filter)

        # Create space-joined version for vectorization
        df['processed_text'] = df['filtered_text'].apply(lambda x: ' '.join(x))

        return df

    def _run_sentiment_analysis(
        self,
        df: pd.DataFrame,
        verbose: bool
    ) -> Dict[str, Any]:
        """Run sentiment analysis phase."""
        # Label sentiment
        if verbose:
            print("  Labeling sentiment...")
        df = df.copy()
        df['sentiment'] = self.sentiment_labeler.label_batch(df['cleaned_text'])

        distribution = df['sentiment'].value_counts().to_dict()

        # Train classifiers
        models = {}

        # Filter out rows with empty processed text
        valid_mask = df['processed_text'].str.len() > 0
        if valid_mask.sum() < 10:
            if verbose:
                print("  Warning: Not enough valid samples for model training")
            return {'distribution': distribution, 'models': models}

        X_train = self.vectorizer.fit_transform(df.loc[valid_mask, 'processed_text'])
        y_train = df.loc[valid_mask, 'sentiment']

        # Balance samples if enabled
        if self.config.sentiment.balance.enabled:
            if verbose:
                print("  Balancing samples...")
            X_train, y_train = self._balance_samples(X_train, y_train)

        # Train models
        model_configs = self.config.sentiment.models

        for model_name in ['naive_bayes', 'svm', 'logistic_regression']:
            if not getattr(model_configs, model_name).enabled:
                continue

            if verbose:
                print(f"  Training {model_name}...")

            classifier = Classifier(model_name)
            model_results = classifier.train(X_train, y_train)
            models[model_name] = model_results

        return {'distribution': distribution, 'models': models}

    def _balance_samples(self, X, y):
        """Balance sample distribution."""
        method = self.config.sentiment.balance.method
        random_state = self.config.sentiment.balance.random_state

        if method == 'undersample':
            from sklearn.utils import resample

            # Combine X and y for resampling
            df = pd.DataFrame({'y': y})
            df['idx'] = range(len(y))

            # Get minority class size
            min_size = y.value_counts().min()

            balanced_idx = []
            for label in y.unique():
                label_idx = df[df['y'] == label]['idx'].values
                if len(label_idx) > min_size:
                    label_idx = resample(
                        label_idx,
                        replace=False,
                        n_samples=min_size,
                        random_state=random_state
                    )
                balanced_idx.extend(label_idx)

            return X[balanced_idx], y.iloc[balanced_idx]

        elif method == 'oversample':
            from sklearn.utils import resample

            df = pd.DataFrame({'y': y})
            df['idx'] = range(len(y))

            max_size = y.value_counts().max()

            balanced_idx = []
            for label in y.unique():
                label_idx = df[df['y'] == label]['idx'].values
                if len(label_idx) < max_size:
                    label_idx = resample(
                        label_idx,
                        replace=True,
                        n_samples=max_size,
                        random_state=random_state
                    )
                balanced_idx.extend(label_idx)

            return X[balanced_idx], y.iloc[balanced_idx]

        return X, y

    def _run_topic_modeling(
        self,
        df: pd.DataFrame,
        verbose: bool
    ) -> Dict[str, Any]:
        """Run topic modeling phase."""
        # Filter valid documents
        valid_mask = df['processed_text'].str.len() > 0
        valid_texts = df.loc[valid_mask, 'processed_text'].tolist()

        if len(valid_texts) < 10:
            if verbose:
                print("  Warning: Not enough valid samples for topic modeling")
            return {'keywords': [], 'topics': []}

        # Extract keywords
        if verbose:
            print("  Extracting keywords...")
        keywords = self.keyword_extractor.extract(valid_texts)

        # Build LDA model
        if verbose:
            print("  Building LDA model...")
        topics = self.lda_model.fit_transform(df.loc[valid_mask, 'filtered_text'].tolist())

        return {'keywords': keywords, 'topics': topics}

    def _run_demand_analysis(
        self,
        df: pd.DataFrame,
        verbose: bool
    ) -> Dict[str, Any]:
        """Run demand analysis phase."""
        # Filter valid documents
        valid_mask = df['processed_text'].str.len() > 0
        valid_texts = df.loc[valid_mask, 'filtered_text'].tolist()

        if len(valid_texts) < 10:
            if verbose:
                print("  Warning: Not enough valid samples for demand analysis")
            return {}

        # Calculate demand intensity
        if verbose:
            print("  Calculating demand intensity...")
        intensity_df = self.demand_calculator.calculate(valid_texts)

        # Calculate demand correlation
        if verbose:
            print("  Calculating demand correlation...")
        correlation_df = self.demand_correlator.analyze(valid_texts)

        return {'intensity': intensity_df, 'correlation': correlation_df}
