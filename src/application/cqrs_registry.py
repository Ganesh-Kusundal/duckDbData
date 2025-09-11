"""
CQRS Registry - Central coordination for Commands and Queries

This module provides a unified registry for managing command and query handlers
across all domains, enabling consistent CQRS implementation.
"""

from typing import Dict, List, Type, Any, Optional
import logging
from dataclasses import dataclass

from .commands.base_command import Command, CommandHandler, CommandBus
from .queries.base_query import Query, QueryHandler, QueryBus
from .commands import (
    trading_commands, analytics_commands, scanning_commands,
    risk_management_commands, broker_integration_commands
)
from .queries import (
    trading_queries, analytics_queries, scanning_queries,
    risk_management_queries, broker_integration_queries
)

logger = logging.getLogger(__name__)


@dataclass
class CQRSConfig:
    """Configuration for CQRS registry."""
    enable_command_logging: bool = True
    enable_query_logging: bool = True
    enable_performance_monitoring: bool = True
    command_timeout_seconds: int = 30
    query_timeout_seconds: int = 30


class CQRSRegistry:
    """
    Central registry for CQRS handlers and buses.

    Manages registration and execution of commands and queries across all domains.
    """

    def __init__(self, config: Optional[CQRSConfig] = None):
        self.config = config or CQRSConfig()
        self.command_bus = CommandBus()
        self.query_bus = QueryBus()
        self._handlers_registered = False

        # Domain handler mappings
        self._domain_handlers = {
            'trading': self._register_trading_handlers,
            'analytics': self._register_analytics_handlers,
            'scanning': self._register_scanning_handlers,
            'risk_management': self._register_risk_management_handlers,
            'broker_integration': self._register_broker_integration_handlers
        }

    def initialize(self) -> None:
        """Initialize the CQRS registry and register all handlers."""
        if not self._handlers_registered:
            logger.info("Initializing CQRS Registry...")
            self._register_all_handlers()
            self._handlers_registered = True
            logger.info("CQRS Registry initialized successfully")

    def _register_all_handlers(self) -> None:
        """Register all command and query handlers."""
        for domain_name, register_func in self._domain_handlers.items():
            try:
                register_func()
                logger.debug(f"Registered handlers for domain: {domain_name}")
            except Exception as e:
                logger.error(f"Failed to register handlers for domain {domain_name}: {e}")
                raise

    def _register_trading_handlers(self) -> None:
        """Register trading domain handlers."""
        # Import handler implementations
        try:
            from .handlers.commands.trading_command_handlers import (
                SubmitOrderCommandHandler,
                CancelOrderCommandHandler,
                ModifyOrderCommandHandler,
                ClosePositionCommandHandler
            )
            from .handlers.queries.trading_query_handlers import (
                GetOrderByIdQueryHandler,
                GetOrdersBySymbolQueryHandler,
                GetPortfolioSummaryQueryHandler
            )

            # Register command handlers
            self.command_bus.register_handler("SubmitOrder", SubmitOrderCommandHandler())
            self.command_bus.register_handler("CancelOrder", CancelOrderCommandHandler())
            self.command_bus.register_handler("ModifyOrder", ModifyOrderCommandHandler())
            self.command_bus.register_handler("ClosePosition", ClosePositionCommandHandler())

            # Register query handlers
            self.query_bus.register_handler("GetOrderById", GetOrderByIdQueryHandler())
            self.query_bus.register_handler("GetOrdersBySymbol", GetOrdersBySymbolQueryHandler())
            self.query_bus.register_handler("GetPortfolioSummary", GetPortfolioSummaryQueryHandler())

        except ImportError as e:
            logger.warning(f"Trading handlers not available: {e}")

    def _register_analytics_handlers(self) -> None:
        """Register analytics domain handlers."""
        try:
            from .handlers.commands.analytics_command_handlers import (
                CalculateIndicatorCommandHandler,
                ExecuteAnalysisCommandHandler
            )
            from .handlers.queries.analytics_query_handlers import (
                GetIndicatorByIdQueryHandler,
                GetAnalysisByIdQueryHandler
            )

            # Register command handlers
            self.command_bus.register_handler("CalculateIndicator", CalculateIndicatorCommandHandler())
            self.command_bus.register_handler("ExecuteAnalysis", ExecuteAnalysisCommandHandler())

            # Register query handlers
            self.query_bus.register_handler("GetIndicatorById", GetIndicatorByIdQueryHandler())
            self.query_bus.register_handler("GetAnalysisById", GetAnalysisByIdQueryHandler())

        except ImportError as e:
            logger.warning(f"Analytics handlers not available: {e}")

    def _register_scanning_handlers(self) -> None:
        """Register scanning domain handlers."""
        try:
            from .handlers.commands.scanning_command_handlers import (
                ExecuteMarketScanCommandHandler,
                ExecuteRuleCommandHandler
            )
            from .handlers.queries.scanning_query_handlers import (
                GetScanByIdQueryHandler,
                GetScanResultsQueryHandler
            )

            # Register command handlers
            self.command_bus.register_handler("ExecuteMarketScan", ExecuteMarketScanCommandHandler())
            self.command_bus.register_handler("ExecuteRule", ExecuteRuleCommandHandler())

            # Register query handlers
            self.query_bus.register_handler("GetScanById", GetScanByIdQueryHandler())
            self.query_bus.register_handler("GetScanResults", GetScanResultsQueryHandler())

        except ImportError as e:
            logger.warning(f"Scanning handlers not available: {e}")

    def _register_risk_management_handlers(self) -> None:
        """Register risk management domain handlers."""
        try:
            from .handlers.commands.risk_management_command_handlers import (
                AssessPortfolioRiskCommandHandler,
                UpdateRiskLimitsCommandHandler
            )
            from .handlers.queries.risk_management_query_handlers import (
                GetRiskAssessmentByIdQueryHandler,
                GetRiskProfilesQueryHandler
            )

            # Register command handlers
            self.command_bus.register_handler("AssessPortfolioRisk", AssessPortfolioRiskCommandHandler())
            self.command_bus.register_handler("UpdateRiskLimits", UpdateRiskLimitsCommandHandler())

            # Register query handlers
            self.query_bus.register_handler("GetRiskAssessmentById", GetRiskAssessmentByIdQueryHandler())
            self.query_bus.register_handler("GetRiskProfiles", GetRiskProfilesQueryHandler())

        except ImportError as e:
            logger.warning(f"Risk management handlers not available: {e}")

    def _register_broker_integration_handlers(self) -> None:
        """Register broker integration domain handlers."""
        try:
            from .handlers.commands.broker_integration_command_handlers import (
                EstablishBrokerConnectionCommandHandler,
                SubmitBrokerOrderCommandHandler
            )
            from .handlers.queries.broker_integration_query_handlers import (
                GetBrokerConnectionByIdQueryHandler,
                GetBrokerAccountsQueryHandler
            )

            # Register command handlers
            self.command_bus.register_handler("EstablishBrokerConnection", EstablishBrokerConnectionCommandHandler())
            self.command_bus.register_handler("SubmitBrokerOrder", SubmitBrokerOrderCommandHandler())

            # Register query handlers
            self.query_bus.register_handler("GetBrokerConnectionById", GetBrokerConnectionByIdQueryHandler())
            self.query_bus.register_handler("GetBrokerAccounts", GetBrokerAccountsQueryHandler())

        except ImportError as e:
            logger.warning(f"Broker integration handlers not available: {e}")

    async def execute_command(self, command: Command) -> Any:
        """Execute a command through the command bus."""
        if self.config.enable_command_logging:
            logger.info(f"Executing command: {command.command_type} (ID: {command.command_id})")

        try:
            result = await self.command_bus.send(command)

            if self.config.enable_command_logging:
                status = "SUCCESS" if result.success else "FAILED"
                logger.info(f"Command {command.command_id} completed: {status}")

            return result

        except Exception as e:
            logger.error(f"Command execution failed: {command.command_id} - {e}")
            raise

    async def execute_query(self, query: Query) -> Any:
        """Execute a query through the query bus."""
        if self.config.enable_query_logging:
            logger.info(f"Executing query: {query.query_type} (ID: {query.query_id})")

        try:
            result = await self.query_bus.send(query)

            if self.config.enable_query_logging:
                logger.info(f"Query {query.query_id} completed successfully")

            return result

        except Exception as e:
            logger.error(f"Query execution failed: {query.query_id} - {e}")
            raise

    def get_registered_commands(self) -> List[str]:
        """Get list of all registered command types."""
        return self.command_bus.get_registered_commands()

    def get_registered_queries(self) -> List[str]:
        """Get list of all registered query types."""
        return self.query_bus.get_registered_queries()

    def has_command_handler(self, command_type: str) -> bool:
        """Check if a command handler is registered."""
        return self.command_bus.has_handler(command_type)

    def has_query_handler(self, query_type: str) -> bool:
        """Check if a query handler is registered."""
        return self.query_bus.has_handler(query_type)

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            'commands_registered': len(self.get_registered_commands()),
            'queries_registered': len(self.get_registered_queries()),
            'domains_registered': len(self._domain_handlers),
            'command_handlers': self.get_registered_commands(),
            'query_handlers': self.get_registered_queries()
        }


# Global registry instance
_cqrs_registry: Optional[CQRSRegistry] = None


def get_cqrs_registry(config: Optional[CQRSConfig] = None) -> CQRSRegistry:
    """Get global CQRS registry instance."""
    global _cqrs_registry
    if _cqrs_registry is None:
        _cqrs_registry = CQRSRegistry(config)
        _cqrs_registry.initialize()
    return _cqrs_registry


def reset_cqrs_registry():
    """Reset global CQRS registry (mainly for testing)."""
    global _cqrs_registry
    _cqrs_registry = None


# Convenience functions for direct access
async def execute_command(command: Command) -> Any:
    """Execute a command using the global registry."""
    registry = get_cqrs_registry()
    return await registry.execute_command(command)


async def execute_query(query: Query) -> Any:
    """Execute a query using the global registry."""
    registry = get_cqrs_registry()
    return await registry.execute_query(query)
