"""
Trading Domain

This package contains the Trading bounded context with entities,
value objects, repositories, and domain services for order management,
position tracking, and trade execution.
"""

from .entities.order import Order, OrderId, OrderType, OrderSide, OrderStatus, Fill, FillId
from .entities.position import Position, PositionId, PositionTrade
from .value_objects.trading_strategy import TradingStrategy, TradingSignal, StrategyId, StrategyName, RiskParameters
from .repositories.order_repository import OrderRepository
from .repositories.position_repository import PositionRepository
from .services.order_execution_service import OrderExecutionService

__all__ = [
    # Entities
    'Order',
    'OrderId',
    'OrderType',
    'OrderSide',
    'OrderStatus',
    'Fill',
    'FillId',
    'Position',
    'PositionId',
    'PositionTrade',

    # Value Objects
    'TradingStrategy',
    'TradingSignal',
    'StrategyId',
    'StrategyName',
    'RiskParameters',

    # Repositories
    'OrderRepository',
    'PositionRepository',

    # Services
    'OrderExecutionService'
]

