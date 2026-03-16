"""Demand analysis modules for comment_analyzer.

This package provides demand insight capabilities including demand intensity
calculation and demand correlation analysis.
"""

from comment_analyzer.demand.intensity import DemandIntensityCalculator
from comment_analyzer.demand.correlation import DemandCorrelationAnalyzer

__all__ = ["DemandIntensityCalculator", "DemandCorrelationAnalyzer"]
