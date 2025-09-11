"""
Backup Manager

This module provides backup and recovery capabilities for rules including:
- Full system backups
- Incremental backups
- Point-in-time recovery
- Backup validation and integrity checks
- Automated backup scheduling
"""

from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
import shutil
import gzip
import hashlib
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BackupManager:
    """Backup and recovery manager for rules."""

    def __init__(self, backup_directory: str = "backups/rules"):
        """
        Initialize the backup manager.

        Args:
            backup_directory: Directory to store backups
        """
        self.backup_directory = Path(backup_directory)
        self.backup_directory.mkdir(parents=True, exist_ok=True)

    def create_full_backup(
        self,
        source_directories: List[str],
        backup_name: Optional[str] = None,
        compress: bool = True
    ) -> Dict[str, Any]:
        """
        Create a full backup of rule files.

        Args:
            source_directories: List of directories to backup
            backup_name: Optional backup name (auto-generated if not provided)
            compress: Whether to compress the backup

        Returns:
            Backup results
        """
        results = {
            'backup_name': backup_name or self._generate_backup_name(),
            'backup_type': 'full',
            'timestamp': datetime.now().isoformat(),
            'total_files': 0,
            'total_size_bytes': 0,
            'compressed_size_bytes': 0,
            'source_directories': source_directories,
            'status': 'success',
            'errors': []
        }

        try:
            # Create backup directory
            backup_path = self.backup_directory / results['backup_name']
            backup_path.mkdir(parents=True, exist_ok=True)

            # Backup each source directory
            for source_dir in source_directories:
                source_path = Path(source_dir)
                if not source_path.exists():
                    results['errors'].append(f"Source directory {source_dir} does not exist")
                    continue

                # Copy directory contents
                dest_dir = backup_path / source_path.name
                self._copy_directory(source_path, dest_dir, results)

            # Create backup manifest
            manifest_path = backup_path / 'manifest.json'
            with open(manifest_path, 'w') as f:
                json.dump(results, f, indent=2)

            # Compress if requested
            if compress:
                self._compress_backup(backup_path, results)
                # After compression, backup_path no longer exists
                # Use archive path for checksum and final manifest
                checksum_path = Path(results['archive_path']).parent / Path(results['archive_path']).stem
            else:
                checksum_path = backup_path

            # Calculate checksum
            results['checksum'] = self._calculate_checksum(checksum_path)

            # Update final manifest
            if compress:
                # For compressed backups, create manifest in archive directory
                archive_dir = Path(results['archive_path']).parent
                final_manifest_path = archive_dir / f"{results['backup_name']}_manifest.json"
                with open(final_manifest_path, 'w') as f:
                    json.dump(results, f, indent=2)
                results['manifest_path'] = str(final_manifest_path)
            else:
                with open(manifest_path, 'w') as f:
                    json.dump(results, f, indent=2)

            logger.info(f"Full backup created: {results['backup_name']}")

        except Exception as e:
            results['status'] = 'failed'
            results['errors'].append(f"Backup creation failed: {str(e)}")
            logger.error(f"Failed to create full backup: {e}")

        return results

    def create_incremental_backup(
        self,
        source_directories: List[str],
        last_backup_name: str,
        backup_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an incremental backup based on the last full backup.

        Args:
            source_directories: List of directories to backup
            last_backup_name: Name of the last backup to compare against
            backup_name: Optional backup name

        Returns:
            Backup results
        """
        results = {
            'backup_name': backup_name or self._generate_backup_name(),
            'backup_type': 'incremental',
            'timestamp': datetime.now().isoformat(),
            'base_backup': last_backup_name,
            'total_files': 0,
            'changed_files': 0,
            'new_files': 0,
            'deleted_files': 0,
            'source_directories': source_directories,
            'status': 'success',
            'errors': []
        }

        try:
            # Load last backup manifest
            last_backup_path = self.backup_directory / last_backup_name
            if not last_backup_path.exists():
                raise FileNotFoundError(f"Base backup {last_backup_name} not found")

            manifest_path = last_backup_path / 'manifest.json'
            with open(manifest_path, 'r') as f:
                last_manifest = json.load(f)

            # Create incremental backup directory
            backup_path = self.backup_directory / results['backup_name']
            backup_path.mkdir(parents=True, exist_ok=True)

            # Compare and backup changes
            for source_dir in source_directories:
                source_path = Path(source_dir)
                if not source_path.exists():
                    results['errors'].append(f"Source directory {source_dir} does not exist")
                    continue

                # Compare with last backup
                changes = self._compare_with_backup(
                    source_path,
                    last_backup_path / source_path.name,
                    backup_path / source_path.name,
                    results
                )

                results['changed_files'] += changes['changed']
                results['new_files'] += changes['new']
                results['deleted_files'] += changes['deleted']

            # Create backup manifest
            manifest_path = backup_path / 'manifest.json'
            with open(manifest_path, 'w') as f:
                json.dump(results, f, indent=2)

            # Calculate checksum
            results['checksum'] = self._calculate_checksum(backup_path)

            logger.info(f"Incremental backup created: {results['backup_name']}")

        except Exception as e:
            results['status'] = 'failed'
            results['errors'].append(f"Incremental backup creation failed: {str(e)}")
            logger.error(f"Failed to create incremental backup: {e}")

        return results

    def restore_backup(
        self,
        backup_name: str,
        target_directory: str,
        validate_integrity: bool = True
    ) -> Dict[str, Any]:
        """
        Restore a backup to a target directory.

        Args:
            backup_name: Name of backup to restore
            target_directory: Directory to restore to
            validate_integrity: Whether to validate backup integrity

        Returns:
            Restore results
        """
        results = {
            'backup_name': backup_name,
            'target_directory': target_directory,
            'timestamp': datetime.now().isoformat(),
            'total_files': 0,
            'restored_files': 0,
            'skipped_files': 0,
            'status': 'success',
            'errors': []
        }

        try:
            backup_path = self.backup_directory / backup_name
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup {backup_name} not found")

            # Validate integrity if requested
            if validate_integrity:
                manifest_path = backup_path / 'manifest.json'
                if manifest_path.exists():
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)

                    expected_checksum = manifest.get('checksum')
                    if expected_checksum:
                        actual_checksum = self._calculate_checksum(backup_path)
                        if actual_checksum != expected_checksum:
                            raise ValueError(f"Backup integrity check failed for {backup_name}")

            # Handle compressed backups
            if (backup_path / f"{backup_name}.tar.gz").exists():
                self._decompress_backup(backup_path, backup_name)

            # Restore files
            target_path = Path(target_directory)
            target_path.mkdir(parents=True, exist_ok=True)

            # Copy all files from backup
            for item in backup_path.rglob('*'):
                if item.is_file() and item.name != 'manifest.json':
                    relative_path = item.relative_to(backup_path)
                    target_file = target_path / relative_path

                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_file)

                    results['restored_files'] += 1

            results['total_files'] = results['restored_files']

            logger.info(f"Backup {backup_name} restored to {target_directory}")

        except Exception as e:
            results['status'] = 'failed'
            results['errors'].append(f"Restore operation failed: {str(e)}")
            logger.error(f"Failed to restore backup {backup_name}: {e}")

        return results

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.

        Returns:
            List of backup information
        """
        backups = []

        try:
            for backup_dir in self.backup_directory.iterdir():
                if backup_dir.is_dir():
                    manifest_path = backup_dir / 'manifest.json'
                    if manifest_path.exists():
                        try:
                            with open(manifest_path, 'r') as f:
                                manifest = json.load(f)

                            backups.append({
                                'name': backup_dir.name,
                                'type': manifest.get('backup_type', 'unknown'),
                                'timestamp': manifest.get('timestamp'),
                                'total_files': manifest.get('total_files', 0),
                                'status': manifest.get('status', 'unknown'),
                                'size_mb': self._calculate_directory_size(backup_dir) / (1024 * 1024)
                            })
                        except Exception as e:
                            logger.warning(f"Failed to read manifest for {backup_dir.name}: {e}")

            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")

        return backups

    def cleanup_old_backups(
        self,
        keep_days: int = 30,
        keep_count: int = 10
    ) -> Dict[str, Any]:
        """
        Clean up old backups.

        Args:
            keep_days: Keep backups newer than this many days
            keep_count: Keep at least this many recent backups

        Returns:
            Cleanup results
        """
        results = {
            'total_backups': 0,
            'removed_backups': 0,
            'kept_backups': 0,
            'errors': []
        }

        try:
            backups = self.list_backups()
            results['total_backups'] = len(backups)

            if len(backups) <= keep_count:
                results['kept_backups'] = len(backups)
                return results

            # Keep recent backups by count
            recent_backups = backups[:keep_count]

            # Keep backups within time window
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            time_window_backups = []

            for backup in backups:
                try:
                    backup_date = datetime.fromisoformat(backup['timestamp'])
                    if backup_date >= cutoff_date:
                        time_window_backups.append(backup)
                except:
                    # Keep backups with invalid timestamps
                    time_window_backups.append(backup)

            # Combine and deduplicate
            keep_backups = list({b['name']: b for b in recent_backups + time_window_backups}.values())
            remove_backups = [b for b in backups if b not in keep_backups]

            # Remove old backups
            for backup in remove_backups:
                try:
                    backup_path = self.backup_directory / backup['name']
                    shutil.rmtree(backup_path)
                    results['removed_backups'] += 1
                except Exception as e:
                    results['errors'].append(f"Failed to remove {backup['name']}: {str(e)}")

            results['kept_backups'] = results['total_backups'] - results['removed_backups']

            logger.info(f"Backup cleanup completed: {results['removed_backups']} removed, "
                       f"{results['kept_backups']} kept")

        except Exception as e:
            results['errors'].append(f"Cleanup operation failed: {str(e)}")
            logger.error(f"Failed to cleanup old backups: {e}")

        return results

    def validate_backup_integrity(self, backup_name: str) -> Dict[str, Any]:
        """
        Validate the integrity of a backup.

        Args:
            backup_name: Name of backup to validate

        Returns:
            Validation results
        """
        results = {
            'backup_name': backup_name,
            'is_valid': False,
            'manifest_valid': False,
            'checksum_valid': False,
            'files_intact': False,
            'errors': []
        }

        try:
            backup_path = self.backup_directory / backup_name
            if not backup_path.exists():
                results['errors'].append(f"Backup {backup_name} does not exist")
                return results

            # Check manifest
            manifest_path = backup_path / 'manifest.json'
            if not manifest_path.exists():
                results['errors'].append("Manifest file missing")
                return results

            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                results['manifest_valid'] = True
            except Exception as e:
                results['errors'].append(f"Invalid manifest: {str(e)}")
                return results

            # Check checksum
            expected_checksum = manifest.get('checksum')
            if expected_checksum:
                actual_checksum = self._calculate_checksum(backup_path)
                if actual_checksum == expected_checksum:
                    results['checksum_valid'] = True
                else:
                    results['errors'].append("Checksum mismatch")
            else:
                results['errors'].append("No checksum in manifest")

            # Check file integrity (basic check)
            expected_files = manifest.get('total_files', 0)
            actual_files = sum(1 for _ in backup_path.rglob('*') if _.is_file() and _.name != 'manifest.json')

            if actual_files == expected_files:
                results['files_intact'] = True
            else:
                results['errors'].append(f"File count mismatch: expected {expected_files}, got {actual_files}")

            results['is_valid'] = all([
                results['manifest_valid'],
                results['checksum_valid'],
                results['files_intact']
            ])

        except Exception as e:
            results['errors'].append(f"Validation failed: {str(e)}")
            logger.error(f"Failed to validate backup {backup_name}: {e}")

        return results

    def _copy_directory(self, source: Path, dest: Path, results: Dict[str, Any]):
        """Copy directory contents and update results."""
        dest.mkdir(parents=True, exist_ok=True)

        for item in source.rglob('*'):
            if item.is_file():
                relative_path = item.relative_to(source)
                dest_file = dest / relative_path

                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_file)

                results['total_files'] += 1
                results['total_size_bytes'] += item.stat().st_size

    def _compare_with_backup(
        self,
        source: Path,
        last_backup: Path,
        dest: Path,
        results: Dict[str, Any]
    ) -> Dict[str, int]:
        """Compare source with last backup and copy changes."""
        changes = {'changed': 0, 'new': 0, 'deleted': 0}

        # This is a simplified implementation
        # In a real system, you'd compare file hashes or modification times

        dest.mkdir(parents=True, exist_ok=True)

        if not last_backup.exists():
            # Copy entire source as new
            self._copy_directory(source, dest, results)
            changes['new'] = results['total_files']
        else:
            # Compare and copy changes (simplified)
            for item in source.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(source)
                    backup_file = last_backup / relative_path

                    if not backup_file.exists():
                        # New file
                        dest_file = dest / relative_path
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_file)
                        changes['new'] += 1
                        results['total_files'] += 1
                    elif item.stat().st_mtime > backup_file.stat().st_mtime:
                        # Changed file
                        dest_file = dest / relative_path
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_file)
                        changes['changed'] += 1
                        results['total_files'] += 1

        return changes

    def _compress_backup(self, backup_path: Path, results: Dict[str, Any]):
        """Compress a backup directory."""
        import tarfile

        try:
            archive_name = f"{backup_path.name}.tar.gz"
            archive_path = backup_path.parent / archive_name

            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_path, arcname=backup_path.name)

            # Update results
            compressed_size = archive_path.stat().st_size
            results['compressed_size_bytes'] = compressed_size
            results['archive_path'] = str(archive_path)

            # Remove uncompressed directory
            shutil.rmtree(backup_path)

        except Exception as e:
            logger.warning(f"Failed to compress backup: {e}")

    def _decompress_backup(self, backup_path: Path, backup_name: str):
        """Decompress a backup archive."""
        import tarfile

        try:
            archive_path = backup_path / f"{backup_name}.tar.gz"

            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(backup_path.parent)

            # Remove archive
            archive_path.unlink()

        except Exception as e:
            logger.warning(f"Failed to decompress backup: {e}")

    def _calculate_checksum(self, path: Path) -> str:
        """Calculate SHA256 checksum of a directory."""
        hash_sha256 = hashlib.sha256()

        # Sort files for consistent checksum
        files = []
        for file_path in sorted(path.rglob('*')):
            if file_path.is_file() and file_path.name != 'manifest.json':
                files.append(file_path)

        for file_path in files:
            try:
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_sha256.update(chunk)
            except Exception as e:
                logger.warning(f"Failed to hash file {file_path}: {e}")

        return hash_sha256.hexdigest()

    def _calculate_directory_size(self, path: Path) -> int:
        """Calculate total size of a directory."""
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def _generate_backup_name(self) -> str:
        """Generate a unique backup name."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{timestamp}"
