"""
Scanning Domain Commands for CQRS Pattern

Commands for scanning operations including market scanning,
signal generation, and rule execution.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base_command import Command


@dataclass
class ExecuteMarketScanCommand(Command):
    """
    Command to execute a market scan

    Runs a scan against market data using specified criteria and rules.
    """

    scan_type: str
    symbol_filter: Optional[str] = None
    scan_date: Optional[datetime] = None
    parameters: Optional[Dict[str, Any]] = None

    @property
    def command_type(self) -> str:
        return "ExecuteMarketScan"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'scan_type': self.scan_type,
            'symbol_filter': self.symbol_filter,
            'scan_date': self.scan_date.isoformat() if self.scan_date else None,
            'parameters': self.parameters or {}
        }


@dataclass
class ExecuteRuleCommand(Command):
    """
    Command to execute a specific scanning rule

    Runs a single rule against market data.
    """

    rule_id: str
    symbol: str
    scan_date: Optional[datetime] = None
    parameters: Optional[Dict[str, Any]] = None

    @property
    def command_type(self) -> str:
        return "ExecuteRule"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'symbol': self.symbol,
            'scan_date': self.scan_date.isoformat() if self.scan_date else None,
            'parameters': self.parameters or {}
        }


@dataclass
class CreateScanTemplateCommand(Command):
    """
    Command to create a scan template

    Defines a reusable scan configuration.
    """

    name: str
    description: str
    scan_type: str
    default_parameters: Dict[str, Any]
    rules: List[str]
    is_active: bool = True

    @property
    def command_type(self) -> str:
        return "CreateScanTemplate"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'scan_type': self.scan_type,
            'default_parameters': self.default_parameters,
            'rules': self.rules,
            'is_active': self.is_active
        }


@dataclass
class ExecuteScanTemplateCommand(Command):
    """
    Command to execute a scan using a template

    Runs a scan using a predefined template configuration.
    """

    template_id: str
    symbol_filter: Optional[str] = None
    scan_date: Optional[datetime] = None
    custom_parameters: Optional[Dict[str, Any]] = None

    @property
    def command_type(self) -> str:
        return "ExecuteScanTemplate"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'template_id': self.template_id,
            'symbol_filter': self.symbol_filter,
            'scan_date': self.scan_date.isoformat() if self.scan_date else None,
            'custom_parameters': self.custom_parameters or {}
        }


@dataclass
class CreateScanningRuleCommand(Command):
    """
    Command to create a new scanning rule

    Defines a new rule for market scanning.
    """

    name: str
    description: str
    rule_type: str
    parameters: Dict[str, Any]
    conditions: List[Dict[str, Any]]
    is_active: bool = True

    @property
    def command_type(self) -> str:
        return "CreateScanningRule"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'rule_type': self.rule_type,
            'parameters': self.parameters,
            'conditions': self.conditions,
            'is_active': self.is_active
        }


@dataclass
class UpdateScanningRuleCommand(Command):
    """
    Command to update an existing scanning rule

    Modifies parameters or conditions of an existing rule.
    """

    rule_id: str
    updates: Dict[str, Any]

    @property
    def command_type(self) -> str:
        return "UpdateScanningRule"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'updates': self.updates
        }


@dataclass
class ValidateScanningRuleCommand(Command):
    """
    Command to validate a scanning rule

    Performs validation checks on rule configuration and logic.
    """

    rule_id: str
    test_symbols: List[str]
    validation_period_days: int = 30

    @property
    def command_type(self) -> str:
        return "ValidateScanningRule"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'test_symbols': self.test_symbols,
            'validation_period_days': self.validation_period_days
        }


@dataclass
class GenerateScanReportCommand(Command):
    """
    Command to generate a scan report

    Creates a report based on scan results.
    """

    scan_id: str
    report_format: str = "html"
    include_details: bool = True
    include_charts: bool = True

    @property
    def command_type(self) -> str:
        return "GenerateScanReport"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'scan_id': self.scan_id,
            'report_format': self.report_format,
            'include_details': self.include_details,
            'include_charts': self.include_charts
        }


@dataclass
class BacktestScanningRuleCommand(Command):
    """
    Command to backtest a scanning rule

    Tests rule performance against historical data.
    """

    rule_id: str
    start_date: datetime
    end_date: datetime
    symbols: List[str]
    backtest_parameters: Optional[Dict[str, Any]] = None

    @property
    def command_type(self) -> str:
        return "BacktestScanningRule"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'symbols': self.symbols,
            'backtest_parameters': self.backtest_parameters or {}
        }


@dataclass
class OptimizeScanningRuleCommand(Command):
    """
    Command to optimize a scanning rule

    Uses optimization algorithms to improve rule parameters.
    """

    rule_id: str
    optimization_target: str
    parameter_ranges: Dict[str, Dict[str, Any]]
    start_date: datetime
    end_date: datetime
    symbols: List[str]

    @property
    def command_type(self) -> str:
        return "OptimizeScanningRule"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'optimization_target': self.optimization_target,
            'parameter_ranges': self.parameter_ranges,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'symbols': self.symbols
        }


@dataclass
class ExportScanResultsCommand(Command):
    """
    Command to export scan results

    Exports scan results to external formats for analysis.
    """

    scan_id: str
    export_format: str
    destination: str
    include_signals: bool = True
    include_raw_data: bool = False

    @property
    def command_type(self) -> str:
        return "ExportScanResults"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'scan_id': self.scan_id,
            'export_format': self.export_format,
            'destination': self.destination,
            'include_signals': self.include_signals,
            'include_raw_data': self.include_raw_data
        }


@dataclass
class CleanScanDataCommand(Command):
    """
    Command to clean scan data

    Removes outdated or invalid scan results and signals.
    """

    older_than_days: int = 90
    scan_types: Optional[List[str]] = None

    @property
    def command_type(self) -> str:
        return "CleanScanData"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'older_than_days': self.older_than_days,
            'scan_types': self.scan_types
        }
