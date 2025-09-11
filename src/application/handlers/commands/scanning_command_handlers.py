"""
Scanning Domain Command Handlers

Command handlers for scanning operations that orchestrate market scanning
and signal detection workflows.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from application.commands.base_command import CommandHandler, CommandResult
from application.commands.scanning_commands import (
    ExecuteMarketScanCommand, ExecuteRuleCommand, CreateScanCommand,
    UpdateScanRulesCommand, ConfigureScannerCommand
)
from domain.scanning.entities.scan import Scan
from domain.scanning.entities.rule import Rule
from domain.scanning.repositories.scan_repository import ScanRepository
from domain.scanning.repositories.rule_repository import RuleRepository
from domain.scanning.services.scan_execution_service import ScanExecutionService
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class ExecuteMarketScanCommandHandler(CommandHandler):
    """
    Handler for ExecuteMarketScanCommand.

    Orchestrates the execution of market scanning operations.
    """

    def __init__(self, scan_repository: Optional[ScanRepository] = None,
                 scan_execution_service: Optional[ScanExecutionService] = None):
        self.scan_repository = scan_repository
        self.scan_execution_service = scan_execution_service

    @property
    def handled_command_type(self) -> str:
        return "ExecuteMarketScan"

    async def handle(self, command: ExecuteMarketScanCommand) -> CommandResult:
        """Handle market scan execution command."""
        try:
            logger.info(f"Executing market scan for {command.symbol or 'all symbols'}")

            # Create scan entity
            scan = Scan(
                symbol=command.symbol,
                scan_type=command.scan_type,
                criteria=command.criteria,
                timeframe=command.timeframe,
                max_results=command.max_results
            )

            # Execute scan
            scan_result = {}
            if self.scan_execution_service:
                execution_result = await self.scan_execution_service.execute_scan(scan)
                scan.results = execution_result.get('results', [])
                scan.execution_time = execution_result.get('execution_time', 0.0)
                scan.metadata = execution_result.get('metadata', {})
                scan.status = "COMPLETED"
                scan.completed_at = datetime.utcnow()
            else:
                # Mock scan execution
                scan.results = [
                    {
                        "symbol": command.symbol or "AAPL",
                        "signal_type": "BREAKOUT",
                        "strength": 0.85,
                        "criteria_matched": ["volume_increase", "price_breakout"],
                        "timestamp": datetime.utcnow()
                    },
                    {
                        "symbol": command.symbol or "GOOGL",
                        "signal_type": "REVERSAL",
                        "strength": 0.72,
                        "criteria_matched": ["rsi_oversold", "momentum_shift"],
                        "timestamp": datetime.utcnow()
                    }
                ]
                scan.execution_time = 1.5
                scan.metadata = {"method": "mock", "rules_applied": 5}
                scan.status = "COMPLETED"
                scan.completed_at = datetime.utcnow()

            # Save scan to repository
            if self.scan_repository:
                await self.scan_repository.save(scan)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "scan_id": scan.id,
                    "symbol": scan.symbol,
                    "scan_type": scan.scan_type,
                    "results_count": len(scan.results),
                    "execution_time": scan.execution_time,
                    "status": scan.status,
                    "results": scan.results
                }
            )

        except Exception as e:
            logger.error(f"Market scan execution failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class ExecuteRuleCommandHandler(CommandHandler):
    """
    Handler for ExecuteRuleCommand.

    Orchestrates the execution of specific scanning rules.
    """

    def __init__(self, rule_repository: Optional[RuleRepository] = None,
                 scan_execution_service: Optional[ScanExecutionService] = None):
        self.rule_repository = rule_repository
        self.scan_execution_service = scan_execution_service

    @property
    def handled_command_type(self) -> str:
        return "ExecuteRule"

    async def handle(self, command: ExecuteRuleCommand) -> CommandResult:
        """Handle rule execution command."""
        try:
            logger.info(f"Executing rule {command.rule_id} on {command.symbol}")

            if not self.rule_repository:
                raise DomainException("Rule repository not available")

            # Find rule
            rule = await self.rule_repository.find_by_id(command.rule_id)
            if not rule:
                raise DomainException(f"Rule not found: {command.rule_id}")

            # Execute rule
            rule_result = {}
            if self.scan_execution_service:
                execution_result = await self.scan_execution_service.execute_rule(
                    rule, command.symbol, command.parameters
                )
                rule_result = execution_result
            else:
                # Mock rule execution
                rule_result = {
                    "rule_id": command.rule_id,
                    "symbol": command.symbol,
                    "condition_met": True,
                    "signal_strength": 0.8,
                    "metadata": {"execution_method": "mock"}
                }

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "rule_id": command.rule_id,
                    "symbol": command.symbol,
                    "rule_result": rule_result,
                    "executed_at": datetime.utcnow()
                }
            )

        except Exception as e:
            logger.error(f"Rule execution failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class CreateScanCommandHandler(CommandHandler):
    """
    Handler for CreateScanCommand.

    Orchestrates the creation of scan configurations.
    """

    def __init__(self, scan_repository: Optional[ScanRepository] = None):
        self.scan_repository = scan_repository

    @property
    def handled_command_type(self) -> str:
        return "CreateScan"

    async def handle(self, command: CreateScanCommand) -> CommandResult:
        """Handle scan creation command."""
        try:
            logger.info(f"Creating scan configuration: {command.name}")

            # Create scan entity
            scan = Scan(
                symbol=command.symbol,
                scan_type=command.scan_type,
                criteria=command.criteria,
                timeframe=command.timeframe,
                max_results=command.max_results,
                name=command.name,
                description=command.description
            )

            # Save scan to repository
            if self.scan_repository:
                await self.scan_repository.save(scan)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "scan_id": scan.id,
                    "name": scan.name,
                    "scan_type": scan.scan_type,
                    "symbol": scan.symbol,
                    "created_at": scan.created_at
                }
            )

        except Exception as e:
            logger.error(f"Scan creation failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class UpdateScanRulesCommandHandler(CommandHandler):
    """
    Handler for UpdateScanRulesCommand.

    Orchestrates the update of scan rules and criteria.
    """

    def __init__(self, scan_repository: Optional[ScanRepository] = None,
                 rule_repository: Optional[RuleRepository] = None):
        self.scan_repository = scan_repository
        self.rule_repository = rule_repository

    @property
    def handled_command_type(self) -> str:
        return "UpdateScanRules"

    async def handle(self, command: UpdateScanRulesCommand) -> CommandResult:
        """Handle scan rules update command."""
        try:
            logger.info(f"Updating scan rules for scan {command.scan_id}")

            if not self.scan_repository:
                raise DomainException("Scan repository not available")

            # Find existing scan
            scan = await self.scan_repository.find_by_id(command.scan_id)
            if not scan:
                raise DomainException(f"Scan not found: {command.scan_id}")

            # Apply rule updates
            updated_rules = []
            for rule_update in command.rule_updates:
                rule_id = rule_update.get("rule_id")
                updates = rule_update.get("updates", {})

                if rule_id and self.rule_repository:
                    # Update individual rule
                    rule = await self.rule_repository.find_by_id(rule_id)
                    if rule:
                        for key, value in updates.items():
                            if hasattr(rule, key):
                                setattr(rule, key, value)
                        await self.rule_repository.update(rule)
                        updated_rules.append(rule_id)

            # Update scan criteria if provided
            if command.criteria_updates:
                for key, value in command.criteria_updates.items():
                    if hasattr(scan, key):
                        setattr(scan, key, value)

                await self.scan_repository.update(scan)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "scan_id": command.scan_id,
                    "rules_updated": updated_rules,
                    "criteria_updated": bool(command.criteria_updates),
                    "updated_at": datetime.utcnow()
                }
            )

        except Exception as e:
            logger.error(f"Scan rules update failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class ConfigureScannerCommandHandler(CommandHandler):
    """
    Handler for ConfigureScannerCommand.

    Orchestrates scanner configuration and setup.
    """

    def __init__(self, rule_repository: Optional[RuleRepository] = None):
        self.rule_repository = rule_repository

    @property
    def handled_command_type(self) -> str:
        return "ConfigureScanner"

    async def handle(self, command: ConfigureScannerCommand) -> CommandResult:
        """Handle scanner configuration command."""
        try:
            logger.info(f"Configuring scanner: {command.scanner_name}")

            # Create or update scanner configuration
            scanner_config = {
                "id": f"scanner_{command.command_id}",
                "name": command.scanner_name,
                "description": command.description,
                "scan_types": command.scan_types,
                "default_criteria": command.default_criteria,
                "enabled_rules": command.enabled_rules,
                "parameters": command.parameters,
                "is_active": command.is_active,
                "created_at": datetime.utcnow()
            }

            # Save configuration (would typically go to a config repository)
            # For now, just return the configuration
            logger.info(f"Scanner configuration created: {scanner_config}")

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "scanner_id": scanner_config["id"],
                    "name": scanner_config["name"],
                    "scan_types": scanner_config["scan_types"],
                    "enabled_rules": scanner_config["enabled_rules"],
                    "is_active": scanner_config["is_active"],
                    "configured_at": scanner_config["created_at"]
                }
            )

        except Exception as e:
            logger.error(f"Scanner configuration failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )
