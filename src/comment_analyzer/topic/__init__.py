"""Topic modeling modules for comment_analyzer.

This package provides topic modeling capabilities including TF-IDF keyword
extraction and LDA topic discovery.
"""

__all__ = ["KeywordExtractor", "LDAModel"]

_LAZY_IMPORTS = {
    "KeywordExtractor": ("comment_analyzer.topic.keywords", "KeywordExtractor"),
    "LDAModel": ("comment_analyzer.topic.lda", "LDAModel"),
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
