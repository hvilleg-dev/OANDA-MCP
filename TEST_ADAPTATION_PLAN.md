# TEST ADAPTATION PLAN — Phase 1 → Phase 2 Integration

**Date:** November 3, 2026 (Day 9-10)  
**Agent:** Test Adapter (a97a98cea916b34a2)  
**Goal:** All 284 tests passing (137 Phase 1 + 146 Phase 2)

---

## Problem Statement

Phase 2 implementations added 3 new modules to server.py:
- Circuit Breaker (wrapped 35 OANDA calls)
- Validators (added HTTP 422 validation)
- Rate Limiter (added X-RateLimit-* headers)

Phase 1 tests (137) were written expecting old response format:
- /health returned `{"status": "ok"}`
- No rate limit headers
- No validators

**Result:** 118 Phase 1 tests failing, 163 passing

---

## Changes Made to server.py

### By Circuit Breaker Agent (a7b6d7a)
```python
# New imports
from src.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

# New endpoint
GET /metrics
  └─ Returns circuit breaker state + metrics

# Enhanced endpoint
GET /health
  └─ Old: {"status": "ok"}
  └─ New: {"status": "healthy", "circuit_breaker_state": "CLOSED", ...}

# Wrapped calls
All OANDA API calls now wrapped with circuit_breaker.call()
```

### By Validator Agent (3336d04)
```python
# New imports
from validators import validate_candle_params, validate_order_params, ...

# Validation logic added to endpoints
- GET /instruments/{instrument}/candles → validate_candle_params()
- POST /order/* → validate_order_params()
- GET /pricing → validate_instrument_name()
- PATCH /trade/{id} → validate_trade_params()

# New response on validation error
HTTP 422: {"errorCode": "INVALID_PARAMETER", "errorMessage": "...", "details": {...}}
```

### By Rate Limiter Agent (8ca3127)
```python
# New imports
from rate_limiter import TokenBucketLimiter, rate_limit

# Decorators added
@app.get("/orders")
@rate_limit(rate_per_minute=100)
async def get_orders():
    ...

# Response headers added (all responses)
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1728403200

# On limit exceeded
HTTP 429: {"errorCode": "RATE_LIMIT_EXCEEDED", "errorMessage": "...", "retryAfter": X}
```

---

## Test Failures Analysis

### Type 1: Response Format Changes (test_health.py)
**Root Cause:** /health endpoint changed response format  
**Example:**
```python
# Test expects:
assert response.json()["status"] == "ok"

# But gets:
{"status": "healthy", "circuit_breaker_state": "CLOSED"}
```

**Fix:** Update assertions to accept new format
```python
assert response.json()["status"] == "healthy"
assert "circuit_breaker_state" in response.json()
```

### Type 2: PluggyTeardownRaisedWarning (most tests)
**Root Cause:** FastAPI TestClient fixture not properly cleaned up  
**Likely Issue:** Circuit breaker async locks not released between tests  
**Example:**
```
pluggy.PluggyTeardownRaisedWarning: A plugin raised an exception 
during an old-style hookwrapper teardown.
```

**Fix:** Ensure TestClient is properly scoped, maybe reset circuit breaker between tests

### Type 3: Rate Limit Headers (integration tests)
**Root Cause:** Tests don't account for new X-RateLimit-* headers  
**Fix:** Update tests to ignore or verify these headers

---

## Adaptation Strategy

### Phase 1: Quick Wins (High Priority)
1. **Fix test_health.py** — Update assertions for new /health format
2. **Add /metrics test** — Verify new metrics endpoint works
3. **Verify rate limit headers** — Tests should pass even with new headers

### Phase 2: Core Tests (Medium Priority)
1. **test_account.py** — Verify all account endpoints work
2. **test_orders.py** — Verify order endpoints with validators
3. **test_trades.py** — Verify trade endpoints
4. **test_instruments.py** — Verify instrument endpoints with validators
5. **test_pricing.py** — Verify pricing endpoints

### Phase 3: Support Tests (Lower Priority)
1. **test_database.py** — Should be unaffected
2. **test_transactions.py** — Should be unaffected
3. **test_mcp_tools.py** — Should be unaffected

---

## Specific Test Updates Needed

### test_health.py
```python
def test_root_endpoint_returns_ok(client):
    response = client.get("/")
    # OLD: assert response.json()["status"] == "ok"
    # NEW:
    assert response.json()["status"] == "healthy"

def test_health_endpoint_returns_ok(client):
    response = client.get("/health")
    # OLD: assert response.json()["status"] == "ok"
    # NEW:
    assert response.json()["status"] == "healthy"
    assert "circuit_breaker_state" in response.json()

def test_health_endpoint_response_format(client):
    response = client.get("/health")
    data = response.json()
    # NEW: verify circuit_breaker_state exists
    assert "circuit_breaker_state" in data
    assert data["circuit_breaker_state"] in ["CLOSED", "OPEN", "HALF_OPEN"]
```

### All Endpoint Tests
```python
def test_get_orders_success(client):
    response = client.get("/orders")
    assert response.status_code == 200
    # Rate limiter adds headers, but shouldn't break test:
    # (headers are not validated by test, just present)
```

---

## Success Criteria

✅ All 284 tests passing (137 Phase 1 + 146 Phase 2)  
✅ No PluggyTeardownRaisedWarning  
✅ All assertions updated for new response formats  
✅ Test output clean and readable  
✅ Ready for v4.0.0 tag  

---

## Timeline

- **Day 9 (Now):** Test Adapter analyzes changes
- **Day 10:** Updates tests iteratively
- **Day 11:** Final verification and merge
- **Day 12:** Tag v4.0.0

---

**Status:** IN PROGRESS  
**Agent:** a97a98cea916b34a2  
**Last Updated:** 2026-11-03 Day 9
