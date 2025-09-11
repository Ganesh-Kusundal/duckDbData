"""
Base External Adapter
Provides common functionality for external service integrations
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import aiohttp
import backoff
import json

logger = logging.getLogger(__name__)


@dataclass
class ExternalServiceResult:
    """Standardized result from external service calls"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ServiceHealth:
    """External service health status"""
    service_name: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    response_time: Optional[float] = None
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    uptime_percentage: Optional[float] = None


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded"""
    pass


class ServiceUnavailableError(Exception):
    """Exception raised when external service is unavailable"""
    pass


class BaseExternalAdapter:
    """
    Base class for external service adapters
    Provides common functionality like retry logic, rate limiting, health checks
    """

    def __init__(self,
                 base_url: str,
                 api_key: Optional[str] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 rate_limit_per_minute: int = 60):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_per_minute = rate_limit_per_minute

        # Rate limiting
        self.request_times = []
        self.rate_limit_lock = asyncio.Lock()

        # Health monitoring
        self.health_checks = []
        self.last_health_check = None
        self.health_status = ServiceHealth(
            service_name=self.__class__.__name__,
            status='unknown'
        )

        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None

        self.logger = logging.getLogger(self.__class__.__name__)

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self):
        """Initialize the adapter"""
        # Create HTTP session with timeout
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        headers = {}

        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
            headers['X-API-Key'] = self.api_key

        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=aiohttp.TCPConnector(limit=10)  # Connection pool
        )

        self.logger.info(f"Initialized {self.__class__.__name__} adapter")

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None
        self.logger.info(f"Cleaned up {self.__class__.__name__} adapter")

    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        async with self.rate_limit_lock:
            now = datetime.now()

            # Remove requests older than 1 minute
            cutoff = now - timedelta(minutes=1)
            self.request_times = [t for t in self.request_times if t > cutoff]

            # Check if we're within rate limit
            if len(self.request_times) >= self.rate_limit_per_minute:
                # Calculate wait time
                oldest_request = min(self.request_times)
                wait_time = 60 - (now - oldest_request).total_seconds()

                if wait_time > 0:
                    self.logger.warning(".2f")
                    await asyncio.sleep(wait_time)

            # Record this request
            self.request_times.append(now)

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        jitter=backoff.random_jitter
    )
    async def _make_request(self,
                           method: str,
                           endpoint: str,
                           params: Optional[Dict[str, Any]] = None,
                           json_data: Optional[Dict[str, Any]] = None,
                           headers: Optional[Dict[str, str]] = None) -> ExternalServiceResult:
        """
        Make HTTP request with retry logic and error handling

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: JSON request body
            headers: Additional headers

        Returns:
            ExternalServiceResult with response data or error
        """
        if not self.session:
            return ExternalServiceResult(
                success=False,
                error="Adapter not initialized"
            )

        # Check rate limit
        await self._check_rate_limit()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = headers or {}

        start_time = datetime.now()

        try:
            self.logger.debug(f"Making {method} request to {url}")

            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=request_headers
            ) as response:

                response_time = (datetime.now() - start_time).total_seconds()

                # Handle rate limiting
                if response.status == 429:
                    retry_after = response.headers.get('Retry-After', '60')
                    self.logger.warning(f"Rate limited, retry after {retry_after}s")
                    raise RateLimitError(f"Rate limit exceeded, retry after {retry_after}s")

                # Handle service unavailable
                if response.status >= 500:
                    raise ServiceUnavailableError(f"Service unavailable: {response.status}")

                # Parse response
                try:
                    if response.content_type == 'application/json':
                        data = await response.json()
                    else:
                        data = await response.text()
                except Exception as e:
                    self.logger.warning(f"Failed to parse response: {e}")
                    data = await response.text()

                if response.status >= 400:
                    error_msg = f"HTTP {response.status}: {data}"
                    self.logger.error(f"Request failed: {error_msg}")
                    return ExternalServiceResult(
                        success=False,
                        error=error_msg,
                        status_code=response.status,
                        response_time=response_time
                    )

                self.logger.debug(f"Request successful: {response.status} in {response_time:.2f}s")

                return ExternalServiceResult(
                    success=True,
                    data=data,
                    status_code=response.status,
                    response_time=response_time
                )

        except asyncio.TimeoutError:
            response_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Request timeout after {response_time:.2f}s"
            self.logger.error(error_msg)
            return ExternalServiceResult(
                success=False,
                error=error_msg,
                response_time=response_time
            )

        except aiohttp.ClientError as e:
            response_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Client error: {str(e)}"
            self.logger.error(error_msg)
            return ExternalServiceResult(
                success=False,
                error=error_msg,
                response_time=response_time
            )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ExternalServiceResult(
                success=False,
                error=error_msg,
                response_time=response_time
            )

    async def health_check(self) -> ServiceHealth:
        """
        Perform health check on external service

        Returns:
            ServiceHealth with current status
        """
        start_time = datetime.now()

        try:
            # Implement service-specific health check
            health_result = await self._perform_health_check()

            response_time = (datetime.now() - start_time).total_seconds()

            if health_result.success:
                status = 'healthy'
                error_message = None
            else:
                status = 'unhealthy'
                error_message = health_result.error

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            status = 'unhealthy'
            error_message = str(e)

        # Update health status
        self.health_status.status = status
        self.health_status.response_time = response_time
        self.health_status.last_check = datetime.now()
        self.health_status.error_message = error_message

        # Calculate uptime percentage (simple implementation)
        self.health_checks.append(status == 'healthy')
        if len(self.health_checks) > 100:  # Keep last 100 checks
            self.health_checks = self.health_checks[-100:]

        if self.health_checks:
            healthy_count = sum(1 for check in self.health_checks if check)
            self.health_status.uptime_percentage = (healthy_count / len(self.health_checks)) * 100

        self.logger.debug(f"Health check completed: {status} ({response_time:.2f}s)")

        return self.health_status

    async def _perform_health_check(self) -> ExternalServiceResult:
        """
        Service-specific health check implementation
        Should be overridden by subclasses
        """
        # Default implementation - try a simple endpoint
        return await self._make_request('GET', 'health')

    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information and capabilities"""
        return {
            'service_name': self.__class__.__name__,
            'base_url': self.base_url,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'health_status': {
                'status': self.health_status.status,
                'response_time': self.health_status.response_time,
                'last_check': self.health_status.last_check.isoformat() if self.health_status.last_check else None,
                'uptime_percentage': self.health_status.uptime_percentage
            }
        }

    def is_healthy(self) -> bool:
        """Check if service is currently healthy"""
        return self.health_status.status == 'healthy'

    async def wait_for_healthy(self, timeout: int = 60, check_interval: int = 5) -> bool:
        """
        Wait for service to become healthy

        Args:
            timeout: Maximum time to wait in seconds
            check_interval: Time between health checks

        Returns:
            True if service becomes healthy within timeout
        """
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout:
            health = await self.health_check()
            if health.status == 'healthy':
                self.logger.info(f"Service became healthy after {(datetime.now() - start_time).total_seconds():.1f}s")
                return True

            await asyncio.sleep(check_interval)

        self.logger.warning(f"Service did not become healthy within {timeout}s timeout")
        return False

    def _log_request(self, method: str, endpoint: str, params: Optional[Dict] = None, **kwargs):
        """Log API request details"""
        log_data = {
            'method': method,
            'endpoint': endpoint,
            'base_url': self.base_url,
            'timestamp': datetime.now().isoformat()
        }

        if params:
            # Mask sensitive parameters
            safe_params = {}
            for key, value in params.items():
                if 'key' in key.lower() or 'token' in key.lower() or 'secret' in key.lower():
                    safe_params[key] = '***MASKED***'
                else:
                    safe_params[key] = value
            log_data['params'] = safe_params

        self.logger.debug(f"External API request: {method} {endpoint}", extra=log_data)
