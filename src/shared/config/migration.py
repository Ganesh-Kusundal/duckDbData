"""
Configuration Migration Utility
Helps migrate from scattered configuration files to consolidated system
"""

import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from .loaders import ConfigLoader
from .config_manager import get_config_manager

logger = logging.getLogger(__name__)


class ConfigMigration:
    """
    Handles migration from scattered configuration files to consolidated system
    """

    def __init__(self):
        """Initialize configuration migration utility"""
        self.loader = ConfigLoader()
        self.config_manager = get_config_manager()

    def migrate_all_configs(self, backup: bool = True) -> Dict[str, Any]:
        """
        Migrate all scattered configuration files to consolidated system

        Args:
            backup: Whether to backup original files

        Returns:
            Migration report
        """
        logger.info("Starting configuration migration...")

        migration_report = {
            "migrated_files": [],
            "skipped_files": [],
            "errors": [],
            "backup_created": False
        }

        # Create backup if requested
        if backup:
            try:
                self._create_backup()
                migration_report["backup_created"] = True
                logger.info("✅ Backup created")
            except Exception as e:
                logger.error(f"Failed to create backup: {e}")
                migration_report["errors"].append(f"Backup failed: {e}")
                return migration_report

        # Migrate individual configuration files
        config_mappings = self._get_config_mappings()

        for config_name, file_paths in config_mappings.items():
            try:
                merged_config = self._merge_config_files(file_paths)
                if merged_config:
                    self._save_migrated_config(config_name, merged_config)
                    migration_report["migrated_files"].append({
                        "name": config_name,
                        "sources": file_paths,
                        "status": "success"
                    })
                    logger.info(f"✅ Migrated {config_name}")
                else:
                    migration_report["skipped_files"].append({
                        "name": config_name,
                        "reason": "No valid configuration found"
                    })
            except Exception as e:
                logger.error(f"Failed to migrate {config_name}: {e}")
                migration_report["errors"].append(f"Migration failed for {config_name}: {e}")

        # Create migration summary
        self._create_migration_summary(migration_report)

        logger.info("Configuration migration completed")
        return migration_report

    def preview_migration(self) -> Dict[str, Any]:
        """
        Preview what will be migrated without actually doing it

        Returns:
            Preview report
        """
        logger.info("Previewing configuration migration...")

        preview_report = {
            "will_migrate": [],
            "will_skip": [],
            "conflicts": [],
            "recommendations": []
        }

        config_mappings = self._get_config_mappings()

        for config_name, file_paths in config_mappings.items():
            existing_files = [p for p in file_paths if p.exists()]

            if existing_files:
                merged_config = self._merge_config_files(existing_files)
                if merged_config:
                    preview_report["will_migrate"].append({
                        "name": config_name,
                        "sources": [str(p) for p in existing_files],
                        "target": str(self._get_target_path(config_name))
                    })
                else:
                    preview_report["will_skip"].append({
                        "name": config_name,
                        "reason": "No valid configuration found"
                    })
            else:
                preview_report["will_skip"].append({
                    "name": config_name,
                    "reason": "No source files found"
                })

        # Check for potential conflicts
        conflicts = self._check_for_conflicts()
        preview_report["conflicts"] = conflicts

        # Generate recommendations
        preview_report["recommendations"] = self._generate_recommendations(preview_report)

        return preview_report

    def rollback_migration(self) -> bool:
        """
        Rollback configuration migration by restoring from backup

        Returns:
            True if rollback successful
        """
        logger.info("Rolling back configuration migration...")

        backup_dir = Path("configs/backup")
        if not backup_dir.exists():
            logger.error("No backup directory found")
            return False

        try:
            # Restore from backup
            for backup_file in backup_dir.glob("*"):
                if backup_file.is_file():
                    target_path = Path("configs") / backup_file.name
                    shutil.copy2(backup_file, target_path)
                    logger.info(f"Restored {backup_file.name}")

            # Remove consolidated config
            consolidated_file = Path("src/shared/config/consolidated_config.yaml")
            if consolidated_file.exists():
                consolidated_file.unlink()
                logger.info("Removed consolidated configuration")

            # Remove environment configs
            env_dir = Path("src/shared/config/environments")
            if env_dir.exists():
                shutil.rmtree(env_dir)
                logger.info("Removed environment configurations")

            logger.info("✅ Migration rollback completed")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback migration: {e}")
            return False

    def _get_config_mappings(self) -> Dict[str, List[Path]]:
        """
        Get mapping of configuration names to their source files

        Returns:
            Dictionary mapping config names to file paths
        """
        return {
            "main": [
                Path("configs/config.yaml"),
                Path("configs/database.yaml"),
                Path("configs/scanners.yaml"),
                Path("configs/analytics.yaml"),
                Path("configs/brokers.yaml")
            ],
            "trade_engine": [
                Path("trade_engine/config/trade_engine.yaml"),
                Path("trade_engine/config/database_config.yaml"),
                Path("trade_engine/config/scanner_config.yaml")
            ],
            "api": [
                Path("configs/config.yaml"),  # API settings from main config
            ],
            "dashboard": [
                Path("configs/analytics.yaml"),  # Dashboard settings
            ],
            "websocket": [
                Path("configs/config.yaml"),  # WebSocket settings
            ]
        }

    def _merge_config_files(self, file_paths: List[Path]) -> Optional[Dict[str, Any]]:
        """
        Merge multiple configuration files

        Args:
            file_paths: List of configuration file paths

        Returns:
            Merged configuration dictionary
        """
        merged_config = {}

        for file_path in file_paths:
            if file_path.exists():
                try:
                    config = self.loader.load_config(file_path)
                    merged_config = self.loader.merge_configs(merged_config, config)
                except Exception as e:
                    logger.warning(f"Failed to load {file_path}: {e}")
                    continue

        return merged_config if merged_config else None

    def _save_migrated_config(self, config_name: str, config: Dict[str, Any]):
        """
        Save migrated configuration to appropriate location

        Args:
            config_name: Name of the configuration
            config: Configuration dictionary
        """
        if config_name == "main":
            target_path = Path("src/shared/config/consolidated_config.yaml")
        else:
            target_path = self._get_target_path(config_name)

        # Create directory if it doesn't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Save configuration
        self.loader.save_config(config, target_path)

    def _get_target_path(self, config_name: str) -> Path:
        """
        Get target path for migrated configuration

        Args:
            config_name: Name of the configuration

        Returns:
            Target file path
        """
        if config_name == "main":
            return Path("src/shared/config/consolidated_config.yaml")
        else:
            return Path(f"src/shared/config/environments/{config_name}.yaml")

    def _create_backup(self):
        """
        Create backup of original configuration files
        """
        backup_dir = Path("configs/backup")
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup main config files
        config_files = [
            "configs/config.yaml",
            "configs/database.yaml",
            "configs/scanners.yaml",
            "configs/analytics.yaml",
            "configs/brokers.yaml",
            "trade_engine/config/trade_engine.yaml"
        ]

        for config_file in config_files:
            src_path = Path(config_file)
            if src_path.exists():
                dst_path = backup_dir / src_path.name
                shutil.copy2(src_path, dst_path)
                logger.debug(f"Backed up {config_file}")

    def _check_for_conflicts(self) -> List[Dict[str, Any]]:
        """
        Check for potential conflicts in configuration migration

        Returns:
            List of conflicts found
        """
        conflicts = []

        # Check if consolidated config already exists
        consolidated_file = Path("src/shared/config/consolidated_config.yaml")
        if consolidated_file.exists():
            conflicts.append({
                "type": "existing_file",
                "file": str(consolidated_file),
                "description": "Consolidated configuration file already exists"
            })

        # Check for environment-specific conflicts
        env_dir = Path("src/shared/config/environments")
        if env_dir.exists():
            existing_env_files = list(env_dir.glob("*.yaml"))
            if existing_env_files:
                conflicts.append({
                    "type": "existing_env_files",
                    "files": [str(f) for f in existing_env_files],
                    "description": "Environment-specific configuration files already exist"
                })

        return conflicts

    def _generate_recommendations(self, preview_report: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on preview report

        Args:
            preview_report: Preview report from migration preview

        Returns:
            List of recommendations
        """
        recommendations = []

        if preview_report["conflicts"]:
            recommendations.append("Resolve existing configuration conflicts before migration")

        if not preview_report["will_migrate"]:
            recommendations.append("No configuration files found to migrate - check file paths")

        if len(preview_report["will_skip"]) > 0:
            recommendations.append("Review skipped configurations to ensure all settings are preserved")

        recommendations.append("Create backup before running actual migration")
        recommendations.append("Test application functionality after migration")
        recommendations.append("Update any scripts that reference old configuration paths")

        return recommendations

    def _create_migration_summary(self, migration_report: Dict[str, Any]):
        """
        Create a summary file of the migration

        Args:
            migration_report: Migration report
        """
        summary_file = Path("configs/migration_summary.yaml")

        summary = {
            "migration_timestamp": "2024-09-05T10:30:00Z",
            "status": "completed" if not migration_report["errors"] else "completed_with_errors",
            "summary": {
                "files_migrated": len(migration_report["migrated_files"]),
                "files_skipped": len(migration_report["skipped_files"]),
                "errors": len(migration_report["errors"]),
                "backup_created": migration_report["backup_created"]
            },
            "details": migration_report
        }

        self.loader.save_config(summary, summary_file)
        logger.info(f"Migration summary saved to {summary_file}")


def migrate_configs(backup: bool = True) -> Dict[str, Any]:
    """
    Convenience function to migrate all configurations

    Args:
        backup: Whether to create backup

    Returns:
        Migration report
    """
    migrator = ConfigMigration()
    return migrator.migrate_all_configs(backup)


def preview_config_migration() -> Dict[str, Any]:
    """
    Convenience function to preview configuration migration

    Returns:
        Preview report
    """
    migrator = ConfigMigration()
    return migrator.preview_migration()


def rollback_config_migration() -> bool:
    """
    Convenience function to rollback configuration migration

    Returns:
        True if rollback successful
    """
    migrator = ConfigMigration()
    return migrator.rollback_migration()


if __name__ == "__main__":
    # CLI interface for migration utility
    import typer

    app = typer.Typer()

    @app.command()
    def preview():
        """Preview configuration migration"""
        migrator = ConfigMigration()
        report = migrator.preview_migration()

        print("Configuration Migration Preview")
        print("=" * 40)
        print(f"Will migrate: {len(report['will_migrate'])} files")
        print(f"Will skip: {len(report['will_skip'])} files")
        print(f"Conflicts: {len(report['conflicts'])}")

        if report['recommendations']:
            print("\nRecommendations:")
            for rec in report['recommendations']:
                print(f"• {rec}")

    @app.command()
    def migrate(backup: bool = True):
        """Migrate configurations"""
        migrator = ConfigMigration()
        report = migrator.migrate_all_configs(backup)

        print("Configuration Migration Results")
        print("=" * 40)
        print(f"Migrated: {len(report['migrated_files'])} files")
        print(f"Skipped: {len(report['skipped_files'])} files")
        print(f"Errors: {len(report['errors'])}")

        if report['errors']:
            print("\nErrors:")
            for error in report['errors']:
                print(f"• {error}")

    @app.command()
    def rollback():
        """Rollback configuration migration"""
        migrator = ConfigMigration()
        success = migrator.rollback_migration()

        if success:
            print("✅ Migration rollback completed successfully")
        else:
            print("❌ Migration rollback failed")

    app()
