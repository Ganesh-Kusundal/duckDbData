"""
Custom Exceptions for DuckDB Financial SDK
==========================================

Provides specific exception types for different error conditions.
"""


class SDKError(Exception):
    """Base exception for SDK errors."""
    pass


class APIError(SDKError):
    """
    Exception raised for API-related errors.

    Attributes:
        message: Error message
        status_code: HTTP status code (if applicable)
    """

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def __str__(self):
        if self.status_code:
            return f"API Error ({self.status_code}): {self.message}"
        return f"API Error: {self.message}"


class AuthenticationError(APIError):
    """Exception raised for authentication failures."""
    pass


class ValidationError(APIError):
    """Exception raised for validation errors."""
    pass


class ConnectionError(SDKError):
    """Exception raised for connection-related errors."""
    pass


class TimeoutError(SDKError):
    """Exception raised for timeout errors."""
    pass


class RateLimitError(APIError):
    """Exception raised when rate limit is exceeded."""
    pass
