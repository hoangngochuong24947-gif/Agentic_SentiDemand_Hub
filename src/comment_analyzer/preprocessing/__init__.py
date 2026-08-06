"""Preprocessing modules for comment_analyzer.

This package provides text preprocessing capabilities including cleaning,
segmentation, and stopword filtering for Chinese text.
"""

__all__ = ["TextCleaner", "JiebaSegmenter", "StopwordFilter"]

_LAZY_IMPORTS = {
    "TextCleaner": ("comment_analyzer.preprocessing.cleaner", "TextCleaner"),
    "JiebaSegmenter": ("comment_analyzer.preprocessing.segmenter", "JiebaSegmenter"),
    "StopwordFilter": ("comment_analyzer.preprocessing.filter", "StopwordFilter"),
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
