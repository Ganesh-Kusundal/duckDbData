"""
Caching Infrastructure for Performance Optimization

Provides caching mechanisms for frequently accessed data,
reducing database load and improving response times.
"""

import asyncio
import json
import logging
import hashlib
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import threading

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached item with metadata."""

    def __init__(self, key: str, value: Any, ttl_seconds: int = 300):
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.accessed_at = datetime.now()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds <= 0:
            return False  # Never expires
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds

    def access(self):
        """Mark the entry as accessed."""
        self.accessed_at = datetime.now()
        self.access_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'key': self.key,
            'value': self.value,
            'created_at': self.created_at.isoformat(),
            'accessed_at': self.accessed_at.isoformat(),
            'ttl_seconds': self.ttl_seconds,
            'access_count': self.access_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create from dictionary."""
        entry = cls(data['key'], data['value'], data['ttl_seconds'])
        entry.created_at = datetime.fromisoformat(data['created_at'])
        entry.accessed_at = datetime.fromisoformat(data['accessed_at'])
        entry.access_count = data['access_count']
        return entry


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set value in cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cached values."""
        pass

    @abstractmethod
    async def has_key(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class InMemoryCacheBackend(CacheBackend):
    """In-memory cache backend using dictionary."""

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                entry.access()
                return entry.value
            elif entry and entry.is_expired():
                # Remove expired entry
                del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set value in cache."""
        async with self._lock:
            # Check if we need to evict entries
            if len(self._cache) >= self._max_size and key not in self._cache:
                await self._evict_least_recently_used()

            entry = CacheEntry(key, value, ttl_seconds)
            self._cache[key] = entry
            return True

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> bool:
        """Clear all cached values."""
        async with self._lock:
            self._cache.clear()
            return True

    async def has_key(self, key: str) -> bool:
        """Check if key exists in cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                return True
            elif entry and entry.is_expired():
                del self._cache[key]
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())
            active_entries = total_entries - expired_entries

            if active_entries > 0:
                avg_access_count = sum(entry.access_count for entry in self._cache.values() if not entry.is_expired()) / active_entries
                avg_age_seconds = sum((datetime.now() - entry.created_at).total_seconds()
                                    for entry in self._cache.values() if not entry.is_expired()) / active_entries
            else:
                avg_access_count = 0
                avg_age_seconds = 0

            return {
                'total_entries': total_entries,
                'active_entries': active_entries,
                'expired_entries': expired_entries,
                'max_size': self._max_size,
                'utilization_percentage': (active_entries / self._max_size) * 100 if self._max_size > 0 else 0,
                'average_access_count': avg_access_count,
                'average_age_seconds': avg_age_seconds
            }

    async def _evict_least_recently_used(self):
        """Evict the least recently used entry."""
        if not self._cache:
            return

        # Find entry with oldest access time
        oldest_key = min(self._cache.keys(),
                        key=lambda k: self._cache[k].accessed_at)

        del self._cache[oldest_key]
        logger.debug(f"Evicted LRU cache entry: {oldest_key}")


class CacheManager:
    """
    Main cache manager providing high-level caching operations.

    Supports multiple cache backends and provides caching strategies.
    """

    def __init__(self, backend: CacheBackend = None):
        self.backend = backend or InMemoryCacheBackend()
        self._cache_strategies: Dict[str, Callable] = {}
        self._enabled = True

    def enable(self):
        """Enable caching."""
        self._enabled = True
        logger.info("Cache manager enabled")

    def disable(self):
        """Disable caching."""
        self._enabled = False
        logger.info("Cache manager disabled")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._enabled:
            return None

        try:
            value = await self.backend.get(key)
            if value is not None:
                logger.debug(f"Cache hit for key: {key}")
            else:
                logger.debug(f"Cache miss for key: {key}")
            return value
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set value in cache."""
        if not self._enabled:
            return False

        try:
            success = await self.backend.set(key, value, ttl_seconds)
            if success:
                logger.debug(f"Cached value for key: {key} (TTL: {ttl_seconds}s)")
            return success
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self._enabled:
            return False

        try:
            success = await self.backend.delete(key)
            if success:
                logger.debug(f"Deleted cache key: {key}")
            return success
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cached values."""
        try:
            success = await self.backend.clear()
            if success:
                logger.info("Cache cleared")
            return success
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    def generate_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments."""
        # Create a string representation of all arguments
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])

        key_string = "|".join(key_parts)

        # Create hash for consistent key length
        return hashlib.md5(key_string.encode()).hexdigest()

    async def get_or_set(self, key: str, value_func: Callable[[], Awaitable[Any]],
                        ttl_seconds: int = 300) -> Any:
        """Get value from cache or set it if not present."""
        # Try to get from cache first
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value

        # Compute value and cache it
        value = await value_func()
        await self.set(key, value, ttl_seconds)
        return value

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching a pattern."""
        # This is a simplified implementation
        # In a real scenario, you'd use pattern matching on keys
        logger.warning("Pattern invalidation not fully implemented")
        return 0

    async def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        results = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                results[key] = value
        return results

    async def set_multi(self, key_value_pairs: Dict[str, Any], ttl_seconds: int = 300) -> bool:
        """Set multiple values in cache."""
        success = True
        for key, value in key_value_pairs.items():
            if not await self.set(key, value, ttl_seconds):
                success = False
        return success

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            stats = await self.backend.get_stats()
            stats['enabled'] = self._enabled
            return stats
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {'error': str(e)}

    # Specialized caching methods for common use cases

    async def cache_database_query(self, query: str, params: tuple = None,
                                 ttl_seconds: int = 300) -> Any:
        """Cache database query results."""
        key = self.generate_key("db_query", query, str(params) if params else "")
        return await self.get_or_set(key, lambda: self._execute_db_query(query, params), ttl_seconds)

    async def cache_api_response(self, url: str, params: Dict[str, Any] = None,
                               ttl_seconds: int = 60) -> Any:
        """Cache API response."""
        key = self.generate_key("api_response", url, params or {})
        return await self.get_or_set(key, lambda: self._fetch_api_response(url, params), ttl_seconds)

    async def cache_computation_result(self, function_name: str, args: List[Any],
                                     kwargs: Dict[str, Any], ttl_seconds: int = 3600) -> Any:
        """Cache expensive computation results."""
        key = self.generate_key("computation", function_name, args, kwargs)
        return await self.get_or_set(key, lambda: self._execute_computation(function_name, args, kwargs), ttl_seconds)

    # Placeholder methods for actual implementations
    async def _execute_db_query(self, query: str, params: tuple = None) -> Any:
        """Execute database query (placeholder)."""
        # This would be implemented to actually execute the query
        return {"query": query, "params": params, "result": "placeholder"}

    async def _fetch_api_response(self, url: str, params: Dict[str, Any] = None) -> Any:
        """Fetch API response (placeholder)."""
        # This would be implemented to actually fetch from API
        return {"url": url, "params": params, "result": "placeholder"}

    async def _execute_computation(self, function_name: str, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        """Execute computation (placeholder)."""
        # This would be implemented to actually execute the computation
        return {"function": function_name, "args": args, "kwargs": kwargs, "result": "placeholder"}


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(backend: CacheBackend = None) -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(backend)
    return _cache_manager


def reset_cache_manager():
    """Reset global cache manager (mainly for testing)."""
    global _cache_manager
    _cache_manager = None


# Decorators for easy caching
def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()

            # Generate cache key
            key_parts = [key_prefix] if key_prefix else []
            key_parts.extend([func.__name__, str(args), str(kwargs)])
            cache_key = cache_manager.generate_key(*key_parts)

            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl_seconds)
            return result

        return wrapper
    return decorator


def cache_invalidate_pattern(pattern: str):
    """Decorator to invalidate cache pattern after function execution."""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Invalidate cache pattern
            cache_manager = get_cache_manager()
            await cache_manager.invalidate_pattern(pattern)

            return result

        return wrapper
    return decorator
