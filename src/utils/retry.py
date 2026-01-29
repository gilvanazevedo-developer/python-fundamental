"""
Retry Utility Module
Provides retry decorator with exponential backoff for handling transient failures.
"""

import time
import functools
import logging
from typing import Tuple, Type, Callable, Optional, Any

from src.logger import get_logger

logger = get_logger(__name__)


class RetryError(Exception):
    """Exception raised when all retry attempts have been exhausted."""

    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 1.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        exceptions: Tuple of exception types to retry on (default: all exceptions)
        on_retry: Optional callback function called on each retry with (exception, attempt_number)

    Returns:
        Decorated function with retry logic

    Example:
        @retry(max_attempts=3, exceptions=(requests.RequestException,))
        def fetch_data(url):
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            func_name = func.__name__

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func_name}: All {max_attempts} attempts failed. "
                            f"Last error: {e}"
                        )
                        raise RetryError(
                            f"Failed after {max_attempts} attempts: {e}",
                            last_exception=e
                        )

                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )

                    logger.warning(
                        f"{func_name}: Attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    # Call optional retry callback
                    if on_retry:
                        on_retry(e, attempt)

                    time.sleep(delay)

            # This should never be reached, but just in case
            raise RetryError(
                f"Unexpected error in retry logic for {func_name}",
                last_exception=last_exception
            )

        return wrapper
    return decorator


def retry_with_fallback(
    fallback_value: Any,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_fallback: bool = True
):
    """
    Retry decorator that returns a fallback value on complete failure.

    Args:
        fallback_value: Value to return if all retries fail
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries
        exceptions: Exception types to retry on
        log_fallback: Whether to log when fallback is used

    Returns:
        Decorated function with retry logic and fallback

    Example:
        @retry_with_fallback(fallback_value=[], max_attempts=3)
        def fetch_items():
            return api.get_items()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            func_name = func.__name__

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        if log_fallback:
                            logger.warning(
                                f"{func_name}: All attempts failed. "
                                f"Using fallback value. Last error: {e}"
                            )
                        return fallback_value

                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        f"{func_name}: Attempt {attempt}/{max_attempts} failed. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)

            return fallback_value

        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascade failures by failing fast when a service is down.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before circuit opens
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exceptions: Exception types that count as failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed, open, half-open

    @property
    def state(self) -> str:
        """Get current circuit state."""
        if self._state == "open":
            # Check if we should try recovery
            if self._last_failure_time is not None:
                time_since_failure = time.time() - self._last_failure_time
                if time_since_failure >= self.recovery_timeout:
                    self._state = "half-open"
        return self._state

    def __call__(self, func: Callable) -> Callable:
        """Decorate a function with circuit breaker logic."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            func_name = func.__name__

            # Check circuit state
            if self.state == "open":
                logger.warning(
                    f"Circuit breaker open for {func_name}. "
                    f"Failing fast."
                )
                raise RetryError(
                    f"Circuit breaker is open for {func_name}"
                )

            try:
                result = func(*args, **kwargs)

                # Success - reset if in half-open state
                if self._state == "half-open":
                    logger.info(
                        f"Circuit breaker recovered for {func_name}"
                    )
                    self._reset()

                return result

            except self.expected_exceptions as e:
                self._record_failure()
                logger.error(
                    f"Circuit breaker failure for {func_name}: {e}. "
                    f"Failures: {self._failure_count}/{self.failure_threshold}"
                )
                raise

        return wrapper

    def _record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(
                f"Circuit breaker opened after {self._failure_count} failures"
            )

    def _reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._failure_count = 0
        self._last_failure_time = None
        self._state = "closed"

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._reset()
