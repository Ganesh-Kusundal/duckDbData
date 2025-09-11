"""
Market Data Command Handlers
CQRS command handlers for market data operations
"""

import logging
from typing import List
from datetime import datetime

from ...commands.base_command import CommandHandler, CommandResult
from ...commands.market_data_commands import (
    UpdateMarketDataCommand,
    ValidateMarketDataCommand,
    ProcessMarketDataBatchCommand
)
from domain.market_data.repositories.market_data_repository import MarketDataRepository
from domain.market_data.services.market_data_service import MarketDataService
try:
    from infrastructure.messaging.event_types import MarketDataReceived, MarketDataUpdated
except ImportError:
    # Fallback for when infrastructure dependencies are not available
    MarketDataReceived = None
    MarketDataUpdated = None

logger = logging.getLogger(__name__)


class UpdateMarketDataCommandHandler(CommandHandler):
    """
    Handler for UpdateMarketDataCommand
    Processes market data updates and stores them in the repository
    """

    def __init__(self, repository: MarketDataRepository):
        self.repository = repository

    @property
    def handled_command_type(self) -> str:
        return "UpdateMarketData"

    async def handle(self, command: UpdateMarketDataCommand) -> CommandResult:
        """
        Handle market data update command

        Args:
            command: UpdateMarketDataCommand with market data to update

        Returns:
            CommandResult with operation outcome
        """
        try:
            logger.info(f"Processing market data update for {command.symbol}")

            # Save market data to repository
            success = await self.repository.save(command.market_data)

            if success:
                # Create domain event
                event = MarketDataReceived(
                    aggregate_id=f"market_data_{command.symbol}",
                    symbol=command.symbol,
                    price=command.market_data.ohlcv.close,
                    volume=command.market_data.ohlcv.volume,
                    timestamp=command.market_data.parsed_timestamp,
                    exchange=getattr(command.market_data, 'exchange', 'NSE')
                )

                result = CommandResult(
                    success=True,
                    command_id=command.command_id,
                    data={'saved': True, 'symbol': command.symbol}
                )
                result.add_event(event)

                logger.info(f"Successfully updated market data for {command.symbol}")
                return result
            else:
                logger.error(f"Failed to save market data for {command.symbol}")
                return CommandResult(
                    success=False,
                    command_id=command.command_id,
                    error_message="Failed to save market data"
                )

        except Exception as e:
            logger.error(f"Error processing market data update for {command.symbol}: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class ValidateMarketDataCommandHandler(CommandHandler):
    """
    Handler for ValidateMarketDataCommand
    Validates market data according to business rules
    """

    def __init__(self, market_data_service: MarketDataService):
        self.market_data_service = market_data_service

    @property
    def handled_command_type(self) -> str:
        return "ValidateMarketData"

    async def handle(self, command: ValidateMarketDataCommand) -> CommandResult:
        """
        Handle market data validation command

        Args:
            command: ValidateMarketDataCommand with data to validate

        Returns:
            CommandResult with validation outcome
        """
        try:
            logger.info(f"Validating market data for symbol: {command.market_data.symbol}")

            # Perform validation
            validation_errors = await self.market_data_service.validate_market_data(
                command.market_data
            )

            if not validation_errors:
                logger.info(f"Market data validation passed for {command.market_data.symbol}")
                return CommandResult(
                    success=True,
                    command_id=command.command_id,
                    data={
                        'validated': True,
                        'symbol': command.market_data.symbol,
                        'validation_errors': []
                    }
                )
            else:
                logger.warning(f"Market data validation failed for {command.market_data.symbol}: {validation_errors}")
                return CommandResult(
                    success=False,
                    command_id=command.command_id,
                    error_message="Market data validation failed",
                    data={
                        'validated': False,
                        'symbol': command.market_data.symbol,
                        'validation_errors': validation_errors
                    }
                )

        except Exception as e:
            logger.error(f"Error validating market data: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class ProcessMarketDataBatchCommandHandler(CommandHandler):
    """
    Handler for ProcessMarketDataBatchCommand
    Processes batches of market data efficiently
    """

    def __init__(self, repository: MarketDataRepository, market_data_service: MarketDataService):
        self.repository = repository
        self.market_data_service = market_data_service

    @property
    def handled_command_type(self) -> str:
        return "ProcessMarketDataBatch"

    async def handle(self, command: ProcessMarketDataBatchCommand) -> CommandResult:
        """
        Handle market data batch processing command

        Args:
            command: ProcessMarketDataBatchCommand with batch to process

        Returns:
            CommandResult with processing outcome
        """
        try:
            logger.info(f"Processing market data batch for {command.batch.symbol}")

            batch = command.batch
            processed_count = 0
            validation_errors = []
            events = []

            # Process each record in the batch
            for record in batch.data:
                # Validate if requested
                if command.processing_options.get('validate_data', True):
                    errors = await self.market_data_service.validate_market_data(record)
                    if errors:
                        validation_errors.extend(errors)
                        if command.processing_options.get('skip_invalid', True):
                            continue

                # Skip duplicates if requested
                if command.processing_options.get('skip_duplicates', True):
                    exists = await self.repository.exists(
                        record.symbol,
                        record.timestamp,
                        record.timeframe
                    )
                    if exists:
                        continue

                # Save the record
                success = await self.repository.save(record)
                if success:
                    processed_count += 1

                    # Create event for successful processing
                    event = MarketDataReceived(
                        aggregate_id=f"market_data_{record.symbol}",
                        symbol=record.symbol,
                        price=record.ohlcv.close,
                        volume=record.ohlcv.volume,
                        timestamp=record.parsed_timestamp,
                        exchange=getattr(record, 'exchange', 'NSE')
                    )
                    events.append(event)

            # Prepare result
            result_data = {
                'batch_symbol': batch.symbol,
                'total_records': len(batch.data),
                'processed_records': processed_count,
                'skipped_records': len(batch.data) - processed_count,
                'validation_errors': validation_errors
            }

            result = CommandResult(
                success=True,
                command_id=command.command_id,
                data=result_data
            )

            # Add events
            for event in events:
                result.add_event(event)

            logger.info(f"Processed {processed_count}/{len(batch.data)} records for {batch.symbol}")

            if validation_errors:
                result.success = False
                result.error_message = f"Batch processing completed with {len(validation_errors)} validation errors"

            return result

        except Exception as e:
            logger.error(f"Error processing market data batch: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )
