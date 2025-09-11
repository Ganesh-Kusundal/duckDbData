"""
Broker Integration Order Execution Repository

This module defines the repository interface and implementation for
managing order execution and tracking in the Broker Integration domain.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal

from domain.broker_integration.value_objects.order_execution import (
    BrokerOrder, ExecutionReport, OrderStatusUpdate
)
from domain.shared.exceptions import DomainException


class OrderExecutionRepository(ABC):
    """Abstract repository for order execution management."""

    @abstractmethod
    def save_order(self, order: BrokerOrder) -> None:
        """Save a broker order."""
        pass

    @abstractmethod
    def find_order_by_id(self, broker_order_id: str) -> Optional[BrokerOrder]:
        """Find broker order by ID."""
        pass

    @abstractmethod
    def find_orders_by_symbol(self, symbol: str) -> List[BrokerOrder]:
        """Find broker orders by symbol."""
        pass

    @abstractmethod
    def find_orders_by_date_range(self, start_date: date, end_date: date) -> List[BrokerOrder]:
        """Find broker orders within date range."""
        pass

    @abstractmethod
    def find_pending_orders(self) -> List[BrokerOrder]:
        """Find all pending orders."""
        pass

    @abstractmethod
    def find_filled_orders(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[BrokerOrder]:
        """Find filled orders within date range."""
        pass

    @abstractmethod
    def update_order_status(self, broker_order_id: str, status_update: OrderStatusUpdate) -> None:
        """Update order status."""
        pass

    @abstractmethod
    def delete_order(self, broker_order_id: str) -> None:
        """Delete a broker order."""
        pass

    @abstractmethod
    def get_order_summary(self, broker_order_id: str) -> Dict[str, Any]:
        """Get order summary with execution details."""
        pass


class ExecutionReportRepository(ABC):
    """Abstract repository for execution reports."""

    @abstractmethod
    def save_report(self, report: ExecutionReport) -> None:
        """Save an execution report."""
        pass

    @abstractmethod
    def find_reports_by_order(self, broker_order_id: str) -> List[ExecutionReport]:
        """Find execution reports for a specific order."""
        pass

    @abstractmethod
    def find_reports_by_symbol(self, symbol: str) -> List[ExecutionReport]:
        """Find execution reports by symbol."""
        pass

    @abstractmethod
    def find_reports_by_date_range(self, start_date: date, end_date: date) -> List[ExecutionReport]:
        """Find execution reports within date range."""
        pass

    @abstractmethod
    def get_execution_summary(self, broker_order_id: str) -> Dict[str, Any]:
        """Get execution summary for an order."""
        pass

    @abstractmethod
    def get_total_executed_quantity(self, broker_order_id: str) -> int:
        """Get total executed quantity for an order."""
        pass

    @abstractmethod
    def get_average_execution_price(self, broker_order_id: str) -> Optional[Decimal]:
        """Get average execution price for an order."""
        pass


class OrderStatusRepository(ABC):
    """Abstract repository for order status tracking."""

    @abstractmethod
    def save_status_update(self, status_update: OrderStatusUpdate) -> None:
        """Save order status update."""
        pass

    @abstractmethod
    def find_status_history(self, broker_order_id: str) -> List[OrderStatusUpdate]:
        """Find status history for an order."""
        pass

    @abstractmethod
    def find_latest_status(self, broker_order_id: str) -> Optional[OrderStatusUpdate]:
        """Find latest status for an order."""
        pass

    @abstractmethod
    def get_status_summary(self, broker_order_id: str) -> Dict[str, Any]:
        """Get status summary for an order."""
        pass


class InMemoryOrderExecutionRepository(OrderExecutionRepository):
    """In-memory implementation of order execution repository."""

    def __init__(self):
        self._orders: Dict[str, BrokerOrder] = {}
        self._status_updates: Dict[str, List[OrderStatusUpdate]] = {}

    def save_order(self, order: BrokerOrder) -> None:
        """Save a broker order."""
        self._orders[order.broker_order_id] = order

    def find_order_by_id(self, broker_order_id: str) -> Optional[BrokerOrder]:
        """Find broker order by ID."""
        return self._orders.get(broker_order_id)

    def find_orders_by_symbol(self, symbol: str) -> List[BrokerOrder]:
        """Find broker orders by symbol."""
        return [
            order for order in self._orders.values()
            if order.symbol == symbol
        ]

    def find_orders_by_date_range(self, start_date: date, end_date: date) -> List[BrokerOrder]:
        """Find broker orders within date range."""
        # Note: This is a simplified implementation
        # In real implementation, orders would have timestamps
        return list(self._orders.values())

    def find_pending_orders(self) -> List[BrokerOrder]:
        """Find all pending orders."""
        pending_order_ids = []
        for order_id, updates in self._status_updates.items():
            if updates:
                latest_status = max(updates, key=lambda x: x.updated_at)
                if latest_status.is_pending() or latest_status.is_partially_filled():
                    pending_order_ids.append(order_id)

        return [self._orders[oid] for oid in pending_order_ids if oid in self._orders]

    def find_filled_orders(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[BrokerOrder]:
        """Find filled orders within date range."""
        filled_order_ids = []
        for order_id, updates in self._status_updates.items():
            if updates:
                latest_status = max(updates, key=lambda x: x.updated_at)
                if latest_status.is_filled():
                    filled_order_ids.append(order_id)

        return [self._orders[oid] for oid in filled_order_ids if oid in self._orders]

    def update_order_status(self, broker_order_id: str, status_update: OrderStatusUpdate) -> None:
        """Update order status."""
        if broker_order_id not in self._status_updates:
            self._status_updates[broker_order_id] = []
        self._status_updates[broker_order_id].append(status_update)

    def delete_order(self, broker_order_id: str) -> None:
        """Delete a broker order."""
        if broker_order_id in self._orders:
            del self._orders[broker_order_id]
        if broker_order_id in self._status_updates:
            del self._status_updates[broker_order_id]

    def get_order_summary(self, broker_order_id: str) -> Dict[str, Any]:
        """Get order summary with execution details."""
        order = self.find_order_by_id(broker_order_id)
        if not order:
            raise DomainException(f"Order not found: {broker_order_id}")

        status_updates = self._status_updates.get(broker_order_id, [])
        latest_status = None
        if status_updates:
            latest_status = max(status_updates, key=lambda x: x.updated_at)

        return {
            'broker_order_id': order.broker_order_id,
            'symbol': order.symbol,
            'side': order.side,
            'quantity': order.quantity,
            'order_type': order.order_type,
            'price': order.price,
            'stop_price': order.stop_price,
            'trail_amount': order.trail_amount,
            'execution_params': order.execution_params.get_execution_summary(),
            'latest_status': latest_status.get_fill_percentage() if latest_status else 0,
            'status_updates_count': len(status_updates)
        }


class InMemoryExecutionReportRepository(ExecutionReportRepository):
    """In-memory implementation of execution report repository."""

    def __init__(self):
        self._reports: Dict[str, List[ExecutionReport]] = {}

    def save_report(self, report: ExecutionReport) -> None:
        """Save an execution report."""
        if report.broker_order_id not in self._reports:
            self._reports[report.broker_order_id] = []
        self._reports[report.broker_order_id].append(report)

    def find_reports_by_order(self, broker_order_id: str) -> List[ExecutionReport]:
        """Find execution reports for a specific order."""
        return self._reports.get(broker_order_id, [])

    def find_reports_by_symbol(self, symbol: str) -> List[ExecutionReport]:
        """Find execution reports by symbol."""
        matching_reports = []
        for order_reports in self._reports.values():
            for report in order_reports:
                if report.symbol == symbol:
                    matching_reports.append(report)
        return matching_reports

    def find_reports_by_date_range(self, start_date: date, end_date: date) -> List[ExecutionReport]:
        """Find execution reports within date range."""
        matching_reports = []
        for order_reports in self._reports.values():
            for report in order_reports:
                report_date = report.execution_time.date()
                if start_date <= report_date <= end_date:
                    matching_reports.append(report)
        return matching_reports

    def get_execution_summary(self, broker_order_id: str) -> Dict[str, Any]:
        """Get execution summary for an order."""
        reports = self.find_reports_by_order(broker_order_id)
        if not reports:
            return {
                'total_executed_quantity': 0,
                'total_value': 0,
                'average_price': None,
                'total_commission': 0,
                'total_fees': 0,
                'execution_count': 0
            }

        total_quantity = sum(report.executed_quantity for report in reports)
        total_value = sum(report.get_execution_value() for report in reports)
        total_commission = sum(report.commission or 0 for report in reports)
        total_fees = sum(report.fees or 0 for report in reports)
        average_price = total_value / Decimal(str(total_quantity)) if total_quantity > 0 else None

        return {
            'total_executed_quantity': total_quantity,
            'total_value': total_value,
            'average_price': average_price,
            'total_commission': total_commission,
            'total_fees': total_fees,
            'execution_count': len(reports)
        }

    def get_total_executed_quantity(self, broker_order_id: str) -> int:
        """Get total executed quantity for an order."""
        reports = self.find_reports_by_order(broker_order_id)
        return sum(report.executed_quantity for report in reports)

    def get_average_execution_price(self, broker_order_id: str) -> Optional[Decimal]:
        """Get average execution price for an order."""
        summary = self.get_execution_summary(broker_order_id)
        return summary['average_price']


class InMemoryOrderStatusRepository(OrderStatusRepository):
    """In-memory implementation of order status repository."""

    def __init__(self):
        self._status_history: Dict[str, List[OrderStatusUpdate]] = {}

    def save_status_update(self, status_update: OrderStatusUpdate) -> None:
        """Save order status update."""
        if status_update.broker_order_id not in self._status_history:
            self._status_history[status_update.broker_order_id] = []
        self._status_history[status_update.broker_order_id].append(status_update)

    def find_status_history(self, broker_order_id: str) -> List[OrderStatusUpdate]:
        """Find status history for an order."""
        return self._status_history.get(broker_order_id, [])

    def find_latest_status(self, broker_order_id: str) -> Optional[OrderStatusUpdate]:
        """Find latest status for an order."""
        history = self.find_status_history(broker_order_id)
        if not history:
            return None
        return max(history, key=lambda x: x.updated_at)

    def get_status_summary(self, broker_order_id: str) -> Dict[str, Any]:
        """Get status summary for an order."""
        history = self.find_status_history(broker_order_id)
        if not history:
            return {
                'current_status': None,
                'status_changes': 0,
                'first_status_time': None,
                'last_status_time': None
            }

        latest_status = max(history, key=lambda x: x.updated_at)
        first_status = min(history, key=lambda x: x.updated_at)

        return {
            'current_status': latest_status.status,
            'status_changes': len(history),
            'first_status_time': first_status.updated_at,
            'last_status_time': latest_status.updated_at,
            'fill_percentage': latest_status.get_fill_percentage()
        }
