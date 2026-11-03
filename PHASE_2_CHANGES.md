# Phase 2 - Tier 1 Changes Summary

## Overview
Phase 2 Tier 1 focused on production-readiness with three major features:
1. **Circuit Breaker** - Resilience and fault tolerance
2. **Input Validators** - Comprehensive parameter validation  
3. **Rate Limiter** - Token bucket rate limiting

## New Modules

### 1. `src/circuit_breaker.py`
- Implements CircuitBreaker pattern with exponential backoff
- States: CLOSED (normal), OPEN (failing), HALF_OPEN (recovery)
- Configuration: failure_threshold (5), recovery_timeout (60s), backoff_multiplier (100ms)
- Wrapped around all OANDA API calls

### 2. `validators.py`
- Validates all user input before API calls
- Returns HTTP 422 for invalid parameters
- Validators include:
  - `validate_instrument_name()` - checks instrument format
  - `validate_candle_params()` - granularity, count, times
  - `validate_order_params()` - instrument, units, price
  - `validate_price_range()` - validates price values
  - `validate_rfc3339_datetime()` - RFC3339 format validation
  - `validate_time_in_force()` - FOK, IOC, GTC, GTD values

### 3. `rate_limiter.py`
- Token bucket rate limiter as @rate_limit() decorator
- Applies rate limits per endpoint:
  - Account endpoints: 50 req/min
  - Order endpoints: 100 req/min
  - Trade endpoints: 100 req/min
  - Pricing endpoints: 100 req/min
  - Instrument endpoints: 50 req/min
- Response headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- Returns HTTP 429 on rate limit exceeded

## Server Changes

### Imports
```python
from src.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from rate_limiter import rate_limit
from validators import (validate_candle_params, validate_order_params, ...)
```

### New Global Objects
```python
circuit_breaker = CircuitBreaker(
    failure_threshold=CIRCUIT_BREAKER_THRESHOLD,
    recovery_timeout=CIRCUIT_BREAKER_TIMEOUT,
    backoff_multiplier=CIRCUIT_BREAKER_BACKOFF_MULTIPLIER
)
```

### New Endpoints
1. **GET /metrics** - Circuit breaker metrics and server statistics
   - Returns circuit breaker state, failure counts, recovery stats
   
### Modified Endpoints

#### GET / (root)
**Before:** `"status": "ok"`  
**After:** `"status": "healthy"`

#### GET /health
**Before:**
```json
{
  "status": "healthy" or "unhealthy",
  "oanda_connection": "ok",
  "db_connection": "ok" or "unavailable",
  "environment": "practice",
  "mode": "PRACTICE"
}
```

**After:**
```json
{
  "status": "healthy" or "unhealthy",
  "oanda_connection": "ok",
  "db_connection": "ok" or "unavailable",
  "environment": "practice",
  "mode": "PRACTICE",
  "circuit_breaker_state": "CLOSED" or "OPEN" or "HALF_OPEN"
}
```

### All Endpoint Decorators
Every endpoint now has:
- `@rate_limit(limit)` - Applies rate limiting
- `await circuit_breaker.call(oanda_client.request, endpoint)` - Wraps API calls
- Input validation with error handling

**Example:**
```python
@app.get("/account")
@rate_limit(50)  # <-- NEW
async def get_account_info():
    try:
        r = accounts.AccountDetails(accountID=OANDA_ACCOUNT_ID)
        await circuit_breaker.call(oanda_client.request, r)  # <-- NEW
        return r.response
    except CircuitBreakerOpenError as e:  # <-- NEW
        raise HTTPException(status_code=503, detail={"errorMessage": str(e)})
    ...
```

### Validation Examples

#### Order Placement
```python
@app.post("/order/market")
@rate_limit(100)
async def place_market_order(order_request: MarketOrderRequest, request: Request):
    # Validation happens inside _place_order()
    try:
        validate_order_params(req["instrument"], req["units"], req.get("price"))
        validate_price_range(req["stop_loss"], min_val=0)
        validate_price_range(req["take_profit"], min_val=0)
    except ValueError as e:
        raise handle_validation_error(str(e))  # HTTP 422
```

#### Candle Retrieval
```python
@app.get("/instruments/{instrument}/candles")
@rate_limit(50)
async def get_candles(instrument: str, ...):
    try:
        validate_instrument_name(instrument)
        validate_candle_params(granularity, count, from_time, to_time)
        validate_price_component(price)
    except ValueError as e:
        raise handle_validation_error(str(e))  # HTTP 422
```

## Error Handling Changes

### Validation Error Format (HTTP 422)
```python
def handle_validation_error(error_msg: str, field: str = None, value: str = None):
    detail = {
        "errorCode": "INVALID_PARAMETER",
        "errorMessage": error_msg,
    }
    if field or value:
        detail["details"] = {}
        if field:
            detail["details"]["field"] = field
        if value is not None:
            detail["details"]["value"] = value
    return HTTPException(status_code=422, detail=detail)
```

### Circuit Breaker Open Error (HTTP 503)
```python
except CircuitBreakerOpenError as e:
    raise HTTPException(status_code=503, detail={"errorMessage": str(e)})
```

### Rate Limit Error (HTTP 429)
Response headers:
- `X-RateLimit-Limit: 50`
- `X-RateLimit-Remaining: 45`
- `X-RateLimit-Reset: 1699564800`
- `Retry-After: 60` (on 429 response)

## Response Format Changes

### Rate Limiting Headers
All responses now include:
- `X-RateLimit-Limit` - Total requests allowed in window
- `X-RateLimit-Remaining` - Requests remaining
- `X-RateLimit-Reset` - Unix timestamp when limit resets

## Configuration Variables

New environment variables:
```bash
CIRCUIT_BREAKER_THRESHOLD=5           # Failures before opening
CIRCUIT_BREAKER_TIMEOUT=60            # Seconds to stay open
CIRCUIT_BREAKER_BACKOFF_MULTIPLIER=100  # ms backoff increment
```

## Test Expectations

### Health Endpoints
- `/` returns `"status": "healthy"` (not "ok")
- `/health` includes `"circuit_breaker_state"` field
- Both endpoints should return 200 OK

### Validation
- Invalid instruments return 422 with INVALID_PARAMETER
- Missing required fields return 422
- Invalid prices return 422
- Invalid datetime formats return 422

### Rate Limiting
- Responses include rate limit headers
- 429 returned on rate limit exceeded
- Tests should not exceed rate limits within test window

### Circuit Breaker
- Endpoints return 503 when circuit is OPEN
- OANDA connection failures increment failure count
- After recovery_timeout, circuit goes to HALF_OPEN

## Phase 2 Test Stats
- **Phase 1 Tests**: 137 tests (now updated for Phase 2)
- **Phase 2 Tests**: 146 tests (new, already passing)
- **Total**: 284 tests
- **Target**: All 284 tests passing

## Breaking Changes from Phase 1
1. `/` endpoint returns `"status": "healthy"` instead of `"ok"`
2. `/health` endpoint now required `circuit_breaker_state` field
3. All endpoints now subject to rate limiting
4. Invalid input returns 422 instead of silently failing or returning 400
5. Circuit breaker may return 503 on API failures

## Non-Breaking Additions
- `GET /metrics` - New endpoint
- Rate limit headers in all responses
- Circuit breaker state tracking
- Input validation (only affects invalid inputs)
