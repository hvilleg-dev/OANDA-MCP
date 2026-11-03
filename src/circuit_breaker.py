"""Circuit Breaker with Exponential Backoff for OANDA API resilience.

Implements the circuit breaker pattern with:
- Three states: CLOSED (normal), OPEN (failing fast), HALF_OPEN (testing recovery)
- Exponential backoff: 2^n * backoff_multiplier ms, capped at 60s
- Async/await compatible using asyncio.sleep
- Thread-safe using asyncio.Lock
- Auto-recovery from HALF_OPEN → CLOSED on success
"""

import asyncio
import logging
import time
from enum import Enum
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Dict

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"           # Normal operation, allow requests
    OPEN = "OPEN"               # Failing, reject fast
    HALF_OPEN = "HALF_OPEN"     # Testing recovery


class CircuitBreakerOpenError(Exception):
    """Raised when circuit is OPEN and rejecting fast."""
    pass


class CircuitBreaker:
    """Circuit breaker with exponential backoff for async operations.

    Args:
        failure_threshold: Number of consecutive failures before OPEN. Default: 5
        recovery_timeout: Seconds in OPEN state before transitioning to HALF_OPEN. Default: 60
        backoff_multiplier: Base milliseconds for exponential backoff calculation. Default: 100
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        backoff_multiplier: int = 100
    ):
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._state_changes = 0
        self._last_state_change = datetime.now(timezone.utc)
        self._open_timestamp: Optional[float] = None
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._backoff_multiplier = backoff_multiplier
        self._current_backoff_ms = 0
        self._lock = asyncio.Lock()
        logger.info(
            f"CircuitBreaker initialized: "
            f"threshold={failure_threshold}, "
            f"timeout={recovery_timeout}s, "
            f"backoff_multiplier={backoff_multiplier}ms"
        )

    async def call(
        self,
        async_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Wrap an async function call with circuit breaker logic.

        Args:
            async_func: Async function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result from async_func if successful

        Raises:
            CircuitBreakerOpenError: If circuit is OPEN
            Any exception raised by async_func if successful call but operation fails
        """
        async with self._lock:
            await self._check_state()

            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. "
                    f"Backoff: {self._current_backoff_ms}ms"
                )

        try:
            result = await async_func(*args, **kwargs)
            async with self._lock:
                await self._on_success()
            return result
        except Exception as e:
            async with self._lock:
                await self._on_failure()
            raise

    async def _check_state(self) -> None:
        """Check if HALF_OPEN should transition back to CLOSED or OPEN to HALF_OPEN."""
        now = time.time()

        if self._state == CircuitState.OPEN:
            if self._open_timestamp and (now - self._open_timestamp) >= self._recovery_timeout:
                logger.info(
                    f"Circuit breaker transitioning: OPEN → HALF_OPEN "
                    f"(after {self._recovery_timeout}s)"
                )
                self._state = CircuitState.HALF_OPEN
                self._failure_count = 0
                self._state_changes += 1
                self._last_state_change = datetime.now(timezone.utc)

    async def _on_success(self) -> None:
        """Handle successful call: reset failure count, transition HALF_OPEN → CLOSED."""
        self._failure_count = 0
        self._success_count += 1
        self._current_backoff_ms = 0

        if self._state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker transitioning: HALF_OPEN → CLOSED (auto-recovery)")
            self._state = CircuitState.CLOSED
            self._state_changes += 1
            self._last_state_change = datetime.now(timezone.utc)

    async def _on_failure(self) -> None:
        """Handle failed call: increment failure count, check if should transition to OPEN."""
        self._failure_count += 1
        failure_count = self._failure_count

        if self._state == CircuitState.CLOSED and failure_count >= self._failure_threshold:
            logger.warning(
                f"Circuit breaker transitioning: CLOSED → OPEN "
                f"(failures: {failure_count}/{self._failure_threshold})"
            )
            self._state = CircuitState.OPEN
            self._open_timestamp = time.time()
            self._state_changes += 1
            self._last_state_change = datetime.now(timezone.utc)
            self._failure_count = 0
        elif self._state == CircuitState.HALF_OPEN:
            # HALF_OPEN → OPEN on any failure (recovery attempt failed)
            logger.warning(
                f"Circuit breaker transitioning: HALF_OPEN → OPEN "
                f"(recovery attempt failed)"
            )
            self._state = CircuitState.OPEN
            self._open_timestamp = time.time()
            self._state_changes += 1
            self._last_state_change = datetime.now(timezone.utc)
            self._failure_count = 0

        # Calculate exponential backoff: 2^n * multiplier, capped at 60s
        if self._state == CircuitState.OPEN:
            exponent = min(failure_count, 10)  # Prevent overflow: 2^10 = 1024
            backoff_ms = min((2 ** exponent) * self._backoff_multiplier, 60_000)
            self._current_backoff_ms = backoff_ms
            logger.debug(f"Exponential backoff: {backoff_ms}ms (attempt {exponent})")

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._open_timestamp = None
        self._current_backoff_ms = 0
        logger.info("Circuit breaker manually reset to CLOSED")

    def get_state(self) -> CircuitState:
        """Return the current circuit breaker state."""
        return self._state

    def get_metrics(self) -> Dict[str, Any]:
        """Return circuit breaker metrics as a dictionary.

        Returns:
            Dict with keys:
            - state: Current state (CLOSED, OPEN, HALF_OPEN)
            - failure_count: Current failure count (resets in HALF_OPEN or CLOSED)
            - success_count: Total successful calls since last state change
            - state_changes: Total number of state transitions
            - last_state_change: ISO 8601 timestamp of last state change
            - current_backoff_ms: Current exponential backoff in milliseconds
            - backoff_multiplier: Base multiplier for backoff calculation
            - failure_threshold: Number of failures before OPEN
            - recovery_timeout_s: Seconds before OPEN → HALF_OPEN transition
        """
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "state_changes": self._state_changes,
            "last_state_change": self._last_state_change.isoformat(),
            "current_backoff_ms": self._current_backoff_ms,
            "backoff_multiplier": self._backoff_multiplier,
            "failure_threshold": self._failure_threshold,
            "recovery_timeout_s": self._recovery_timeout,
        }
