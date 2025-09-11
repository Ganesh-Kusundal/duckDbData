"""
API Dependencies
Dependency injection setup for API endpoints
"""

from typing import Optional
from fastapi import Request, Depends, HTTPException

from src.application.services.market_data_application_service import MarketDataApplicationService
from src.infrastructure.dependency_container import get_container as get_dependency_container


def get_application_service(request: Request) -> MarketDataApplicationService:
    """
    Get MarketDataApplicationService from dependency container

    Args:
        request: FastAPI request object

    Returns:
        MarketDataApplicationService instance
    """
    container = getattr(request.app.state, 'container', None)
    if container is None:
        raise HTTPException(
            status_code=500,
            detail="Dependency container not initialized"
        )

    # Get the application service from container
    service = container.get(MarketDataApplicationService)
    if service is None:
        raise HTTPException(
            status_code=500,
            detail="Application service not available"
        )

    return service


def get_current_user_token(request: Request) -> Optional[str]:
    """
    Extract authentication token from request
    Placeholder for authentication middleware

    Args:
        request: FastAPI request object

    Returns:
        Authentication token or None
    """
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix

    # Extract token from query parameters (for websocket upgrades)
    return request.query_params.get("token")


def require_authentication(token: Optional[str] = Depends(get_current_user_token)):
    """
    Require authentication for protected endpoints
    Placeholder for actual authentication logic

    Args:
        token: Authentication token

    Raises:
        HTTPException: If authentication fails
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # TODO: Implement actual token validation
    # For now, accept any non-empty token
    if len(token) < 10:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )


def get_request_id(request: Request) -> str:
    """
    Generate or extract request ID for tracing

    Args:
        request: FastAPI request object

    Returns:
        Request ID string
    """
    # Check if request ID is provided in headers
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        return request_id

    # Generate new request ID
    import uuid
    return str(uuid.uuid4())


def get_correlation_id(
    request: Request,
    request_id: str = Depends(get_request_id)
) -> str:
    """
    Get correlation ID for request tracing

    Args:
        request: FastAPI request object
        request_id: Request ID

    Returns:
        Correlation ID
    """
    # Use X-Correlation-ID header if provided
    correlation_id = request.headers.get("X-Correlation-ID")
    if correlation_id:
        return correlation_id

    # Fall back to request ID
    return request_id
