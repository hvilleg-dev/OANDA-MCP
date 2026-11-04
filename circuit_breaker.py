"""
Synchronous Circuit Breaker for OANDA MCP Server.

CLOSED → OPEN → HALF_OPEN → CLOSED pattern for the synchronous oandapyV20 client.
Complements TokenBucketLimiter (rate_limiter.py): rate limiter controls frequency,
circuit breaker controls failure response (429s, 5xx, timeouts).
"""

import time
import threading
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """Raised when a call is blocked because the circuit breaker is OPEN."""

    def __init__(self, cooldown_remaining: float):
        self.cooldown_remaining = round(cooldown_remaining, 1)
        super().__init__(
            f"Circuit breaker OPEN — retry in {self.cooldown_remaining}s."
        )


class CircuitBreaker:
    """
    Thread-safe synchronous circuit breaker.

    States:
      CLOSED    — normal, failures counted toward threshold
      OPEN      — calls blocked, cooldown ticking
      HALF_OPEN — one probe allowed to test recovery

    Usage:
        cb = CircuitBreaker(threshold=5, cooldown=60)
        cb.call(oanda_client.request, endpoint_object)
    """

    def __init__(self, threshold: int = 5, cooldown: int = 60):
        self.threshold = threshold
        self.cooldown = cooldown

        self._state = "CLOSED"
        self._failures = 0
        self._total_failures = 0
        self._total_calls = 0
        self._total_success = 0
        self._opened_at: float = 0.0
        self._last_failure_at: Optional[float] = None
        self._probe_in_flight = False
        self._events: List[Dict] = []
        self._start_time = time.time()
        self._lock = threading.Lock()

    # ── public API ────────────────────────────────────────────────────────

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute func(*args, **kwargs) through the circuit breaker.

        Raises CircuitBreakerOpenError if OPEN and cooldown has not elapsed.
        Re-raises any exception from func after registering the failure.
        """
        with self._lock:
            self._total_calls += 1
            if self._state == "OPEN":
                elapsed = time.time() - self._opened_at
                remaining = self.cooldown - elapsed
                if remaining > 0:
                    raise CircuitBreakerOpenError(remaining)
                if not self._probe_in_flight:
                    self._probe_in_flight = True
                    self._do_transition("HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(0)

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except CircuitBreakerOpenError:
            raise
        except Exception as exc:
            self._on_failure(exc)
            raise

    def get_status(self) -> Dict[str, Any]:
        """Returns a snapshot dict for /health and /metrics."""
        with self._lock:
            now = time.time()
            remaining = 0.0
            if self._state == "OPEN":
                remaining = max(0.0, self.cooldown - (now - self._opened_at))
            return {
                "state": self._state,
                "failures": self._failures,
                "total_failures": self._total_failures,
                "total_calls": self._total_calls,
                "total_success": self._total_success,
                "cooldown_remaining_s": round(remaining, 1),
                "last_failure_at": self._last_failure_at,
                "uptime_s": round(now - self._start_time, 1),
                "threshold": self.threshold,
                "cooldown_s": self.cooldown,
                "recent_events": list(self._events[-10:]),
            }

    # ── internal ──────────────────────────────────────────────────────────

    def _on_success(self):
        with self._lock:
            self._total_success += 1
            prev = self._state
            self._failures = 0
            self._probe_in_flight = False
            if prev == "HALF_OPEN":
                self._do_transition("CLOSED")

    def _on_failure(self, exc: Exception):
        with self._lock:
            self._failures += 1
            self._total_failures += 1
            self._last_failure_at = time.time()
            if self._state == "HALF_OPEN":
                self._probe_in_flight = False
                self._opened_at = time.time()
                self._do_transition("OPEN")
            elif self._state == "CLOSED" and self._failures >= self.threshold:
                self._opened_at = time.time()
                self._do_transition("OPEN")

    def _do_transition(self, new_state: str):
        """Must be called with self._lock held."""
        old = self._state
        self._state = new_state
        self._events.append({
            "ts": time.time(),
            "from": old,
            "to": new_state,
            "failures": self._failures,
        })
        if len(self._events) > 20:
            self._events.pop(0)
        level = logging.WARNING if new_state == "OPEN" else logging.INFO
        logger.log(level, "Circuit breaker: %s → %s (failures=%d)", old, new_state, self._failures)
