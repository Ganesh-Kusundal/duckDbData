"""
Trading Rules Engine
===================

Evaluates breakout patterns against predefined trading rules.
"""

import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, time
import logging

try:
    from ..core.pattern_analyzer import BreakoutPattern
except ImportError:
    # Handle case when running as standalone module
    from typing import Any as BreakoutPattern

logger = logging.getLogger(__name__)


@dataclass
class TradingRule:
    """Represents a trading rule for signal generation."""
    name: str
    description: str
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    enabled: bool = True
    created_at: datetime = None
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class TradingSignal:
    """Represents a generated trading signal."""
    symbol: str
    rule_name: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    timestamp: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class RuleEngine:
    """Engine for evaluating trading rules against patterns."""

    def __init__(self):
        self.rules: Dict[str, TradingRule] = {}
        self.signal_callbacks: List[Callable] = []
        self._load_default_rules()

    def add_rule(self, rule: TradingRule) -> None:
        """Add a trading rule to the engine."""
        self.rules[rule.name] = rule
        logger.info(f"Added trading rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a trading rule from the engine."""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"Removed trading rule: {rule_name}")
            return True
        return False

    def evaluate_pattern(self, pattern: BreakoutPattern) -> List[TradingSignal]:
        """Evaluate a pattern against all active rules."""
        signals = []

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            signal = self._evaluate_single_rule(pattern, rule)
            if signal:
                signals.append(signal)
                rule.last_triggered = datetime.now()
                rule.trigger_count += 1

        # Notify callbacks
        for callback in self.signal_callbacks:
            try:
                callback(signals)
            except Exception as e:
                logger.error(f"Signal callback failed: {e}")

        return signals

    def _evaluate_single_rule(self, pattern: BreakoutPattern, rule: TradingRule) -> Optional[TradingSignal]:
        """Evaluate a single pattern against a single rule."""
        try:
            # Check volume condition
            if 'min_volume_multiplier' in rule.conditions:
                if pattern.volume_multiplier < rule.conditions['min_volume_multiplier']:
                    return None

            # Check price move condition
            if 'min_price_move' in rule.conditions:
                if pattern.price_move_pct < rule.conditions['min_price_move']:
                    return None

            # Check confidence condition
            if 'min_confidence' in rule.conditions:
                if pattern.confidence_score < rule.conditions['min_confidence']:
                    return None

            # Check time window condition
            if 'time_window' in rule.conditions:
                time_window = rule.conditions['time_window']
                pattern_time = pattern.trigger_time.time()
                start_time = datetime.strptime(time_window['start'], '%H:%M').time()
                end_time = datetime.strptime(time_window['end'], '%H:%M').time()

                if not (start_time <= pattern_time <= end_time):
                    return None

            # Check symbol filter
            if 'symbols' in rule.conditions:
                if pattern.symbol not in rule.conditions['symbols']:
                    return None

            # All conditions met - generate signal
            signal_type = rule.actions.get('signal_type', 'BUY')
            confidence = min(pattern.confidence_score, 1.0)

            # Calculate price targets
            entry_price = pattern.technical_indicators.get('entry_price', 0)
            price_move_pct = pattern.price_move_pct

            if signal_type == 'BUY':
                price_target = entry_price * (1 + abs(price_move_pct) * 0.8)  # 80% of breakout move
                stop_loss = entry_price * (1 - abs(price_move_pct) * 0.5)    # 50% of breakout move
            else:
                price_target = entry_price * (1 - abs(price_move_pct) * 0.8)
                stop_loss = entry_price * (1 + abs(price_move_pct) * 0.5)

            signal = TradingSignal(
                symbol=pattern.symbol,
                rule_name=rule.name,
                signal_type=signal_type,
                confidence=confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                metadata={
                    'pattern_type': pattern.pattern_type,
                    'volume_multiplier': pattern.volume_multiplier,
                    'price_move_pct': pattern.price_move_pct,
                    'trigger_time': pattern.trigger_time.isoformat()
                }
            )

            logger.info(f"Rule {rule.name} triggered signal: {signal.symbol} {signal.signal_type}")
            return signal

        except Exception as e:
            logger.error(f"Error evaluating rule {rule.name}: {e}")
            return None

    def add_signal_callback(self, callback: Callable) -> None:
        """Add a callback for signal notifications."""
        self.signal_callbacks.append(callback)

    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics about rule performance."""
        stats = {
            'total_rules': len(self.rules),
            'active_rules': len([r for r in self.rules.values() if r.enabled]),
            'total_triggers': sum(r.trigger_count for r in self.rules.values()),
            'rules': []
        }

        for rule in self.rules.values():
            rule_stats = {
                'name': rule.name,
                'enabled': rule.enabled,
                'trigger_count': rule.trigger_count,
                'last_triggered': rule.last_triggered.isoformat() if rule.last_triggered else None,
                'created_at': rule.created_at.isoformat()
            }
            stats['rules'].append(rule_stats)

        return stats

    def _load_default_rules(self) -> None:
        """Load default trading rules."""
        # Volume Spike Breakout Rule
        volume_rule = TradingRule(
            name="volume_spike_breakout",
            description="High volume breakout with price momentum",
            conditions={
                'min_volume_multiplier': 1.5,
                'min_price_move': 0.02,
                'min_confidence': 0.6,
                'time_window': {'start': '09:35', 'end': '10:30'}
            },
            actions={
                'signal_type': 'BUY'
            }
        )

        # Time Window Momentum Rule
        time_rule = TradingRule(
            name="time_window_momentum",
            description="Opening range breakout with time-based momentum",
            conditions={
                'min_volume_multiplier': 1.2,
                'min_price_move': 0.015,
                'min_confidence': 0.5,
                'time_window': {'start': '09:35', 'end': '09:50'}
            },
            actions={
                'signal_type': 'BUY'
            }
        )

        self.add_rule(volume_rule)
        self.add_rule(time_rule)

    def save_rules_to_file(self, filename: str = "trading_rules.json") -> None:
        """Save current rules to JSON file."""
        rules_data = []
        for rule in self.rules.values():
            rule_dict = {
                'name': rule.name,
                'description': rule.description,
                'conditions': rule.conditions,
                'actions': rule.actions,
                'enabled': rule.enabled,
                'created_at': rule.created_at.isoformat(),
                'last_triggered': rule.last_triggered.isoformat() if rule.last_triggered else None,
                'trigger_count': rule.trigger_count
            }
            rules_data.append(rule_dict)

        with open(filename, 'w') as f:
            json.dump(rules_data, f, indent=2)

        logger.info(f"Saved {len(rules_data)} rules to {filename}")

    def load_rules_from_file(self, filename: str = "trading_rules.json") -> None:
        """Load rules from JSON file."""
        try:
            with open(filename, 'r') as f:
                rules_data = json.load(f)

            for rule_dict in rules_data:
                rule = TradingRule(
                    name=rule_dict['name'],
                    description=rule_dict['description'],
                    conditions=rule_dict['conditions'],
                    actions=rule_dict['actions'],
                    enabled=rule_dict.get('enabled', True)
                )
                # Restore metadata
                if 'created_at' in rule_dict:
                    rule.created_at = datetime.fromisoformat(rule_dict['created_at'])
                if 'last_triggered' in rule_dict and rule_dict['last_triggered']:
                    rule.last_triggered = datetime.fromisoformat(rule_dict['last_triggered'])
                rule.trigger_count = rule_dict.get('trigger_count', 0)

                self.add_rule(rule)

            logger.info(f"Loaded {len(rules_data)} rules from {filename}")

        except FileNotFoundError:
            logger.warning(f"Rules file {filename} not found")
        except Exception as e:
            logger.error(f"Error loading rules from {filename}: {e}")
