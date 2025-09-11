"""
API Middleware Configuration
Sets up CORS, security, logging, and other middleware for the unified API
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging API requests and responses
    Provides detailed request/response logging for monitoring and debugging
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request details and response time

        Args:
            request: FastAPI request object
            call_next: Next middleware/request handler

        Returns:
            Response object
        """
        start_time = time.time()

        # Log request
        logger.info(
            f"📨 {request.method} {request.url.path} "
            f"- Client: {request.client.host if request.client else 'unknown'} "
            f"- User-Agent: {request.headers.get('user-agent', 'unknown')}"
        )

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response
        logger.info(
            f"📤 {request.method} {request.url.path} "
            f"- Status: {response.status_code} "
            f"- Time: {process_time:.3f}s "
            f"- Size: {response.headers.get('content-length', 'unknown')}"
        )

        # Add processing time to response headers
        response.headers["X-Process-Time"] = str(process_time)

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to all responses
    Implements security best practices for API responses
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response

        Args:
            request: FastAPI request object
            call_next: Next middleware/request handler

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # API-specific headers
        response.headers["X-API-Version"] = "2.0.0"

        return response


def setup_middleware(app):
    """
    Setup all middleware for the FastAPI application

    Args:
        app: FastAPI application instance
    """
    # CORS middleware - allow frontend applications
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8080", "*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware - security for production
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure specific hosts for production
    )

    # Request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    logger.info("✅ API Middleware configured")


def setup_cors_for_development(app):
    """
    Setup CORS specifically for development environment
    More permissive settings for local development

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins in development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info("✅ Development CORS configured (allow all origins)")


def setup_cors_for_production(app, allowed_origins: list[str]):
    """
    Setup CORS specifically for production environment
    Restrictive settings for security

    Args:
        app: FastAPI application instance
        allowed_origins: List of allowed origin URLs
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    logger.info(f"✅ Production CORS configured for origins: {allowed_origins}")
