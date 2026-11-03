# OANDA MCP Server Test Suite

Comprehensive pytest test suite for the OANDA MCP Server with 80%+ code coverage.

## Test Structure

```
tests/
├── __init__.py                 # Test package init
├── conftest.py                 # Pytest configuration and fixtures
├── test_health.py              # Health check endpoint tests (3 tests)
├── test_account.py             # Account endpoint tests (6 tests)
├── test_orders.py              # Orders endpoint tests (8 tests)
├── test_trades.py              # Trades endpoint tests (6 tests)
├── test_mcp_tools.py           # MCP tools endpoint tests (4 tests)
├── test_pricing.py             # Pricing endpoint tests (8 tests)
├── test_instruments.py         # Instruments endpoint tests (10 tests)
├── test_database.py            # Database endpoint tests (11 tests)
├── test_transactions.py        # Transactions endpoint tests (12 tests)
├── test_utils.py               # Test utilities and helpers
└── README.md                   # This file
```

## Test Files Overview

### test_health.py
- `test_root_endpoint_returns_ok()` - GET / returns OK
- `test_health_endpoint_returns_ok()` - GET /health returns OK
- `test_health_endpoints_response_format()` - Response format validation

### test_account.py
- `test_get_account_info_success()` - GET /account
- `test_get_account_summary_success()` - GET /account/summary
- `test_get_account_instruments_success()` - GET /account/instruments
- `test_get_account_changes_success()` - GET /account/changes
- `test_patch_account_configuration_success()` - PATCH /account/configuration
- Error handling and validation tests

### test_orders.py
- `test_get_orders_success()` - GET /orders
- `test_get_pending_orders_success()` - GET /orders/pending
- `test_place_market_order_success()` - POST /order/market
- `test_place_limit_order_success()` - POST /order/limit
- `test_place_stop_order_success()` - POST /order/stop
- `test_modify_order_success()` - PATCH /order/{id}
- `test_delete_order_success()` - DELETE /order/{id}
- Error handling and validation tests

### test_trades.py
- `test_get_trades_success()` - GET /trades
- `test_get_open_trades_success()` - GET /trades/open
- `test_get_trade_details_success()` - GET /trade/{id}
- `test_modify_trade_stop_loss_success()` - PATCH /trade/{id}
- `test_close_trade_full_success()` - PUT /trade/{id}/close
- Error handling and validation tests

### test_mcp_tools.py
- `test_mcp_info_returns_success()` - GET /mcp
- `test_mcp_list_tools_returns_tools()` - GET /mcp/tools
- `test_mcp_call_tool_basic()` - POST /mcp/call
- Tool validation tests

### test_pricing.py
- `test_get_current_price_success()` - GET /price/{instrument}
- `test_get_multiple_prices_success()` - GET /pricing
- Price data validation tests

### test_instruments.py
- `test_get_candles_success()` - GET /instruments/{instrument}/candles
- `test_get_orderbook_success()` - GET /instruments/{instrument}/orderbook
- `test_get_positionbook_success()` - GET /instruments/{instrument}/positionbook
- `test_get_historical_data_success()` - GET /historical/{instrument}
- Historical data and candlestick tests

### test_database.py
- `test_db_get_requests_success()` - GET /db/requests
- `test_db_get_orders_success()` - GET /db/orders
- `test_db_get_trades_success()` - GET /db/trades
- `test_db_get_errors_success()` - GET /db/errors
- `test_db_get_stats_success()` - GET /db/stats

### test_transactions.py
- `test_get_transactions_success()` - GET /transactions
- `test_get_transaction_detail_success()` - GET /transaction/{id}
- `test_get_transactions_by_range_success()` - GET /transactions/range
- `test_get_transactions_since_success()` - GET /transactions/since/{id}
- Transaction query tests

## Running Tests

### Install test dependencies
```bash
pip install -r requirements-dev.txt
```

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_health.py
```

### Run specific test class
```bash
pytest tests/test_account.py::TestAccountEndpoints
```

### Run specific test
```bash
pytest tests/test_health.py::TestHealthEndpoints::test_root_endpoint_returns_ok
```

### Run with coverage
```bash
pytest --cov=server --cov-report=html
```

### Run with verbose output
```bash
pytest -v
```

### Run with specific markers
```bash
pytest -m "health"
pytest -m "not slow"
```

### Run in parallel
```bash
pytest -n auto
```

### Run with timeout
```bash
pytest --timeout=30
```

## Coverage

Target: **80%+ code coverage**

### Generate coverage report
```bash
pytest --cov=server --cov-report=html --cov-report=term-missing
```

The HTML report will be generated in `htmlcov/index.html`.

### View coverage summary
```bash
pytest --cov=server --cov-report=term-missing
```

## Fixtures

Common fixtures available in `conftest.py`:

- `mock_oanda_client` - Mocked OANDA API client
- `mock_db_pool` - Mocked asyncpg database pool
- `sample_account_data` - Sample account response
- `sample_order_data` - Sample order response
- `sample_trade_data` - Sample trade response
- `sample_pending_orders` - Sample pending orders list
- `sample_open_trades` - Sample open trades list
- `sample_candle_data` - Sample candle/historical data
- `sample_pricing_data` - Sample pricing data
- `sample_instruments_data` - Sample instruments data
- `sample_error_response` - Sample error response
- `sample_mcp_tools_list` - Sample MCP tools list
- `client_env_vars` - Environment variables setup

## Test Categories

### Unit Tests
Tests individual endpoints in isolation:
- `test_health.py` - Health checks
- `test_account.py` - Account operations
- `test_orders.py` - Order operations
- `test_trades.py` - Trade operations

### Integration Tests
Tests multiple components working together:
- `test_mcp_tools.py` - MCP integration
- `test_database.py` - Database integration
- `test_transactions.py` - Transaction handling

### API Tests
Tests HTTP endpoints and response formats:
- All test files validate JSON responses
- Status code validation
- Response structure validation

## Best Practices

1. **Test Independence**: Each test is independent and can run in any order
2. **Mocking**: All external calls (OANDA API, database) are mocked
3. **Clear Names**: Test names describe what is being tested
4. **Fixtures**: Reusable fixtures for common setup
5. **Error Handling**: Both success and error paths tested
6. **Documentation**: Tests serve as API documentation

## Continuous Integration

Tests are configured to run in CI/CD pipelines. See `.github/workflows/` for configuration.

## Troubleshooting

### Tests fail with import errors
```bash
export PYTHONPATH=/d/2026/Trading\ 2026/Oanda\ MCP:$PYTHONPATH
pytest
```

### Tests hang
Check for missing mocks or async context manager issues. Run with timeout:
```bash
pytest --timeout=10
```

### Coverage below 80%
Run coverage report to identify uncovered lines:
```bash
pytest --cov=server --cov-report=term-missing
```

## Configuration Files

- `pytest.ini` - Pytest configuration
- `.coveragerc` - Coverage configuration
- `conftest.py` - Pytest fixtures and hooks

## Adding New Tests

1. Create new test file: `tests/test_feature.py`
2. Add test class: `class TestFeatureEndpoints:`
3. Add test methods: `def test_feature_operation_success(self, client):`
4. Use fixtures from `conftest.py`
5. Mock external dependencies
6. Run: `pytest tests/test_feature.py`

## Test Metrics

- **Total Tests**: 68 test cases
- **Coverage Target**: 80%+
- **Average Test Duration**: < 100ms
- **Test Categories**: 9 (Health, Account, Orders, Trades, MCP, Pricing, Instruments, Database, Transactions)

## Environment Setup

Tests require these environment variables:
- `OANDA_API_KEY` - Test API key
- `OANDA_ACCOUNT_ID` - Test account ID
- `OANDA_ENVIRONMENT` - "practice" for testing
- `DATABASE_URL` - Test database URL (mocked in tests)

All are automatically set by fixtures. No manual configuration needed.

## Support

For test-related issues or improvements:
1. Check this README
2. Review test files for similar tests
3. Check pytest documentation: https://docs.pytest.org/
4. Review fixture documentation in conftest.py
