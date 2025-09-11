"""
Trading Domain Commands for CQRS Pattern

Commands for trading operations including order management,
position management, and trade execution.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from .base_command import Command


@dataclass
class SubmitOrderCommand(Command):
    """
    Command to submit a new trading order

    Creates and submits a new order for execution through the broker integration.
    """

    symbol: str
    side: str  # "BUY", "SELL", "SHORT"
    quantity: int
    order_type: str  # "MARKET", "LIMIT", "STOP", "STOP_LIMIT"
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "DAY"
    strategy_id: Optional[str] = None
    risk_profile_id: Optional[str] = None

    def __post_init__(self):
        # Initialize base Command attributes
        super().__init__()

    @property
    def command_type(self) -> str:
        return "SubmitOrder"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'order_type': self.order_type,
            'price': str(self.price) if self.price else None,
            'stop_price': str(self.stop_price) if self.stop_price else None,
            'time_in_force': self.time_in_force,
            'strategy_id': self.strategy_id,
            'risk_profile_id': self.risk_profile_id
        }


@dataclass
class CancelOrderCommand(Command):
    """
    Command to cancel an existing order

    Cancels a pending order that has not yet been filled.
    """

    order_id: str
    reason: Optional[str] = None

    def __post_init__(self):
        # Initialize base Command attributes
        super().__init__()

    @property
    def command_type(self) -> str:
        return "CancelOrder"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'order_id': self.order_id,
            'reason': self.reason
        }


@dataclass
class ModifyOrderCommand(Command):

    def __post_init__(self):
        # Initialize base Command attributes
        super().__init__()
    """
    Command to modify an existing order

    Modifies order parameters like quantity, price, or stop levels.
    """

    order_id: str
    modifications: Dict[str, Any]
    reason: Optional[str] = None

    @property
    def command_type(self) -> str:
        return "ModifyOrder"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'order_id': self.order_id,
            'modifications': self.modifications,
            'reason': self.reason
        }


@dataclass
class ClosePositionCommand(Command):

    def __post_init__(self):
        # Initialize base Command attributes
        super().__init__()
    """
    Command to close an existing position

    Closes a position by submitting an opposing order.
    """

    position_id: str
    quantity: Optional[int] = None  # None means close entire position
    order_type: str = "MARKET"
    price: Optional[Decimal] = None

    @property
    def command_type(self) -> str:
        return "ClosePosition"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'position_id': self.position_id,
            'quantity': self.quantity,
            'order_type': self.order_type,
            'price': str(self.price) if self.price else None
        }


@dataclass
class AdjustPositionCommand(Command):

    def __post_init__(self):
        # Initialize base Command attributes
        super().__init__()
    """
    Command to adjust an existing position

    Adjusts position size by adding to or reducing the position.
    """

    position_id: str
    adjustment_type: str  # "ADD", "REDUCE"
    quantity: int
    order_type: str = "MARKET"
    price: Optional[Decimal] = None

    @property
    def command_type(self) -> str:
        return "AdjustPosition"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'position_id': self.position_id,
            'adjustment_type': self.adjustment_type,
            'quantity': self.quantity,
            'order_type': self.order_type,
            'price': str(self.price) if self.price else None
        }


@dataclass
class CreateTradingStrategyCommand(Command):

    def __post_init__(self):
        # Initialize base Command attributes
        super().__init__()
    """
    Command to create a new trading strategy

    Defines a new trading strategy with entry/exit rules.
    """

    name: str
    description: str
    strategy_type: str
    parameters: Dict[str, Any]
    risk_profile_id: Optional[str] = None
    is_active: bool = True

    @property
    def command_type(self) -> str:
        return "CreateTradingStrategy"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'strategy_type': self.strategy_type,
            'parameters': self.parameters,
            'risk_profile_id': self.risk_profile_id,
            'is_active': self.is_active
        }


@dataclass
class ExecuteTradingStrategyCommand(Command):

    def __post_init__(self):
        # Initialize base Command attributes
        super().__init__()
    """
    Command to execute a trading strategy

    Triggers execution of a predefined trading strategy.
    """

    strategy_id: str
    symbol: str
    timeframe: str
    execution_parameters: Optional[Dict[str, Any]] = None

    @property
    def command_type(self) -> str:
        return "ExecuteTradingStrategy"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'execution_parameters': self.execution_parameters or {}
        }


@dataclass
class UpdatePositionRiskCommand(Command):

    def __post_init__(self):
        # Initialize base Command attributes
        super().__init__()
    """
    Command to update position risk parameters

    Adjusts risk management parameters for an existing position.
    """

    position_id: str
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    trailing_stop: Optional[Decimal] = None
    max_loss_percentage: Optional[float] = None

    @property
    def command_type(self) -> str:
        return "UpdatePositionRisk"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'position_id': self.position_id,
            'stop_loss_price': str(self.stop_loss_price) if self.stop_loss_price else None,
            'take_profit_price': str(self.take_profit_price) if self.take_profit_price else None,
            'trailing_stop': str(self.trailing_stop) if self.trailing_stop else None,
            'max_loss_percentage': self.max_loss_percentage
        }


@dataclass
class ProcessTradeExecutionCommand(Command):

    def __post_init__(self):
        # Initialize base Command attributes
        super().__init__()
    """
    Command to process a trade execution

    Records and processes the execution of a trade from broker.
    """

    order_id: str
    execution_id: str
    executed_quantity: int
    executed_price: Decimal
    execution_time: datetime
    commission: Optional[Decimal] = None
    fees: Optional[Decimal] = None

    @property
    def command_type(self) -> str:
        return "ProcessTradeExecution"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'order_id': self.order_id,
            'execution_id': self.execution_id,
            'executed_quantity': self.executed_quantity,
            'executed_price': str(self.executed_price),
            'execution_time': self.execution_time.isoformat(),
            'commission': str(self.commission) if self.commission else None,
            'fees': str(self.fees) if self.fees else None
        }


@dataclass
class RebalancePortfolioCommand(Command):

    def __post_init__(self):
        # Initialize base Command attributes
        super().__init__()
    """
    Command to rebalance portfolio

    Adjusts portfolio allocations based on target weights.
    """

    portfolio_id: str
    target_allocations: Dict[str, float]
    rebalance_type: str = "full"  # "full", "partial", "threshold"
    threshold_percentage: float = 5.0

    @property
    def command_type(self) -> str:
        return "RebalancePortfolio"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'portfolio_id': self.portfolio_id,
            'target_allocations': self.target_allocations,
            'rebalance_type': self.rebalance_type,
            'threshold_percentage': self.threshold_percentage
        }


@dataclass
class LiquidatePositionsCommand(Command):

    def __post_init__(self):
        # Initialize base Command attributes
        super().__init__()
    """
    Command to liquidate all positions

    Closes all open positions, typically for emergency situations.
    """

    reason: str
    emergency: bool = False
    order_type: str = "MARKET"

    @property
    def command_type(self) -> str:
        return "LiquidatePositions"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'reason': self.reason,
            'emergency': self.emergency,
            'order_type': self.order_type
        }
