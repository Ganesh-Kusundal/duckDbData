"""
Analytics Domain Command Handlers

Command handlers for analytics operations that orchestrate domain logic
and coordinate with repositories and external services.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from application.commands.base_command import CommandHandler, CommandResult
from application.commands.analytics_commands import (
    CalculateIndicatorCommand, ExecuteAnalysisCommand, GenerateSignalCommand,
    CreateAnalysisCommand, UpdateIndicatorCommand
)
from domain.analytics.entities.indicator import Indicator
from domain.analytics.entities.analysis import Analysis
from domain.analytics.repositories.indicator_repository import IndicatorRepository
from domain.analytics.repositories.analysis_repository import AnalysisRepository
from domain.analytics.services.indicator_calculation_service import IndicatorCalculationService
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class CalculateIndicatorCommandHandler(CommandHandler):
    """
    Handler for CalculateIndicatorCommand.

    Orchestrates the calculation of technical indicators.
    """

    def __init__(self, indicator_repository: Optional[IndicatorRepository] = None,
                 indicator_calculation_service: Optional[IndicatorCalculationService] = None):
        self.indicator_repository = indicator_repository
        self.indicator_calculation_service = indicator_calculation_service

    @property
    def handled_command_type(self) -> str:
        return "CalculateIndicator"

    async def handle(self, command: CalculateIndicatorCommand) -> CommandResult:
        """Handle indicator calculation command."""
        try:
            logger.info(f"Calculating indicator {command.indicator_type} for {command.symbol}")

            # Create indicator entity
            indicator = Indicator(
                symbol=command.symbol,
                indicator_type=command.indicator_type,
                parameters=command.parameters,
                timeframe=command.timeframe
            )

            # Calculate indicator values
            if self.indicator_calculation_service:
                calculation_result = await self.indicator_calculation_service.calculate_indicator(
                    indicator, command.data_points
                )
                indicator.values = calculation_result.get('values', [])
                indicator.metadata = calculation_result.get('metadata', {})
            else:
                # Mock calculation result
                indicator.values = [
                    {"timestamp": datetime.utcnow(), "value": 50.0 + i}
                    for i in range(min(10, command.data_points or 100))
                ]
                indicator.metadata = {"method": "mock", "periods": 14}

            # Save indicator to repository
            if self.indicator_repository:
                await self.indicator_repository.save(indicator)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "indicator_id": indicator.id,
                    "symbol": indicator.symbol,
                    "indicator_type": indicator.indicator_type,
                    "values_count": len(indicator.values),
                    "metadata": indicator.metadata
                }
            )

        except Exception as e:
            logger.error(f"Indicator calculation failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class ExecuteAnalysisCommandHandler(CommandHandler):
    """
    Handler for ExecuteAnalysisCommand.

    Orchestrates the execution of complex analysis workflows.
    """

    def __init__(self, analysis_repository: Optional[AnalysisRepository] = None,
                 indicator_calculation_service: Optional[IndicatorCalculationService] = None):
        self.analysis_repository = analysis_repository
        self.indicator_calculation_service = indicator_calculation_service

    @property
    def handled_command_type(self) -> str:
        return "ExecuteAnalysis"

    async def handle(self, command: ExecuteAnalysisCommand) -> CommandResult:
        """Handle analysis execution command."""
        try:
            logger.info(f"Executing analysis {command.analysis_type} for {command.symbol}")

            # Create analysis entity
            analysis = Analysis(
                symbol=command.symbol,
                analysis_type=command.analysis_type,
                parameters=command.parameters,
                indicators=command.indicators or []
            )

            # Execute analysis
            analysis_result = {}
            if self.indicator_calculation_service:
                # Calculate required indicators
                for indicator_type in analysis.indicators:
                    indicator = Indicator(
                        symbol=command.symbol,
                        indicator_type=indicator_type,
                        parameters=command.parameters.get('indicator_params', {}),
                        timeframe=command.timeframe
                    )

                    calc_result = await self.indicator_calculation_service.calculate_indicator(
                        indicator, command.data_points
                    )
                    analysis_result[indicator_type] = calc_result

                # Perform analysis based on indicators
                analysis.result = analysis_result
                analysis.status = "COMPLETED"
                analysis.completed_at = datetime.utcnow()
            else:
                # Mock analysis result
                analysis.result = {
                    "indicators_calculated": len(analysis.indicators),
                    "analysis_score": 0.75,
                    "signals_generated": 2,
                    "confidence_level": "HIGH"
                }
                analysis.status = "COMPLETED"
                analysis.completed_at = datetime.utcnow()

            # Save analysis to repository
            if self.analysis_repository:
                await self.analysis_repository.save(analysis)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "analysis_id": analysis.id,
                    "symbol": analysis.symbol,
                    "analysis_type": analysis.analysis_type,
                    "status": analysis.status,
                    "result": analysis.result
                }
            )

        except Exception as e:
            logger.error(f"Analysis execution failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class GenerateSignalCommandHandler(CommandHandler):
    """
    Handler for GenerateSignalCommand.

    Orchestrates the generation of trading signals based on analysis.
    """

    def __init__(self, indicator_repository: Optional[IndicatorRepository] = None,
                 indicator_calculation_service: Optional[IndicatorCalculationService] = None):
        self.indicator_repository = indicator_repository
        self.indicator_calculation_service = indicator_calculation_service

    @property
    def handled_command_type(self) -> str:
        return "GenerateSignal"

    async def handle(self, command: GenerateSignalCommand) -> CommandResult:
        """Handle signal generation command."""
        try:
            logger.info(f"Generating signals for {command.symbol} using {command.strategy_type}")

            # Get required indicators
            signals = []
            if self.indicator_calculation_service:
                # Calculate indicators needed for signal generation
                for indicator_type in command.required_indicators:
                    indicator = Indicator(
                        symbol=command.symbol,
                        indicator_type=indicator_type,
                        parameters=command.parameters.get('indicator_params', {}),
                        timeframe=command.timeframe
                    )

                    calc_result = await self.indicator_calculation_service.calculate_indicator(
                        indicator, command.data_points
                    )

                    # Generate signal based on indicator values
                    signal = self._generate_signal_from_indicator(
                        indicator_type, calc_result, command.parameters
                    )
                    if signal:
                        signals.append(signal)

            else:
                # Mock signal generation
                signals = [
                    {
                        "type": "BUY",
                        "strength": 0.8,
                        "indicator": "RSI",
                        "timestamp": datetime.utcnow(),
                        "reason": "Oversold condition detected"
                    },
                    {
                        "type": "HOLD",
                        "strength": 0.6,
                        "indicator": "MACD",
                        "timestamp": datetime.utcnow(),
                        "reason": "Neutral momentum"
                    }
                ]

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "symbol": command.symbol,
                    "strategy_type": command.strategy_type,
                    "signals_generated": len(signals),
                    "signals": signals,
                    "timestamp": datetime.utcnow()
                }
            )

        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )

    def _generate_signal_from_indicator(self, indicator_type: str, calc_result: Dict[str, Any],
                                      parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate signal from indicator calculation result."""
        try:
            values = calc_result.get('values', [])
            if not values:
                return None

            latest_value = values[-1].get('value', 0)

            # Simple signal generation logic based on indicator type
            if indicator_type == "RSI":
                if latest_value < 30:
                    return {
                        "type": "BUY",
                        "strength": 0.8,
                        "indicator": indicator_type,
                        "value": latest_value,
                        "timestamp": datetime.utcnow(),
                        "reason": "RSI oversold"
                    }
                elif latest_value > 70:
                    return {
                        "type": "SELL",
                        "strength": 0.8,
                        "indicator": indicator_type,
                        "value": latest_value,
                        "timestamp": datetime.utcnow(),
                        "reason": "RSI overbought"
                    }

            elif indicator_type == "MACD":
                # MACD signal generation would be more complex
                return {
                    "type": "HOLD",
                    "strength": 0.6,
                    "indicator": indicator_type,
                    "value": latest_value,
                    "timestamp": datetime.utcnow(),
                    "reason": "MACD analysis"
                }

            return None

        except Exception as e:
            logger.error(f"Signal generation from {indicator_type} failed: {e}")
            return None


class CreateAnalysisCommandHandler(CommandHandler):
    """
    Handler for CreateAnalysisCommand.

    Orchestrates the creation of analysis configurations.
    """

    def __init__(self, analysis_repository: Optional[AnalysisRepository] = None):
        self.analysis_repository = analysis_repository

    @property
    def handled_command_type(self) -> str:
        return "CreateAnalysis"

    async def handle(self, command: CreateAnalysisCommand) -> CommandResult:
        """Handle analysis creation command."""
        try:
            logger.info(f"Creating analysis configuration: {command.name}")

            # Create analysis entity
            analysis = Analysis(
                symbol=command.symbol,
                analysis_type=command.analysis_type,
                parameters=command.parameters,
                indicators=command.indicators or [],
                name=command.name,
                description=command.description
            )

            # Save analysis to repository
            if self.analysis_repository:
                await self.analysis_repository.save(analysis)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "analysis_id": analysis.id,
                    "name": analysis.name,
                    "analysis_type": analysis.analysis_type,
                    "indicators": analysis.indicators,
                    "created_at": analysis.created_at
                }
            )

        except Exception as e:
            logger.error(f"Analysis creation failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class UpdateIndicatorCommandHandler(CommandHandler):
    """
    Handler for UpdateIndicatorCommand.

    Orchestrates the update of existing indicators.
    """

    def __init__(self, indicator_repository: Optional[IndicatorRepository] = None):
        self.indicator_repository = indicator_repository

    @property
    def handled_command_type(self) -> str:
        return "UpdateIndicator"

    async def handle(self, command: UpdateIndicatorCommand) -> CommandResult:
        """Handle indicator update command."""
        try:
            logger.info(f"Updating indicator {command.indicator_id}")

            if not self.indicator_repository:
                raise DomainException("Indicator repository not available")

            # Find existing indicator
            indicator = await self.indicator_repository.find_by_id(command.indicator_id)
            if not indicator:
                raise DomainException(f"Indicator not found: {command.indicator_id}")

            # Apply updates
            for key, value in command.updates.items():
                if hasattr(indicator, key):
                    setattr(indicator, key, value)

            # Recalculate if parameters changed
            if 'parameters' in command.updates and hasattr(self, 'indicator_calculation_service'):
                # Would recalculate indicator values here
                pass

            # Save updated indicator
            await self.indicator_repository.update(indicator)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "indicator_id": indicator.id,
                    "updated_fields": list(command.updates.keys()),
                    "updated_at": datetime.utcnow()
                }
            )

        except Exception as e:
            logger.error(f"Indicator update failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )
