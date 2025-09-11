"""
Breakout Scanner Rule Mapper

This module provides the mapping between the original BreakoutScanner
and the new rule-based system. It translates the original scanner logic
into rule definitions and provides backward compatibility.
"""

from typing import Dict, List, Any, Optional
from datetime import date, time, timedelta
import logging

from ..engine.rule_engine import RuleEngine
from ..templates.breakout_rules import BreakoutRuleTemplates
from ..schema.rule_types import RuleType, SignalType

logger = logging.getLogger(__name__)


class BreakoutRuleMapper:
    """Maps BreakoutScanner logic to rule-based system."""

    def __init__(self, rule_engine: RuleEngine):
        """
        Initialize the breakout rule mapper.

        Args:
            rule_engine: The rule engine instance to use
        """
        self.rule_engine = rule_engine
        self._default_rules_loaded = False
        self.scanner_read = None  # Will be set by startup.py

    def load_default_rules(self):
        """Load the default breakout rules into the engine."""
        if self._default_rules_loaded:
            return

        default_rules = BreakoutRuleTemplates.get_all_templates()

        try:
            self.rule_engine.load_rules(default_rules)
            logger.info(f"Loaded {len(default_rules)} default breakout rules")
        except Exception as e:
            logger.error(f"Failed to load default breakout rules: {e}")

        self._default_rules_loaded = True

    def create_rule_from_config(
        self,
        rule_id: str,
        name: str,
        config: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a breakout rule from the original scanner configuration.

        Args:
            rule_id: Unique rule identifier
            name: Human-readable rule name
            config: Original scanner configuration
            **kwargs: Additional rule parameters

        Returns:
            Rule dictionary compatible with the rule engine
        """
        # Extract parameters from original config
        volume_multiplier = config.get('breakout_volume_ratio', 1.5)
        min_price = config.get('min_price', 50)
        max_price = config.get('max_price', 2000)
        min_volume = config.get('min_volume', 10000)

        # Extract time parameters
        cutoff_time = config.get('breakout_cutoff_time', time(9, 50))
        cutoff_time_str = cutoff_time.strftime('%H:%M')

        # Extract risk management parameters
        stop_loss_pct = config.get('stop_loss_pct', 0.02)
        take_profit_pct = config.get('take_profit_pct', 0.06)
        max_position_pct = config.get('max_position_size_pct', 10.0)

        # Create rule using template
        rule = BreakoutRuleTemplates.create_custom_breakout_rule(
            rule_id=rule_id,
            name=name,
            volume_multiplier=volume_multiplier,
            min_stock_price=min_price,
            max_stock_price=max_price,
            min_volume=min_volume,
            breakout_cutoff_time=cutoff_time_str,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            max_position_pct=max_position_pct,
            **kwargs
        )

        # Add original config reference for compatibility
        rule['metadata']['original_config'] = config
        rule['metadata']['migration_info'] = {
            'migrated_from': 'BreakoutScanner',
            'migration_date': '2025-09-08',
            'compatibility_mode': True
        }

        return rule

    def execute_breakout_scan(
        self,
        scan_date: date,
        rule_ids: Optional[List[str]] = None,
        cutoff_time: Optional[time] = None,
        max_results: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute breakout scan using the rule engine.

        Args:
            scan_date: Date to scan
            rule_ids: Specific rules to execute (None = all breakout rules)
            cutoff_time: Override cutoff time
            max_results: Maximum results per rule
            **kwargs: Additional execution parameters

        Returns:
            Scan results in format compatible with original scanner
        """
        # Ensure default rules are loaded
        self.load_default_rules()

        # If no specific rules provided, find all breakout rules
        if rule_ids is None:
            rule_ids = []
            for rule_id, rule in self.rule_engine.rules.items():
                if rule.get('rule_type') == 'breakout' and rule.get('enabled', True):
                    rule_ids.append(rule_id)

        if not rule_ids:
            logger.warning("No breakout rules found or enabled")
            return {
                'success': False,
                'error': 'No breakout rules available',
                'results': []
            }

        # Execute rules
        batch_result = self.rule_engine.execute_rules_batch(
            rule_ids=rule_ids,
            scan_date=scan_date,
            start_time=time(9, 15),
            end_time=cutoff_time or time(9, 50),
            **kwargs
        )

        # Debug logging for batch result
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Batch result from rule engine has {len(batch_result.get('signals', []))} signals")
            logger.debug(f"Batch result keys: {list(batch_result.keys()) if isinstance(batch_result, dict) else 'Not a dict'}")
            logger.debug(f"Batch result total_signals: {batch_result.get('total_signals', 'N/A')}")
            logger.debug(f"Batch result successful_executions: {batch_result.get('successful_executions', 'N/A')}")

        # Convert to format compatible with original scanner
        results = self._convert_to_scanner_format(batch_result)

        return {
            'success': batch_result['failed_executions'] == 0,
            'total_rules': batch_result['total_rules'],
            'successful_executions': batch_result['successful_executions'],
            'failed_executions': batch_result['failed_executions'],
            'total_signals': len(results),
            'results': results[:max_results]  # Limit results as per original scanner
        }

    def execute_date_range_scan(
        self,
        start_date: date,
        end_date: date,
        rule_ids: Optional[List[str]] = None,
        cutoff_time: Optional[time] = None,
        max_results_per_day: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute breakout scan over a date range (equivalent to original scan_date_range).

        Args:
            start_date: Start date for scanning
            end_date: End date for scanning
            rule_ids: Specific rules to execute
            cutoff_time: Override cutoff time
            max_results_per_day: Maximum results per day
            **kwargs: Additional parameters

        Returns:
            Date range scan results
        """
        # Generate trading days
        trading_days = self._get_trading_days(start_date, end_date)

        all_results = []
        daily_stats = []

        for scan_date in trading_days:
            try:
                daily_result = self.execute_breakout_scan(
                    scan_date=scan_date,
                    rule_ids=rule_ids,
                    cutoff_time=cutoff_time,
                    max_results=max_results_per_day,
                    **kwargs
                )

                if daily_result['success'] and daily_result['results']:
                    # Add scan_date to each result
                    for result in daily_result['results']:
                        result['scan_date'] = scan_date

                    all_results.extend(daily_result['results'])

                    daily_stats.append({
                        'date': scan_date,
                        'results_count': len(daily_result['results']),
                        'success': True
                    })
                else:
                    daily_stats.append({
                        'date': scan_date,
                        'results_count': 0,
                        'success': False,
                        'error': daily_result.get('error', 'Unknown error')
                    })

            except Exception as e:
                logger.error(f"Error scanning {scan_date}: {e}")
                daily_stats.append({
                    'date': scan_date,
                    'results_count': 0,
                    'success': False,
                    'error': str(e)
                })

        # Calculate overall statistics
        total_days = len(trading_days)
        successful_days = sum(1 for stat in daily_stats if stat['success'])
        total_results = len(all_results)

        return {
            'success': successful_days > 0,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'summary': {
                'total_trading_days': total_days,
                'successful_scan_days': successful_days,
                'total_breakout_signals': total_results,
                'avg_signals_per_day': total_results / total_days if total_days > 0 else 0
            },
            'results': all_results,
            'daily_stats': daily_stats
        }

    def get_rule_performance(self, rule_id: str) -> Dict[str, Any]:
        """
        Get performance statistics for a breakout rule.

        Args:
            rule_id: Rule identifier

        Returns:
            Performance statistics
        """
        return self.rule_engine.get_rule_stats(rule_id)

    def compare_with_original_scanner(
        self,
        original_scanner,
        scan_date: date,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare rule-based results with original scanner results.

        Args:
            original_scanner: Original BreakoutScanner instance
            scan_date: Date to compare
            config: Scanner configuration

        Returns:
            Comparison results
        """
        # Execute original scanner
        try:
            original_results = original_scanner.scan(scan_date)
            original_count = len(original_results) if hasattr(original_results, '__len__') else 0
        except Exception as e:
            logger.error(f"Original scanner failed: {e}")
            original_results = []
            original_count = 0

        # Execute rule-based scanner
        rule_result = self.execute_breakout_scan(scan_date, max_results=10)
        rule_count = len(rule_result.get('results', []))

        # Compare results
        comparison = {
            'scan_date': scan_date.isoformat(),
            'original_scanner_results': original_count,
            'rule_based_results': rule_count,
            'results_match': abs(original_count - rule_count) <= 1,  # Allow small difference
            'difference': rule_count - original_count,
            'config': config
        }

        # Detailed comparison if both have results
        if original_count > 0 and rule_count > 0:
            comparison['detailed_comparison'] = {
                'original_symbols': [r.get('symbol') for r in (original_results if isinstance(original_results, list) else [])],
                'rule_symbols': [r.get('symbol') for r in rule_result.get('results', [])],
                'overlap_count': len(set([r.get('symbol') for r in (original_results if isinstance(original_results, list) else [])]) &
                                   set([r.get('symbol') for r in rule_result.get('results', [])]))
            }

        return comparison

    def _convert_to_scanner_format(self, batch_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert rule engine results to original scanner format."""
        converted_results = []

        rule_results = batch_result.get('rule_results', {})

        # Use the aggregated signals from batch execution
        batch_signals = batch_result.get('signals', [])
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Converting batch_result keys: {list(batch_result.keys())}")
            logger.debug(f"Batch result success: {batch_result.get('success', 'N/A')}")
            logger.debug(f"Batch result signals count: {len(batch_signals)}")
            logger.debug(f"Rule results count: {len(rule_results)}")
            logger.debug(f"Batch has 'results' key: {'results' in batch_result}")
            logger.debug(f"Batch has 'rule_results' key: {'rule_results' in batch_result}")

        for signal in batch_signals:
            scanner_result = self._convert_signal_to_scanner_format(signal)
            converted_results.append(scanner_result)

        # Sort by probability score (descending) to match original behavior
        converted_results.sort(key=lambda x: x.get('probability_score', 0), reverse=True)

        return converted_results

    def _convert_signal_to_scanner_format(self, signal) -> Dict[str, Any]:
        """Convert a single signal to scanner format."""

        # Handle both dict and TradingSignal object formats
        if hasattr(signal, 'price'):
            # It's a TradingSignal object
            price = signal.price
            volume = getattr(signal, 'volume', 0)
            confidence = signal.confidence
            symbol = signal.symbol
            rule_id = signal.rule_id
            signal_type = signal.signal_type.value if hasattr(signal.signal_type, 'value') else str(signal.signal_type)
        else:
            # It's a dictionary
            price = signal.get('price', 0)
            volume = signal.get('volume', 0)
            confidence = signal.get('confidence', 0)
            symbol = signal.get('symbol', 'N/A')
            rule_id = signal.get('rule_id', 'unknown')
            signal_type = signal.get('signal_type', 'BUY')

        # Get the actual price change percentage from the signal metadata
        price_change_pct = 1.0  # Default fallback

        # Try to get price_change_pct from metadata for TradingSignal objects
        if hasattr(signal, 'metadata') and signal.metadata:
            market_data_snapshot = signal.metadata.get('market_data_snapshot', {})
            if 'price_change_pct' in market_data_snapshot:
                price_change_pct = market_data_snapshot['price_change_pct']

        # Try to get from signal object attributes
        if hasattr(signal, 'metadata') and signal.metadata and 'price_change_pct' in signal.metadata:
            price_change_pct = signal.metadata['price_change_pct']

        # Get additional price data from metadata
        price_at_0950 = None
        price_at_1515 = None
        daily_performance_pct = None

        if hasattr(signal, 'metadata') and signal.metadata:
            market_data_snapshot = signal.metadata.get('market_data_snapshot', {})
            price_at_0950 = market_data_snapshot.get('price_at_0950')
            price_at_1515 = market_data_snapshot.get('price_at_1515')
            daily_performance_pct = market_data_snapshot.get('daily_performance_pct')

        # Debug logging
        if symbol == 'INTELLECT':
            if hasattr(signal, 'metadata') and signal.metadata:
                logger.info(f"DEBUG INTELLECT: metadata keys: {list(signal.metadata.keys())}")
                market_data_snapshot = signal.metadata.get('market_data_snapshot', {})
                logger.info(f"DEBUG INTELLECT: market_data_snapshot keys: {list(market_data_snapshot.keys())}")
                logger.info(f"DEBUG INTELLECT: price_at_1515 = {price_at_1515}")
                logger.info(f"DEBUG INTELLECT: daily_performance_pct = {daily_performance_pct}")
            else:
                logger.info(f"DEBUG INTELLECT: no metadata available")

        return {
            'symbol': symbol,
            'breakout_price': price,
            'price_at_0950': round(price_at_0950, 2) if price_at_0950 else None,
            'price_at_1515': round(price_at_1515, 2) if price_at_1515 else None,
            'daily_performance_pct': round(daily_performance_pct, 2) if daily_performance_pct else None,
            'current_high': price * 1.01 if price > 0 else None,  # Estimate
            'current_low': price * 0.99 if price > 0 else None,   # Estimate
            'current_volume': volume,
            'breakout_pct': round(price_change_pct, 2),  # Use actual calculated percentage
            'volume_ratio': 1.5,  # Default from rules
            'probability_score': confidence * 100,
            'entry_price': price,  # Use breakout price as entry
            'stop_loss': price * 0.98 if price > 0 else None,  # 2% stop loss
            'take_profit': price * 1.06 if price > 0 else None,  # 6% take profit
            'performance_rank': confidence * 100,
            'signal_type': signal_type,
            'rule_id': rule_id
        }

    def _get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """Get list of trading days in the date range (weekdays only)."""
        trading_days = []
        current_date = start_date

        while current_date <= end_date:
            # Skip weekends (Monday=0, Sunday=6)
            if current_date.weekday() < 5:
                trading_days.append(current_date)
            current_date += timedelta(days=1)

        return trading_days


class RuleBasedBreakoutScanner:
    """
    Rule-based breakout scanner that provides the same interface as the original
    BreakoutScanner but uses the rule engine internally.
    """

    def __init__(self, rule_engine: RuleEngine):
        """
        Initialize the rule-based breakout scanner.

        Args:
            rule_engine: Rule engine instance
        """
        self.rule_mapper = BreakoutRuleMapper(rule_engine)
        self.rule_mapper.load_default_rules()

    @property
    def scanner_name(self) -> str:
        return "rule_based_breakout"

    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> List[Dict[str, Any]]:
        """
        Single-day scan (backward compatibility with original interface).
        """
        result = self.rule_mapper.execute_breakout_scan(
            scan_date=scan_date,
            cutoff_time=cutoff_time
        )

        if result['success']:
            # Convert internal field names to user-friendly output format
            user_friendly_results = []
            for signal in result['results']:
                user_signal = {
                    'symbol': signal.get('symbol'),
                    'signal_type': signal.get('signal_type', 'BUY'),
                    'confidence': signal.get('probability_score', 0) / 100,  # Convert from percentage
                    'price': signal.get('breakout_price'),  # Map breakout_price to price
                    'volume': signal.get('current_volume'),  # Map current_volume to volume
                    'rule_id': signal.get('rule_id'),
                    # Keep additional fields for advanced users
                    'entry_price': signal.get('entry_price'),
                    'stop_loss': signal.get('stop_loss'),
                    'take_profit': signal.get('take_profit'),
                    'breakout_pct': signal.get('breakout_pct'),
                    'volume_ratio': signal.get('volume_ratio'),
                    'performance_rank': signal.get('performance_rank')
                }
                user_friendly_results.append(user_signal)

            return user_friendly_results
        else:
            logger.error(f"Scan failed: {result.get('error', 'Unknown error')}")
            return []

    def scan_date_range(
        self,
        start_date: date,
        end_date: date,
        cutoff_time: Optional[time] = None,
        end_of_day_time: Optional[time] = None
    ) -> List[Dict[str, Any]]:
        """
        Date range scan (equivalent to original functionality).
        """
        result = self.rule_mapper.execute_date_range_scan(
            start_date=start_date,
            end_date=end_date,
            cutoff_time=cutoff_time
        )

        if result['success']:
            return result['results']
        else:
            logger.error("Date range scan failed")
            return []

    def get_config(self) -> Dict[str, Any]:
        """Get scanner configuration."""
        return {
            'scanner_type': 'rule_based',
            'supported_rules': ['breakout-standard', 'breakout-aggressive', 'breakout-conservative'],
            'default_volume_multiplier': 1.5,
            'default_cutoff_time': '09:45'
        }

    def display_results_table(self, results: List[Dict[str, Any]], title: str = "Rule-Based Breakout Scanner Results"):
        """Display results in table format (compatible with original)."""
        if not results:
            print("⚠️  No results to display")
            return

        print(f"\n📊 {title}")
        print("=" * 80)

        print("┌" + "─" * 10 + "┬" + "─" * 10 + "┬" + "─" * 12 + "┬" + "─" * 10 + "┬" + "─" * 12 + "┬" + "─" * 10 + "┬" + "─" * 12 + "┬" + "─" * 8 + "┬" + "─" * 6 + "┬" + "─" * 10 + "┐")
        print("│ {:<8} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<6} │ {:<4} │ {:<8} │".format(
            "Symbol", "Date", "Breakout", "Entry", "Stop Loss", "Take", "Volume", "Prob", "Rank", "Rule"))
        print("│ {:<8} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<6} │ {:<4} │ {:<8} │".format(
            "", "", "Price", "Price", "", "Profit", "Ratio", "Score", "", "ID"))
        print("├" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 12 + "┼" + "─" * 10 + "┼" + "─" * 12 + "┼" + "─" * 10 + "┼" + "─" * 12 + "┼" + "─" * 8 + "┼" + "─" * 6 + "┼" + "─" * 10 + "┤")

        for result in results[:15]:
            symbol = result.get('symbol', 'N/A')[:8]
            scan_date = result.get('scan_date')
            if scan_date:
                if hasattr(scan_date, 'strftime'):
                    date_str = scan_date.strftime('%Y-%m-%d')
                else:
                    date_str = str(scan_date)
            else:
                date_str = 'N/A'
            breakout_price = result.get('breakout_price', 0)
            entry_price = result.get('entry_price', breakout_price)
            stop_loss = result.get('stop_loss', 0)
            take_profit = result.get('take_profit', 0)
            volume_ratio = result.get('volume_ratio', 1.0)
            probability_score = result.get('probability_score', 0)
            performance_rank = result.get('performance_rank', 0)
            rule_id = result.get('rule_id', 'N/A')[:8]

            print("│ {:<8} │ {:<8} │ ₹{:>8.2f} │ ₹{:>6.2f} │ ₹{:>8.2f} │ ₹{:>6.2f} │ {:>8.1f}x │ {:>5.1f}% │ {:>4.2f} │ {:<8} │".format(
                symbol, date_str, breakout_price, entry_price, stop_loss, take_profit,
                volume_ratio, probability_score, performance_rank, rule_id))

        print("└" + "─" * 10 + "┴" + "─" * 10 + "┴" + "─" * 12 + "┴" + "─" * 10 + "┴" + "─" * 12 + "┴" + "─" * 10 + "┴" + "─" * 12 + "┴" + "─" * 8 + "┴" + "─" * 6 + "┴" + "─" * 10 + "┘")

        print()
        if results:
            successful_count = sum(1 for r in results if r.get('breakout_successful', True))
            total_count = len(results)
            success_rate = (successful_count / total_count * 100) if total_count > 0 else 0
            avg_probability = sum(r.get('probability_score', 0) for r in results) / len(results) if results else 0

            print("📈 Summary Statistics:")
            print(f"   Total Breakouts: {total_count}")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Average Probability Score: {avg_probability:.1f}%")
            print(f"   Rules Used: {len(set(r.get('rule_id') for r in results))}")

    def export_results(self, results: List[Dict[str, Any]], filename: str = "rule_based_breakout_results.csv"):
        """Export results to CSV file."""
        import csv

        if not results:
            print("⚠️  No results to export")
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if results:
                    fieldnames = results[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(results)

            print(f"💾 Results exported to {filename}")
            print(f"📊 Exported {len(results)} records")

        except Exception as e:
            print(f"❌ Failed to export results: {e}")
