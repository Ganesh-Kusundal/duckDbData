"""
System Client
============

Client for system monitoring and management operations.
"""

from typing import Dict, List, Optional, Any


class SystemClient:
    """
    Client for system operations.

    Provides methods to monitor and manage system resources.
    """

    def __init__(self, client):
        """Initialize system client."""
        self.client = client

    def get_info(self) -> Dict:
        """
        Get system information.

        Returns:
            System information
        """
        return self.client._make_request('GET', '/system/info')

    def get_health(self) -> Dict:
        """
        Get system health status.

        Returns:
            Health status information
        """
        return self.client._make_request('GET', '/system/health')

    def get_metrics(self) -> Dict:
        """
        Get system performance metrics.

        Returns:
            Performance metrics
        """
        return self.client._make_request('GET', '/system/metrics')

    def get_logs(self,
                lines: int = 100,
                level: Optional[str] = None,
                service: Optional[str] = None) -> List[Dict]:
        """
        Get system logs.

        Args:
            lines: Number of log lines to retrieve
            level: Log level filter (DEBUG, INFO, WARNING, ERROR)
            service: Service filter

        Returns:
            List of log entries
        """
        params = {'lines': lines}
        if level:
            params['level'] = level
        if service:
            params['service'] = service

        return self.client._make_request('GET', '/system/logs', params=params)

    def get_configuration(self) -> Dict:
        """
        Get system configuration.

        Returns:
            System configuration
        """
        return self.client._make_request('GET', '/system/config')

    def update_configuration(self, config: Dict) -> Dict:
        """
        Update system configuration.

        Args:
            config: Configuration updates

        Returns:
            Update confirmation
        """
        return self.client._make_request('PUT', '/system/config', data=config)

    def restart_service(self, service: str) -> Dict:
        """
        Restart a system service.

        Args:
            service: Service name

        Returns:
            Restart confirmation
        """
        return self.client._make_request('POST', f'/system/services/{service}/restart')

    def get_services_status(self) -> List[Dict]:
        """
        Get status of all system services.

        Returns:
            List of service status information
        """
        return self.client._make_request('GET', '/system/services')

    def get_disk_usage(self) -> Dict:
        """
        Get disk usage information.

        Returns:
            Disk usage statistics
        """
        return self.client._make_request('GET', '/system/disk')

    def get_memory_usage(self) -> Dict:
        """
        Get memory usage information.

        Returns:
            Memory usage statistics
        """
        return self.client._make_request('GET', '/system/memory')

    def get_cpu_usage(self) -> Dict:
        """
        Get CPU usage information.

        Returns:
            CPU usage statistics
        """
        return self.client._make_request('GET', '/system/cpu')

    def get_network_stats(self) -> Dict:
        """
        Get network statistics.

        Returns:
            Network usage statistics
        """
        return self.client._make_request('GET', '/system/network')

    def clear_cache(self, cache_type: str = "all") -> Dict:
        """
        Clear system cache.

        Args:
            cache_type: Type of cache to clear (all, query, data, etc.)

        Returns:
            Cache clearing confirmation
        """
        return self.client._make_request('POST', '/system/cache/clear',
                                       data={'type': cache_type})

    def backup_database(self, backup_path: Optional[str] = None) -> Dict:
        """
        Create database backup.

        Args:
            backup_path: Optional backup destination path

        Returns:
            Backup operation status
        """
        data = {}
        if backup_path:
            data['path'] = backup_path

        return self.client._make_request('POST', '/system/backup/database', data=data)

    def restore_database(self, backup_path: str) -> Dict:
        """
        Restore database from backup.

        Args:
            backup_path: Path to backup file

        Returns:
            Restore operation status
        """
        return self.client._make_request('POST', '/system/restore/database',
                                       data={'path': backup_path})

    def get_backup_history(self) -> List[Dict]:
        """
        Get backup history.

        Returns:
            List of backup operations
        """
        return self.client._make_request('GET', '/system/backups/history')

    def run_maintenance(self, maintenance_type: str = "full") -> Dict:
        """
        Run system maintenance.

        Args:
            maintenance_type: Type of maintenance (full, quick, vacuum, etc.)

        Returns:
            Maintenance operation status
        """
        return self.client._make_request('POST', '/system/maintenance',
                                       data={'type': maintenance_type})
