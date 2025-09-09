"""
Tests for Rule Persistence Layer

This module tests the persistence capabilities including:
- Database storage and retrieval
- File system operations
- Version control and history
- Backup and recovery
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.rules.storage.rule_repository import RuleRepository
from src.rules.storage.file_manager import FileManager
from src.rules.storage.version_manager import VersionManager
from src.rules.storage.backup_manager import BackupManager
from src.rules.schema.rule_types import RuleType, SignalType


class TestRuleRepository:
    """Test rule repository functionality."""

    @pytest.fixture
    def mock_db_connection(self):
        """Create mock database connection."""
        conn = Mock()
        # Mock cursor
        cursor = Mock()
        conn.cursor.return_value = cursor
        conn.commit = Mock()
        return conn

    @pytest.fixture
    def repository(self, mock_db_connection):
        """Create rule repository instance."""
        repo = RuleRepository(mock_db_connection)
        # Mock the table creation
        repo._execute_query = Mock()
        return repo

    def test_save_rule(self, repository):
        """Test saving a rule to database."""
        rule = {
            'rule_id': 'test-rule',
            'name': 'Test Rule',
            'rule_type': 'breakout',
            'conditions': {'breakout_conditions': {'min_volume_multiplier': 1.5}},
            'actions': {'signal_type': 'BUY'},
            'metadata': {'author': 'test', 'version': '1.0.0'}
        }

        # Mock successful save
        repository._execute_query.return_value = []

        success = repository.save_rule(rule)
        assert success

        # Verify query was called
        assert repository._execute_query.called

    def test_load_rule(self, repository):
        """Test loading a rule from database."""
        rule_id = 'test-rule'

        # Mock database response
        mock_row = (
            'test-rule', 'Test Rule', 'Description', 'breakout', True, 50,
            '{"breakout_conditions": {"min_volume_multiplier": 1.5}}',
            '{"signal_type": "BUY"}',
            '{"author": "test", "version": "1.0.0"}',
            '2025-01-01T10:00:00', '2025-01-01T10:00:00', '1.0.0', 'test',
            '["tag1", "tag2"]'
        )
        repository._execute_query.return_value = [mock_row]

        rule = repository.load_rule(rule_id)

        assert rule is not None
        assert rule['rule_id'] == 'test-rule'
        assert rule['name'] == 'Test Rule'
        assert rule['rule_type'] == 'breakout'
        assert rule['enabled'] is True

    def test_load_rules_with_filters(self, repository):
        """Test loading rules with filters."""
        # Mock database response
        mock_rows = [
            ('rule1', 'Rule 1', None, 'breakout', True, 50, '{}', '{}', '{}',
             None, None, '1.0.0', 'test', None),
            ('rule2', 'Rule 2', None, 'crp', True, 45, '{}', '{}', '{}',
             None, None, '1.0.0', 'test', None)
        ]
        repository._execute_query.return_value = mock_rows

        # Test rule type filter
        rules = repository.load_rules(rule_type=RuleType.BREAKOUT)
        breakout_rules = [r for r in rules if r['rule_type'] == 'breakout']
        assert len(breakout_rules) == 1
        assert breakout_rules[0]['rule_type'] == 'breakout'

        # Test enabled only filter
        rules = repository.load_rules(enabled_only=True)
        assert len(rules) == 2

    def test_delete_rule(self, repository):
        """Test deleting a rule."""
        rule_id = 'test-rule'

        repository._execute_query.return_value = []
        success = repository.delete_rule(rule_id)

        assert success
        # Should call delete queries 3 times (main table, executions, versions)
        assert repository._execute_query.call_count == 3

    def test_save_execution_result(self, repository):
        """Test saving execution result."""
        rule_id = 'test-rule'
        success = True
        execution_time = 150.5
        signals_generated = 3

        repository._execute_query.return_value = []
        success_save = repository.save_execution_result(
            rule_id, success, execution_time, signals_generated
        )

        assert success_save
        repository._execute_query.assert_called_once()

    def test_get_rule_statistics(self, repository):
        """Test getting rule execution statistics."""
        rule_id = 'test-rule'

        # Mock database response
        mock_row = (10, 8, 80.0, 25, '2025-01-01T10:00:00')
        repository._execute_query.return_value = [mock_row]

        stats = repository.get_rule_statistics(rule_id)

        assert stats['rule_id'] == rule_id
        assert stats['total_executions'] == 10
        assert stats['successful_executions'] == 8
        assert stats['success_rate'] == 0.8
        assert stats['total_signals_generated'] == 25


class TestFileManager:
    """Test file manager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def file_manager(self, temp_dir):
        """Create file manager instance."""
        return FileManager(str(temp_dir))

    def test_save_rule_to_file(self, file_manager, temp_dir):
        """Test saving rule to file."""
        rule = {
            'rule_id': 'test-rule',
            'name': 'Test Rule',
            'rule_type': 'breakout',
            'conditions': {'breakout_conditions': {'min_volume_multiplier': 1.5}},
            'actions': {'signal_type': 'BUY'},
            'metadata': {'author': 'test', 'version': '1.0.0'}
        }

        success = file_manager.save_rule_to_file(rule)
        assert success

        # Check file was created
        rule_file = temp_dir / 'breakout_test-rule.json'
        assert rule_file.exists()

        # Check file contents
        with open(rule_file, 'r') as f:
            saved_rule = json.load(f)

        assert saved_rule['rule_id'] == 'test-rule'
        assert saved_rule['name'] == 'Test Rule'

    def test_load_rule_from_file(self, file_manager, temp_dir):
        """Test loading rule from file."""
        rule = {
            'rule_id': 'test-rule',
            'name': 'Test Rule',
            'rule_type': 'breakout',
            'conditions': {},
            'actions': {'signal_type': 'BUY'},
            'metadata': {'author': 'test', 'version': '1.0.0'}
        }

        # Save rule first
        rule_file = temp_dir / 'test_rule.json'
        with open(rule_file, 'w') as f:
            json.dump(rule, f)

        # Load rule
        loaded_rule = file_manager.load_rule_from_file('test_rule.json')

        assert loaded_rule is not None
        assert loaded_rule['rule_id'] == 'test-rule'
        assert loaded_rule['name'] == 'Test Rule'

    def test_load_rules_from_directory(self, file_manager, temp_dir):
        """Test loading multiple rules from directory."""
        # Create test rule files
        rule1 = {
            'rule_id': 'rule1',
            'name': 'Rule 1',
            'rule_type': 'breakout',
            'conditions': {},
            'actions': {'signal_type': 'BUY'},
            'metadata': {'author': 'test', 'version': '1.0.0'}
        }

        rule2 = {
            'rule_id': 'rule2',
            'name': 'Rule 2',
            'rule_type': 'crp',
            'conditions': {},
            'actions': {'signal_type': 'SELL'},
            'metadata': {'author': 'test', 'version': '1.0.0'}
        }

        with open(temp_dir / 'rule1.json', 'w') as f:
            json.dump(rule1, f)

        with open(temp_dir / 'rule2.json', 'w') as f:
            json.dump(rule2, f)

        # Load rules
        rules = file_manager.load_rules_from_directory()

        assert len(rules) == 2
        rule_ids = [r['rule_id'] for r in rules]
        assert 'rule1' in rule_ids
        assert 'rule2' in rule_ids

    def test_get_rule_files_info(self, file_manager, temp_dir):
        """Test getting rule file information."""
        # Create test files
        rule_file = temp_dir / 'test.json'
        rule_file.write_text('{}')

        files_info = file_manager.get_rule_files_info()

        assert len(files_info) == 1
        assert files_info[0]['filename'] == 'test.json'
        assert 'size_bytes' in files_info[0]
        assert 'modified_time' in files_info[0]

    def test_find_rules_by_criteria(self, file_manager, temp_dir):
        """Test finding rules by criteria."""
        # Create test rule files
        breakout_rule = {
            'rule_id': 'breakout-rule',
            'name': 'Breakout Rule',
            'rule_type': 'breakout',
            'conditions': {},
            'actions': {'signal_type': 'BUY'},
            'metadata': {'author': 'test', 'tags': ['breakout'], 'version': '1.0.0'}
        }

        crp_rule = {
            'rule_id': 'crp-rule',
            'name': 'CRP Rule',
            'rule_type': 'crp',
            'conditions': {},
            'actions': {'signal_type': 'SELL'},
            'metadata': {'author': 'test', 'tags': ['crp'], 'version': '1.0.0'}
        }

        with open(temp_dir / 'breakout.json', 'w') as f:
            json.dump(breakout_rule, f)

        with open(temp_dir / 'crp.json', 'w') as f:
            json.dump(crp_rule, f)

        # Find by rule type
        breakout_rules = file_manager.find_rules_by_criteria({'rule_type': 'breakout'})
        assert len(breakout_rules) == 1
        assert breakout_rules[0]['rule_type'] == 'breakout'

        # Find by tags
        tagged_rules = file_manager.find_rules_by_criteria({'tags': ['breakout']})
        assert len(tagged_rules) == 1
        assert 'breakout' in tagged_rules[0]['metadata']['tags']


class TestVersionManager:
    """Test version manager functionality."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        repo = Mock()
        repo._save_rule_version = Mock()
        repo._execute_query = Mock()
        return repo

    @pytest.fixture
    def version_manager(self, mock_repository):
        """Create version manager instance."""
        return VersionManager(mock_repository)

    def test_create_version(self, version_manager, mock_repository):
        """Test creating a new rule version."""
        rule = {
            'rule_id': 'test-rule',
            'name': 'Test Rule',
            'rule_type': 'breakout',
            'conditions': {},
            'actions': {'signal_type': 'BUY'},
            'metadata': {'author': 'test', 'version': '1.0.0'}
        }

        mock_repository._save_rule_version.return_value = True

        success = version_manager.create_version(rule, 'test_author', 'Updated conditions')

        assert success
        mock_repository._save_rule_version.assert_called_once()

    def test_get_version_history(self, version_manager, mock_repository):
        """Test getting version history."""
        rule_id = 'test-rule'

        # Mock database response
        mock_rows = [
            ('1.0.0', '{"rule_id": "test-rule"}', '2025-01-01T10:00:00', 'author1', 'Initial version'),
            ('1.1.0', '{"rule_id": "test-rule"}', '2025-01-02T10:00:00', 'author2', 'Updated conditions')
        ]
        mock_repository._execute_query.return_value = mock_rows

        history = version_manager.get_version_history(rule_id)

        assert len(history) == 2
        assert history[0]['version'] == '1.0.0'
        assert history[0]['change_description'] == 'Initial version'
        assert history[1]['version'] == '1.1.0'

    def test_compare_versions(self, version_manager, mock_repository):
        """Test comparing rule versions."""
        rule_id = 'test-rule'
        version1 = '1.0.0'
        version2 = '1.1.0'

        # Mock version data
        v1_data = {'rule_id': 'test-rule', 'name': 'Old Name'}
        v2_data = {'rule_id': 'test-rule', 'name': 'New Name'}

        with patch.object(version_manager, 'get_version') as mock_get_version:
            mock_get_version.side_effect = [v1_data, v2_data]

            result = version_manager.compare_versions(rule_id, version1, version2)

            assert result['rule_id'] == rule_id
            assert result['version1'] == version1
            assert result['version2'] == version2
            assert result['has_changes'] is True
            assert 'changes' in result

    def test_rollback_to_version(self, version_manager, mock_repository):
        """Test rolling back to a previous version."""
        rule_id = 'test-rule'
        version = '1.0.0'

        version_data = {
            'rule_id': 'test-rule',
            'name': 'Old Rule',
            'rule_type': 'breakout',
            'conditions': {},
            'actions': {'signal_type': 'BUY'},
            'metadata': {'author': 'rollback_author', 'version': '1.0.0'}
        }

        with patch.object(version_manager, 'get_version', return_value=version_data):
            mock_repository.save_rule.return_value = True

            success = version_manager.rollback_to_version(
                rule_id, version, 'rollback_author', 'Rolling back to stable version'
            )

            assert success
            mock_repository.save_rule.assert_called_once()


class TestBackupManager:
    """Test backup manager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def backup_manager(self, temp_dir):
        """Create backup manager instance."""
        backup_dir = temp_dir / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        return BackupManager(str(backup_dir))

    def test_create_full_backup(self, backup_manager, temp_dir):
        """Test creating a full backup."""
        # Create source files
        source_dir = temp_dir / 'source'
        source_dir.mkdir()

        rule_file = source_dir / 'test_rule.json'
        rule_data = {
            'rule_id': 'test-rule',
            'name': 'Test Rule',
            'rule_type': 'breakout'
        }

        with open(rule_file, 'w') as f:
            json.dump(rule_data, f)

        # Create backup (without compression for testing)
        result = backup_manager.create_full_backup([str(source_dir)], compress=False)

        assert result['status'] == 'success'
        assert result['total_files'] >= 1
        assert 'backup_name' in result
        assert 'checksum' in result

    def test_list_backups(self, backup_manager, temp_dir):
        """Test listing backups."""
        # Create a mock backup directory
        backup_dir = temp_dir / 'backups' / 'test_backup'
        backup_dir.mkdir(parents=True)

        manifest = {
            'backup_type': 'full',
            'timestamp': datetime.now().isoformat(),
            'total_files': 5,
            'status': 'success'
        }

        with open(backup_dir / 'manifest.json', 'w') as f:
            json.dump(manifest, f)

        # List backups
        backups = backup_manager.list_backups()

        assert len(backups) >= 1
        assert backups[0]['name'] == 'test_backup'
        assert backups[0]['type'] == 'full'

    def test_validate_backup_integrity(self, backup_manager, temp_dir):
        """Test backup integrity validation."""
        # Create a mock backup
        backup_dir = temp_dir / 'backups' / 'test_backup'
        backup_dir.mkdir(parents=True)

        # Create a test file
        test_file = backup_dir / 'test.json'
        test_file.write_text('{"test": "data"}')

        # Create manifest
        manifest = {
            'backup_type': 'full',
            'timestamp': datetime.now().isoformat(),
            'total_files': 1,
            'status': 'success'
        }

        manifest_file = backup_dir / 'manifest.json'
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f)

        # Add checksum to manifest
        manifest['checksum'] = backup_manager._calculate_checksum(backup_dir)
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f)

        # Validate backup
        result = backup_manager.validate_backup_integrity('test_backup')

        assert result['is_valid'] is True
        assert result['manifest_valid'] is True
        assert result['checksum_valid'] is True
        assert result['files_intact'] is True

    def test_cleanup_old_backups(self, backup_manager, temp_dir):
        """Test cleaning up old backups."""
        # This test would be more complex in practice
        # For now, just test the method exists and returns expected structure

        result = backup_manager.cleanup_old_backups(keep_days=30, keep_count=5)

        assert 'total_backups' in result
        assert 'removed_backups' in result
        assert 'kept_backups' in result
        assert 'errors' in result


class TestIntegration:
    """Integration tests for persistence layer."""

    def test_full_persistence_workflow(self, temp_dir):
        """Test full persistence workflow."""
        # Create components
        file_manager = FileManager(str(temp_dir / 'rules'))
        backup_manager = BackupManager(str(temp_dir / 'backups'))

        # Create a test rule
        rule = {
            'rule_id': 'integration-test',
            'name': 'Integration Test Rule',
            'rule_type': 'breakout',
            'conditions': {'breakout_conditions': {'min_volume_multiplier': 2.0}},
            'actions': {'signal_type': 'BUY'},
            'metadata': {'author': 'integration_test', 'version': '1.0.0'}
        }

        # Save to file
        success = file_manager.save_rule_to_file(rule)
        assert success

        # Load from file
        loaded_rule = file_manager.load_rule_from_file('breakout_integration-test.json')
        assert loaded_rule is not None
        assert loaded_rule['rule_id'] == 'integration-test'

        # Create backup
        backup_result = backup_manager.create_full_backup([str(temp_dir / 'rules')], compress=False)
        assert backup_result['status'] == 'success'

        # List backups
        backups = backup_manager.list_backups()
        assert len(backups) >= 1

        print(f"✅ Integration test passed: {len(backups)} backup(s) created")
