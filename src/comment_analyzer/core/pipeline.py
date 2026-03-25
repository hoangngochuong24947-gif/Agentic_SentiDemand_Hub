"""Pipeline orchestrator for comment analysis.

This module provides the main CommentPipeline class that orchestrates
the entire analysis workflow from data loading to result generation.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from loguru import logger
from tqdm import tqdm

from comment_analyzer.core.config import Config
from comment_analyzer.core.log_manager import LogManager, get_log_manager, init_logging
from comment_analyzer.core.output_manager import OutputManager, SavedFileInfo
from comment_analyzer.core.settings import Settings, get_settings
from comment_analyzer.preprocessing.cleaner import TextCleaner
from comment_analyzer.preprocessing.filter import StopwordFilter
from comment_analyzer.preprocessing.segmenter import JiebaSegmenter
from comment_analyzer.sentiment.classifier import Classifier, ModelResults
from comment_analyzer.sentiment.labeler import SentimentLabeler
from comment_analyzer.sentiment.vectorizer import TFIDFVectorizer
from comment_analyzer.topic.keywords import KeywordExtractor
from comment_analyzer.topic.lda import LDAModel
from comment_analyzer.demand.intensity import DemandIntensityCalculator
from comment_analyzer.demand.correlation import DemandCorrelationAnalyzer
from comment_analyzer.insights.briefing import BriefingPack, InsightBriefingBuilder


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
        output_manager: OutputManager for saving results
        log_manager: LogManager for logging important information
        saved_files: List of saved file information
        start_time: Pipeline start timestamp
        end_time: Pipeline end timestamp
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
    settings: Optional[Settings] = None
    output_manager: Optional[OutputManager] = None
    log_manager: Optional[LogManager] = None
    saved_files: List[SavedFileInfo] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    ai_briefing: Optional[BriefingPack] = None

    def __post_init__(self):
        """Initialize managers if not provided."""
        if self.settings is None:
            self.settings = get_settings()
        if self.output_manager is None:
            self.output_manager = OutputManager(self.settings)
        if self.log_manager is None:
            self.log_manager = get_log_manager()

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

        if self.saved_files:
            lines.append(f"\n--- Saved Files ({len(self.saved_files)} total) ---")
            for info in self.saved_files[-5:]:  # Show last 5
                lines.append(f"  [{info.category}] {info.final_path.name}")

        lines.append("\n" + "=" * 50)
        return "\n".join(lines)

    def save(self, output_dir: Optional[Union[str, Path]] = None) -> None:
        """Save all results using the output manager with categorized folders.

        Args:
            output_dir: Optional custom output directory. If None, uses settings.
        """
        if output_dir:
            # Create temporary settings with custom path
            from comment_analyzer.core.settings import PathConfig
            custom_settings = self.settings.model_copy()
            custom_settings.paths.output_base = Path(output_dir)
            self.output_manager = OutputManager(custom_settings)

        logger.info("Starting to save pipeline results...")

        # Save processed data (derived columns)
        self._save_processed_data()

        # Save sentiment analysis results
        self._save_sentiment_results()

        # Save topic modeling results
        self._save_topic_results()

        # Save demand analysis results
        self._save_demand_results()

        # Save AI briefing package for downstream LLM execution
        self._save_ai_briefing()

        # Log important summary information
        self._log_summary()

        logger.info(f"Saved {len(self.saved_files)} files successfully")

    def visualize(self, source_name: str = "analysis") -> List[str]:
        """Generate all visualization charts as standalone HTML files.

        Each file is saved to ``~/.sentidemand/outputs/{source}_{date}/``
        and registered in ``manifest.json`` for history tracking.

        Args:
            source_name: Name of the data source (used in folder naming
                         and manifest tracking). The original CSV filename
                         without extension works well here.

        Returns:
            List of absolute paths to generated HTML files.

        Example:
            >>> results = pipeline.run(df)
            >>> files = results.visualize("jd_comments")
            >>> # Open any file in your browser to see the chart
        """
        from comment_analyzer.visualization.generator import VisualizationGenerator
        gen = VisualizationGenerator(self.settings, self)
        return gen.generate_all(source_name)

    def build_ai_briefing(self, source_name: str = "analysis") -> BriefingPack:
        """Build and cache an AI prompt package for this result set."""
        if self.ai_briefing is None:
            self.ai_briefing = InsightBriefingBuilder().build(self, source_name=source_name)
        return self.ai_briefing

    def _save_processed_data(self) -> None:
        """Save processed data with derived columns."""
        if self.processed_data is not None and not self.processed_data.empty:
            info = self.output_manager.save_dataframe(
                self.processed_data,
                "processed_data.csv",
                category="derived",
                use_sequence=True
            )
            self.saved_files.append(info)
            logger.debug(f"Saved processed data: {info.final_path}")

    def _save_sentiment_results(self) -> None:
        """Save sentiment analysis results to sentiment_models folder."""
        # Save sentiment distribution
        if self.sentiment_distribution:
            df_dist = pd.DataFrame(
                list(self.sentiment_distribution.items()),
                columns=['sentiment', 'count']
            )
            info = self.output_manager.save_dataframe(
                df_dist,
                "sentiment_distribution.csv",
                category="sentiment",
                use_sequence=True
            )
            self.saved_files.append(info)

            # Log important sentiment distribution info
            self.log_manager.log_analysis(
                "sentiment_distribution",
                self.sentiment_distribution,
                extra={"total_comments": len(self.original_data)}
            )

        # Save model reports
        for name, results in self.sentiment_models.items():
            if hasattr(results, 'classification_report'):
                info = self.output_manager.save_text(
                    results.classification_report,
                    f"model_report_{name}.txt",
                    category="sentiment",
                    use_sequence=True
                )
                self.saved_files.append(info)

                # Log model results
                if hasattr(results, 'metrics'):
                    self.log_manager.log_model_result(
                        name,
                        results.metrics,
                        params=getattr(results, 'params', None)
                    )

                # Log important model info
                self.log_manager.log_important(
                    f"Trained {name} model",
                    category="ml",
                    data={"has_report": True}
                )

    def _save_topic_results(self) -> None:
        """Save topic modeling results to word_frequency folder."""
        # Save keywords
        if self.top_keywords:
            df_keywords = pd.DataFrame(self.top_keywords, columns=['word', 'score'])
            info = self.output_manager.save_dataframe(
                df_keywords,
                "top_keywords.csv",
                category="word_frequency",
                use_sequence=True
            )
            self.saved_files.append(info)

            # Log important keywords info
            top_5_words = [w for w, _ in self.top_keywords[:5]]
            self.log_manager.log_important(
                f"Top keywords: {', '.join(top_5_words)}",
                category="analysis",
                data={"keyword_count": len(self.top_keywords)}
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
            if topics_df:
                df_topics = pd.DataFrame(topics_df)
                info = self.output_manager.save_dataframe(
                    df_topics,
                    "topics.csv",
                    category="word_frequency",
                    use_sequence=True
                )
                self.saved_files.append(info)

                # Log topic info
                topic_summary = {
                    f"topic_{i}": [w for w, _ in t.get('words', [])[:5]]
                    for i, t in enumerate(self.topics[:3])
                }
                self.log_manager.log_analysis(
                    "topic_modeling",
                    topic_summary,
                    extra={"num_topics": len(self.topics)}
                )

    def _save_demand_results(self) -> None:
        """Save demand analysis results to demand_analysis folder."""
        # Save demand intensity
        if self.demand_intensity is not None and not self.demand_intensity.empty:
            info = self.output_manager.save_dataframe(
                self.demand_intensity,
                "demand_intensity.csv",
                category="demand",
                use_sequence=True
            )
            self.saved_files.append(info)

            # Log demand intensity summary
            intensity_summary = {
                col: float(self.demand_intensity[col].mean())
                for col in self.demand_intensity.columns
            }
            self.log_manager.log_analysis(
                "demand_intensity",
                intensity_summary
            )

        # Save demand correlation
        if self.demand_correlation is not None and not self.demand_correlation.empty:
            info = self.output_manager.save_dataframe(
                self.demand_correlation,
                "demand_correlation.csv",
                category="demand",
                use_sequence=True
            )
            self.saved_files.append(info)

            # Log important correlation info
            self.log_manager.log_important(
                "Demand correlation analysis completed",
                category="analysis",
                data={
                    "correlation_shape": list(self.demand_correlation.shape),
                    "columns": list(self.demand_correlation.columns)
                }
            )

    def _save_ai_briefing(self) -> None:
        """Save the AI prompt package as JSON for external LLM execution."""
        briefing = self.build_ai_briefing()
        info = self.output_manager.save_json(
            briefing.to_dict(),
            "ai_briefing.json",
            category="derived",
            use_sequence=True,
        )
        self.saved_files.append(info)

    def _log_summary(self) -> None:
        """Log important summary information."""
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        summary_data = {
            "total_comments": len(self.original_data),
            "processed_comments": len(self.processed_data) if self.processed_data is not None else 0,
            "sentiment_categories": list(self.sentiment_distribution.keys()),
            "keyword_count": len(self.top_keywords),
            "topic_count": len(self.topics),
            "has_demand_analysis": self.demand_intensity is not None,
            "saved_files_count": len(self.saved_files),
            "duration_seconds": duration,
        }

        self.log_manager.log_important(
            "Pipeline analysis completed successfully",
            category="pipeline",
            data=summary_data
        )

        if duration:
            self.log_manager.log_pipeline_end(duration, summary_data)

    def generate_output_summary(self) -> str:
        """Generate a summary of all saved output files.

        Returns:
            Formatted summary string
        """
        if self.output_manager:
            return self.output_manager.generate_summary()
        return "No output manager available"


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
        >>> results.save()

        >>> # With custom config
        >>> from comment_analyzer.core.settings import Settings
        >>> settings = Settings()
        >>> pipeline = CommentPipeline(settings=settings)
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

    def __init__(
        self,
        config: Optional[Config] = None,
        settings: Optional[Settings] = None,
        log_manager: Optional[LogManager] = None
    ):
        """Initialize the pipeline with configuration.

        Args:
            config: Legacy Config object (for backward compatibility)
            settings: New Settings object (recommended)
            log_manager: Optional LogManager instance
        """
        # Use settings if provided, otherwise convert from config, or use defaults
        self.config = config or Config()
        if settings is not None:
            self.settings = settings
        elif config is not None:
            # Migrate from legacy config
            self.settings = Settings(**config._config)
            if hasattr(config, 'paths'):
                self.settings.paths = config.paths
        else:
            self.settings = get_settings()

        # Initialize logging
        self.log_manager = log_manager or get_log_manager()
        if not hasattr(LogManager, '_configured') or not LogManager._configured:
            init_logging(self.settings)

        # Initialize components
        self._init_components()

        logger.info(f"CommentPipeline initialized (platform: {self.settings.data.platform})")

    def _init_components(self) -> None:
        """Initialize all pipeline components based on configuration."""
        # Preprocessing
        self.cleaner = TextCleaner(
            remove_urls=self.settings.preprocessing.clean.remove_urls,
            remove_emails=self.settings.preprocessing.clean.remove_emails,
            remove_html=self.settings.preprocessing.clean.remove_html,
            remove_extra_spaces=self.settings.preprocessing.clean.remove_extra_spaces,
            normalize_whitespace=self.settings.preprocessing.clean.normalize_whitespace,
        )

        self.segmenter = JiebaSegmenter(
            mode=self.settings.preprocessing.segmentation.mode,
            custom_dict_path=self.settings.preprocessing.segmentation.custom_dict_path,
        )

        self.stopword_filter = StopwordFilter(
            stopwords_path=self.settings.get_stopwords_path(),
            extra_words=self.settings.preprocessing.stopwords.extra_words,
        )

        # Sentiment
        self.sentiment_labeler = SentimentLabeler(
            method=self.settings.sentiment.labeling_method,
            threshold_positive=self.settings.sentiment.snownlp.threshold_positive,
            threshold_negative=self.settings.sentiment.snownlp.threshold_negative,
        )

        self.vectorizer = TFIDFVectorizer(
            max_features=self.settings.sentiment.tfidf.max_features,
            min_df=self.settings.sentiment.tfidf.min_df,
            max_df=self.settings.sentiment.tfidf.max_df,
            ngram_range=tuple(self.settings.sentiment.tfidf.ngram_range),
        )

        # Topic
        self.keyword_extractor = KeywordExtractor(
            method=self.settings.topic.keywords.method,
            top_k=self.settings.topic.keywords.top_k,
        )

        self.lda_model = LDAModel(
            num_topics=self.settings.topic.lda.num_topics,
            passes=self.settings.topic.lda.passes,
            iterations=self.settings.topic.lda.iterations,
            alpha=self.settings.topic.lda.alpha,
            eta=self.settings.topic.lda.eta,
            random_state=self.settings.topic.lda.random_state,
        )

        # Demand
        self.demand_calculator = DemandIntensityCalculator(
            keywords_path=self.settings.get_demand_keywords_path(),
            method=self.settings.demand.intensity.method,
            normalization=self.settings.demand.intensity.normalization,
        )

        self.demand_correlator = DemandCorrelationAnalyzer(
            keywords=self.demand_calculator.keywords,
            method=self.settings.demand.correlation.method,
            min_cooccurrence=self.settings.demand.correlation.min_cooccurrence,
            window_size=self.settings.demand.correlation.window_size,
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
        platform = platform or self.settings.data.platform
        if platform in self.PLATFORM_MAPPINGS:
            df = self._standardize_columns(df, platform)

        # Log data loading
        self.log_manager.log_data_info(
            data_name=path.name,
            row_count=len(df),
            column_info={col: str(dtype) for col, dtype in df.dtypes.items()}
        )

        logger.info(f"Loaded {len(df)} rows from {path}")
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
        keywords = self.settings.data.text_column_keywords

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
        start_time = datetime.now()
        original_df = df.copy()

        self.log_manager.log_pipeline_start({
            "total_rows": len(df),
            "columns": list(df.columns),
            "platform": self.settings.data.platform,
        })

        # Detect text column if not specified
        if text_column is None:
            text_column = self.detect_text_column(df)

        logger.info(f"Using text column: '{text_column}'")
        logger.info(f"Processing {len(df)} comments...")

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

        end_time = datetime.now()

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
            config=None,  # Legacy config not used
            settings=self.settings,
            log_manager=self.log_manager,
            start_time=start_time,
            end_time=end_time,
        )

        if verbose:
            print("\n" + results.summary())

        logger.info("Pipeline completed successfully")
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
        df['normalized_text'] = df['cleaned_text'].progress_apply(self.cleaner.normalize_chinese_punctuation)
        df['analysis_text'] = df['normalized_text'].progress_apply(self.cleaner.remove_punctuation)

        # Segmentation
        if verbose:
            print("  Segmenting text...")
        df['segmented_text'] = df['analysis_text'].progress_apply(self.segmenter.segment)

        # Stopword filtering
        if verbose:
            print("  Filtering stopwords...")
        df['filtered_text'] = df['segmented_text'].progress_apply(self.stopword_filter.filter)
        df['filtered_text'] = df['filtered_text'].progress_apply(self._filter_noise_tokens)

        # Create space-joined version for vectorization
        df['processed_text'] = df['filtered_text'].apply(lambda x: ' '.join(x))

        logger.debug(f"Preprocessing complete: {len(df)} documents processed")
        return df

    @staticmethod
    def _filter_noise_tokens(tokens: List[str]) -> List[str]:
        """Remove punctuation and malformed tokens missed by upstream cleaning."""
        filtered: List[str] = []
        punctuation_tokens = {
            ",", ".", "!", "?", ";", ":", "-", "_", "/", "\\", "|",
            "，", "。", "！", "？", "；", "：", "、", "…", "—", "（", "）",
            "(", ")", "[", "]", "{", "}", "<", ">", '"', "'", "“", "”", "‘", "’",
        }
        for token in tokens:
            if not token:
                continue
            normalized = str(token).strip().lower()
            if not normalized:
                continue
            if normalized in punctuation_tokens:
                continue
            if re.fullmatch(r"[\W_]+", normalized, flags=re.UNICODE):
                continue
            if re.fullmatch(r"\d+(?:\.\d+)?", normalized):
                continue
            if "�" in normalized:
                continue
            if len(normalized) == 1 and not re.search(r"[\u4e00-\u9fffA-Za-z]", normalized):
                continue
            filtered.append(token)
        return filtered

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
            logger.warning("Not enough valid samples for model training")
            return {'distribution': distribution, 'models': models}

        X_train = self.vectorizer.fit_transform(df.loc[valid_mask, 'processed_text'])
        y_train = df.loc[valid_mask, 'sentiment']

        # Balance samples if enabled
        if self.settings.sentiment.balance.enabled:
            if verbose:
                print("  Balancing samples...")
            X_train, y_train = self._balance_samples(X_train, y_train)

        # Train models
        model_configs = self.settings.sentiment.models

        for model_name in ['naive_bayes', 'svm', 'logistic_regression']:
            model_config = getattr(model_configs, model_name)
            if not model_config.enabled:
                continue

            if verbose:
                print(f"  Training {model_name}...")

            try:
                classifier = Classifier(model_name)
                model_results = classifier.train(X_train, y_train)
                models[model_name] = model_results

                self.log_manager.log_important(
                    f"Successfully trained {model_name}",
                    category="ml"
                )
            except Exception as e:
                logger.error(f"Failed to train {model_name}: {e}")
                self.log_manager.log_error(e, {"model": model_name}, category="ml")

        return {'distribution': distribution, 'models': models}

    def _balance_samples(self, X, y):
        """Balance sample distribution."""
        method = self.settings.sentiment.balance.method
        random_state = self.settings.sentiment.balance.random_state

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
            logger.warning("Not enough valid samples for topic modeling")
            return {'keywords': [], 'topics': []}

        # Extract keywords
        if verbose:
            print("  Extracting keywords...")
        keywords = self.keyword_extractor.extract(valid_texts)

        # Build LDA model
        if verbose:
            print("  Building LDA model...")
        topics = self.lda_model.fit_transform(df.loc[valid_mask, 'filtered_text'].tolist())

        self.log_manager.log_important(
            f"Topic modeling complete: {len(topics)} topics, {len(keywords)} keywords",
            category="analysis"
        )

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
            logger.warning("Not enough valid samples for demand analysis")
            return {}

        # Calculate demand intensity
        if verbose:
            print("  Calculating demand intensity...")
        intensity_df = self.demand_calculator.calculate(valid_texts)

        # Calculate demand correlation
        if verbose:
            print("  Calculating demand correlation...")
        correlation_df = self.demand_correlator.analyze(valid_texts)

        self.log_manager.log_important(
            "Demand analysis complete",
            category="analysis",
            data={
                "intensity_shape": list(intensity_df.shape) if intensity_df is not None else None,
                "correlation_shape": list(correlation_df.shape) if correlation_df is not None else None,
            }
        )

        return {'intensity': intensity_df, 'correlation': correlation_df}
