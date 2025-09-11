"""
Analytics Domain

This package contains the Analytics bounded context with entities,
value objects, repositories, and domain services for technical analysis,
statistical calculations, and pattern recognition.
"""

from .entities.indicator import Indicator, IndicatorId, IndicatorType, IndicatorValue, Symbol, IndicatorName
from .entities.analysis import Analysis, AnalysisId, AnalysisType, AnalysisStatus, Pattern, ConfidenceLevel
from .value_objects.statistics import (
    Mean, StandardDeviation, Variance, Correlation, SharpeRatio,
    Volatility, ReturnMetrics, StatisticalSummary, TrendAnalysis
)
from .repositories.indicator_repository import IndicatorRepository
from .repositories.analysis_repository import AnalysisRepository
from .services.indicator_calculation_service import IndicatorCalculationService

__all__ = [
    # Entities
    'Indicator',
    'IndicatorId',
    'IndicatorType',
    'IndicatorValue',
    'Symbol',
    'IndicatorName',
    'Analysis',
    'AnalysisId',
    'AnalysisType',
    'AnalysisStatus',
    'Pattern',
    'ConfidenceLevel',

    # Value Objects
    'Mean',
    'StandardDeviation',
    'Variance',
    'Correlation',
    'SharpeRatio',
    'Volatility',
    'ReturnMetrics',
    'StatisticalSummary',
    'TrendAnalysis',

    # Repositories
    'IndicatorRepository',
    'AnalysisRepository',

    # Services
    'IndicatorCalculationService'
]

