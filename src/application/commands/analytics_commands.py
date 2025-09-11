"""
Analytics Domain Commands for CQRS Pattern

Commands for analytics operations including indicator calculations,
analysis execution, and data processing.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base_command import Command


@dataclass
class CalculateIndicatorCommand(Command):
    """
    Command to calculate a technical indicator

    Triggers calculation of a specific technical indicator for market data.
    """

    symbol: str
    timeframe: str
    indicator_name: str
    parameters: Dict[str, Any]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @property
    def command_type(self) -> str:
        return "CalculateIndicator"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'indicator_name': self.indicator_name,
            'parameters': self.parameters,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }


@dataclass
class CalculateMultipleIndicatorsCommand(Command):
    """
    Command to calculate multiple indicators

    Calculates multiple technical indicators in a single operation.
    """

    symbol: str
    timeframe: str
    indicators: List[Dict[str, Any]]  # List of indicator configs
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @property
    def command_type(self) -> str:
        return "CalculateMultipleIndicators"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'indicators': self.indicators,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }


@dataclass
class ExecuteAnalysisCommand(Command):
    """
    Command to execute a market analysis

    Runs a complete analysis including multiple indicators and signals.
    """

    analysis_type: str
    symbol: str
    timeframe: str
    parameters: Dict[str, Any]
    include_signals: bool = True

    @property
    def command_type(self) -> str:
        return "ExecuteAnalysis"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'analysis_type': self.analysis_type,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'parameters': self.parameters,
            'include_signals': self.include_signals
        }


@dataclass
class GenerateAnalysisReportCommand(Command):
    """
    Command to generate an analysis report

    Creates a comprehensive report based on analysis results.
    """

    report_type: str
    symbol: str
    timeframe: str
    analysis_ids: List[str]
    report_format: str = "html"
    include_charts: bool = True

    @property
    def command_type(self) -> str:
        return "GenerateAnalysisReport"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'report_type': self.report_type,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'analysis_ids': self.analysis_ids,
            'report_format': self.report_format,
            'include_charts': self.include_charts
        }


@dataclass
class UpdateIndicatorParametersCommand(Command):
    """
    Command to update indicator calculation parameters

    Modifies parameters for existing indicator calculations.
    """

    indicator_id: str
    new_parameters: Dict[str, Any]

    @property
    def command_type(self) -> str:
        return "UpdateIndicatorParameters"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'indicator_id': self.indicator_id,
            'new_parameters': self.new_parameters
        }


@dataclass
class RecalculateIndicatorsCommand(Command):
    """
    Command to recalculate indicators

    Recalculates indicators based on updated data or parameters.
    """

    symbol: str
    timeframe: str
    indicator_names: List[str]
    start_date: Optional[datetime] = None
    force_recalculation: bool = False

    @property
    def command_type(self) -> str:
        return "RecalculateIndicators"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'indicator_names': self.indicator_names,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'force_recalculation': self.force_recalculation
        }


@dataclass
class CreateAnalysisTemplateCommand(Command):
    """
    Command to create an analysis template

    Defines a reusable analysis configuration.
    """

    name: str
    description: str
    analysis_type: str
    default_parameters: Dict[str, Any]
    indicators: List[str]
    is_active: bool = True

    @property
    def command_type(self) -> str:
        return "CreateAnalysisTemplate"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'analysis_type': self.analysis_type,
            'default_parameters': self.default_parameters,
            'indicators': self.indicators,
            'is_active': self.is_active
        }


@dataclass
class ExecuteAnalysisTemplateCommand(Command):
    """
    Command to execute an analysis using a template

    Runs analysis using a predefined template configuration.
    """

    template_id: str
    symbol: str
    timeframe: str
    custom_parameters: Optional[Dict[str, Any]] = None

    @property
    def command_type(self) -> str:
        return "ExecuteAnalysisTemplate"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'template_id': self.template_id,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'custom_parameters': self.custom_parameters or {}
        }


@dataclass
class ValidateAnalysisResultsCommand(Command):
    """
    Command to validate analysis results

    Performs quality checks on analysis outputs.
    """

    analysis_id: str
    validation_rules: List[str]
    threshold_values: Optional[Dict[str, float]] = None

    @property
    def command_type(self) -> str:
        return "ValidateAnalysisResults"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'analysis_id': self.analysis_id,
            'validation_rules': self.validation_rules,
            'threshold_values': self.threshold_values or {}
        }


@dataclass
class ExportAnalysisDataCommand(Command):
    """
    Command to export analysis data

    Exports analysis results and indicators to external formats.
    """

    analysis_ids: List[str]
    export_format: str
    destination: str
    include_raw_data: bool = False
    compression: Optional[str] = None

    @property
    def command_type(self) -> str:
        return "ExportAnalysisData"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'analysis_ids': self.analysis_ids,
            'export_format': self.export_format,
            'destination': self.destination,
            'include_raw_data': self.include_raw_data,
            'compression': self.compression
        }


@dataclass
class CleanAnalysisDataCommand(Command):
    """
    Command to clean analysis data

    Removes outdated or invalid analysis results.
    """

    symbol: str
    timeframe: str
    analysis_types: List[str]
    older_than_days: int = 30

    @property
    def command_type(self) -> str:
        return "CleanAnalysisData"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'analysis_types': self.analysis_types,
            'older_than_days': self.older_than_days
        }
