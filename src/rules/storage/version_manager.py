"""
Version Manager

This module provides version control capabilities for rules including:
- Rule versioning and history tracking
- Version comparison and diff generation
- Rollback to previous versions
- Version cleanup and maintenance
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import logging
import difflib

logger = logging.getLogger(__name__)


class VersionManager:
    """Version control manager for rules."""

    def __init__(self, repository=None):
        """
        Initialize the version manager.

        Args:
            repository: Rule repository instance for database operations
        """
        self.repository = repository
        self._version_cache: Dict[str, List[Dict[str, Any]]] = {}

    def create_version(
        self,
        rule: Dict[str, Any],
        author: str,
        description: str = ""
    ) -> bool:
        """
        Create a new version of a rule.

        Args:
            rule: Rule dictionary
            author: Author of the change
            description: Description of the change

        Returns:
            Success status
        """
        if not self.repository:
            logger.error("No repository available for version management")
            return False

        try:
            rule_id = rule['rule_id']

            # Get current version
            current_version = rule.get('metadata', {}).get('version', '1.0.0')

            # Increment version (simple semantic versioning)
            new_version = self._increment_version(current_version)

            # Update rule with new version
            rule['metadata']['version'] = new_version
            rule['metadata']['updated_at'] = datetime.now().isoformat()

            # Save version to database
            success = self.repository._save_rule_version(rule, description)

            if success:
                logger.info(f"Created version {new_version} for rule {rule_id}")
                # Clear cache for this rule
                if rule_id in self._version_cache:
                    del self._version_cache[rule_id]
            else:
                logger.error(f"Failed to create version for rule {rule_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to create version: {e}")
            return False

    def get_version_history(self, rule_id: str) -> List[Dict[str, Any]]:
        """
        Get version history for a rule.

        Args:
            rule_id: Rule identifier

        Returns:
            List of version records
        """
        if not self.repository:
            logger.error("No repository available")
            return []

        # Check cache first
        if rule_id in self._version_cache:
            return self._version_cache[rule_id]

        try:
            # Query database for versions
            sql = """
            SELECT version, rule_data, created_at, author, change_description
            FROM rule_versions
            WHERE rule_id = ?
            ORDER BY created_at DESC
            """

            results = self.repository._execute_query(sql, (rule_id,))

            versions = []
            for row in results:
                version_data = json.loads(row[1]) if row[1] else {}
                versions.append({
                    'version': row[0],
                    'rule_data': version_data,
                    'created_at': row[2],
                    'author': row[3],
                    'change_description': row[4]
                })

            # Cache the results
            self._version_cache[rule_id] = versions

            logger.info(f"Retrieved {len(versions)} versions for rule {rule_id}")
            return versions

        except Exception as e:
            logger.error(f"Failed to get version history for {rule_id}: {e}")
            return []

    def get_version(self, rule_id: str, version: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific version of a rule.

        Args:
            rule_id: Rule identifier
            version: Version string

        Returns:
            Rule data for the specified version
        """
        versions = self.get_version_history(rule_id)

        for version_record in versions:
            if version_record['version'] == version:
                return version_record['rule_data']

        logger.warning(f"Version {version} not found for rule {rule_id}")
        return None

    def compare_versions(
        self,
        rule_id: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare two versions of a rule.

        Args:
            rule_id: Rule identifier
            version1: First version to compare
            version2: Second version to compare

        Returns:
            Comparison results
        """
        try:
            v1_data = self.get_version(rule_id, version1)
            v2_data = self.get_version(rule_id, version2)

            if not v1_data or not v2_data:
                return {
                    'error': f"One or both versions not found: {version1}, {version2}"
                }

            # Compare JSON structures
            v1_json = json.dumps(v1_data, indent=2, sort_keys=True)
            v2_json = json.dumps(v2_data, indent=2, sort_keys=True)

            # Generate diff
            diff = list(difflib.unified_diff(
                v1_json.splitlines(keepends=True),
                v2_json.splitlines(keepends=True),
                fromfile=f"{rule_id}@{version1}",
                tofile=f"{rule_id}@{version2}",
                lineterm=''
            ))

            # Analyze changes
            changes = self._analyze_changes(v1_data, v2_data)

            return {
                'rule_id': rule_id,
                'version1': version1,
                'version2': version2,
                'has_changes': len(diff) > 0,
                'diff': ''.join(diff),
                'changes': changes,
                'v1_data': v1_data,
                'v2_data': v2_data
            }

        except Exception as e:
            logger.error(f"Failed to compare versions {version1} and {version2}: {e}")
            return {'error': str(e)}

    def rollback_to_version(
        self,
        rule_id: str,
        version: str,
        author: str,
        description: str = ""
    ) -> bool:
        """
        Rollback a rule to a previous version.

        Args:
            rule_id: Rule identifier
            version: Version to rollback to
            author: Author of the rollback
            description: Description of the rollback

        Returns:
            Success status
        """
        if not self.repository:
            logger.error("No repository available")
            return False

        try:
            # Get the version data
            version_data = self.get_version(rule_id, version)
            if not version_data:
                logger.error(f"Version {version} not found for rule {rule_id}")
                return False

            # Update the current rule with version data
            version_data['metadata']['author'] = author
            version_data['metadata']['updated_at'] = datetime.now().isoformat()

            # Save as new version
            success = self.repository.save_rule(version_data)

            if success:
                # Create version record for rollback
                rollback_description = f"Rolled back to version {version}: {description}"
                self.repository._save_rule_version(version_data, rollback_description)

                logger.info(f"Successfully rolled back rule {rule_id} to version {version}")
                # Clear cache
                if rule_id in self._version_cache:
                    del self._version_cache[rule_id]

            return success

        except Exception as e:
            logger.error(f"Failed to rollback rule {rule_id} to version {version}: {e}")
            return False

    def cleanup_old_versions(
        self,
        rule_id: Optional[str] = None,
        keep_versions: int = 10,
        older_than_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Clean up old versions to save space.

        Args:
            rule_id: Specific rule ID or None for all rules
            keep_versions: Number of recent versions to keep
            older_than_days: Remove versions older than this many days

        Returns:
            Cleanup results
        """
        if not self.repository:
            logger.error("No repository available")
            return {'error': 'No repository available'}

        results = {
            'total_versions': 0,
            'removed_versions': 0,
            'kept_versions': 0,
            'errors': []
        }

        try:
            # Build query conditions
            conditions = []
            params = []

            if rule_id:
                conditions.append("rule_id = ?")
                params.append(rule_id)

            if older_than_days:
                from datetime import timedelta
                cutoff_date = datetime.now() - timedelta(days=older_than_days)
                conditions.append("created_at < ?")
                params.append(cutoff_date)

            where_clause = " AND ".join(conditions) if conditions else ""

            # Get versions to potentially remove
            sql = f"""
            SELECT rule_id, version, created_at
            FROM rule_versions
            {'WHERE ' + where_clause if where_clause else ''}
            ORDER BY rule_id, created_at DESC
            """

            versions = self.repository._execute_query(sql, tuple(params))
            results['total_versions'] = len(versions)

            # Group by rule_id and determine which to keep/remove
            rule_versions = {}
            for row in versions:
                rule_id_val = row[0]
                if rule_id_val not in rule_versions:
                    rule_versions[rule_id_val] = []
                rule_versions[rule_id_val].append({
                    'version': row[1],
                    'created_at': row[2]
                })

            versions_to_remove = []

            for rule_id_val, vers in rule_versions.items():
                # Sort by creation date (newest first)
                vers.sort(key=lambda x: x['created_at'], reverse=True)

                # Keep the most recent versions
                if len(vers) > keep_versions:
                    versions_to_remove.extend(vers[keep_versions:])

            # Remove old versions
            for version_info in versions_to_remove:
                try:
                    delete_sql = """
                    DELETE FROM rule_versions
                    WHERE rule_id = ? AND version = ?
                    """
                    self.repository._execute_query(delete_sql, (rule_id, version_info['version']))
                    results['removed_versions'] += 1
                except Exception as e:
                    results['errors'].append(f"Failed to remove version {version_info['version']}: {str(e)}")

            results['kept_versions'] = results['total_versions'] - results['removed_versions']

            # Clear cache
            if rule_id:
                self._version_cache.pop(rule_id, None)
            else:
                self._version_cache.clear()

            logger.info(f"Version cleanup completed: {results['removed_versions']} removed, "
                       f"{results['kept_versions']} kept")

        except Exception as e:
            results['errors'].append(f"Cleanup operation failed: {str(e)}")
            logger.error(f"Failed to cleanup old versions: {e}")

        return results

    def get_version_stats(self, rule_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get version statistics.

        Args:
            rule_id: Specific rule ID or None for all rules

        Returns:
            Statistics dictionary
        """
        if not self.repository:
            return {'error': 'No repository available'}

        try:
            if rule_id:
                sql = """
                SELECT COUNT(*) as version_count,
                       MIN(created_at) as oldest_version,
                       MAX(created_at) as newest_version
                FROM rule_versions
                WHERE rule_id = ?
                """
                params = (rule_id,)
            else:
                sql = """
                SELECT COUNT(*) as total_versions,
                       COUNT(DISTINCT rule_id) as rules_with_versions,
                       MIN(created_at) as oldest_version,
                       MAX(created_at) as newest_version
                FROM rule_versions
                """
                params = ()

            results = self.repository._execute_query(sql, params)

            if results:
                row = results[0]
                if rule_id:
                    return {
                        'rule_id': rule_id,
                        'version_count': row[0],
                        'oldest_version': row[1],
                        'newest_version': row[2]
                    }
                else:
                    return {
                        'total_versions': row[0],
                        'rules_with_versions': row[1],
                        'oldest_version': row[2],
                        'newest_version': row[3]
                    }

            return {}

        except Exception as e:
            logger.error(f"Failed to get version stats: {e}")
            return {'error': str(e)}

    def _increment_version(self, current_version: str) -> str:
        """Increment a version string using semantic versioning."""
        try:
            parts = current_version.split('.')
            if len(parts) >= 3:
                major = int(parts[0])
                minor = int(parts[1])
                patch = int(parts[2])

                # Simple increment of patch version
                return f"{major}.{minor}.{patch + 1}"
            else:
                # Fallback: append .1
                return f"{current_version}.1"
        except:
            # Fallback: append timestamp
            timestamp = int(datetime.now().timestamp())
            return f"{current_version}.{timestamp}"

    def _analyze_changes(self, old_rule: Dict[str, Any], new_rule: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze what changed between two rule versions."""
        changes = {
            'metadata_changes': [],
            'condition_changes': [],
            'action_changes': [],
            'structural_changes': []
        }

        try:
            # Compare metadata
            old_meta = old_rule.get('metadata', {})
            new_meta = new_rule.get('metadata', {})

            for key in set(old_meta.keys()) | set(new_meta.keys()):
                old_val = old_meta.get(key)
                new_val = new_meta.get(key)
                if old_val != new_val:
                    changes['metadata_changes'].append({
                        'field': key,
                        'old_value': old_val,
                        'new_value': new_val
                    })

            # Compare conditions
            old_conditions = old_rule.get('conditions', {})
            new_conditions = new_rule.get('conditions', {})

            self._compare_dicts(old_conditions, new_conditions, changes['condition_changes'], 'conditions')

            # Compare actions
            old_actions = old_rule.get('actions', {})
            new_actions = new_rule.get('actions', {})

            self._compare_dicts(old_actions, new_actions, changes['action_changes'], 'actions')

            # Check for structural changes
            old_keys = set(old_rule.keys())
            new_keys = set(new_rule.keys())

            added_keys = new_keys - old_keys
            removed_keys = old_keys - new_keys

            if added_keys:
                changes['structural_changes'].append(f"Added fields: {list(added_keys)}")
            if removed_keys:
                changes['structural_changes'].append(f"Removed fields: {list(removed_keys)}")

        except Exception as e:
            changes['structural_changes'].append(f"Error analyzing changes: {str(e)}")

        return changes

    def _compare_dicts(self, old_dict: Dict, new_dict: Dict, changes_list: List, prefix: str):
        """Recursively compare two dictionaries."""
        all_keys = set(old_dict.keys()) | set(new_dict.keys())

        for key in all_keys:
            old_val = old_dict.get(key)
            new_val = new_dict.get(key)

            if old_val != new_val:
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    # Recursively compare nested dictionaries
                    nested_changes = []
                    self._compare_dicts(old_val, new_val, nested_changes, f"{prefix}.{key}")
                    changes_list.extend(nested_changes)
                else:
                    changes_list.append({
                        'field': f"{prefix}.{key}",
                        'old_value': old_val,
                        'new_value': new_val
                    })

    def clear_cache(self):
        """Clear the version cache."""
        self._version_cache.clear()
        logger.info("Version manager cache cleared")
