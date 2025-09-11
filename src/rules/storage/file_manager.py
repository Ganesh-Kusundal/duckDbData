"""
File Manager

This module provides file system operations for rule management including:
- Loading rules from JSON files
- Saving rules to JSON files
- Directory-based rule organization
- File validation and error handling
"""

from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FileManager:
    """File system manager for rule operations."""

    def __init__(self, base_directory: str = "src/rules/templates"):
        """
        Initialize the file manager.

        Args:
            base_directory: Base directory for rule files
        """
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)
        self._rule_cache: Dict[str, Dict[str, Any]] = {}
        self._last_modified: Dict[str, float] = {}

    def save_rule_to_file(self, rule: Dict[str, Any], filename: Optional[str] = None) -> bool:
        """
        Save a rule to a JSON file.

        Args:
            rule: Rule dictionary
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Success status
        """
        try:
            if not filename:
                rule_id = rule.get('rule_id', 'unknown')
                rule_type = rule.get('rule_type', 'custom')
                filename = f"{rule_type}_{rule_id}.json"

            filepath = self.base_directory / filename

            # Ensure the rule has proper metadata
            if 'metadata' not in rule:
                rule['metadata'] = {}

            rule['metadata']['updated_at'] = datetime.now().isoformat()
            rule['metadata']['file_path'] = str(filepath)

            # Write to file with pretty formatting
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(rule, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"Rule {rule.get('rule_id')} saved to {filepath}")

            # Update cache
            self._rule_cache[filepath.name] = rule
            self._last_modified[filepath.name] = filepath.stat().st_mtime

            return True

        except Exception as e:
            logger.error(f"Failed to save rule to file: {e}")
            return False

    def load_rule_from_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load a rule from a JSON file.

        Args:
            filename: Rule filename

        Returns:
            Rule dictionary or None if not found
        """
        try:
            filepath = self.base_directory / filename

            if not filepath.exists():
                logger.warning(f"Rule file {filepath} not found")
                return None

            with open(filepath, 'r', encoding='utf-8') as f:
                rule = json.load(f)

            # Update cache
            self._rule_cache[filename] = rule
            self._last_modified[filename] = filepath.stat().st_mtime

            logger.info(f"Rule loaded from {filepath}")
            return rule

        except Exception as e:
            logger.error(f"Failed to load rule from {filename}: {e}")
            return None

    def load_rules_from_directory(
        self,
        subdirectory: Optional[str] = None,
        pattern: str = "*.json"
    ) -> List[Dict[str, Any]]:
        """
        Load all rules from a directory.

        Args:
            subdirectory: Optional subdirectory within base_directory
            pattern: File pattern to match (default: *.json)

        Returns:
            List of rule dictionaries
        """
        try:
            search_dir = self.base_directory
            if subdirectory:
                search_dir = search_dir / subdirectory
                search_dir.mkdir(parents=True, exist_ok=True)

            rules = []
            json_files = list(search_dir.glob(pattern))

            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        rule = json.load(f)
                        rules.append(rule)

                    # Update cache
                    filename = json_file.name
                    self._rule_cache[filename] = rule
                    self._last_modified[filename] = json_file.stat().st_mtime

                except Exception as e:
                    logger.error(f"Failed to load rule from {json_file}: {e}")
                    continue

            logger.info(f"Loaded {len(rules)} rules from {search_dir}")
            return rules

        except Exception as e:
            logger.error(f"Failed to load rules from directory: {e}")
            return []

    def save_rules_to_directory(
        self,
        rules: List[Dict[str, Any]],
        subdirectory: Optional[str] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Save multiple rules to a directory.

        Args:
            rules: List of rule dictionaries
            subdirectory: Optional subdirectory to save to
            overwrite: Whether to overwrite existing files

        Returns:
            Save results
        """
        results = {
            'total_rules': len(rules),
            'saved_rules': 0,
            'skipped_rules': 0,
            'failed_rules': 0,
            'errors': []
        }

        try:
            save_dir = self.base_directory
            if subdirectory:
                save_dir = save_dir / subdirectory
                save_dir.mkdir(parents=True, exist_ok=True)

            for rule in rules:
                try:
                    rule_id = rule.get('rule_id', 'unknown')
                    rule_type = rule.get('rule_type', 'custom')
                    filename = f"{rule_type}_{rule_id}.json"

                    filepath = save_dir / filename

                    # Check if file exists and overwrite is disabled
                    if filepath.exists() and not overwrite:
                        results['skipped_rules'] += 1
                        logger.info(f"Skipped existing file: {filepath}")
                        continue

                    # Save the rule
                    success = self.save_rule_to_file(rule, filename)
                    if success:
                        results['saved_rules'] += 1
                    else:
                        results['failed_rules'] += 1
                        results['errors'].append(f"Failed to save {rule_id}")

                except Exception as e:
                    results['failed_rules'] += 1
                    results['errors'].append(f"Error saving {rule.get('rule_id', 'unknown')}: {str(e)}")

            logger.info(f"Save operation completed: {results['saved_rules']} saved, "
                       f"{results['skipped_rules']} skipped, {results['failed_rules']} failed")

        except Exception as e:
            results['errors'].append(f"Directory operation failed: {str(e)}")
            logger.error(f"Failed to save rules to directory: {e}")

        return results

    def get_rule_files_info(self, subdirectory: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get information about rule files in a directory.

        Args:
            subdirectory: Optional subdirectory to scan

        Returns:
            List of file information dictionaries
        """
        try:
            scan_dir = self.base_directory
            if subdirectory:
                scan_dir = scan_dir / subdirectory
                if not scan_dir.exists():
                    return []

            files_info = []
            json_files = list(scan_dir.glob("*.json"))

            for json_file in json_files:
                try:
                    stat = json_file.stat()
                    files_info.append({
                        'filename': json_file.name,
                        'path': str(json_file),
                        'size_bytes': stat.st_size,
                        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'is_cached': json_file.name in self._rule_cache
                    })
                except Exception as e:
                    logger.warning(f"Failed to get info for {json_file}: {e}")
                    continue

            return files_info

        except Exception as e:
            logger.error(f"Failed to get rule files info: {e}")
            return []

    def validate_rule_files(
        self,
        subdirectory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate all rule files in a directory.

        Args:
            subdirectory: Optional subdirectory to validate

        Returns:
            Validation results
        """
        from ..schema.validation_engine import RuleValidator

        results = {
            'total_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'validation_errors': [],
            'file_errors': []
        }

        try:
            files_info = self.get_rule_files_info(subdirectory)

            if not files_info:
                return results

            validator = RuleValidator()

            for file_info in files_info:
                results['total_files'] += 1
                filename = file_info['filename']

                try:
                    rule = self.load_rule_from_file(filename)
                    if not rule:
                        results['invalid_files'] += 1
                        results['file_errors'].append({
                            'file': filename,
                            'error': 'Failed to load rule'
                        })
                        continue

                    # Validate the rule
                    validation_result = validator.validate_rule(rule)

                    if validation_result.is_valid:
                        results['valid_files'] += 1
                    else:
                        results['invalid_files'] += 1
                        results['validation_errors'].append({
                            'file': filename,
                            'rule_id': rule.get('rule_id'),
                            'errors': [err.message for err in validation_result.errors]
                        })

                except Exception as e:
                    results['invalid_files'] += 1
                    results['file_errors'].append({
                        'file': filename,
                        'error': str(e)
                    })

            logger.info(f"Validation completed: {results['valid_files']} valid, "
                       f"{results['invalid_files']} invalid out of {results['total_files']} files")

        except Exception as e:
            results['file_errors'].append({
                'file': 'directory_scan',
                'error': str(e)
            })
            logger.error(f"Failed to validate rule files: {e}")

        return results

    def find_rules_by_criteria(
        self,
        criteria: Dict[str, Any],
        subdirectory: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find rules matching specific criteria.

        Args:
            criteria: Search criteria dictionary
            subdirectory: Optional subdirectory to search

        Returns:
            List of matching rules
        """
        try:
            all_rules = self.load_rules_from_directory(subdirectory)
            matching_rules = []

            for rule in all_rules:
                match = True

                # Check rule_type
                if 'rule_type' in criteria:
                    if rule.get('rule_type') != criteria['rule_type']:
                        match = False
                        continue

                # Check tags
                if 'tags' in criteria:
                    rule_tags = rule.get('metadata', {}).get('tags', [])
                    required_tags = criteria['tags']
                    if not isinstance(required_tags, list):
                        required_tags = [required_tags]

                    if not all(tag in rule_tags for tag in required_tags):
                        match = False
                        continue

                # Check author
                if 'author' in criteria:
                    if rule.get('metadata', {}).get('author') != criteria['author']:
                        match = False
                        continue

                # Check enabled status
                if 'enabled' in criteria:
                    if rule.get('enabled', True) != criteria['enabled']:
                        match = False
                        continue

                # Check rule_id pattern
                if 'rule_id_pattern' in criteria:
                    import re
                    if not re.search(criteria['rule_id_pattern'], rule.get('rule_id', '')):
                        match = False
                        continue

                if match:
                    matching_rules.append(rule)

            logger.info(f"Found {len(matching_rules)} rules matching criteria")
            return matching_rules

        except Exception as e:
            logger.error(f"Failed to find rules by criteria: {e}")
            return []

    def create_backup(
        self,
        backup_directory: str,
        subdirectory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a backup of rule files.

        Args:
            backup_directory: Directory to save backup
            subdirectory: Optional subdirectory to backup

        Returns:
            Backup results
        """
        import shutil

        results = {
            'total_files': 0,
            'backed_up_files': 0,
            'failed_files': 0,
            'errors': []
        }

        try:
            backup_path = Path(backup_directory)
            backup_path.mkdir(parents=True, exist_ok=True)

            source_dir = self.base_directory
            if subdirectory:
                source_dir = source_dir / subdirectory

            if not source_dir.exists():
                results['errors'].append(f"Source directory {source_dir} does not exist")
                return results

            # Copy all JSON files
            json_files = list(source_dir.glob("*.json"))
            results['total_files'] = len(json_files)

            for json_file in json_files:
                try:
                    shutil.copy2(json_file, backup_path / json_file.name)
                    results['backed_up_files'] += 1
                except Exception as e:
                    results['failed_files'] += 1
                    results['errors'].append(f"Failed to backup {json_file.name}: {str(e)}")

            # Create backup metadata
            metadata = {
                'backup_timestamp': datetime.now().isoformat(),
                'source_directory': str(source_dir),
                'total_files': results['total_files'],
                'backed_up_files': results['backed_up_files'],
                'failed_files': results['failed_files']
            }

            with open(backup_path / 'backup_metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Backup completed: {results['backed_up_files']} files backed up to {backup_path}")

        except Exception as e:
            results['errors'].append(f"Backup operation failed: {str(e)}")
            logger.error(f"Failed to create backup: {e}")

        return results

    def clear_cache(self):
        """Clear the file cache."""
        self._rule_cache.clear()
        self._last_modified.clear()
        logger.info("File manager cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cached_files': len(self._rule_cache),
            'cache_size_mb': sum(
                len(json.dumps(rule)) for rule in self._rule_cache.values()
            ) / (1024 * 1024)
        }
