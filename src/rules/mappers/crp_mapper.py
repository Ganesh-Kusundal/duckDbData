"""
CRP Scanner Rule Mapper

This module provides the mapping between the original CRPScanner
and the new rule-based system. It translates the original scanner logic
into rule definitions and provides backward compatibility.
"""

from typing import Dict, List, Any, Optional
from datetime import date, time, timedelta
import logging

from ..engine.rule_engine import RuleEngine
from ..templates.crp_rules import CRPRuleTemplates
from ..schema.rule_types import RuleType, SignalType

logger = logging.getLogger(__name__)


class CRPRuleMapper:
    """Maps CRPScanner logic to rule-based system."""

    def __init__(self, rule_engine: RuleEngine):
        """
        Initialize the CRP rule mapper.

        Args:
            rule_engine: The rule engine instance to use
        """
        self.rule_engine = rule_engine
        self._default_rules_loaded = False
        self.scanner_read = None  # Will be set by startup.py

    def load_default_rules(self):
        """Load the default CRP rules into the engine."""
        if self._default_rules_loaded:
            return

        default_rules = CRPRuleTemplates.get_all_templates()

        try:
            self.rule_engine.load_rules(default_rules)
            logger.info(f"Loaded {len(default_rules)} default CRP rules")
        except Exception as e:
            logger.error(f"Failed to load default CRP rules: {e}")

        self._default_rules_loaded = True

    def create_rule_from_config(
        self,
        rule_id: str,
        name: str,
        config: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a CRP rule from the original scanner configuration.

        Args:
            rule_id: Unique rule identifier
            name: Human-readable rule name
            config: Original scanner configuration
            **kwargs: Additional rule parameters

        Returns:
            Rule dictionary compatible with the rule engine
        """
        # Extract parameters from original config
        close_threshold_pct = config.get('close_threshold_pct', 2.0)
        range_threshold_pct = config.get('range_threshold_pct', 3.0)
        min_volume = config.get('min_volume', 50000)
        max_volume = config.get('max_volume', 5000000)
        min_price = config.get('min_price', 50)
        max_price = config.get('max_price', 2000)

        # Extract time parameters
        cutoff_time = config.get('crp_cutoff_time', time(9, 50))
        cutoff_time_str = cutoff_time.strftime('%H:%M')

        # Extract risk management parameters
        stop_loss_pct = config.get('stop_loss_pct', 0.02)
        take_profit_pct = config.get('take_profit_pct', 0.06)
        max_position_pct = config.get('max_position_size_pct', 10.0)

        # Create rule using template
        rule = CRPRuleTemplates.create_custom_crp_rule(
            rule_id=rule_id,
            name=name,
            close_threshold_pct=close_threshold_pct,
            range_threshold_pct=range_threshold_pct,
            min_volume=min_volume,
            max_volume=max_volume,
            min_stock_price=min_price,
            max_stock_price=max_price,
            crp_cutoff_time=cutoff_time_str,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            max_position_pct=max_position_pct,
            **kwargs
        )

        # Add original config reference for compatibility
        rule['metadata']['original_config'] = config
        rule['metadata']['migration_info'] = {
            'migrated_from': 'CRPScanner',
            'migration_date': '2025-09-08',
            'compatibility_mode': True
        }

        return rule

    def execute_crp_scan(
        self,
        scan_date: date,
        rule_ids: Optional[List[str]] = None,
        cutoff_time: Optional[time] = None,
        max_results: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute CRP scan using the rule engine.

        Args:
            scan_date: Date to scan
            rule_ids: Specific rules to execute (None = all CRP rules)
            cutoff_time: Override cutoff time
            max_results: Maximum results per rule
            **kwargs: Additional execution parameters

        Returns:
            Scan results in format compatible with original scanner
        """
        # Ensure default rules are loaded
        self.load_default_rules()

        # If no specific rules provided, find all CRP rules
        if rule_ids is None:
            rule_ids = []
            for rule_id, rule in self.rule_engine.rules.items():
                if rule.get('rule_type') == 'crp' and rule.get('enabled', True):
                    rule_ids.append(rule_id)

        if not rule_ids:
            logger.warning("No CRP rules found or enabled")
            return {
                'success': False,
                'error': 'No CRP rules available',
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
        Execute CRP scan over a date range (equivalent to original scan_date_range).

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
                daily_result = self.execute_crp_scan(
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
                'total_crp_signals': total_results,
                'avg_signals_per_day': total_results / total_days if total_days > 0 else 0
            },
            'results': all_results,
            'daily_stats': daily_stats
        }

    def get_rule_performance(self, rule_id: str) -> Dict[str, Any]:
        """
        Get performance statistics for a CRP rule.

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
            original_scanner: Original CRPScanner instance
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
        rule_result = self.execute_crp_scan(scan_date, max_results=10)
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

        # Handle both single rule result and batch result formats
        if isinstance(batch_result.get('results'), list):
            # Single rule result format
            for signal in batch_result['results']:
                scanner_result = self._convert_signal_to_scanner_format(signal)
                converted_results.append(scanner_result)
        else:
            # Batch result format
            for rule_result in rule_results.values():
                if not rule_result.get('success', False):
                    continue

                for signal in rule_result.get('signals', []):
                    scanner_result = self._convert_signal_to_scanner_format(signal)
                    converted_results.append(scanner_result)

        # Sort by CRP probability score (descending) to match original behavior
        converted_results.sort(key=lambda x: x.get('crp_probability_score', 0), reverse=True)

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

        return {
            'symbol': symbol,
            'crp_price': price,
            'open_price': price,  # Use crp_price as open_price
            'current_high': price * 1.01 if price > 0 else None,
            'current_low': price * 0.99 if price > 0 else None,
            'current_volume': volume,
            'current_range_pct': 2.0,  # Default CRP range
            'close_score': 0.4,  # Default scores
            'range_score': 0.3,
            'volume_score': 0.2,
            'momentum_score': 0.1,
            'crp_probability_score': confidence * 100,
            'close_position': 'Near High',  # Default position
            'entry_price': price,
            'stop_loss': price * 0.98 if price > 0 else None,
            'take_profit': price * 1.06 if price > 0 else None,
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


class RuleBasedCRPScanner:
    """
    Rule-based CRP scanner that provides the same interface as the original
    CRPScanner but uses the rule engine internally.
    """

    def __init__(self, rule_engine: RuleEngine):
        """
        Initialize the rule-based CRP scanner.

        Args:
            rule_engine: Rule engine instance
        """
        self.rule_mapper = CRPRuleMapper(rule_engine)
        self.rule_mapper.load_default_rules()

    @property
    def scanner_name(self) -> str:
        return "rule_based_crp"

    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> List[Dict[str, Any]]:
        """
        Single-day scan (backward compatibility with original interface).
        """
        result = self.rule_mapper.execute_crp_scan(
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
                    'confidence': signal.get('crp_probability_score', 0) / 100,  # Convert from percentage
                    'price': signal.get('crp_price'),  # Map crp_price to price
                    'volume': signal.get('current_volume'),  # Map current_volume to volume
                    'rule_id': signal.get('rule_id'),
                    # Keep additional CRP-specific fields
                    'entry_price': signal.get('entry_price'),
                    'stop_loss': signal.get('stop_loss'),
                    'take_profit': signal.get('take_profit'),
                    'close_position': signal.get('close_position'),
                    'current_range_pct': signal.get('current_range_pct'),
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
            'supported_rules': ['crp-standard', 'crp-aggressive', 'crp-conservative', 'crp-high-probability'],
            'default_close_threshold_pct': 2.0,
            'default_range_threshold_pct': 3.0,
            'default_cutoff_time': '09:45'
        }

    def display_results_table(self, results: List[Dict[str, Any]], title: str = "Rule-Based CRP Scanner Results"):
        """Display results in table format (compatible with original)."""
        if not results:
            print("⚠️  No results to display")
            return

        print(f"\n🎯 {title}")
        print("=" * 100)

        # Print table with better formatting (updated for top 3 stocks)
        print("┌" + "─" * 10 + "┬" + "─" * 10 + "┬" + "─" * 12 + "┬" + "─" * 10 + "┬" + "─" * 12 + "┬" + "─" * 10 + "┬" + "─" * 10 + "┬" + "─" * 8 + "┬" + "─" * 6 + "┬" + "─" * 12 + "┐")
        print("│ {:<8} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<8} │ {:<8} │ {:<6} │ {:<4} │ {:<10} │".format(
            "Symbol", "Date", "CRP", "EOD", "Price", "Close", "Current", "Prob", "Rank", "Perform"))
        print("│ {:<8} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<8} │ {:<8} │ {:<6} │ {:<4} │ {:<10} │".format(
            "", "", "Price", "Price", "Change", "Pos", "Range%", "Score", "", "Rank"))

        print("├" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 12 + "┼" + "─" * 10 + "┼" + "─" * 12 + "┼" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 8 + "┼" + "─" * 6 + "┼" + "─" * 12 + "┤")

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
            crp_price = result.get('crp_price', 0)
            eod_price = result.get('eod_price', 0)
            price_change = result.get('price_change_pct', 0)
            close_position = result.get('close_position', 'N/A')[:8]  # Truncate position
            current_range_pct = result.get('current_range_pct', 0)
            crp_probability_score = result.get('crp_probability_score', 0)
            performance_rank = result.get('performance_rank', 0)

            print("│ {:<8} │ {:<8} │ ₹{:>8.2f} │ ₹{:>6.2f} │ {:>+8.2f}% │ {:<8} │ {:>6.2f}% │ {:>5.1f}% │ {:>4.2f} │ {:>8.2f} │".format(
                symbol, date_str, crp_price, eod_price, price_change,
                close_position, current_range_pct, crp_probability_score, performance_rank, performance_rank))

        print("└" + "─" * 10 + "┴" + "─" * 10 + "┴" + "─" * 12 + "┴" + "─" * 10 + "┴" + "─" * 12 + "┴" + "─" * 10 + "┴" + "─" * 10 + "┴" + "─" * 8 + "┴" + "─" * 6 + "┴" + "─" * 12 + "┘")

        print()

        # Display summary statistics
        if results:
            successful_count = sum(1 for r in results if r.get('crp_successful', True))
            total_count = len(results)
            success_rate = (successful_count / total_count * 100) if total_count > 0 else 0
            avg_change = sum(r.get('price_change_pct', 0) for r in results) / len(results) if results else 0

            print("📈 Summary Statistics (Top 3 Stocks Per Day):")
            print(f"   Total CRP Patterns: {total_count}")
            print(f"   Successful CRP Patterns: {successful_count}")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Average Price Change: {avg_change:.2f}%")
            print(f"   Average CRP Probability Score: {sum(r.get('crp_probability_score', 0) for r in results) / len(results) if results else 0:.1f}%")

    def export_results(self, results: List[Dict[str, Any]], filename: str = "rule_based_crp_results.csv"):
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
