"""Pytest configuration and fixtures for OANDA MCP Server tests"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, Optional

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Clean server module from cache
if 'server' in sys.modules:
    del sys.modules['server']


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_oanda_client():
    """Mock OANDA API client"""
    mock_client = MagicMock()
    mock_client.request = MagicMock(return_value={
        "account": {
            "id": "123456",
            "alias": "Primary Account",
            "currency": "USD",
            "balance": "50000.00",
            "unrealizedPL": "100.00",
            "marginUsed": "5000.00",
            "marginAvailable": "45000.00",
            "marginRate": "0.02"
        }
    })
    return mock_client


@pytest.fixture
def mock_db_pool():
    """Mock asyncpg database pool"""
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock execute methods
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchval = AsyncMock(return_value=None)

    return mock_pool


@pytest.fixture
def sample_account_data():
    """Sample account data response"""
    return {
        "account": {
            "id": "123456",
            "alias": "Primary Account",
            "currency": "USD",
            "balance": "50000.00",
            "unrealizedPL": "100.50",
            "marginUsed": "5000.00",
            "marginAvailable": "45000.00",
            "marginRate": "0.02",
            "createdByUserID": 1,
            "createdTime": "2025-01-01T00:00:00Z",
            "pl": "5000.00",
            "resettablePL": "5000.00",
            "financing": "10.00",
            "commission": "50.00",
            "positions": [],
            "trades": [],
            "orders": []
        }
    }


@pytest.fixture
def sample_order_data():
    """Sample order data"""
    return {
        "order": {
            "id": "order-123",
            "createTime": "2025-01-01T00:00:00Z",
            "state": "PENDING",
            "clientExtensions": {
                "id": "order-001"
            },
            "type": "MARKET",
            "instrument": "EUR_USD",
            "units": "1000",
            "timeInForce": "FOK",
            "priceBound": "1.08500",
            "triggerCondition": "DEFAULT",
            "takeProfitOnFill": {
                "price": "1.10000"
            },
            "stopLossOnFill": {
                "price": "1.07000"
            },
            "tradeOpenDetails": {
                "initialUnits": "1000",
                "initialMarginRequired": "50.00"
            }
        },
        "orderFillTransaction": {
            "id": "order-fill-123",
            "type": "ORDER_FILL",
            "orderID": "order-123",
            "instrument": "EUR_USD",
            "units": "1000",
            "price": "1.08500",
            "pl": "0.00",
            "financing": "0.00",
            "commission": "10.00",
            "accountBalance": "49990.00",
            "tradeOpened": {
                "tradeID": "trade-123",
                "units": "1000",
                "price": "1.08500"
            }
        },
        "relatedTransactionIDs": ["order-fill-123"]
    }


@pytest.fixture
def sample_trade_data():
    """Sample trade data"""
    return {
        "trade": {
            "id": "trade-123",
            "instrument": "EUR_USD",
            "price": "1.08500",
            "openTime": "2025-01-01T00:00:00Z",
            "state": "OPEN",
            "initialUnits": "1000",
            "units": "1000",
            "realizedPL": "0.00",
            "unrealizedPL": "100.00",
            "marginRequired": "50.00",
            "dividendAdjustment": "0.00",
            "financing": "0.00",
            "commission": "10.00",
            "closingTransactionIDs": [],
            "clientExtensions": {
                "id": "trade-001"
            },
            "takeProfitOrder": {
                "id": "tp-order-123",
                "price": "1.10000"
            },
            "stopLossOrder": {
                "id": "sl-order-123",
                "price": "1.07000"
            }
        }
    }


@pytest.fixture
def sample_pending_orders():
    """Sample pending orders list"""
    return {
        "orders": [
            {
                "id": "order-100",
                "type": "LIMIT",
                "instrument": "EUR_USD",
                "units": "500",
                "state": "PENDING",
                "priceBound": "1.07000",
                "createTime": "2025-01-01T00:00:00Z"
            },
            {
                "id": "order-101",
                "type": "STOP",
                "instrument": "GBP_USD",
                "units": "-1000",
                "state": "PENDING",
                "priceBound": "1.25000",
                "createTime": "2025-01-01T01:00:00Z"
            }
        ]
    }


@pytest.fixture
def sample_open_trades():
    """Sample open trades list"""
    return {
        "trades": [
            {
                "id": "trade-100",
                "instrument": "EUR_USD",
                "price": "1.08500",
                "openTime": "2025-01-01T00:00:00Z",
                "state": "OPEN",
                "units": "1000",
                "unrealizedPL": "150.00"
            },
            {
                "id": "trade-101",
                "instrument": "GBP_USD",
                "price": "1.25000",
                "openTime": "2025-01-01T12:00:00Z",
                "state": "OPEN",
                "units": "-500",
                "unrealizedPL": "-75.00"
            }
        ]
    }


@pytest.fixture
def sample_candle_data():
    """Sample candle/historical data"""
    return {
        "instrument": "EUR_USD",
        "granularity": "D",
        "candles": [
            {
                "complete": True,
                "volume": 1000,
                "time": "2025-01-01T00:00:00Z",
                "bid": {
                    "o": "1.08000",
                    "h": "1.09000",
                    "l": "1.07000",
                    "c": "1.08500"
                },
                "ask": {
                    "o": "1.08010",
                    "h": "1.09010",
                    "l": "1.07010",
                    "c": "1.08510"
                }
            }
        ]
    }


@pytest.fixture
def sample_pricing_data():
    """Sample pricing data"""
    return {
        "prices": [
            {
                "instrument": "EUR_USD",
                "time": "2025-01-01T00:00:00Z",
                "bid": "1.08000",
                "ask": "1.08010",
                "status": "tradeable"
            },
            {
                "instrument": "GBP_USD",
                "time": "2025-01-01T00:00:00Z",
                "bid": "1.25000",
                "ask": "1.25010",
                "status": "tradeable"
            }
        ]
    }


@pytest.fixture
def sample_instruments_data():
    """Sample instruments data"""
    return {
        "instruments": [
            {
                "name": "Euro/US Dollar",
                "type": "CURRENCY",
                "pipLocation": -4,
                "maximumOrderUnits": "10000000",
                "maximumPositionSize": "0",
                "maximumTradeUnitSize": "10000000",
                "minimumTradeSize": 1,
                "displayName": "EUR/USD",
                "name": "EUR_USD"
            },
            {
                "name": "British Pound/US Dollar",
                "type": "CURRENCY",
                "pipLocation": -4,
                "maximumOrderUnits": "10000000",
                "maximumPositionSize": "0",
                "maximumTradeUnitSize": "10000000",
                "minimumTradeSize": 1,
                "displayName": "GBP/USD",
                "name": "GBP_USD"
            }
        ]
    }


@pytest.fixture
def sample_error_response():
    """Sample error response from OANDA"""
    return {
        "errorCode": "INVALID_INSTRUMENT",
        "errorMessage": "The instrument provided is not valid for trading",
        "orderRejectTransaction": {
            "rejectReason": "INSUFFICIENT_MARGIN"
        }
    }


@pytest.fixture
def mock_fastapi_request():
    """Mock FastAPI Request object"""
    mock_request = MagicMock()
    mock_request.url.hostname = "localhost"
    mock_request.client.host = "127.0.0.1"
    mock_request.headers = {"user-agent": "test-client"}
    return mock_request


@pytest.fixture
def sample_mcp_tools_list():
    """Sample MCP tools list"""
    return {
        "tools": [
            {
                "name": "get_account",
                "description": "Get account information",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "place_market_order",
                "description": "Place a market order",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "instrument": {"type": "string"},
                        "units": {"type": "integer"}
                    },
                    "required": ["instrument", "units"]
                }
            },
            {
                "name": "get_trades",
                "description": "Get open trades",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    }


@pytest.fixture
def sample_account_summary():
    """Sample account summary response"""
    return {
        "account": {
            "id": "123456",
            "balance": "50000.00",
            "unrealizedPL": "100.50",
            "marginUsed": "5000.00",
            "marginAvailable": "45000.00",
            "openTradeCount": 2,
            "openPositionCount": 2,
            "pendingOrderCount": 1,
            "pl": "5000.00",
            "resettablePL": "5000.00",
            "financing": "10.00",
            "commission": "50.00"
        }
    }


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data"""
    return {
        "transaction": {
            "id": "100",
            "time": "2025-01-01T00:00:00Z",
            "type": "ORDER_FILL",
            "accountID": "123456",
            "userID": 1,
            "batchID": "100",
            "requestID": "0",
            "instrument": "EUR_USD",
            "units": "1000",
            "price": "1.08500",
            "pl": "0.00",
            "financing": "0.00",
            "commission": "10.00",
            "accountBalance": "49990.00",
            "tradeOpened": {
                "tradeID": "trade-123",
                "units": "1000",
                "price": "1.08500"
            }
        }
    }


@pytest.fixture
def sample_account_changes():
    """Sample account changes response"""
    return {
        "changes": {
            "ordersCreated": [
                {
                    "id": "order-200",
                    "type": "LIMIT",
                    "state": "PENDING"
                }
            ],
            "ordersClosed": [],
            "ordersTriggered": [],
            "trades": [
                {
                    "id": "trade-123",
                    "units": "1000",
                    "unrealizedPL": "100.00"
                }
            ],
            "positions": [
                {
                    "instrument": "EUR_USD",
                    "long": {
                        "units": "1000",
                        "realizedPL": "0.00",
                        "unrealizedPL": "100.00"
                    },
                    "short": {
                        "units": "0",
                        "realizedPL": "0.00",
                        "unrealizedPL": "0.00"
                    }
                }
            ]
        },
        "lastTransactionID": "100"
    }


@pytest.fixture
def client_env_vars(monkeypatch):
    """Set required environment variables"""
    monkeypatch.setenv("OANDA_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("OANDA_ACCOUNT_ID", "123456")
    monkeypatch.setenv("OANDA_ENVIRONMENT", "practice")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test_db")


@pytest.fixture
def mock_v20_error():
    """Mock OANDA V20Error"""
    from oandapyV20.exceptions import V20Error
    error_response = {
        "errorCode": "INVALID_INSTRUMENT",
        "errorMessage": "The instrument provided is not valid",
        "orderRejectTransaction": {
            "rejectReason": "INSUFFICIENT_MARGIN"
        }
    }
    return V20Error(json.dumps(error_response))


@pytest.fixture(autouse=True)
def reset_modules():
    """Reset modules before each test to ensure clean imports"""
    # Clean up before test
    modules_to_remove = [mod for mod in sys.modules if 'server' in mod]
    for mod in modules_to_remove:
        sys.modules.pop(mod, None)

    yield

    # Clean up after test
    modules_to_remove = [mod for mod in sys.modules if 'server' in mod]
    for mod in modules_to_remove:
        sys.modules.pop(mod, None)


@pytest.fixture(scope="function")
def app_fixture_with_mocks():
    """Global fixture with mocked server components"""
    # Patch environment variables
    env_patch = patch.dict('os.environ', {
        'OANDA_API_KEY': 'test-key',
        'OANDA_ACCOUNT_ID': '123456',
        'OANDA_ENVIRONMENT': 'practice',
        'CIRCUIT_BREAKER_THRESHOLD': '5',
        'CIRCUIT_BREAKER_TIMEOUT': '60',
        'CIRCUIT_BREAKER_BACKOFF_MULTIPLIER': '100',
        'DATABASE_URL': 'postgresql://test:test@localhost/test_db'
    })

    env_patch.start()

    try:
        # Patch before importing server
        oanda_patcher = patch('oandapyV20.API')
        mock_api_class = oanda_patcher.start()

        # Create mock instances
        mock_oanda_client = MagicMock()
        mock_stream_client = MagicMock()
        mock_api_class.side_effect = [mock_oanda_client, mock_stream_client]

        # Setup OANDA client mock using a wrapper to handle both return_value and side_effect
        class RequestMock:
            def __init__(self):
                self.return_value = None
                self.side_effect = None
                self.call_count = 0

            def __call__(self, endpoint):
                self.call_count += 1
                # If return_value was explicitly set, use it
                if self.return_value is not None:
                    response_data = self.return_value
                    if isinstance(response_data, dict):
                        endpoint.response = response_data
                    return endpoint

                # Otherwise use default
                endpoint.response = {
                    "account": {
                        "id": "123456",
                        "currency": "USD",
                        "balance": "50000.00",
                    }
                }
                return endpoint

        mock_oanda_client.request = RequestMock()
        mock_stream_client.request = RequestMock()

        # Now import server
        import server

        # Patch circuit breaker call to actually execute the function
        async def mock_call(func, *args, **kwargs):
            """Mock circuit breaker that just calls the function directly"""
            result = func(*args, **kwargs)
            return result

        server.circuit_breaker.call = AsyncMock(side_effect=mock_call)
        server.circuit_breaker.get_state = MagicMock(return_value=MagicMock(value="CLOSED"))
        server.circuit_breaker.get_metrics = MagicMock(return_value={"state": "CLOSED", "failures": 0})

        # Setup mock db_pool as None (so logging skips database operations in tests)
        server.db_pool = None

        result = {
            'app': server.app,
            'mock_oanda_client': mock_oanda_client,
            'mock_circuit_breaker': server.circuit_breaker,
            'mock_pool': server.db_pool,
        }

        yield result

    finally:
        oanda_patcher.stop()
        env_patch.stop()
        # Clean modules after test
        if 'server' in sys.modules:
            del sys.modules['server']
