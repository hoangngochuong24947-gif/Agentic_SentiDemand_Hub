"""Demand analysis modules for comment_analyzer.

This package provides demand insight capabilities including demand intensity
calculation and demand correlation analysis.
"""

__all__ = ["DemandIntensityCalculator", "DemandCorrelationAnalyzer"]

_LAZY_IMPORTS = {
    "DemandIntensityCalculator": ("comment_analyzer.demand.intensity", "DemandIntensityCalculator"),
    "DemandCorrelationAnalyzer": ("comment_analyzer.demand.correlation", "DemandCorrelationAnalyzer"),
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
