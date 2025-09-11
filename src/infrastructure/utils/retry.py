"""
Retry utility with configurable tenacity decorators using ConfigManager.
Provides retry logic for transient errors in infrastructure components.
"""

from functools import wraps
from typing import Callable, Any, Optional
from datetime import datetime
import logging

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_log
from tenacity.wait import wait_exponential

from src.domain.exceptions import (
    DatabaseConnectionError, 
    BrokerAPIError, 
    TradingError
)
from src.infrastructure.config.config_manager import ConfigManager


logger = logging.getLogger(__name__)


def get_retry_config(config_manager: Optional[ConfigManager], section: str = "retry") -> dict:
    """
    Get retry configuration from ConfigManager or use defaults.
    
    Args:
        config_manager: ConfigManager instance
        section: Configuration section for retry settings
        
    Returns:
        Dictionary with retry parameters
    """
    if not config_manager:
        # Default configuration
        return {
            "max_retries": 3,
            "initial_backoff": 1.0,
            "max_backoff": 10.0,
            "backoff_multiplier": 2.0,
            "retry_on_exceptions": [DatabaseConnectionError, BrokerAPIError]
        }
    
    try:
        retry_config = config_manager.get_config(section) or {}
        
        # Specific retry settings for scanners if available
        if "scanners" in config_manager.get_config():
            scanners_retry = config_manager.get_value("scanners.retry", {})
            retry_config.update(scanners_retry)
        
        # Validate and set defaults
        config = {
            "max_retries": retry_config.get("max_retries", 3),
            "initial_backoff": retry_config.get("initial_backoff", 1.0),
            "max_backoff": retry_config.get("max_backoff", 10.0),
            "backoff_multiplier": retry_config.get("backoff_multiplier", 2.0),
            "retry_on_exceptions": [
                DatabaseConnectionError, 
                BrokerAPIError
            ]
        }
        
        # Add specific exceptions from config if provided
        if "retry_exceptions" in retry_config:
            exception_classes = []
            for exc_name in retry_config["retry_exceptions"]:
                try:
                    # Import and add exception class
                    if exc_name == "DatabaseConnectionError":
                        exception_classes.append(DatabaseConnectionError)
                    elif exc_name == "BrokerAPIError":
                        exception_classes.append(BrokerAPIError)
                    elif exc_name == "TradingError":
                        exception_classes.append(TradingError)
                    else:
                        # Assume it's a built-in exception
                        import builtins
                        if hasattr(builtins, exc_name):
                            exception_classes.append(getattr(builtins, exc_name))
                except ImportError:
                    logger.warning(f"Could not import exception {exc_name} for retry")
            
            config["retry_on_exceptions"] = exception_classes
        
        logger.debug(f"Loaded retry configuration: {config}")
        return config
        
    except Exception as e:
        logger.warning(f"Failed to load retry config, using defaults: {e}")
        return {
            "max_retries": 3,
            "initial_backoff": 1.0,
            "max_backoff": 10.0,
            "backoff_multiplier": 2.0,
            "retry_on_exceptions": [DatabaseConnectionError, BrokerAPIError]
        }


def retry_on_transient_errors(
    config_manager: Optional[ConfigManager] = None,
    max_retries: Optional[int] = None,
    wait: Optional[Callable] = None,
    retry_exceptions: Optional[list] = None,
    before_retry: Optional[Callable] = None,
    log_level: int = logging.INFO
) -> Callable:
    """
    Decorator factory for retrying on transient errors.
    
    Args:
        config_manager: ConfigManager for retry settings
        max_retries: Maximum retry attempts (overrides config)
        wait: Wait strategy (overrides config)
        retry_exceptions: Specific exceptions to retry on (overrides config)
        before_retry: Callback before each retry
        log_level: Log level for retry logging
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        # Get retry configuration
        retry_config = get_retry_config(config_manager)
        
        # Override with decorator parameters if provided
        if max_retries is not None:
            retry_config["max_retries"] = max_retries
        if retry_exceptions is not None:
            retry_config["retry_on_exceptions"] = retry_exceptions
        
        # Create tenacity retry configuration
        tenacity_retry = retry(
            stop=stop_after_attempt(retry_config["max_retries"]),
            wait=wait_exponential(
                min=retry_config["initial_backoff"],
                max=retry_config["max_backoff"],
                multiplier=retry_config["backoff_multiplier"]
            ),
            retry=retry_if_exception_type(tuple(retry_config["retry_on_exceptions"])),
            before=before_log(logger, log_level),
            reraise=True
        )
        
        @wraps(func)
        @tenacity_retry
        def wrapper(*args, **kwargs):
            print(f"DEBUG RETRY WRAPPER: func={func.__name__}, args_count={len(args)}, first_arg_type={type(args[0]) if args else None}")
            if args:
                print(f"DEBUG RETRY WRAPPER: first_arg={args[0] if len(args) > 0 else 'None'}")
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def retry_db_operation(config_manager: Optional[ConfigManager] = None, **kwargs) -> Callable:
    """
    Specialized retry decorator for database operations.
    
    Args:
        config_manager: ConfigManager for retry settings
        **kwargs: Additional retry parameters (max_retries, etc.)
        
    Returns:
        Decorator for DB operations
    """
    retry_config = get_retry_config(config_manager, "database.retry")
    retry_config["retry_on_exceptions"] = [DatabaseConnectionError]
    retry_config.update(kwargs)
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            print(f"DEBUG RETRY_DB DECORATOR APPLIED: {func.__name__} called with {len(args)} args")
            # Create tenacity retry configuration inside wrapper to ensure it's fresh
            tenacity_retry = retry(
                stop=stop_after_attempt(retry_config["max_retries"]),
                wait=wait_exponential(
                    min=retry_config["initial_backoff"],
                    max=retry_config["max_backoff"],
                    multiplier=retry_config["backoff_multiplier"]
                ),
                retry=retry_if_exception_type(DatabaseConnectionError),
                before=before_log(logger, logging.INFO),
                reraise=True
            )
            
            @wraps(func)
            def inner_wrapper(*inner_args, **inner_kwargs):
                print(f"DEBUG RETRY_DB INNER: func={func.__name__}, args_count={len(inner_args)}")
                return func(*inner_args, **inner_kwargs)
            
            return tenacity_retry(inner_wrapper)(*args, **kwargs)
        
        return wrapper
    
    return decorator


def retry_api_call(config_manager: Optional[ConfigManager] = None) -> Callable:
    """
    Specialized retry decorator for API calls.
    
    Args:
        config_manager: ConfigManager for retry settings
        
    Returns:
        Decorator for API operations
    """
    retry_config = get_retry_config(config_manager, "api.retry")
    retry_config["retry_on_exceptions"] = [BrokerAPIError]
    
    def decorator(func: Callable) -> Callable:
        tenacity_retry = retry(
            stop=stop_after_attempt(retry_config["max_retries"]),
            wait=wait_exponential(
                min=retry_config["initial_backoff"],
                max=retry_config["max_backoff"],
                multiplier=retry_config["backoff_multiplier"]
            ),
            retry=retry_if_exception_type(BrokerAPIError),
            before=before_log(logger, logging.INFO),
            reraise=True
        )
        
        @wraps(func)
        @tenacity_retry
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# Example usage:
# @retry_on_transient_errors(config_manager)
# def connect_to_database():
#     # Database connection logic
#     pass
#
# @retry_db_operation(config_manager)
# def execute_query(query):
#     # Query execution logic
#     pass