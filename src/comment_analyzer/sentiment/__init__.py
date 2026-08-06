"""Sentiment analysis modules for comment_analyzer.

This package provides sentiment labeling, vectorization, and classification
capabilities for comment sentiment analysis.
"""

__all__ = ["SentimentLabeler", "TFIDFVectorizer", "Classifier", "ModelResults"]

_LAZY_IMPORTS = {
    "SentimentLabeler": ("comment_analyzer.sentiment.labeler", "SentimentLabeler"),
    "TFIDFVectorizer": ("comment_analyzer.sentiment.vectorizer", "TFIDFVectorizer"),
    "Classifier": ("comment_analyzer.sentiment.classifier", "Classifier"),
    "ModelResults": ("comment_analyzer.sentiment.classifier", "ModelResults"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        import importlib

        module_name, attr = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_name)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
