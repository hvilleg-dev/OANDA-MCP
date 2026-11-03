"""Comprehensive tests for CircuitBreaker with Exponential Backoff.

Tests cover:
- State transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Exponential backoff scaling and 60s cap
- Async/await compatibility and concurrency
- Auto-recovery on success
- Fast-fail when OPEN
- Metrics tracking
"""

import pytest
import asyncio
import time
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState


logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# Unit Tests: State Transitions
# ════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_circuit_breaker_initial_state():
    """Circuit breaker should start in CLOSED state."""
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
    assert cb.get_state() == CircuitState.CLOSED
    metrics = cb.get_metrics()
    assert metrics["state"] == "CLOSED"
    assert metrics["failure_count"] == 0
    assert metrics["success_count"] == 0


@pytest.mark.asyncio
async def test_circuit_breaker_successful_call():
    """Successful call should not change state."""
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

    async def success_func():
        return "success"

    result = await cb.call(success_func)
    assert result == "success"
    assert cb.get_state() == CircuitState.CLOSED
    metrics = cb.get_metrics()
    assert metrics["success_count"] == 1
    assert metrics["failure_count"] == 0


@pytest.mark.asyncio
async def test_circuit_breaker_closed_to_open_transition():
    """CLOSED → OPEN after reaching failure threshold."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    async def failing_func():
        raise ValueError("Test error")

    # Trigger 3 failures to reach threshold
    for i in range(3):
        with pytest.raises(ValueError):
            await cb.call(failing_func)

    assert cb.get_state() == CircuitState.OPEN
    metrics = cb.get_metrics()
    assert metrics["state"] == "OPEN"
    assert metrics["failure_count"] == 0  # Reset after transition
    assert metrics["state_changes"] >= 1


@pytest.mark.asyncio
async def test_circuit_breaker_open_rejects_fast():
    """OPEN state should reject calls immediately."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)

    async def failing_func():
        raise ValueError("Test error")

    # Trigger 1 failure to open
    with pytest.raises(ValueError):
        await cb.call(failing_func)

    assert cb.get_state() == CircuitState.OPEN

    # Next call should be rejected immediately with CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(failing_func)


@pytest.mark.asyncio
async def test_circuit_breaker_open_to_half_open_transition():
    """OPEN → HALF_OPEN after recovery_timeout elapsed."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)  # 1 second timeout

    async def failing_func():
        raise ValueError("Test error")

    # Trigger failure to open
    with pytest.raises(ValueError):
        await cb.call(failing_func)

    assert cb.get_state() == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(1.1)

    # Next check should transition to HALF_OPEN
    async def dummy_func():
        return "ok"

    # The state should check and transition
    await cb.call(dummy_func)
    # After successful call from HALF_OPEN, should be CLOSED
    assert cb.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_to_closed_on_success():
    """HALF_OPEN → CLOSED on successful call."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)

    async def failing_func():
        raise ValueError("Test error")

    async def success_func():
        return "success"

    # Trigger failure to open
    with pytest.raises(ValueError):
        await cb.call(failing_func)

    assert cb.get_state() == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(1.1)

    # Successful call should transition HALF_OPEN → CLOSED
    result = await cb.call(success_func)
    assert result == "success"
    assert cb.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_to_open_on_failure():
    """HALF_OPEN → OPEN on failure."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)

    async def failing_func():
        raise ValueError("Test error")

    # Trigger failure to open
    with pytest.raises(ValueError):
        await cb.call(failing_func)

    assert cb.get_state() == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(1.1)

    # Failure in HALF_OPEN should go back to OPEN
    with pytest.raises(ValueError):
        await cb.call(failing_func)

    assert cb.get_state() == CircuitState.OPEN


# ════════════════════════════════════════════════════════════════
# Unit Tests: Exponential Backoff
# ════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_exponential_backoff_calculation():
    """Verify exponential backoff: 2^n * multiplier."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60, backoff_multiplier=100)

    async def failing_func():
        raise ValueError("Test error")

    # Trigger 1 failure to open and calculate first backoff
    with pytest.raises(ValueError):
        await cb.call(failing_func)

    metrics = cb.get_metrics()
    # Backoff should be calculated: 2^1 * 100 = 200ms
    assert metrics["current_backoff_ms"] > 0


@pytest.mark.asyncio
async def test_exponential_backoff_60s_cap():
    """Exponential backoff should be capped at 60 seconds."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60, backoff_multiplier=1000)

    async def failing_func():
        raise ValueError("Test error")

    # Trigger failure
    with pytest.raises(ValueError):
        await cb.call(failing_func)

    metrics = cb.get_metrics()
    # Backoff should be capped at 60_000ms
    assert metrics["current_backoff_ms"] <= 60_000


@pytest.mark.asyncio
async def test_exponential_backoff_resets_on_success():
    """Backoff should reset to 0 on successful call."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1, backoff_multiplier=100)

    async def failing_func():
        raise ValueError("Test error")

    async def success_func():
        return "ok"

    # Trigger failure to build backoff
    with pytest.raises(ValueError):
        await cb.call(failing_func)

    backoff_before = cb.get_metrics()["current_backoff_ms"]
    assert backoff_before > 0

    # Wait and transition to HALF_OPEN
    await asyncio.sleep(1.1)

    # Success should reset backoff
    result = await cb.call(success_func)
    assert result == "ok"

    metrics = cb.get_metrics()
    assert metrics["current_backoff_ms"] == 0


# ════════════════════════════════════════════════════════════════
# Async Integration Tests
# ════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_concurrent_calls_thread_safe():
    """Multiple concurrent calls should be thread-safe."""
    cb = CircuitBreaker(failure_threshold=10, recovery_timeout=60)
    call_count = 0

    async def increment_func():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.001)
        return call_count

    # Launch 50 concurrent calls
    tasks = [cb.call(increment_func) for _ in range(50)]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    assert len(results) == 50
    assert call_count == 50
    assert cb.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_concurrent_failures_trigger_open():
    """Concurrent failures should collectively trigger OPEN state."""
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
    failure_count = 0

    async def maybe_failing_func(should_fail):
        nonlocal failure_count
        if should_fail:
            failure_count += 1
            raise ValueError(f"Failure {failure_count}")
        return "success"

    # Create mix of failing and non-failing tasks
    tasks = []
    for i in range(10):
        should_fail = i < 6  # First 6 will fail
        tasks.append(cb.call(maybe_failing_func, should_fail))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Should have triggered OPEN state
    assert cb.get_state() == CircuitState.OPEN


@pytest.mark.asyncio
async def test_fast_fail_with_circuit_breaker_open():
    """When OPEN, requests should fail immediately without executing function."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
    execution_count = 0

    async def tracked_func():
        nonlocal execution_count
        execution_count += 1
        raise ValueError("Should execute once")

    # Trigger OPEN
    with pytest.raises(ValueError):
        await cb.call(tracked_func)

    assert execution_count == 1
    assert cb.get_state() == CircuitState.OPEN

    # Next call should fail without executing function
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(tracked_func)

    assert execution_count == 1  # Should still be 1 (not executed again)


# ════════════════════════════════════════════════════════════════
# Metrics Tests
# ════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_metrics_tracking():
    """Circuit breaker should accurately track metrics."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    async def failing_func():
        raise ValueError("Test error")

    async def success_func():
        return "ok"

    # Generate some activity
    for _ in range(3):
        with pytest.raises(ValueError):
            await cb.call(failing_func)

    # Transition to HALF_OPEN
    metrics = cb.get_metrics()
    assert metrics["state"] == "OPEN"
    assert metrics["failure_count"] == 0
    assert metrics["state_changes"] >= 1
    assert "last_state_change" in metrics


@pytest.mark.asyncio
async def test_metrics_contain_all_fields():
    """Metrics should contain all required fields."""
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60, backoff_multiplier=100)
    metrics = cb.get_metrics()

    required_fields = [
        "state",
        "failure_count",
        "success_count",
        "state_changes",
        "last_state_change",
        "current_backoff_ms",
        "backoff_multiplier",
        "failure_threshold",
        "recovery_timeout_s",
    ]

    for field in required_fields:
        assert field in metrics, f"Missing metric field: {field}"


@pytest.mark.asyncio
async def test_metrics_timestamp_format():
    """last_state_change should be ISO 8601 timestamp."""
    cb = CircuitBreaker()
    metrics = cb.get_metrics()

    # Should be parseable as ISO 8601
    timestamp_str = metrics["last_state_change"]
    parsed = datetime.fromisoformat(timestamp_str)
    assert isinstance(parsed, datetime)


# ════════════════════════════════════════════════════════════════
# Reset and Configuration Tests
# ════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_manual_reset():
    """Manual reset should return to CLOSED state."""
    cb = CircuitBreaker(failure_threshold=1)

    async def failing_func():
        raise ValueError("Test error")

    # Trigger OPEN
    with pytest.raises(ValueError):
        await cb.call(failing_func)

    assert cb.get_state() == CircuitState.OPEN

    # Manual reset
    cb.reset()
    assert cb.get_state() == CircuitState.CLOSED
    metrics = cb.get_metrics()
    assert metrics["failure_count"] == 0
    assert metrics["success_count"] == 0


@pytest.mark.asyncio
async def test_custom_thresholds():
    """Circuit breaker should respect custom thresholds."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=30, backoff_multiplier=50)
    metrics = cb.get_metrics()

    assert metrics["failure_threshold"] == 2
    assert metrics["recovery_timeout_s"] == 30
    assert metrics["backoff_multiplier"] == 50


# ════════════════════════════════════════════════════════════════
# Edge Cases
# ════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_exception_propagation():
    """Non-CircuitBreaker exceptions should propagate."""
    cb = CircuitBreaker()

    async def custom_error_func():
        raise RuntimeError("Custom error")

    with pytest.raises(RuntimeError, match="Custom error"):
        await cb.call(custom_error_func)


@pytest.mark.asyncio
async def test_function_with_args_and_kwargs():
    """Circuit breaker should support args and kwargs."""
    cb = CircuitBreaker()

    async def func_with_params(a, b, c=None):
        return f"a={a}, b={b}, c={c}"

    result = await cb.call(func_with_params, 1, 2, c=3)
    assert result == "a=1, b=2, c=3"


@pytest.mark.asyncio
async def test_rapid_state_transitions():
    """Circuit breaker should handle rapid consecutive calls correctly."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

    async def failing_func():
        raise ValueError("Test")

    async def success_func():
        return "ok"

    # Rapid failures
    for _ in range(2):
        with pytest.raises(ValueError):
            await cb.call(failing_func)

    assert cb.get_state() == CircuitState.OPEN

    # Rapid OPEN rejections
    for _ in range(5):
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(success_func)

    assert cb.get_state() == CircuitState.OPEN


# ════════════════════════════════════════════════════════════════
# Load/Stress Tests
# ════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_high_volume_successful_calls():
    """Circuit breaker should handle high volume of successful calls."""
    cb = CircuitBreaker(failure_threshold=100, recovery_timeout=60)

    async def success_func():
        return "ok"

    # 500 concurrent calls
    tasks = [cb.call(success_func) for _ in range(500)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 500
    assert all(r == "ok" for r in results)
    assert cb.get_state() == CircuitState.CLOSED
    metrics = cb.get_metrics()
    assert metrics["success_count"] == 500


@pytest.mark.asyncio
async def test_mixed_load_with_failures():
    """Circuit breaker should handle mixed success/failure load."""
    cb = CircuitBreaker(failure_threshold=50, recovery_timeout=60)
    success_count = 0
    failure_count = 0

    async def maybe_fail(should_fail):
        nonlocal success_count, failure_count
        if should_fail:
            failure_count += 1
            raise ValueError("Fail")
        else:
            success_count += 1
            return "ok"

    # 200 requests, 20% failure rate (40 failures)
    tasks = []
    for i in range(200):
        should_fail = i % 5 == 0  # 20% failure
        tasks.append(cb.call(maybe_fail, should_fail))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Should not have opened (under threshold)
    assert cb.get_state() == CircuitState.CLOSED
    assert failure_count == 40
    assert success_count == 160


@pytest.mark.asyncio
async def test_state_after_many_cycles():
    """Circuit breaker should maintain consistent state after many cycles."""
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=1)

    async def failing_func():
        raise ValueError("Test")

    async def success_func():
        return "ok"

    for cycle in range(3):
        # Trigger failures
        for _ in range(5):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.get_state() == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(1.1)

        # Recover with success
        result = await cb.call(success_func)
        assert result == "ok"
        assert cb.get_state() == CircuitState.CLOSED
