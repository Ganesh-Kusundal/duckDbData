"""
Intraday Trade Engine - Backtesting + Live Trading Parity
==================================================

A unified trade engine that runs the same strategies in backtesting and live trading
without code drift, using DDD + SOLID principles on top of DuckDB infrastructure.

Features:
- Top-3 → Concentrate → Pyramid → Exit Others intraday strategy
- Deterministic backtesting with NSE tick-size handling
- Real-time live trading with broker integration
- DuckDB persistence for all trade artifacts
- Comprehensive telemetry and analytics

Architecture:
- Domain-Driven Design with clear bounded contexts
- Port/Adapter pattern for external dependencies
- SOLID principles for maintainability and extensibility
- StrategyRunner with backtest/live parity
"""

__version__ = "1.0.0"
__author__ = "Trade Engine Team"
