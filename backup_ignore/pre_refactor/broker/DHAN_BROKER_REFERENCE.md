# Dhan Broker Reference (Tradehull + dhanhq)

This reference documents the Dhan broker integration available under `broker/` for quick LLM consumption. It covers the high‑level wrapper (`broker/tradehull_broker.py`) and the underlying Tradehull/DhanHQ capabilities (orders, quotes, feeds, 20‑level depth, and Super Order v2).

- Entry point: `from broker import get_broker`
- Wrapper: `TradehullBrokerWrapper` (adds standardized 5/20‑level depth and delegates the rest)
- Underlying: `Tradehull` (from `Dhan_Tradehull`) + `dhanhq` SDK (`DhanContext`, `MarketFeed`, `OrderUpdate`, optional `FullDepth`)


## Installation

```bash
pip install Dhan_Tradehull dhanhq python-dotenv pandas numpy mibian pytz requests
```


## Credentials

The wrapper loads credentials via environment variables (from `.env` or `broker_config.env` if present):

- `DHAN_CLIENT_ID`
- `DHAN_API_TOKEN`  ← matches wrapper code

Example `.env`:

```
DHAN_CLIENT_ID=YOUR_CLIENT_ID
DHAN_API_TOKEN=YOUR_LONG_LIVED_TOKEN
```

Notes:
- Missing/blank values raise validation errors.
- Basic connection is sanity‑checked by fetching balance.
 - Do not commit real tokens. Rotate if exposed.

File references:
- `broker/tradehull_broker.py:33` (singleton `get_broker`)
- `broker/tradehull_broker.py:63` (env read)


## Getting a Broker

```python
from broker import get_broker

broker = get_broker()       # returns singleton instance
# broker = get_broker(True) # force a fresh instance
```

Behavior:
- Wraps `Dhan_Tradehull.Tradehull(client_id, access_token)` in `TradehullBrokerWrapper`.
- Delegates unknown attributes/methods to the underlying Tradehull instance.

File references:
- `broker/tradehull_broker.py:120` (wrapper init)
- `broker/tradehull_broker.py:488` (delegation via `__getattr__`)


## Market Data

5‑level depth (standardized):

```python
quote = broker.get_quote_data("TCS")
# => {
#   'symbol': 'TCS', 'last_price': float, 'volume': int,
#   'depth': { 'bids': [...], 'asks': [...] }, 'ohlc': {...},
#   'depth_level': 5,
#   ...
# }
```

- Source: `broker/tradehull_broker.py:192`
- Converts Tradehull `depth.buy/sell` to `bids/asks`.

20‑level depth (snapshot) via `dhanhq` FullDepth:

```python
snapshot = broker.get_20_level_depth("RELIANCE")
# => { 'timestamp': float, 'depth_level': 20, 'data': <raw> }
```

20‑level depth (stream):

```python
def on_depth(payload: dict):
    # payload keys: timestamp, depth_level=20, data
    pass

broker.start_20_level_depth_stream(["TCS", "RELIANCE"], callback=on_depth)
# ... later
broker.stop_20_level_depth_stream()
```

- Source: `broker/tradehull_broker.py:256` (snapshot), `:290` (start stream), `:346` (stop)
- Symbol→securityId resolution uses instrument file or common fallbacks (`:452`).

Other Tradehull market data helpers available from the underlying object include (names may vary by `Dhan_Tradehull` version):

- `get_ltp_data(names)`: return last traded prices per symbol
- `get_quote_data(names)`: raw quotes per symbol
- `get_ohlc_data(names)`: OHLC per symbol
- `get_historical_data(symbol, exchange, timeframe, start, end)`
- `get_intraday_data(symbol, exchange, timeframe)` + `resample_timeframe(df, '5T')`
- Transformations: `heikin_ashi(df)`, `renko_bricks(df, box_size=7)`


## Feeds and WebSockets

Real‑time feeds (via `dhanhq.MarketFeed`):

- `start_market_feed(instruments, feed_type='ticker')` → returns feed handle
- `get_live_market_data(instruments, feed_type='ticker')` → single snapshot
- `subscribe_to_symbols(symbols, feed_type='ticker', callback=fn)`

Order updates (via `dhanhq.OrderUpdate`):

- `start_order_updates()` → returns socket handle
- `get_order_updates_sync()` → blocking connect
- `start_order_updates_thread()` → non‑blocking thread

Candles (WebSocket assembled from ticks):

- `start_candle_stream(symbols, timeframe=1, callback=None)` → returns `CandleStreamer`
- `stream_candles_sync/async(...)` → run the stream for a duration
- `get_live_candles(symbols, timeframe=1, num_candles=10)` → quick snapshot builder

Notes:
- Feed types commonly used: `ticker` (15), `quote` (17), `full` (21, v2).
- Wrapper also supports native `FullDepth` for 20‑level orderbook.


## Orders (Standard)

Common methods on the underlying Tradehull instance (delegated via wrapper):

- `order_placement(tradingsymbol, exchange, quantity, price, trigger_price, order_type, transaction_type, trade_type, ...)` → orderId
- `modify_order(order_id, order_type, quantity, price=..., trigger_price=..., validity='DAY', leg_name=None)`
- `cancel_order(order_id)`
- `place_slice_order(...)` → list of orderIds or single orderId
- `kill_switch('ON'|'OFF')`

Reports and state:

- `get_balance()`
- `get_holdings()`, `get_positions()`, `get_orderbook()`, `get_trade_book()`
- `order_report()` → status dicts, `get_order_detail/status/executed_price/exchange_time(order_id)`
- `cancel_all_orders()`
- `get_live_pnl()`
- `margin_calculator(...)`


## Options Utilities

- Strike selection: `ATM_Strike_Selection(Underlying, Expiry)`, `OTM_Strike_Selection(..., OTM_count)`, `ITM_Strike_Selection(..., ITM_count)`
- Expiries: `get_expiry_list(Underlying, exchange)`
- Option chain: `get_option_chain(Underlying, exchange, expiry, num_strikes=10)` + `format_option_chain(data)`
- Greeks: `get_option_greek(strike, expiry, asset, interest_rate, flag, scrip_type)`
- Misc: `get_lot_size(tradingsymbol)`


## Super Order v2 (Bracket/Cover/Trailing)

Convenience wrappers (via underlying Tradehull implementation):

```python
# Bracket order
oid = broker.place_bracket_order(
    tradingsymbol="POWERGRID", exchange="NSE", transaction_type="BUY",
    quantity=100, entry_price=250.0, target_price=255.0, stop_loss_price=245.0,
    trade_type="MIS", trailing_jump=0.5
)

# Cover order (entry + SL only)
oid2 = broker.place_cover_order(
    tradingsymbol="POWERGRID", exchange="NSE", transaction_type="SELL",
    quantity=100, entry_price=254.5, stop_loss_price=260.0,
)
```

Direct Super Order control:

- `place_super_order(...)` → returns orderId
- `modify_super_order_leg(order_id, leg_name, price=?, quantity=?, stop_loss_price=?, trailing_jump=?)` (25‑mod cap tracked)
- `cancel_super_order_leg(order_id, 'ENTRY_LEG'|'TARGET_LEG'|'STOP_LOSS_LEG')`
- `get_super_orders()` / `get_super_order_status(order_id)`
- `update_trailing_stop_super_order(order_id, new_stop_price, trailing_jump=?)`
- `recreate_super_order_if_needed(order_id)` (auto‑recreation once near hard cap)
- `disable_trailing_stop(order_id)`
- `start_super_order_updates(callback)` (WebSocket)

Notes:
- Super Orders use Dhan REST endpoints directly; provide `client_id` and `access_token`.
- Modification counts are tracked to guard the 25‑update limit.


## UI Wiring Cheatsheet

This table maps UI controls (Topbar, Ticket) to broker parameters used by the wrapper/underlying Tradehull methods.

- Symbol select → `tradingsymbol` (string like `RELIANCE`, `TCS`). Exchange default `NSE`.
- Interval select → affects charts only; not used for orders.
- Order Ticket
  - Side (Buy/Sell) → `transaction_type` = `BUY` | `SELL`
  - Qty → `quantity` (int, lots apply for derivatives)
  - Type → `order_type` = `MARKET` | `LIMIT` | `STOP_LOSS`
  - Price (for limit) → `price`
  - Stop (SL) → `trigger_price`
  - Product → `trade_type` = `MIS` (intraday) | `CNC` (delivery) | as supported

Place order example (LIMIT):

```python
from broker import get_broker
br = get_broker()
order_id = br.order_placement(
    tradingsymbol='RELIANCE', exchange='NSE',
    quantity=1, price=2500.00, trigger_price=0,
    order_type='LIMIT', transaction_type='BUY', trade_type='MIS'
)
```

Market order example:

```python
order_id = br.order_placement(
    tradingsymbol='RELIANCE', exchange='NSE',
    quantity=1, price=0, trigger_price=0,
    order_type='MARKET', transaction_type='SELL', trade_type='MIS'
)
```

Modify example:

```python
br.modify_order(order_id=order_id, order_type='LIMIT', quantity=2, price=2510.00, validity='DAY')
```

Cancel example:

```python
br.cancel_order(order_id)
```


## Error Handling & Rate Limits

- The wrapper validates presence of `DHAN_CLIENT_ID` and `DHAN_API_TOKEN` and raises clear exceptions.
- On init, a balance check surfaces auth errors early; other transient errors are tolerated.
- Use `debug="YES"` to log verbose details for depth/feed operations.
- Respect DhanHQ API limits; space rapid update loops (e.g., depth stream uses small sleeps).



## Quick Checks and Utilities

- `broker.is_connected()` / `broker.is_available()`
- `broker.add_depth_callback(fn)` for 20‑level depth stream
- Use `debug="YES"` in many methods to get verbose logs


## File Reference Map

- `broker/__init__.py:20` usage examples and quick overview
- `broker/tradehull_broker.py:33` `get_broker` (singleton + env)
- `broker/tradehull_broker.py:192` `get_quote_data` (standard 5‑level)
- `broker/tradehull_broker.py:256` `get_20_level_depth` (snapshot)
- `broker/tradehull_broker.py:290` `start_20_level_depth_stream` (live 20‑level)
- `broker/tradehull_broker.py:346` `stop_20_level_depth_stream`
- `broker/tradehull_broker.py:368` `add_depth_callback`
- `broker/tradehull_broker.py:452` `_get_security_id_for_symbol`
- `broker/tradehull_broker.py:488` `__getattr__` (delegate to Tradehull)


## Notes for LLMs

- Prefer wrapper entry points: `get_broker`, then call needed methods on `broker`.
- For 20‑level orderbook use `get_20_level_depth` or `start_20_level_depth_stream`.
- For Super Orders, use the convenience helpers or the explicit leg APIs.
- When calling methods not found on the wrapper, they are forwarded to the Tradehull instance.
