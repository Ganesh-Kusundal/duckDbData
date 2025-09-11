"""
Database Access Manager - Handles Concurrent Database Access

This module provides a proper database access management system that can handle
concurrent requests, manage locks, and ensure data consistency.
"""

import threading
import queue
import time
import logging
from typing import Any, Callable, Optional
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DatabaseRequest:
    """Represents a database access request."""
    request_id: str
    operation: Callable[[], Any]
    callback: Optional[Callable[[Any], None]] = None
    priority: int = 1  # Higher priority = processed first


class DatabaseAccessManager:
    """
    Manages concurrent database access with proper queuing and synchronization.

    This class ensures that database operations are processed sequentially
    to avoid lock conflicts while allowing multiple threads to queue requests.
    """

    def __init__(self, max_queue_size: int = 100, max_workers: int = 1):
        """
        Initialize the database access manager.

        Args:
            max_queue_size: Maximum number of queued requests
            max_workers: Number of worker threads (keep at 1 for database safety)
        """
        self.max_queue_size = max_queue_size
        self.max_workers = max_workers

        # Thread synchronization
        self._lock = threading.RLock()
        self._queue = queue.PriorityQueue(maxsize=max_queue_size)
        self._results = {}  # request_id -> result
        self._errors = {}   # request_id -> error

        # Worker thread
        self._worker_thread = None
        self._running = False
        self._request_counter = 0

        logger.info(f"Database Access Manager initialized (max_queue: {max_queue_size}, workers: {max_workers})")

    def start(self):
        """Start the database access manager."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

            logger.info("Database Access Manager started")

    def stop(self):
        """Stop the database access manager."""
        with self._lock:
            if not self._running:
                return

            self._running = False
            # Add a sentinel value to stop the worker
            try:
                self._queue.put_nowait((0, None))  # Priority 0, None request = stop signal
            except:
                pass

            if self._worker_thread:
                self._worker_thread.join(timeout=5)

            logger.info("Database Access Manager stopped")

    def submit_request(
        self,
        operation: Callable[[], Any],
        priority: int = 1,
        timeout: float = 30.0
    ) -> str:
        """
        Submit a database operation request.

        Args:
            operation: Callable that performs the database operation
            priority: Priority level (higher = processed first)
            timeout: Maximum time to wait for queue space

        Returns:
            Request ID for tracking the operation

        Raises:
            queue.Full: If queue is full and timeout is exceeded
        """
        with self._lock:
            if not self._running:
                raise RuntimeError("Database Access Manager is not running")

            request_id = f"req_{self._request_counter}"
            self._request_counter += 1

            request = DatabaseRequest(
                request_id=request_id,
                operation=operation,
                priority=priority
            )

            # Use negative priority for Python's PriorityQueue (lower value = higher priority)
            try:
                self._queue.put((-priority, request), timeout=timeout)
                logger.debug(f"Request {request_id} queued (priority: {priority})")
                return request_id
            except queue.Full:
                logger.error(f"Request queue full, failed to submit request {request_id}")
                raise

    def get_result(self, request_id: str, timeout: float = 30.0) -> Any:
        """
        Get the result of a completed database operation.

        Args:
            request_id: Request ID returned by submit_request
            timeout: Maximum time to wait for result

        Returns:
            Operation result

        Raises:
            TimeoutError: If result not available within timeout
            Exception: If operation failed
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            with self._lock:
                if request_id in self._errors:
                    error = self._errors[request_id]
                    del self._errors[request_id]
                    raise error

                if request_id in self._results:
                    result = self._results[request_id]
                    del self._results[request_id]
                    return result

            time.sleep(0.1)  # Brief wait before checking again

        raise TimeoutError(f"Result for request {request_id} not available within {timeout}s")

    def execute_sync(
        self,
        operation: Callable[[], Any],
        priority: int = 1,
        timeout: float = 30.0
    ) -> Any:
        """
        Execute a database operation synchronously.

        Args:
            operation: Callable that performs the database operation
            priority: Priority level for the operation
            timeout: Maximum time to wait for completion

        Returns:
            Operation result
        """
        request_id = self.submit_request(operation, priority, timeout)
        return self.get_result(request_id, timeout)

    def _worker_loop(self):
        """Main worker loop that processes queued requests."""
        logger.info("Database Access Manager worker started")

        while self._running:
            try:
                # Get next request from queue
                priority, request = self._queue.get(timeout=1.0)

                if request is None:  # Stop signal
                    break

                logger.debug(f"Processing request {request.request_id}")

                try:
                    # Execute the operation
                    result = request.operation()

                    # Store the result
                    with self._lock:
                        self._results[request.request_id] = result

                    logger.debug(f"Request {request.request_id} completed successfully")

                except Exception as e:
                    logger.error(f"Request {request.request_id} failed: {e}")

                    # Store the error
                    with self._lock:
                        self._errors[request.request_id] = e

                finally:
                    # Mark task as done
                    self._queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                time.sleep(1.0)  # Brief pause on error

        logger.info("Database Access Manager worker stopped")

    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        """Check if the manager is running."""
        with self._lock:
            return self._running


# Global instance
_access_manager: Optional[DatabaseAccessManager] = None


def get_database_access_manager() -> DatabaseAccessManager:
    """Get the global database access manager instance."""
    global _access_manager

    if _access_manager is None:
        _access_manager = DatabaseAccessManager()
        _access_manager.start()

    return _access_manager


@contextmanager
def database_access_context():
    """
    Context manager for database access operations.

    Usage:
        with database_access_context() as db:
            result = db.execute_query("SELECT * FROM table")
    """
    manager = get_database_access_manager()

    # This would need to be integrated with the actual database manager
    # For now, it's a placeholder for the concept
    try:
        yield manager
    finally:
        pass



