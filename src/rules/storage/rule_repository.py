"""
Rule Repository

This module provides database operations for rule persistence including:
- CRUD operations for rules
- Rule metadata management
- Performance tracking storage
- Query optimization for rule retrieval
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import logging

from ..schema.rule_types import RuleType, SignalType

logger = logging.getLogger(__name__)


class RuleRepository:
    """Database repository for rule operations."""

    def __init__(self, db_connection=None):
        """
        Initialize the rule repository.

        Args:
            db_connection: Database connection object
        """
        self.db_connection = db_connection
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        """Ensure required database tables exist."""
        if not self.db_connection:
            logger.warning("No database connection provided - tables will not be created")
            return

        # Create rules table
        rules_table_sql = """
        CREATE TABLE IF NOT EXISTS rules (
            rule_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            rule_type TEXT NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            priority INTEGER DEFAULT 50,
            conditions TEXT NOT NULL,  -- JSON string
            actions TEXT NOT NULL,     -- JSON string
            metadata TEXT,             -- JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            version TEXT DEFAULT '1.0.0',
            author TEXT,
            tags TEXT  -- JSON array string
        );
        """

        # Create rule executions table for performance tracking
        executions_table_sql = """
        CREATE TABLE IF NOT EXISTS rule_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT NOT NULL,
            execution_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN NOT NULL,
            execution_time_ms REAL,
            signals_generated INTEGER DEFAULT 0,
            error_message TEXT,
            context_data TEXT,  -- JSON string
            FOREIGN KEY (rule_id) REFERENCES rules(rule_id)
        );
        """

        # Create rule versions table for versioning
        versions_table_sql = """
        CREATE TABLE IF NOT EXISTS rule_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT NOT NULL,
            version TEXT NOT NULL,
            rule_data TEXT NOT NULL,  -- Complete JSON rule
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            author TEXT,
            change_description TEXT,
            FOREIGN KEY (rule_id) REFERENCES rules(rule_id)
        );
        """

        # Create indexes for performance
        indexes_sql = """
        CREATE INDEX IF NOT EXISTS idx_rules_type ON rules(rule_type);
        CREATE INDEX IF NOT EXISTS idx_rules_enabled ON rules(enabled);
        CREATE INDEX IF NOT EXISTS idx_executions_rule_id ON rule_executions(rule_id);
        CREATE INDEX IF NOT EXISTS idx_executions_timestamp ON rule_executions(execution_timestamp);
        CREATE INDEX IF NOT EXISTS idx_versions_rule_id ON rule_versions(rule_id);
        """

        try:
            # Execute table creation
            for sql in [rules_table_sql, executions_table_sql, versions_table_sql, indexes_sql]:
                if sql.strip():
                    self._execute_query(sql)

            logger.info("Rule repository tables ensured")
        except Exception as e:
            logger.error(f"Failed to create rule repository tables: {e}")

    def save_rule(self, rule: Dict[str, Any]) -> bool:
        """
        Save or update a rule in the database.

        Args:
            rule: Rule dictionary

        Returns:
            Success status
        """
        if not self.db_connection:
            logger.error("No database connection available")
            return False

        try:
            rule_id = rule['rule_id']
            now = datetime.now()

            # Prepare data for storage
            conditions_json = json.dumps(rule.get('conditions', {}))
            actions_json = json.dumps(rule.get('actions', {}))
            metadata_json = json.dumps(rule.get('metadata', {}))
            tags_json = json.dumps(rule.get('metadata', {}).get('tags', []))

            # Check if rule exists
            existing = self._execute_query(
                "SELECT rule_id FROM rules WHERE rule_id = ?",
                (rule_id,)
            )

            if existing:
                # Update existing rule
                sql = """
                UPDATE rules SET
                    name = ?, description = ?, rule_type = ?, enabled = ?,
                    priority = ?, conditions = ?, actions = ?, metadata = ?,
                    updated_at = ?, version = ?, author = ?, tags = ?
                WHERE rule_id = ?
                """
                params = (
                    rule.get('name'),
                    rule.get('description'),
                    rule.get('rule_type'),
                    rule.get('enabled', True),
                    rule.get('priority', 50),
                    conditions_json,
                    actions_json,
                    metadata_json,
                    now,
                    rule.get('metadata', {}).get('version', '1.0.0'),
                    rule.get('metadata', {}).get('author'),
                    tags_json,
                    rule_id
                )
            else:
                # Insert new rule
                sql = """
                INSERT INTO rules (
                    rule_id, name, description, rule_type, enabled, priority,
                    conditions, actions, metadata, created_at, updated_at,
                    version, author, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    rule_id,
                    rule.get('name'),
                    rule.get('description'),
                    rule.get('rule_type'),
                    rule.get('enabled', True),
                    rule.get('priority', 50),
                    conditions_json,
                    actions_json,
                    metadata_json,
                    now,
                    now,
                    rule.get('metadata', {}).get('version', '1.0.0'),
                    rule.get('metadata', {}).get('author'),
                    tags_json
                )

            self._execute_query(sql, params)

            # Save version history
            self._save_rule_version(rule, "Rule saved/updated")

            logger.info(f"Rule {rule_id} saved successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to save rule {rule.get('rule_id')}: {e}")
            return False

    def load_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a rule from the database.

        Args:
            rule_id: Rule identifier

        Returns:
            Rule dictionary or None if not found
        """
        if not self.db_connection:
            logger.error("No database connection available")
            return None

        try:
            result = self._execute_query(
                "SELECT * FROM rules WHERE rule_id = ?",
                (rule_id,)
            )

            if not result:
                return None

            row = result[0]
            rule = {
                'rule_id': row[0],
                'name': row[1],
                'description': row[2],
                'rule_type': row[3],
                'enabled': bool(row[4]),
                'priority': row[5],
                'conditions': json.loads(row[6]) if row[6] else {},
                'actions': json.loads(row[7]) if row[7] else {},
                'metadata': json.loads(row[8]) if row[8] else {},
                'created_at': row[9],
                'updated_at': row[10],
                'version': row[11],
                'author': row[12],
                'tags': json.loads(row[13]) if row[13] else []
            }

            # Merge tags into metadata
            if rule['tags']:
                rule['metadata']['tags'] = rule['tags']

            return rule

        except Exception as e:
            logger.error(f"Failed to load rule {rule_id}: {e}")
            return None

    def load_rules(
        self,
        rule_type: Optional[RuleType] = None,
        enabled_only: bool = False,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Load multiple rules with optional filtering.

        Args:
            rule_type: Filter by rule type
            enabled_only: Only load enabled rules
            tags: Filter by tags
            limit: Maximum number of rules to return

        Returns:
            List of rule dictionaries
        """
        if not self.db_connection:
            logger.error("No database connection available")
            return []

        try:
            conditions = []
            params = []

            if rule_type:
                conditions.append("rule_type = ?")
                params.append(rule_type.value)

            if enabled_only:
                conditions.append("enabled = ?")
                params.append(True)

            if tags:
                # This is a simplified tag filter - in practice you'd want more sophisticated tag matching
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ?")
                    params.append(f'%{tag}%')
                if tag_conditions:
                    conditions.append(f"({' OR '.join(tag_conditions)})")

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            limit_clause = f" LIMIT {limit}" if limit else ""

            sql = f"SELECT * FROM rules WHERE {where_clause} ORDER BY priority DESC, created_at DESC{limit_clause}"

            results = self._execute_query(sql, params)
            rules = []

            for row in results:
                rule = {
                    'rule_id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'rule_type': row[3],
                    'enabled': bool(row[4]),
                    'priority': row[5],
                    'conditions': json.loads(row[6]) if row[6] else {},
                    'actions': json.loads(row[7]) if row[7] else {},
                    'metadata': json.loads(row[8]) if row[8] else {},
                    'created_at': row[9],
                    'updated_at': row[10],
                    'version': row[11],
                    'author': row[12],
                    'tags': json.loads(row[13]) if row[13] else []
                }

                # Merge tags into metadata
                if rule['tags']:
                    rule['metadata']['tags'] = rule['tags']

                rules.append(rule)

            logger.info(f"Loaded {len(rules)} rules from database")
            return rules

        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            return []

    def delete_rule(self, rule_id: str) -> bool:
        """
        Delete a rule from the database.

        Args:
            rule_id: Rule identifier

        Returns:
            Success status
        """
        if not self.db_connection:
            logger.error("No database connection available")
            return False

        try:
            # Delete from main table
            self._execute_query("DELETE FROM rules WHERE rule_id = ?", (rule_id,))

            # Delete related records
            self._execute_query("DELETE FROM rule_executions WHERE rule_id = ?", (rule_id,))
            self._execute_query("DELETE FROM rule_versions WHERE rule_id = ?", (rule_id,))

            logger.info(f"Rule {rule_id} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to delete rule {rule_id}: {e}")
            return False

    def save_execution_result(
        self,
        rule_id: str,
        success: bool,
        execution_time_ms: float,
        signals_generated: int,
        error_message: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save rule execution result for performance tracking.

        Args:
            rule_id: Rule identifier
            success: Whether execution was successful
            execution_time_ms: Execution time in milliseconds
            signals_generated: Number of signals generated
            error_message: Error message if execution failed
            context_data: Additional context data

        Returns:
            Success status
        """
        if not self.db_connection:
            logger.error("No database connection available")
            return False

        try:
            context_json = json.dumps(context_data) if context_data else None

            sql = """
            INSERT INTO rule_executions (
                rule_id, success, execution_time_ms, signals_generated,
                error_message, context_data
            ) VALUES (?, ?, ?, ?, ?, ?)
            """

            params = (rule_id, success, execution_time_ms, signals_generated,
                     error_message, context_json)

            self._execute_query(sql, params)
            return True

        except Exception as e:
            logger.error(f"Failed to save execution result for {rule_id}: {e}")
            return False

    def get_rule_statistics(self, rule_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get execution statistics for rules.

        Args:
            rule_id: Specific rule ID or None for all rules

        Returns:
            Statistics dictionary
        """
        if not self.db_connection:
            logger.error("No database connection available")
            return {}

        try:
            if rule_id:
                sql = """
                SELECT
                    COUNT(*) as total_executions,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_executions,
                    AVG(execution_time_ms) as avg_execution_time,
                    SUM(signals_generated) as total_signals,
                    MAX(execution_timestamp) as last_executed
                FROM rule_executions
                WHERE rule_id = ?
                """
                params = (rule_id,)
            else:
                sql = """
                SELECT
                    rule_id,
                    COUNT(*) as total_executions,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_executions,
                    AVG(execution_time_ms) as avg_execution_time,
                    SUM(signals_generated) as total_signals,
                    MAX(execution_timestamp) as last_executed
                FROM rule_executions
                GROUP BY rule_id
                ORDER BY total_executions DESC
                """
                params = ()

            results = self._execute_query(sql, params)

            if rule_id and results:
                row = results[0]
                return {
                    'rule_id': rule_id,
                    'total_executions': row[0],
                    'successful_executions': row[1],
                    'success_rate': row[1] / row[0] if row[0] > 0 else 0,
                    'avg_execution_time_ms': row[2],
                    'total_signals_generated': row[3],
                    'last_executed': row[4]
                }
            elif not rule_id:
                stats = {}
                for row in results:
                    stats[row[0]] = {
                        'total_executions': row[1],
                        'successful_executions': row[2],
                        'success_rate': row[2] / row[1] if row[1] > 0 else 0,
                        'avg_execution_time_ms': row[3],
                        'total_signals_generated': row[4],
                        'last_executed': row[5]
                    }
                return stats

            return {}

        except Exception as e:
            logger.error(f"Failed to get rule statistics: {e}")
            return {}

    def get_repository_stats(self) -> Dict[str, Any]:
        """
        Get overall repository statistics.

        Returns:
            Statistics dictionary
        """
        if not self.db_connection:
            return {'error': 'No database connection'}

        try:
            # Count rules by type
            rule_counts = self._execute_query("""
                SELECT rule_type, COUNT(*) as count
                FROM rules
                GROUP BY rule_type
            """)

            # Count total executions
            execution_counts = self._execute_query("""
                SELECT COUNT(*) as total, SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
                FROM rule_executions
            """)

            stats = {
                'total_rules': sum(row[1] for row in rule_counts),
                'rules_by_type': {row[0]: row[1] for row in rule_counts},
                'total_executions': execution_counts[0][0] if execution_counts else 0,
                'successful_executions': execution_counts[0][1] if execution_counts else 0,
                'execution_success_rate': (
                    execution_counts[0][1] / execution_counts[0][0]
                    if execution_counts and execution_counts[0][0] > 0 else 0
                )
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get repository stats: {e}")
            return {'error': str(e)}

    def _execute_query(self, sql: str, params: Tuple = ()) -> List[Tuple]:
        """Execute a SQL query and return results."""
        if not self.db_connection:
            raise Exception("No database connection available")

        try:
            cursor = self.db_connection.cursor()
            cursor.execute(sql, params)
            results = cursor.fetchall()

            # For INSERT/UPDATE/DELETE queries, commit the transaction
            if sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                self.db_connection.commit()

            return results

        except Exception as e:
            logger.error(f"Query execution failed: {sql} - {e}")
            raise

    def _save_rule_version(self, rule: Dict[str, Any], change_description: str):
        """Save a version of the rule for history tracking."""
        try:
            sql = """
            INSERT INTO rule_versions (rule_id, version, rule_data, author, change_description)
            VALUES (?, ?, ?, ?, ?)
            """

            params = (
                rule['rule_id'],
                rule.get('metadata', {}).get('version', '1.0.0'),
                json.dumps(rule),
                rule.get('metadata', {}).get('author'),
                change_description
            )

            self._execute_query(sql, params)

        except Exception as e:
            logger.warning(f"Failed to save rule version: {e}")
