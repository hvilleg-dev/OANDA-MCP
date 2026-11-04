"""Tests for the synchronous CircuitBreaker (circuit_breaker.py at project root).

This is the circuit breaker used by server.py to wrap oandapyV20 API calls.
"""

import time
import threading
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from circuit_breaker import CircuitBreaker, CircuitBreakerOpenError


# ── helpers ───────────────────────────────────────────────────────────────────

def _success():
    return "ok"

def _fail():
    raise ValueError("simulated failure")


# ── initial state ─────────────────────────────────────────────────────────────

def test_initial_state():
    cb = CircuitBreaker(threshold=3, cooldown=60)
    s = cb.get_status()
    assert s["state"] == "CLOSED"
    assert s["failures"] == 0
    assert s["total_calls"] == 0
    assert s["total_success"] == 0
    assert s["total_failures"] == 0


# ── successful call ───────────────────────────────────────────────────────────

def test_successful_call_passes_through():
    cb = CircuitBreaker(threshold=3, cooldown=60)
    result = cb.call(_success)
    assert result == "ok"
    s = cb.get_status()
    assert s["state"] == "CLOSED"
    assert s["total_success"] == 1
    assert s["failures"] == 0


def test_successful_call_with_args():
    cb = CircuitBreaker()

    def add(a, b):
        return a + b

    assert cb.call(add, 2, 3) == 5


# ── failure counting ──────────────────────────────────────────────────────────

def test_failures_below_threshold_stay_closed():
    cb = CircuitBreaker(threshold=3, cooldown=60)
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(_fail)
    assert cb.get_status()["state"] == "CLOSED"
    assert cb.get_status()["failures"] == 2


def test_threshold_reached_opens_circuit():
    cb = CircuitBreaker(threshold=3, cooldown=60)
    for _ in range(3):
        with pytest.raises(ValueError):
            cb.call(_fail)
    assert cb.get_status()["state"] == "OPEN"


# ── OPEN state blocks calls ───────────────────────────────────────────────────

def test_open_state_raises_circuit_breaker_open_error():
    cb = CircuitBreaker(threshold=1, cooldown=60)
    with pytest.raises(ValueError):
        cb.call(_fail)
    with pytest.raises(CircuitBreakerOpenError) as exc_info:
        cb.call(_success)
    assert exc_info.value.cooldown_remaining > 0


def test_open_state_does_not_execute_function():
    cb = CircuitBreaker(threshold=1, cooldown=60)
    call_count = [0]

    def tracked():
        call_count[0] += 1
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        cb.call(tracked)

    assert call_count[0] == 1
    with pytest.raises(CircuitBreakerOpenError):
        cb.call(tracked)
    assert call_count[0] == 1  # not called again


# ── HALF_OPEN probe ───────────────────────────────────────────────────────────

def test_cooldown_expired_transitions_to_half_open():
    cb = CircuitBreaker(threshold=1, cooldown=1)
    with pytest.raises(ValueError):
        cb.call(_fail)
    assert cb.get_status()["state"] == "OPEN"
    time.sleep(1.1)
    # Next call probes
    result = cb.call(_success)
    assert result == "ok"
    assert cb.get_status()["state"] == "CLOSED"


def test_half_open_failure_reopens():
    cb = CircuitBreaker(threshold=1, cooldown=1)
    with pytest.raises(ValueError):
        cb.call(_fail)
    time.sleep(1.1)
    with pytest.raises(ValueError):
        cb.call(_fail)
    assert cb.get_status()["state"] == "OPEN"


def test_half_open_only_one_probe_at_a_time():
    """While a probe is in flight, further calls get CircuitBreakerOpenError."""
    cb = CircuitBreaker(threshold=1, cooldown=1)
    with pytest.raises(ValueError):
        cb.call(_fail)
    time.sleep(1.1)
    # Manually set probe_in_flight to simulate concurrent probe
    with cb._lock:
        cb._probe_in_flight = True
        cb._state = "OPEN"
        cb._opened_at = time.time() - 2  # cooldown already elapsed
    with pytest.raises(CircuitBreakerOpenError):
        cb.call(_success)


# ── state transitions log ─────────────────────────────────────────────────────

def test_state_events_recorded():
    cb = CircuitBreaker(threshold=1, cooldown=1)
    with pytest.raises(ValueError):
        cb.call(_fail)
    time.sleep(1.1)
    cb.call(_success)
    events = cb.get_status()["recent_events"]
    states = [(e["from"], e["to"]) for e in events]
    assert ("CLOSED", "OPEN") in states
    assert ("HALF_OPEN", "CLOSED") in states


# ── metrics ───────────────────────────────────────────────────────────────────

def test_metrics_totals():
    cb = CircuitBreaker(threshold=10, cooldown=60)
    for _ in range(3):
        cb.call(_success)
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(_fail)
    s = cb.get_status()
    assert s["total_calls"] == 5
    assert s["total_success"] == 3
    assert s["total_failures"] == 2
    assert s["failures"] == 2


def test_get_status_contains_required_keys():
    cb = CircuitBreaker()
    s = cb.get_status()
    for key in ["state", "failures", "total_failures", "total_calls", "total_success",
                "cooldown_remaining_s", "last_failure_at", "uptime_s",
                "threshold", "cooldown_s", "recent_events"]:
        assert key in s, f"Missing key: {key}"


def test_cooldown_remaining_zero_when_closed():
    cb = CircuitBreaker()
    assert cb.get_status()["cooldown_remaining_s"] == 0.0


def test_cooldown_remaining_positive_when_open():
    cb = CircuitBreaker(threshold=1, cooldown=60)
    with pytest.raises(ValueError):
        cb.call(_fail)
    assert cb.get_status()["cooldown_remaining_s"] > 0


# ── consecutive failure reset ─────────────────────────────────────────────────

def test_success_resets_consecutive_failures():
    cb = CircuitBreaker(threshold=5, cooldown=60)
    for _ in range(3):
        with pytest.raises(ValueError):
            cb.call(_fail)
    assert cb.get_status()["failures"] == 3
    cb.call(_success)
    assert cb.get_status()["failures"] == 0


# ── thread safety ─────────────────────────────────────────────────────────────

def test_thread_safe_concurrent_calls():
    cb = CircuitBreaker(threshold=100, cooldown=60)
    results = []
    errors = []

    def work():
        try:
            r = cb.call(_success)
            results.append(r)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=work) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 50
    assert len(errors) == 0
    assert cb.get_status()["state"] == "CLOSED"


def test_thread_safe_concurrent_failures():
    cb = CircuitBreaker(threshold=5, cooldown=60)

    def fail():
        try:
            cb.call(_fail)
        except Exception:
            pass

    threads = [threading.Thread(target=fail) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    s = cb.get_status()
    # Once OPEN (after 5 failures), remaining threads get CircuitBreakerOpenError
    # and the function is NOT called — so total_failures reflects only actual calls
    assert s["state"] == "OPEN"
    assert s["total_failures"] >= 5  # at least threshold reached
    assert s["total_failures"] <= 10  # never more than thread count
