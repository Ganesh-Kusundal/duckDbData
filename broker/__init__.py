"""
Broker module for trading operations.
Provides broker instance management and configuration.

Super Order v2 API Integration:
- Complete Dhan Super Order v2 API support
- Bracket orders (entry + target + stop loss)
- Cover orders (entry + stop loss)
- Trailing stop loss management
- 25-modification limit protection with auto-recreation
- Real-time WebSocket order updates
- Comprehensive error handling

Native 20-Level Depth Support:
- 5-level depth via REST API (get_quote_data)
- 20-level depth via WebSocket (native DhanHQ v2.1.0 FullDepth)
- Real-time depth streaming with callbacks
- Standardized data structures

Usage:
    from broker import get_broker
    
    broker = get_broker()
    
    # Get 5-level depth
    quote_data = broker.get_quote_data('TCS')
    
    # Get 20-level depth snapshot
    depth_data = broker.get_20_level_depth('TCS')
    
    # Start 20-level depth streaming
    broker.start_20_level_depth_stream(['TCS'], callback=on_depth_update)
    
    # Place bracket order with trailing stop
    order_id = broker.place_bracket_order(
        tradingsymbol="POWERGRID",
        exchange="NSE",
        transaction_type="BUY",
        quantity=100,
        entry_price=250.0,
        target_price=255.0,
        stop_loss_price=245.0,
        trailing_jump=0.5
    )
    
    # Monitor and manage orders
    orders = broker.get_super_orders()
    ws = broker.start_super_order_updates(callback_function)

Documentation:
- README_SUPER_ORDER.md - Quick start guide
- example_super_order.py - Complete examples
- ../docs/SUPER_ORDER_API_GUIDE.md - Detailed API reference
"""

from .tradehull_broker import get_broker

__all__ = ['get_broker'] 