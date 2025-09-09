#!/usr/bin/env python3
"""
Demonstration of the Rule Persistence Layer

This script demonstrates the complete persistence capabilities including:
- Database storage and retrieval
- File system operations
- Version control and history
- Backup and recovery
"""

import tempfile
from pathlib import Path
from datetime import datetime

from src.rules.storage.rule_repository import RuleRepository
from src.rules.storage.file_manager import FileManager
from src.rules.storage.version_manager import VersionManager
from src.rules.storage.backup_manager import BackupManager
from src.rules.schema.rule_types import RuleType, SignalType


def main():
    """Demonstrate the persistence layer functionality."""
    print("💾 Unified Rule Persistence Layer Demo")
    print("=" * 50)

    # Use temporary directories for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        rules_dir = temp_path / 'rules'
        backup_dir = temp_path / 'backups'

        print(f"📁 Using temporary directory: {temp_dir}")

        # 1. Initialize components
        print("\n🔧 Initializing Persistence Components...")

        # Mock database connection for demo
        mock_db = MockDatabaseConnection()

        repository = RuleRepository(mock_db)
        file_manager = FileManager(str(rules_dir))
        version_manager = VersionManager(repository)
        backup_manager = BackupManager(str(backup_dir))

        print("✅ Components initialized")

        # 2. Create sample rules
        print("\n📝 Creating Sample Rules...")

        breakout_rule = {
            'rule_id': 'demo-breakout-v1',
            'name': 'Demo Breakout Rule v1',
            'rule_type': 'breakout',
            'enabled': True,
            'priority': 50,
            'conditions': {
                'breakout_conditions': {
                    'min_volume_multiplier': 1.5,
                    'min_price_move_pct': 0.025
                },
                'time_window': {'start': '09:35', 'end': '10:30'}
            },
            'actions': {
                'signal_type': 'BUY',
                'risk_management': {
                    'stop_loss_pct': 0.02,
                    'take_profit_pct': 0.06
                }
            },
            'metadata': {
                'author': 'demo_user',
                'version': '1.0.0',
                'created_at': datetime.now().isoformat(),
                'tags': ['breakout', 'volume', 'demo']
            }
        }

        crp_rule = {
            'rule_id': 'demo-crp-v1',
            'name': 'Demo CRP Rule v1',
            'rule_type': 'crp',
            'enabled': True,
            'priority': 45,
            'conditions': {
                'crp_conditions': {
                    'close_threshold_pct': 2.0,
                    'range_threshold_pct': 3.0
                }
            },
            'actions': {
                'signal_type': 'BUY',
                'confidence_calculation': 'weighted_average'
            },
            'metadata': {
                'author': 'demo_user',
                'version': '1.0.0',
                'created_at': datetime.now().isoformat(),
                'tags': ['crp', 'pattern', 'demo']
            }
        }

        rules = [breakout_rule, crp_rule]
        print(f"✅ Created {len(rules)} sample rules")

        # 3. Demonstrate database operations
        print("\n💾 Database Operations...")

        # Save rules to database
        for rule in rules:
            success = repository.save_rule(rule)
            print(f"   {'✅' if success else '❌'} Saved rule: {rule['rule_id']}")

        # Load rules from database
        loaded_rules = repository.load_rules()
        print(f"   📊 Loaded {len(loaded_rules)} rules from database")

        # Load specific rule
        specific_rule = repository.load_rule('demo-breakout-v1')
        if specific_rule:
            print(f"   🔍 Loaded specific rule: {specific_rule['name']}")

        # Filter rules
        breakout_rules = repository.load_rules(rule_type=RuleType.BREAKOUT)
        print(f"   🎯 Found {len(breakout_rules)} breakout rules")

        # 4. Demonstrate file operations
        print("\n📁 File System Operations...")

        # Save rules to files
        for rule in rules:
            success = file_manager.save_rule_to_file(rule)
            print(f"   {'✅' if success else '❌'} Saved rule to file: {rule['rule_id']}")

        # Load rules from directory
        dir_rules = file_manager.load_rules_from_directory()
        print(f"   📂 Loaded {len(dir_rules)} rules from directory")

        # Get file information
        file_info = file_manager.get_rule_files_info()
        print(f"   📋 Found {len(file_info)} rule files")
        for info in file_info[:2]:  # Show first 2
            print(f"      - {info['filename']}: {info['size_bytes']} bytes")

        # Find rules by criteria
        breakout_files = file_manager.find_rules_by_criteria({'rule_type': 'breakout'})
        print(f"   🔎 Found {len(breakout_files)} breakout rule files")

        # 5. Demonstrate version control
        print("\n📈 Version Control Operations...")

        # Create version for breakout rule
        success = version_manager.create_version(
            breakout_rule, 'demo_user', 'Initial demo version'
        )
        print(f"   {'✅' if success else '❌'} Created version 1.0.0 for breakout rule")

        # Modify and create new version
        breakout_rule['metadata']['version'] = '1.1.0'
        breakout_rule['conditions']['breakout_conditions']['min_volume_multiplier'] = 2.0

        success = version_manager.create_version(
            breakout_rule, 'demo_user', 'Increased volume multiplier'
        )
        print(f"   {'✅' if success else '❌'} Created version 1.1.0 for breakout rule")

        # Get version history
        history = version_manager.get_version_history('demo-breakout-v1')
        print(f"   📚 Version history: {len(history)} versions")
        for version in history:
            print(f"      - v{version['version']}: {version['change_description']}")

        # Compare versions
        if len(history) >= 2:
            comparison = version_manager.compare_versions('demo-breakout-v1', '1.0.0', '1.1.0')
            print(f"   🔄 Version comparison: {'Changes found' if comparison['has_changes'] else 'No changes'}")

        # 6. Demonstrate backup operations
        print("\n💼 Backup and Recovery Operations...")

        # Create full backup
        backup_result = backup_manager.create_full_backup([str(rules_dir)], compress=False)
        print(f"   {'✅' if backup_result['status'] == 'success' else '❌'} Full backup: {backup_result['backup_name']}")
        print(f"      - Files: {backup_result['total_files']}")
        print(f"      - Size: {backup_result['total_size_bytes']} bytes")

        # List backups
        backups = backup_manager.list_backups()
        print(f"   📋 Available backups: {len(backups)}")
        for backup in backups:
            print(f"      - {backup['name']}: {backup['type']} ({backup['size_mb']:.2f} MB)")

        # Validate backup integrity
        if backups:
            validation = backup_manager.validate_backup_integrity(backups[0]['name'])
            print(f"   🔒 Backup integrity: {'✅ Valid' if validation['is_valid'] else '❌ Invalid'}")

        # 7. Demonstrate statistics
        print("\n📊 Statistics and Analytics...")

        # Repository statistics
        repo_stats = repository.get_repository_stats()
        print("   💾 Repository Stats:")
        print(f"      - Total rules: {repo_stats.get('total_rules', 0)}")
        print(f"      - Rules by type: {repo_stats.get('rules_by_type', {})}")

        # Rule execution statistics (mock data)
        print("   📈 Rule Performance Stats:")
        print("      - demo-breakout-v1: 85% success rate, 150ms avg execution")
        print("      - demo-crp-v1: 78% success rate, 120ms avg execution")

        # Version statistics
        version_stats = version_manager.get_version_stats('demo-breakout-v1')
        print("   📚 Version Stats:")
        print(f"      - Total versions: {version_stats.get('version_count', 0)}")
        print(f"      - Latest version: {version_stats.get('newest_version', 'N/A')}")

        print("\n🎉 Persistence Layer Demo Complete!")
        print("\n💡 Key Features Demonstrated:")
        print("   ✅ Database storage and retrieval")
        print("   ✅ File system operations")
        print("   ✅ Version control and history")
        print("   ✅ Backup and recovery")
        print("   ✅ Statistics and analytics")
        print("   ✅ Rule organization and management")

        print(f"\n🧹 Cleaning up temporary directory: {temp_dir}")


class MockDatabaseConnection:
    """Mock database connection for demo purposes."""

    def __init__(self):
        self.rules = {}
        self.executions = {}
        self.versions = {}
        self.next_id = 1

    def cursor(self):
        return MockCursor(self)

    def commit(self):
        pass

    def execute_query(self, sql, params=None):
        """Mock SQL execution."""
        if params is None:
            params = ()

        # Simple mock implementation for demo
        if 'INSERT INTO rules' in sql:
            rule_id = params[0]
            self.rules[rule_id] = params
            return []
        elif 'SELECT * FROM rules' in sql:
            return [list(rule_data) for rule_data in self.rules.values()]
        elif 'SELECT * FROM rules WHERE rule_id = ?' in sql:
            rule_id = params[0]
            if rule_id in self.rules:
                return [list(self.rules[rule_id])]
            return []
        else:
            return []


class MockCursor:
    """Mock database cursor."""

    def __init__(self, connection):
        self.connection = connection
        self.results = []

    def execute(self, sql, params=None):
        self.results = self.connection.execute_query(sql, params)

    def fetchall(self):
        return self.results

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


if __name__ == "__main__":
    main()
