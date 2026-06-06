"""Pydantic-based configuration management for comment_analyzer."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PathConfig(BaseModel):
    """Configuration for file system paths."""

    output_base: Path = Field(default=Path("./outputs"), description="Base directory for all outputs")
    visualization_base: Path = Field(
        default=Path.home() / ".sentidemand" / "outputs",
        description="Base directory for visualization HTML outputs",
    )
    upload_dir: Path = Field(
        default=Path.home() / ".sentidemand" / "uploads",
        description="Directory for uploaded data files",
    )
    demand_folder: str = Field(default="demand_analysis", description="Folder for demand outputs")
    sentiment_folder: str = Field(default="sentiment_models", description="Folder for sentiment outputs")
    word_frequency_folder: str = Field(default="word_frequency", description="Folder for keyword outputs")
    derived_columns_folder: str = Field(default="derived_columns", description="Folder for derived outputs")
    logs_folder: str = Field(default="logs", description="Folder for logs")
    config_dir: Path = Field(default=Path("./config"), description="Directory for configuration files")

    @field_validator("output_base", "visualization_base", "upload_dir", "config_dir", mode="before")
    @classmethod
    def validate_path(cls, value: Union[str, Path]) -> Path:
        path = Path(value) if isinstance(value, str) else value
        return path.expanduser()

    @model_validator(mode="after")
    def validate_all_paths(self) -> "PathConfig":
        self.output_base = Path(self.output_base).expanduser()
        self.visualization_base = Path(self.visualization_base).expanduser()
        self.upload_dir = Path(self.upload_dir).expanduser()
        self.config_dir = Path(self.config_dir).expanduser()
        return self

    @staticmethod
    def _ensure_path(path: Union[str, Path]) -> Path:
        return Path(path) if isinstance(path, str) else path

    def get_demand_path(self) -> Path:
        return self._ensure_path(self.output_base) / self.demand_folder

    def get_sentiment_path(self) -> Path:
        return self._ensure_path(self.output_base) / self.sentiment_folder

    def get_word_frequency_path(self) -> Path:
        return self._ensure_path(self.output_base) / self.word_frequency_folder

    def get_derived_columns_path(self) -> Path:
        return self._ensure_path(self.output_base) / self.derived_columns_folder

    def get_logs_path(self) -> Path:
        return self._ensure_path(self.output_base) / self.logs_folder

    def get_visualization_path(self) -> Path:
        return self._ensure_path(self.visualization_base)

    def get_upload_path(self) -> Path:
        return self._ensure_path(self.upload_dir)

    def ensure_directories(self) -> None:
        self.get_demand_path().mkdir(parents=True, exist_ok=True)
        self.get_sentiment_path().mkdir(parents=True, exist_ok=True)
        self.get_word_frequency_path().mkdir(parents=True, exist_ok=True)
        self.get_derived_columns_path().mkdir(parents=True, exist_ok=True)
        self.get_logs_path().mkdir(parents=True, exist_ok=True)
        self.get_visualization_path().mkdir(parents=True, exist_ok=True)
        self.get_upload_path().mkdir(parents=True, exist_ok=True)


class DataConfig(BaseModel):
    """Configuration for data loading and column detection."""

    platform: Literal["generic", "jd", "taobao", "bilibili"] = "generic"
    language: Literal["zh", "ko", "auto"] = "zh"
    text_column_keywords: List[str] = Field(
        default=["content", "comment", "review", "text", "评论", "内容", "评价", "리뷰", "후기"]
    )
    rating_column_keywords: List[str] = Field(
        default=["rating", "score", "star", "评分", "星级", "평점"]
    )
    date_column_keywords: List[str] = Field(
        default=["date", "time", "created", "时间", "日期", "작성일"]
    )


class CleanConfig(BaseModel):
    """Configuration for text cleaning."""

    remove_urls: bool = True
    remove_emails: bool = True
    remove_html: bool = True
    remove_extra_spaces: bool = True
    normalize_whitespace: bool = True


class SegmentationConfig(BaseModel):
    """Configuration for text segmentation."""

    mode: Literal["precise", "full", "search"] = "precise"
    backend: Literal["auto", "jieba", "okt", "mecab", "regex"] = "auto"
    custom_dict_path: Optional[Path] = None


class StopwordsConfig(BaseModel):
    """Configuration for stopword filtering."""

    use_default: bool = True
    custom_path: Optional[Path] = None
    extra_words: List[str] = Field(default_factory=list)
    strategy: Literal["default", "custom", "hybrid"] = "hybrid"


class PreprocessingConfig(BaseModel):
    """Configuration for preprocessing pipeline."""

    clean: CleanConfig = Field(default_factory=CleanConfig)
    segmentation: SegmentationConfig = Field(default_factory=SegmentationConfig)
    stopwords: StopwordsConfig = Field(default_factory=StopwordsConfig)


class SnowNLPConfig(BaseModel):
    """Configuration for SnowNLP sentiment labeling."""

    threshold_positive: float = Field(default=0.6, ge=0.0, le=1.0)
    threshold_negative: float = Field(default=0.4, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "SnowNLPConfig":
        if self.threshold_positive <= self.threshold_negative:
            raise ValueError("threshold_positive must be greater than threshold_negative")
        return self


class BalanceConfig(BaseModel):
    """Configuration for sample balancing."""

    enabled: bool = True
    method: Literal["undersample", "oversample", "none"] = "undersample"
    random_state: int = 42


class TFIDFConfig(BaseModel):
    """Configuration for TF-IDF vectorization."""

    max_features: int = Field(default=5000, gt=0)
    min_df: Union[int, float] = 2
    max_df: Union[int, float] = 0.95
    ngram_range: List[int] = Field(default=[1, 2])

    @field_validator("ngram_range")
    @classmethod
    def validate_ngram_range(cls, value: List[int]) -> List[int]:
        if len(value) != 2:
            raise ValueError("ngram_range must have exactly 2 elements")
        if value[0] > value[1]:
            raise ValueError("ngram_range[0] must be <= ngram_range[1]")
        return value


class ModelConfig(BaseModel):
    """Configuration for a single ML model."""

    enabled: bool = True
    model_config = {"extra": "allow"}


class ModelsConfig(BaseModel):
    """Configuration for all sentiment models."""

    naive_bayes: ModelConfig = Field(default_factory=lambda: ModelConfig(enabled=True, alpha=1.0))
    svm: ModelConfig = Field(default_factory=lambda: ModelConfig(enabled=True, kernel="linear", C=1.0))
    logistic_regression: ModelConfig = Field(
        default_factory=lambda: ModelConfig(enabled=True, C=1.0, max_iter=1000)
    )


class SentimentConfig(BaseModel):
    """Configuration for sentiment analysis."""

    labeling_method: Literal["auto", "snownlp", "lexicon", "manual"] = "auto"
    snownlp: SnowNLPConfig = Field(default_factory=SnowNLPConfig)
    balance: BalanceConfig = Field(default_factory=BalanceConfig)
    tfidf: TFIDFConfig = Field(default_factory=TFIDFConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)


class KeywordsConfig(BaseModel):
    """Configuration for keyword extraction."""

    method: Literal["tfidf", "frequency"] = "tfidf"
    top_k: int = Field(default=20, gt=0)


class LDAConfig(BaseModel):
    """Configuration for LDA topic modeling."""

    num_topics: int = Field(default=5, gt=0)
    passes: int = Field(default=15, gt=0)
    iterations: int = Field(default=100, gt=0)
    alpha: Union[str, float] = "auto"
    eta: Union[str, float] = "auto"
    random_state: int = 42


class TopicConfig(BaseModel):
    """Configuration for topic modeling."""

    keywords: KeywordsConfig = Field(default_factory=KeywordsConfig)
    lda: LDAConfig = Field(default_factory=LDAConfig)


class IntensityConfig(BaseModel):
    """Configuration for demand intensity calculation."""

    method: Literal["tfidf_weighted", "simple_count"] = "tfidf_weighted"
    normalization: Literal["minmax", "standard", "none"] = "minmax"


class CorrelationConfig(BaseModel):
    """Configuration for demand correlation analysis."""

    method: Literal["cooccurrence", "pmi"] = "cooccurrence"
    min_cooccurrence: int = Field(default=2, ge=0)
    window_size: int = Field(default=50, gt=0)


class DemandConfig(BaseModel):
    """Configuration for demand analysis."""

    intensity: IntensityConfig = Field(default_factory=IntensityConfig)
    correlation: CorrelationConfig = Field(default_factory=CorrelationConfig)


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format_string: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    rotation: str = Field(default="10 MB", description="Log file rotation size")
    retention: str = Field(default="30 days", description="Log file retention period")
    compression: str = Field(default="zip", description="Compression format for old logs")
    log_to_console: bool = True
    log_to_file: bool = True


class OutputConfig(BaseModel):
    """Configuration for output files."""

    save_intermediate: bool = False
    encoding: str = "utf-8-sig"
    float_format: str = "%.4f"
    csv_index: bool = False
    use_sequence_numbers: bool = True
    sequence_padding: int = 3


class VisualizationConfig(BaseModel):
    """Configuration for visualization generation."""

    theme: Literal["dark", "light"] = "dark"
    locale: str = "zh-CN"
    auto_open_browser: bool = True
    gallery_port: int = 8765
    charts: Dict[str, bool] = Field(
        default_factory=lambda: {
            "sentiment_donut": True,
            "sentiment_wordcloud": True,
            "sentiment_distribution": True,
            "sentiment_scatter": True,
            "features_bidirectional": True,
            "features_lollipop": True,
            "features_heatmap": True,
            "features_tfidf_scatter": True,
            "topics_nightingale": True,
            "topics_bubble": True,
            "topics_radar": True,
            "demand_funnel": True,
            "demand_network": True,
            "demand_dashboard": True,
        }
    )


class Settings(BaseSettings):
    """Main application settings using Pydantic."""

    model_config = SettingsConfigDict(
        env_prefix="COMMENT_ANALYZER_",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "comment-analyzer"
    app_version: str = "0.2.0"
    debug: bool = False

    paths: PathConfig = Field(default_factory=PathConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    sentiment: SentimentConfig = Field(default_factory=SentimentConfig)
    topic: TopicConfig = Field(default_factory=TopicConfig)
    demand: DemandConfig = Field(default_factory=DemandConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)

    def get_stopwords_path(self) -> Optional[Path]:
        custom_path = self.preprocessing.stopwords.custom_path
        if custom_path:
            return Path(custom_path)
        if self.preprocessing.stopwords.use_default:
            return self.paths.config_dir / ("stopwords_ko.txt" if self.data.language == "ko" else "stopwords.txt")
        return None

    def get_demand_keywords_path(self) -> Path:
        return self.paths.config_dir / ("demand_keywords_ko.json" if self.data.language == "ko" else "demand_keywords.json")

    def get_sentiment_lexicon_path(self) -> Path:
        return self.paths.config_dir / (
            "sentiment_lexicon_ko.json" if self.data.language == "ko" else "sentiment_lexicon_zh.json"
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def to_yaml_file(self, path: Union[str, Path]) -> None:
        import yaml

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            yaml.dump(self.to_dict(), handle, default_flow_style=False, allow_unicode=True)


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None


def init_settings(env_file: Optional[Union[str, Path]] = None, **kwargs: Any) -> Settings:
    global _settings
    _settings = Settings(_env_file=env_file, **kwargs)
    return _settings
