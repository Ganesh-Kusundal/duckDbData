"""
Market Data Commands for CQRS Pattern
Commands for market data write operations
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from .base_command import Command
from domain.market_data.entities.market_data import MarketData, MarketDataBatch
from domain.market_data.value_objects.ohlcv import OHLCV


class UpdateMarketDataCommand(Command):
    """
    Command to update market data
    Used when new market data arrives from external sources
    """

    def __init__(self, symbol: str, market_data: MarketData, source: str = "external_feed", correlation_id: Optional[str] = None):
        super().__init__(correlation_id)
        self.symbol = symbol
        self.market_data = market_data
        self.source = source

    @property
    def command_type(self) -> str:
        return "UpdateMarketData"

    def _get_command_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'market_data': self.market_data.to_dict(),
            'source': self.source
        }


class ValidateMarketDataCommand(Command):
    """
    Command to validate market data
    Ensures data quality before processing
    """

    def __init__(self, market_data: MarketData, validation_rules: Optional[List[str]] = None, correlation_id: Optional[str] = None):
        super().__init__(correlation_id)
        self.market_data = market_data
        self.validation_rules = validation_rules or ['price_range', 'volume_positive', 'timestamp_valid']

    @property
    def command_type(self) -> str:
        return "ValidateMarketData"

    def _get_command_data(self) -> dict:
        return {
            'market_data': self.market_data.to_dict(),
            'validation_rules': self.validation_rules
        }


class ProcessMarketDataBatchCommand(Command):
    """
    Command to process a batch of market data
    Handles bulk data operations efficiently
    """

    def __init__(self, batch: MarketDataBatch, processing_options: Optional[dict] = None, correlation_id: Optional[str] = None):
        super().__init__(correlation_id)
        self.batch = batch
        self.processing_options = processing_options or {
            'validate_data': True,
            'skip_duplicates': True,
            'batch_size': 1000
        }

    @property
    def command_type(self) -> str:
        return "ProcessMarketDataBatch"

    def _get_command_data(self) -> dict:
        return {
            'batch': self.batch.to_dict(),
            'processing_options': self.processing_options
        }


@dataclass
class CalculateTechnicalIndicatorsCommand(Command):
    """
    Command to calculate technical indicators
    Triggers indicator calculations for market data
    """

    symbol: str
    timeframe: str
    indicators: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @property
    def command_type(self) -> str:
        return "CalculateTechnicalIndicators"

    def _get_command_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'indicators': self.indicators,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }


@dataclass
class DetectMarketAnomaliesCommand(Command):
    """
    Command to detect market anomalies
    Scans for unusual price movements or volume spikes
    """

    symbol: str
    timeframe: str
    anomaly_types: List[str]
    sensitivity: float = 0.05  # Anomaly detection threshold
    lookback_periods: int = 30

    @property
    def command_type(self) -> str:
        return "DetectMarketAnomalies"

    def _get_command_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'anomaly_types': self.anomaly_types,
            'sensitivity': self.sensitivity,
            'lookback_periods': self.lookback_periods
        }


@dataclass
class AggregateMarketDataCommand(Command):
    """
    Command to aggregate market data
    Creates summary statistics and aggregations
    """

    symbol: str
    timeframe: str
    aggregation_type: str  # 'daily', 'weekly', 'monthly'
    start_date: datetime
    end_date: datetime

    @property
    def command_type(self) -> str:
        return "AggregateMarketData"

    def _get_command_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'aggregation_type': self.aggregation_type,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }


@dataclass
class CleanMarketDataCommand(Command):
    """
    Command to clean market data
    Removes duplicates, fixes inconsistencies, validates data quality
    """

    symbol: str
    timeframe: str
    cleaning_operations: List[str]
    date_range: Optional[tuple[datetime, datetime]] = None

    def __post_init__(self):
        if not self.cleaning_operations:
            self.cleaning_operations = ['remove_duplicates', 'fix_missing_data', 'validate_ranges']

    @property
    def command_type(self) -> str:
        return "CleanMarketData"

    def _get_command_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'cleaning_operations': self.cleaning_operations,
            'date_range': (
                self.date_range[0].isoformat(),
                self.date_range[1].isoformat()
            ) if self.date_range else None
        }


@dataclass
class ExportMarketDataCommand(Command):
    """
    Command to export market data
    Exports data in various formats for external consumption
    """

    symbol: str
    timeframe: str
    export_format: str  # 'csv', 'json', 'parquet'
    date_range: Optional[tuple[datetime, datetime]] = None
    destination: str = "file"  # 'file', 's3', 'database'
    compression: Optional[str] = None

    @property
    def command_type(self) -> str:
        return "ExportMarketData"

    def _get_command_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'export_format': self.export_format,
            'date_range': (
                self.date_range[0].isoformat(),
                self.date_range[1].isoformat()
            ) if self.date_range else None,
            'destination': self.destination,
            'compression': self.compression
        }
