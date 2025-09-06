# Technical Indicators - Practical Usage Examples

## 🎯 Trading Strategy Examples

### 1. RSI Oversold + Support Level Strategy

```python
from core.technical_indicators.storage import TechnicalIndicatorsStorage
from datetime import date, timedelta
import pandas as pd

def find_oversold_at_support(symbol, days_back=30):
    """Find RSI oversold conditions near support levels."""
    storage = TechnicalIndicatorsStorage('data/technical_indicators')
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    # Load 5-minute data
    data = storage.load_indicators(symbol, '5T', start_date, end_date)
    
    if data.empty:
        return pd.DataFrame()
    
    # Define conditions
    oversold = data['rsi_14'] < 30
    near_support = (
        (data['close'] <= data['support_level_1'] * 1.02) &
        (data['close'] >= data['support_level_1'] * 0.98)
    )
    
    # Find signals
    signals = data[oversold & near_support].copy()
    
    if not signals.empty:
        signals['signal_type'] = 'RSI_OVERSOLD_AT_SUPPORT'
        signals['support_distance'] = abs(signals['close'] - signals['support_level_1'])
        
    return signals[['timestamp', 'close', 'rsi_14', 'support_level_1', 'support_distance', 'signal_type']]

# Example usage
signals = find_oversold_at_support('RELIANCE')
print(f"Found {len(signals)} oversold signals at support for RELIANCE")
if not signals.empty:
    print(signals.tail())
```

### 2. Supply/Demand Zone Breakout Strategy

```python
def detect_zone_breakouts(symbol, timeframe='15T', days_back=7):
    """Detect breakouts from supply/demand zones."""
    storage = TechnicalIndicatorsStorage('data/technical_indicators')
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    data = storage.load_indicators(symbol, timeframe, start_date, end_date)
    
    if data.empty:
        return pd.DataFrame()
    
    breakouts = []
    
    for i in range(1, len(data)):
        current = data.iloc[i]
        previous = data.iloc[i-1]
        
        # Supply zone breakout (price breaks above supply zone)
        if (previous['close'] <= current['supply_zone_high'] and 
            current['close'] > current['supply_zone_high'] and
            current['volume'] > current['volume_sma_20'] * 1.5):
            
            breakouts.append({
                'timestamp': current['timestamp'],
                'type': 'SUPPLY_BREAKOUT',
                'price': current['close'],
                'zone_high': current['supply_zone_high'],
                'zone_low': current['supply_zone_low'],
                'zone_strength': current['supply_zone_strength'],
                'volume': current['volume'],
                'volume_ratio': current['volume'] / current['volume_sma_20']
            })
        
        # Demand zone breakout (price breaks below demand zone)
        if (previous['close'] >= current['demand_zone_low'] and 
            current['close'] < current['demand_zone_low'] and
            current['volume'] > current['volume_sma_20'] * 1.5):
            
            breakouts.append({
                'timestamp': current['timestamp'],
                'type': 'DEMAND_BREAKDOWN',
                'price': current['close'],
                'zone_high': current['demand_zone_high'],
                'zone_low': current['demand_zone_low'],
                'zone_strength': current['demand_zone_strength'],
                'volume': current['volume'],
                'volume_ratio': current['volume'] / current['volume_sma_20']
            })
    
    return pd.DataFrame(breakouts)

# Example usage
breakouts = detect_zone_breakouts('TCS', '15T', 7)
print(f"Found {len(breakouts)} zone breakouts for TCS")
if not breakouts.empty:
    print(breakouts)
```

### 3. Multi-Timeframe Trend Analysis

```python
def analyze_multi_timeframe_trend(symbol):
    """Analyze trend across multiple timeframes."""
    storage = TechnicalIndicatorsStorage('data/technical_indicators')
    today = date.today()
    
    timeframes = ['5T', '15T', '1H', '1D']
    analysis = {}
    
    for tf in timeframes:
        data = storage.load_indicators(symbol, tf, today, today)
        
        if not data.empty:
            latest = data.iloc[-1]
            
            # Determine trend direction
            if latest['close'] > latest['sma_20'] and latest['sma_20'] > latest['sma_50']:
                trend = 'BULLISH'
            elif latest['close'] < latest['sma_20'] and latest['sma_20'] < latest['sma_50']:
                trend = 'BEARISH'
            else:
                trend = 'SIDEWAYS'
            
            analysis[tf] = {
                'trend': trend,
                'close': latest['close'],
                'sma_20': latest['sma_20'],
                'sma_50': latest['sma_50'],
                'rsi': latest['rsi_14'],
                'adx': latest['adx_14'],
                'support': latest['support_level_1'],
                'resistance': latest['resistance_level_1']
            }
    
    return analysis

# Example usage
trend_analysis = analyze_multi_timeframe_trend('INFY')
for timeframe, data in trend_analysis.items():
    print(f"{timeframe}: {data['trend']} - RSI: {data['rsi']:.1f}, ADX: {data['adx']:.1f}")
```

## 📊 Screening & Scanning Examples

### 1. RSI Divergence Scanner

```python
def scan_rsi_divergence(symbols, timeframe='1H', days_back=10):
    """Scan for RSI divergences across multiple symbols."""
    storage = TechnicalIndicatorsStorage('data/technical_indicators')
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    divergences = []
    
    for symbol in symbols:
        try:
            data = storage.load_indicators(symbol, timeframe, start_date, end_date)
            
            if len(data) < 20:  # Need enough data
                continue
            
            # Look for bullish divergence (price makes lower low, RSI makes higher low)
            for i in range(10, len(data)-5):
                price_window = data['close'].iloc[i-10:i+5]
                rsi_window = data['rsi_14'].iloc[i-10:i+5]
                
                price_low_idx = price_window.idxmin()
                rsi_low_idx = rsi_window.idxmin()
                
                # Check if we have a potential divergence
                if (price_low_idx != rsi_low_idx and 
                    data.loc[price_low_idx, 'close'] < data.loc[rsi_low_idx, 'close'] and
                    data.loc[price_low_idx, 'rsi_14'] > data.loc[rsi_low_idx, 'rsi_14']):
                    
                    divergences.append({
                        'symbol': symbol,
                        'timestamp': data.iloc[i]['timestamp'],
                        'type': 'BULLISH_DIVERGENCE',
                        'price': data.iloc[i]['close'],
                        'rsi': data.iloc[i]['rsi_14']
                    })
                    break  # One per symbol
                    
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    return pd.DataFrame(divergences)

# Example usage
symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']
divergences = scan_rsi_divergence(symbols)
print(f"Found {len(divergences)} RSI divergences")
if not divergences.empty:
    print(divergences)
```

### 2. Volume Breakout Scanner

```python
def scan_volume_breakouts(symbols, timeframe='5T', volume_threshold=2.0):
    """Scan for high-volume breakouts."""
    storage = TechnicalIndicatorsStorage('data/technical_indicators')
    today = date.today()
    
    breakouts = []
    
    for symbol in symbols:
        try:
            data = storage.load_indicators(symbol, timeframe, today, today)
            
            if data.empty:
                continue
            
            latest = data.iloc[-1]
            
            # Check for volume breakout
            if (latest['volume_ratio'] > volume_threshold and
                latest['close'] > latest['resistance_level_1'] and
                latest['rsi_14'] > 50):
                
                breakouts.append({
                    'symbol': symbol,
                    'timestamp': latest['timestamp'],
                    'close': latest['close'],
                    'resistance': latest['resistance_level_1'],
                    'volume_ratio': latest['volume_ratio'],
                    'rsi': latest['rsi_14'],
                    'breakout_percentage': ((latest['close'] - latest['resistance_level_1']) / latest['resistance_level_1']) * 100
                })
                
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    return pd.DataFrame(breakouts)

# Example usage
symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'WIPRO', 'LT', 'MARUTI']
breakouts = scan_volume_breakouts(symbols, volume_threshold=1.5)
print(f"Found {len(breakouts)} volume breakouts")
if not breakouts.empty:
    print(breakouts.sort_values('volume_ratio', ascending=False))
```

## 🔍 Analysis & Research Examples

### 1. Support/Resistance Strength Analysis

```python
def analyze_sr_strength(symbol, timeframe='1D', days_back=90):
    """Analyze the strength and reliability of support/resistance levels."""
    storage = TechnicalIndicatorsStorage('data/technical_indicators')
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    data = storage.load_indicators(symbol, timeframe, start_date, end_date)
    
    if data.empty:
        return None
    
    # Analyze support levels
    support_analysis = {}
    for level_col, strength_col in [('support_level_1', 'support_strength_1'),
                                   ('support_level_2', 'support_strength_2'),
                                   ('support_level_3', 'support_strength_3')]:
        
        support_data = data[[level_col, strength_col]].dropna()
        if not support_data.empty:
            avg_level = support_data[level_col].mean()
            avg_strength = support_data[strength_col].mean()
            level_stability = support_data[level_col].std() / avg_level * 100  # CV%
            
            support_analysis[level_col] = {
                'average_level': avg_level,
                'average_strength': avg_strength,
                'stability_cv': level_stability,
                'current_level': support_data[level_col].iloc[-1],
                'current_strength': support_data[strength_col].iloc[-1]
            }
    
    # Analyze resistance levels
    resistance_analysis = {}
    for level_col, strength_col in [('resistance_level_1', 'resistance_strength_1'),
                                   ('resistance_level_2', 'resistance_strength_2'),
                                   ('resistance_level_3', 'resistance_strength_3')]:
        
        resistance_data = data[[level_col, strength_col]].dropna()
        if not resistance_data.empty:
            avg_level = resistance_data[level_col].mean()
            avg_strength = resistance_data[strength_col].mean()
            level_stability = resistance_data[level_col].std() / avg_level * 100  # CV%
            
            resistance_analysis[level_col] = {
                'average_level': avg_level,
                'average_strength': avg_strength,
                'stability_cv': level_stability,
                'current_level': resistance_data[level_col].iloc[-1],
                'current_strength': resistance_data[strength_col].iloc[-1]
            }
    
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'period_days': days_back,
        'support_levels': support_analysis,
        'resistance_levels': resistance_analysis,
        'current_price': data['close'].iloc[-1]
    }

# Example usage
sr_analysis = analyze_sr_strength('RELIANCE', '1D', 90)
if sr_analysis:
    print(f"Support/Resistance Analysis for {sr_analysis['symbol']}")
    print(f"Current Price: {sr_analysis['current_price']:.2f}")
    print("\nSupport Levels:")
    for level, data in sr_analysis['support_levels'].items():
        print(f"  {level}: {data['current_level']:.2f} (Strength: {data['current_strength']:.1f})")
    print("\nResistance Levels:")
    for level, data in sr_analysis['resistance_levels'].items():
        print(f"  {level}: {data['current_level']:.2f} (Strength: {data['current_strength']:.1f})")
```

### 2. Supply/Demand Zone Effectiveness

```python
def analyze_zone_effectiveness(symbol, timeframe='15T', days_back=30):
    """Analyze how effective supply/demand zones are."""
    storage = TechnicalIndicatorsStorage('data/technical_indicators')
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    data = storage.load_indicators(symbol, timeframe, start_date, end_date)
    
    if data.empty:
        return None
    
    zone_tests = []
    
    for i in range(1, len(data)):
        current = data.iloc[i]
        previous = data.iloc[i-1]
        
        # Test supply zone
        if (current['supply_zone_low'] == current['supply_zone_low'] and  # Not NaN
            previous['close'] < current['supply_zone_low'] and
            current['close'] >= current['supply_zone_low']):
            
            # Price entered supply zone, check if it was rejected
            rejection = False
            for j in range(i+1, min(i+10, len(data))):  # Look ahead 10 periods
                future = data.iloc[j]
                if future['close'] < current['supply_zone_low']:
                    rejection = True
                    break
            
            zone_tests.append({
                'timestamp': current['timestamp'],
                'zone_type': 'SUPPLY',
                'zone_high': current['supply_zone_high'],
                'zone_low': current['supply_zone_low'],
                'zone_strength': current['supply_zone_strength'],
                'test_price': current['close'],
                'rejected': rejection
            })
        
        # Test demand zone
        if (current['demand_zone_high'] == current['demand_zone_high'] and  # Not NaN
            previous['close'] > current['demand_zone_high'] and
            current['close'] <= current['demand_zone_high']):
            
            # Price entered demand zone, check if it was supported
            support = False
            for j in range(i+1, min(i+10, len(data))):  # Look ahead 10 periods
                future = data.iloc[j]
                if future['close'] > current['demand_zone_high']:
                    support = True
                    break
            
            zone_tests.append({
                'timestamp': current['timestamp'],
                'zone_type': 'DEMAND',
                'zone_high': current['demand_zone_high'],
                'zone_low': current['demand_zone_low'],
                'zone_strength': current['demand_zone_strength'],
                'test_price': current['close'],
                'rejected': support  # For demand zones, "rejected" means supported
            })
    
    if not zone_tests:
        return None
    
    zone_df = pd.DataFrame(zone_tests)
    
    # Calculate effectiveness
    supply_tests = zone_df[zone_df['zone_type'] == 'SUPPLY']
    demand_tests = zone_df[zone_df['zone_type'] == 'DEMAND']
    
    effectiveness = {
        'symbol': symbol,
        'timeframe': timeframe,
        'period_days': days_back,
        'total_tests': len(zone_tests),
        'supply_zone_tests': len(supply_tests),
        'demand_zone_tests': len(demand_tests),
        'supply_effectiveness': supply_tests['rejected'].mean() * 100 if len(supply_tests) > 0 else 0,
        'demand_effectiveness': demand_tests['rejected'].mean() * 100 if len(demand_tests) > 0 else 0,
        'overall_effectiveness': zone_df['rejected'].mean() * 100
    }
    
    return effectiveness

# Example usage
zone_effectiveness = analyze_zone_effectiveness('TCS', '15T', 30)
if zone_effectiveness:
    print(f"Zone Effectiveness Analysis for {zone_effectiveness['symbol']}")
    print(f"Supply Zone Effectiveness: {zone_effectiveness['supply_effectiveness']:.1f}%")
    print(f"Demand Zone Effectiveness: {zone_effectiveness['demand_effectiveness']:.1f}%")
    print(f"Overall Effectiveness: {zone_effectiveness['overall_effectiveness']:.1f}%")
```

## 🤖 Automated Monitoring Examples

### 1. Daily Market Scanner

```python
def daily_market_scan():
    """Comprehensive daily market scan."""
    from core.duckdb_infra.database import DuckDBManager
    
    # Get all available symbols
    db = DuckDBManager()
    all_symbols = db.get_available_symbols()[:50]  # Limit for example
    
    storage = TechnicalIndicatorsStorage('data/technical_indicators')
    today = date.today()
    
    results = {
        'oversold_stocks': [],
        'overbought_stocks': [],
        'breakout_stocks': [],
        'volume_spikes': [],
        'zone_tests': []
    }
    
    for symbol in all_symbols:
        try:
            # Load daily data
            data = storage.load_indicators(symbol, '1D', today, today)
            if data.empty:
                continue
                
            latest = data.iloc[-1]
            
            # RSI conditions
            if latest['rsi_14'] < 30:
                results['oversold_stocks'].append({
                    'symbol': symbol,
                    'rsi': latest['rsi_14'],
                    'close': latest['close'],
                    'support': latest['support_level_1']
                })
            elif latest['rsi_14'] > 70:
                results['overbought_stocks'].append({
                    'symbol': symbol,
                    'rsi': latest['rsi_14'],
                    'close': latest['close'],
                    'resistance': latest['resistance_level_1']
                })
            
            # Breakout conditions
            if (latest['close'] > latest['resistance_level_1'] and
                latest['volume_ratio'] > 1.5):
                results['breakout_stocks'].append({
                    'symbol': symbol,
                    'close': latest['close'],
                    'resistance': latest['resistance_level_1'],
                    'volume_ratio': latest['volume_ratio']
                })
            
            # Volume spikes
            if latest['volume_ratio'] > 2.0:
                results['volume_spikes'].append({
                    'symbol': symbol,
                    'volume_ratio': latest['volume_ratio'],
                    'close': latest['close']
                })
            
            # Zone tests
            if (latest['close'] >= latest['supply_zone_low'] and 
                latest['close'] <= latest['supply_zone_high']):
                results['zone_tests'].append({
                    'symbol': symbol,
                    'zone_type': 'SUPPLY',
                    'close': latest['close'],
                    'zone_strength': latest['supply_zone_strength']
                })
            elif (latest['close'] >= latest['demand_zone_low'] and 
                  latest['close'] <= latest['demand_zone_high']):
                results['zone_tests'].append({
                    'symbol': symbol,
                    'zone_type': 'DEMAND',
                    'close': latest['close'],
                    'zone_strength': latest['demand_zone_strength']
                })
                
        except Exception as e:
            continue
    
    return results

# Example usage
scan_results = daily_market_scan()
print(f"📊 Daily Market Scan Results")
print(f"Oversold stocks: {len(scan_results['oversold_stocks'])}")
print(f"Overbought stocks: {len(scan_results['overbought_stocks'])}")
print(f"Breakout stocks: {len(scan_results['breakout_stocks'])}")
print(f"Volume spikes: {len(scan_results['volume_spikes'])}")
print(f"Zone tests: {len(scan_results['zone_tests'])}")

# Show top results
if scan_results['breakout_stocks']:
    print("\n🚀 Top Breakouts:")
    breakouts_df = pd.DataFrame(scan_results['breakout_stocks'])
    print(breakouts_df.sort_values('volume_ratio', ascending=False).head())
```

### 2. Alert System

```python
def generate_alerts(symbols, alert_config):
    """Generate trading alerts based on technical conditions."""
    storage = TechnicalIndicatorsStorage('data/technical_indicators')
    today = date.today()
    
    alerts = []
    
    for symbol in symbols:
        try:
            # Load 5-minute data for intraday alerts
            data = storage.load_indicators(symbol, '5T', today, today)
            if data.empty:
                continue
                
            latest = data.iloc[-1]
            
            # RSI alerts
            if alert_config.get('rsi_oversold', False) and latest['rsi_14'] < 30:
                alerts.append({
                    'symbol': symbol,
                    'timestamp': latest['timestamp'],
                    'alert_type': 'RSI_OVERSOLD',
                    'message': f"{symbol} RSI oversold at {latest['rsi_14']:.1f}",
                    'price': latest['close'],
                    'priority': 'HIGH' if latest['rsi_14'] < 25 else 'MEDIUM'
                })
            
            # Support test alerts
            if (alert_config.get('support_test', False) and
                latest['close'] <= latest['support_level_1'] * 1.01 and
                latest['close'] >= latest['support_level_1'] * 0.99):
                alerts.append({
                    'symbol': symbol,
                    'timestamp': latest['timestamp'],
                    'alert_type': 'SUPPORT_TEST',
                    'message': f"{symbol} testing support at {latest['support_level_1']:.2f}",
                    'price': latest['close'],
                    'priority': 'HIGH'
                })
            
            # Volume spike alerts
            if (alert_config.get('volume_spike', False) and
                latest['volume_ratio'] > alert_config.get('volume_threshold', 2.0)):
                alerts.append({
                    'symbol': symbol,
                    'timestamp': latest['timestamp'],
                    'alert_type': 'VOLUME_SPIKE',
                    'message': f"{symbol} volume spike {latest['volume_ratio']:.1f}x average",
                    'price': latest['close'],
                    'priority': 'MEDIUM'
                })
                
        except Exception as e:
            continue
    
    return sorted(alerts, key=lambda x: x['timestamp'], reverse=True)

# Example usage
watchlist = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK']
config = {
    'rsi_oversold': True,
    'support_test': True,
    'volume_spike': True,
    'volume_threshold': 1.8
}

alerts = generate_alerts(watchlist, config)
print(f"📢 Generated {len(alerts)} alerts")
for alert in alerts[:5]:  # Show top 5
    print(f"{alert['priority']} - {alert['message']} at {alert['price']:.2f}")
```

These examples demonstrate practical applications of the technical indicators system for trading, analysis, and monitoring. Each example can be customized and extended based on specific requirements.
