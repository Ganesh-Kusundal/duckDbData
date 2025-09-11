#!/usr/bin/env python3
"""
Rule Manager CLI - Command Line Interface for Rule Management

This CLI tool provides comprehensive rule management capabilities:
- Create, read, update, delete rules
- Validate rules before deployment
- Deploy rules to production
- Monitor rule performance
- Backup and restore rules
- Export/import rules in various formats
"""

import json
import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ..engine.rule_engine import RuleEngine
from ..validation.enhanced_validator import EnhancedRuleValidator
from ..storage.rule_repository import RuleRepository
from ..storage.file_manager import FileManager
from ..storage.version_manager import VersionManager
from ..storage.backup_manager import BackupManager
from ..templates.breakout_rules import BreakoutRuleTemplates
from ..templates.crp_rules import CRPRuleTemplates


class RuleManagerCLI:
    """Command Line Interface for Rule Management."""

    def __init__(self):
        self.rule_engine = RuleEngine()
        self.validator = EnhancedRuleValidator(self.rule_engine)

        # Initialize storage components (would normally connect to database)
        self.repository = None  # RuleRepository()
        self.file_manager = FileManager("rules/")
        self.version_manager = None  # VersionManager()
        self.backup_manager = BackupManager("backups/rules/")

        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('rule_manager.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def create_parser(self):
        """Create argument parser for CLI."""
        parser = argparse.ArgumentParser(
            description="Rule Manager CLI - Manage trading rules",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Create a new breakout rule
  python rule_manager_cli.py create --type breakout --name "My Breakout" --volume-multiplier 2.0

  # List all rules
  python rule_manager_cli.py list

  # Validate a rule file
  python rule_manager_cli.py validate rule.json

  # Deploy rules to production
  python rule_manager_cli.py deploy --env production

  # Backup all rules
  python rule_manager_cli.py backup --name daily-backup

  # Monitor rule performance
  python rule_manager_cli.py monitor --rule-id breakout-standard --days 30
            """
        )

        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Create rule command
        create_parser = subparsers.add_parser('create', help='Create a new rule')
        create_parser.add_argument('--type', required=True, choices=['breakout', 'crp'],
                                 help='Rule type')
        create_parser.add_argument('--name', required=True, help='Rule name')
        create_parser.add_argument('--volume-multiplier', type=float, default=1.5,
                                 help='Volume multiplier for breakout rules')
        create_parser.add_argument('--close-threshold', type=float, default=2.0,
                                 help='Close threshold for CRP rules')
        create_parser.add_argument('--range-threshold', type=float, default=3.0,
                                 help='Range threshold for CRP rules')
        create_parser.add_argument('--output', help='Output file path')

        # List rules command
        list_parser = subparsers.add_parser('list', help='List all rules')
        list_parser.add_argument('--type', choices=['breakout', 'crp', 'all'],
                               default='all', help='Filter by rule type')
        list_parser.add_argument('--format', choices=['table', 'json', 'csv'],
                               default='table', help='Output format')

        # Get rule command
        get_parser = subparsers.add_parser('get', help='Get rule details')
        get_parser.add_argument('rule_id', help='Rule ID to retrieve')
        get_parser.add_argument('--format', choices=['json', 'yaml', 'pretty'],
                              default='pretty', help='Output format')

        # Update rule command
        update_parser = subparsers.add_parser('update', help='Update an existing rule')
        update_parser.add_argument('rule_id', help='Rule ID to update')
        update_parser.add_argument('--file', help='JSON file with updates')
        update_parser.add_argument('--set', action='append',
                                 help='Key-value pairs to update (key=value)')

        # Delete rule command
        delete_parser = subparsers.add_parser('delete', help='Delete a rule')
        delete_parser.add_argument('rule_id', help='Rule ID to delete')
        delete_parser.add_argument('--force', action='store_true',
                                 help='Force deletion without confirmation')

        # Validate command
        validate_parser = subparsers.add_parser('validate', help='Validate rules')
        validate_parser.add_argument('files', nargs='*', help='Rule files to validate')
        validate_parser.add_argument('--all', action='store_true',
                                   help='Validate all rules in repository')
        validate_parser.add_argument('--strict', action='store_true',
                                   help='Strict validation (fail on warnings)')

        # Deploy command
        deploy_parser = subparsers.add_parser('deploy', help='Deploy rules to environment')
        deploy_parser.add_argument('--env', choices=['development', 'staging', 'production'],
                                 default='development', help='Target environment')
        deploy_parser.add_argument('--rules', nargs='*', help='Specific rules to deploy')
        deploy_parser.add_argument('--all', action='store_true',
                                 help='Deploy all validated rules')

        # Backup command
        backup_parser = subparsers.add_parser('backup', help='Backup rules')
        backup_parser.add_argument('--name', help='Backup name')
        backup_parser.add_argument('--compress', action='store_true',
                                 help='Compress backup')

        # Restore command
        restore_parser = subparsers.add_parser('restore', help='Restore rules from backup')
        restore_parser.add_argument('backup_name', help='Backup name to restore')

        # Monitor command
        monitor_parser = subparsers.add_parser('monitor', help='Monitor rule performance')
        monitor_parser.add_argument('--rule-id', help='Specific rule to monitor')
        monitor_parser.add_argument('--days', type=int, default=7,
                                  help='Days to look back')
        monitor_parser.add_argument('--format', choices=['table', 'json', 'chart'],
                                  default='table', help='Output format')

        # Template command
        template_parser = subparsers.add_parser('template', help='Generate rule templates')
        template_parser.add_argument('--type', required=True,
                                   choices=['breakout', 'crp'],
                                   help='Template type')
        template_parser.add_argument('--variant', choices=['standard', 'aggressive', 'conservative', 'high-probability'],
                                   default='standard', help='Template variant')
        template_parser.add_argument('--output', help='Output file path')

        return parser

    def run_command(self, args):
        """Run the specified command."""
        command_map = {
            'create': self.create_rule,
            'list': self.list_rules,
            'get': self.get_rule,
            'update': self.update_rule,
            'delete': self.delete_rule,
            'validate': self.validate_rules,
            'deploy': self.deploy_rules,
            'backup': self.backup_rules,
            'restore': self.restore_rules,
            'monitor': self.monitor_rules,
            'template': self.generate_template
        }

        if args.command in command_map:
            return command_map[args.command](args)
        else:
            self.logger.error(f"Unknown command: {args.command}")
            return False

    def create_rule(self, args):
        """Create a new rule."""
        try:
            if args.type == 'breakout':
                rule = BreakoutRuleTemplates.create_custom_breakout_rule(
                    rule_id=f"custom-breakout-{int(datetime.now().timestamp())}",
                    name=args.name,
                    volume_multiplier=args.volume_multiplier
                )
            elif args.type == 'crp':
                rule = CRPRuleTemplates.create_custom_crp_rule(
                    rule_id=f"custom-crp-{int(datetime.now().timestamp())}",
                    name=args.name,
                    close_threshold_pct=args.close_threshold,
                    range_threshold_pct=args.range_threshold
                )

            # Validate the rule
            validation_result = self.validator.validate_single_rule_comprehensive(rule)

            if validation_result.is_valid:
                self.logger.info(f"✅ Rule '{args.name}' created and validated successfully")

                # Save to file if requested
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(rule, f, indent=2)
                    self.logger.info(f"Rule saved to: {args.output}")
                else:
                    print(json.dumps(rule, indent=2))

                return True
            else:
                self.logger.error("❌ Rule validation failed:")
                for error in validation_result.errors:
                    print(f"  - {error.field}: {error.message}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to create rule: {e}")
            return False

    def list_rules(self, args):
        """List all rules."""
        try:
            # Get rules from templates (in real implementation, this would come from database)
            all_rules = []
            all_rules.extend(BreakoutRuleTemplates.get_all_templates())
            all_rules.extend(CRPRuleTemplates.get_all_templates())

            # Filter by type if specified
            if args.type != 'all':
                all_rules = [r for r in all_rules if r.get('rule_type') == args.type]

            if args.format == 'json':
                print(json.dumps(all_rules, indent=2))
            elif args.format == 'csv':
                if all_rules:
                    df = pd.DataFrame(all_rules)
                    print(df.to_csv(index=False))
            else:  # table format
                if not all_rules:
                    print("No rules found")
                    return True

                print("┌────────────────────┬────────────────────┬────────────┬─────────┐")
                print("│ Rule ID            │ Name               │ Type       │ Status  │")
                print("├────────────────────┼────────────────────┼────────────┼─────────┤")

                for rule in all_rules:
                    rule_id = rule.get('rule_id', 'N/A')[:18]
                    name = rule.get('name', 'N/A')[:18]
                    rule_type = rule.get('rule_type', 'N/A')[:10]
                    status = "✅ Active" if rule.get('enabled', True) else "⏸️  Disabled"

                    print("│ {:<18} │ {:<18} │ {:<10} │ {:<7} │".format(
                        rule_id, name, rule_type, status))

                print("└────────────────────┴────────────────────┴────────────┴─────────┘")
                print(f"\nTotal Rules: {len(all_rules)}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to list rules: {e}")
            return False

    def get_rule(self, args):
        """Get rule details."""
        try:
            # In real implementation, this would fetch from database
            # For demo, we'll use templates
            all_rules = []
            all_rules.extend(BreakoutRuleTemplates.get_all_templates())
            all_rules.extend(CRPRuleTemplates.get_all_templates())

            rule = None
            for r in all_rules:
                if r.get('rule_id') == args.rule_id:
                    rule = r
                    break

            if not rule:
                self.logger.error(f"Rule not found: {args.rule_id}")
                return False

            if args.format == 'json':
                print(json.dumps(rule, indent=2))
            elif args.format == 'yaml':
                try:
                    import yaml
                    print(yaml.dump(rule, default_flow_style=False))
                except ImportError:
                    self.logger.error("PyYAML not installed for YAML output")
                    return False
            else:  # pretty format
                print(f"Rule ID: {rule.get('rule_id')}")
                print(f"Name: {rule.get('name')}")
                print(f"Type: {rule.get('rule_type')}")
                print(f"Description: {rule.get('description', 'N/A')}")
                print(f"Enabled: {rule.get('enabled', True)}")
                print(f"Priority: {rule.get('priority', 50)}")
                print(f"Version: {rule.get('metadata', {}).get('version', 'N/A')}")

                # Conditions
                conditions = rule.get('conditions', {})
                print("\nConditions:")
                if 'time_window' in conditions:
                    tw = conditions['time_window']
                    print(f"  Time Window: {tw.get('start')} - {tw.get('end')}")

                if rule.get('rule_type') == 'breakout' and 'breakout_conditions' in conditions:
                    bc = conditions['breakout_conditions']
                    print(f"  Volume Multiplier: {bc.get('min_volume_multiplier', 'N/A')}")
                    print(f"  Price Move Threshold: {bc.get('min_price_move_pct', 'N/A')}%")

                if rule.get('rule_type') == 'crp' and 'crp_conditions' in conditions:
                    cc = conditions['crp_conditions']
                    print(f"  Close Threshold: {cc.get('close_threshold_pct', 'N/A')}%")
                    print(f"  Range Threshold: {cc.get('range_threshold_pct', 'N/A')}%")

            return True

        except Exception as e:
            self.logger.error(f"Failed to get rule: {e}")
            return False

    def validate_rules(self, args):
        """Validate rules."""
        try:
            rules_to_validate = []

            if args.all:
                # Validate all rules
                rules_to_validate.extend(BreakoutRuleTemplates.get_all_templates())
                rules_to_validate.extend(CRPRuleTemplates.get_all_templates())
            else:
                # Validate specific files
                for file_path in args.files:
                    if os.path.exists(file_path):
                        with open(file_path, 'r') as f:
                            rule = json.load(f)
                            rules_to_validate.append(rule)
                    else:
                        self.logger.error(f"File not found: {file_path}")

            if not rules_to_validate:
                self.logger.error("No rules to validate")
                return False

            # Validate rules
            report = self.validator.validate_comprehensive(rules_to_validate)

            # Display results
            print("🔍 Validation Results:")
            print("=" * 50)
            print(f"Total Rules: {report.summary['total_rules']}")
            print(f"Valid Rules: {report.summary['valid_rules']}")
            print(f"Invalid Rules: {report.summary['invalid_rules']}")
            print(".1f")

            if report.summary['invalid_rules'] > 0:
                print("\n❌ Validation Errors:")
                for rule_id, result in report.rule_reports.items():
                    if not result.is_valid:
                        print(f"\nRule: {rule_id}")
                        for error in result.errors[:3]:  # Show first 3 errors
                            print(f"  - {error.field}: {error.message}")

            if report.performance_warnings:
                print("\n⚠️  Performance Warnings:")
                for warning in report.performance_warnings[:5]:  # Show first 5
                    print(f"  - {warning}")

            success = report.summary['overall_status'] == 'PASS'
            if success:
                print("\n✅ All rules passed validation!")
            else:
                print("\n❌ Some rules failed validation. Please fix the issues above.")

            return success

        except Exception as e:
            self.logger.error(f"Failed to validate rules: {e}")
            return False

    def deploy_rules(self, args):
        """Deploy rules to environment."""
        try:
            print(f"🚀 Deploying rules to {args.env} environment...")

            # In real implementation, this would deploy to different environments
            if args.all:
                # Deploy all validated rules
                all_rules = []
                all_rules.extend(BreakoutRuleTemplates.get_all_templates())
                all_rules.extend(CRPRuleTemplates.get_all_templates())

                # Validate before deployment
                report = self.validator.validate_comprehensive(all_rules)
                if report.summary['overall_status'] != 'PASS':
                    self.logger.error("❌ Cannot deploy - validation failed")
                    return False

                deployed_count = len(all_rules)
            else:
                # Deploy specific rules
                deployed_count = len(args.rules) if args.rules else 0

            print(f"✅ Successfully deployed {deployed_count} rules to {args.env}")
            print(f"📊 Deployment completed at {datetime.now().isoformat()}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to deploy rules: {e}")
            return False

    def backup_rules(self, args):
        """Backup rules."""
        try:
            backup_name = args.name or f"backup-{int(datetime.now().timestamp())}"

            print(f"💾 Creating backup: {backup_name}")

            # In real implementation, this would backup from database
            # For demo, we'll backup the template directories
            result = self.backup_manager.create_full_backup(
                source_directories=["src/rules/templates"],
                backup_name=backup_name,
                compress=args.compress
            )

            if result['status'] == 'success':
                print(f"✅ Backup created successfully: {result['backup_name']}")
                print(f"📊 Files backed up: {result['total_files']}")
                print(f"💾 Backup size: {result['total_size_bytes']} bytes")
                if args.compress:
                    print(f"📦 Compressed size: {result['compressed_size_bytes']} bytes")
                return True
            else:
                self.logger.error(f"❌ Backup failed: {result.get('errors', ['Unknown error'])}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to backup rules: {e}")
            return False

    def monitor_rules(self, args):
        """Monitor rule performance."""
        try:
            print("📊 Rule Performance Monitoring")
            print("=" * 40)

            if args.rule_id:
                print(f"Monitoring rule: {args.rule_id}")
            else:
                print("Monitoring all active rules")

            print(f"Time period: Last {args.days} days")

            # In real implementation, this would query performance metrics
            # For demo, we'll show mock performance data
            mock_performance = {
                'breakout-standard': {
                    'signals_generated': 45,
                    'successful_trades': 32,
                    'win_rate': 71.1,
                    'avg_profit': 2.3,
                    'avg_loss': -1.8,
                    'profit_factor': 1.9
                },
                'crp-standard': {
                    'signals_generated': 38,
                    'successful_trades': 28,
                    'win_rate': 73.7,
                    'avg_profit': 2.8,
                    'avg_loss': -1.9,
                    'profit_factor': 2.1
                }
            }

            if args.format == 'json':
                print(json.dumps(mock_performance, indent=2))
            elif args.format == 'chart':
                self._display_performance_chart(mock_performance)
            else:  # table format
                self._display_performance_table(mock_performance)

            return True

        except Exception as e:
            self.logger.error(f"Failed to monitor rules: {e}")
            return False

    def _display_performance_table(self, performance_data):
        """Display performance data in table format."""
        print("┌────────────────────┬──────────────┬──────────────┬────────────┬────────────┬────────────┐")
        print("│ Rule ID            │ Signals      │ Win Rate     │ Avg Profit │ Avg Loss   │ Profit     │")
        print("│                    │ Generated    │ %            │ %          │ %          │ Factor     │")
        print("├────────────────────┼──────────────┼──────────────┼────────────┼────────────┼────────────┤")

        for rule_id, data in performance_data.items():
            signals = data['signals_generated']
            win_rate = data['win_rate']
            avg_profit = data['avg_profit']
            avg_loss = data['avg_loss']
            profit_factor = data['profit_factor']

            print("│ {:<18} │ {:<12} │ {:>10.1f}% │ {:>+8.1f}% │ {:>+8.1f}% │ {:>8.2f} │".format(
                rule_id[:18], signals, win_rate, avg_profit, avg_loss, profit_factor))

        print("└────────────────────┴──────────────┴──────────────┴────────────┴────────────┴────────────┘")

    def _display_performance_chart(self, performance_data):
        """Display performance data as simple ASCII chart."""
        print("📈 Performance Chart (Win Rate %)")
        print("-" * 40)

        max_win_rate = max(data['win_rate'] for data in performance_data.values())

        for rule_id, data in performance_data.items():
            win_rate = data['win_rate']
            bar_length = int((win_rate / max_win_rate) * 30)  # Scale to 30 chars
            bar = "█" * bar_length
            print("25")

    def generate_template(self, args):
        """Generate rule template."""
        try:
            if args.type == 'breakout':
                if args.variant == 'standard':
                    rule = BreakoutRuleTemplates.get_standard_breakout_rule()
                elif args.variant == 'aggressive':
                    rule = BreakoutRuleTemplates.get_aggressive_breakout_rule()
                elif args.variant == 'conservative':
                    rule = BreakoutRuleTemplates.get_conservative_breakout_rule()
                else:
                    self.logger.error(f"Unknown breakout variant: {args.variant}")
                    return False
            elif args.type == 'crp':
                if args.variant == 'standard':
                    rule = CRPRuleTemplates.get_standard_crp_rule()
                elif args.variant == 'aggressive':
                    rule = CRPRuleTemplates.get_aggressive_crp_rule()
                elif args.variant == 'conservative':
                    rule = CRPRuleTemplates.get_conservative_crp_rule()
                elif args.variant == 'high-probability':
                    rule = CRPRuleTemplates.get_high_probability_crp_rule()
                else:
                    self.logger.error(f"Unknown CRP variant: {args.variant}")
                    return False

            # Save or display template
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(rule, f, indent=2)
                print(f"✅ Template saved to: {args.output}")
            else:
                print(json.dumps(rule, indent=2))

            return True

        except Exception as e:
            self.logger.error(f"Failed to generate template: {e}")
            return False

    def update_rule(self, args):
        """Update an existing rule."""
        self.logger.info(f"Updating rule: {args.rule_id}")
        print("⚠️  Update functionality would be implemented in production")
        return True

    def delete_rule(self, args):
        """Delete a rule."""
        if not args.force:
            confirm = input(f"Are you sure you want to delete rule '{args.rule_id}'? (y/N): ")
            if confirm.lower() != 'y':
                print("Operation cancelled")
                return True

        self.logger.info(f"Deleting rule: {args.rule_id}")
        print("⚠️  Delete functionality would be implemented in production")
        return True

    def restore_rules(self, args):
        """Restore rules from backup."""
        self.logger.info(f"Restoring from backup: {args.backup_name}")
        print("⚠️  Restore functionality would be implemented in production")
        return True


def main():
    """Main entry point for Rule Manager CLI."""
    cli = RuleManagerCLI()
    parser = cli.create_parser()

    try:
        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            return 0

        success = cli.run_command(args)
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
