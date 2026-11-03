"""Utility functions and test helpers for OANDA MCP Server tests"""

import asyncio
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock
import json
from datetime import datetime


class MockOANDAClient:
    """Mock OANDA client for testing"""

    def __init__(self):
        self.request_log = []
        self.responses = {}

    def set_response(self, key: str, response: Dict[str, Any]):
        """Set response for a specific request key"""
        self.responses[key] = response

    def request(self, *args, **kwargs):
        """Mock request method"""
        self.request_log.append((args, kwargs))
        # Return a default response if no specific one set
        return self.responses.get("default", {})


class MockDatabasePool:
    """Mock database pool for testing"""

    def __init__(self):
        self.data = {}
        self.queries = []

    async def acquire(self):
        """Acquire connection context manager"""
        return MockDatabaseConnection(self)

    async def execute_query(self, query: str, *args):
        """Execute and log query"""
        self.queries.append((query, args))


class MockDatabaseConnection:
    """Mock database connection"""

    def __init__(self, pool: MockDatabasePool):
        self.pool = pool

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def execute(self, query: str, *args):
        """Execute query"""
        self.pool.queries.append((query, args))
        return None

    async def fetch(self, query: str, *args):
        """Fetch results"""
        self.pool.queries.append((query, args))
        return []

    async def fetchval(self, query: str, *args):
        """Fetch single value"""
        self.pool.queries.append((query, args))
        return None


def create_mock_account(
    account_id: str = "123456",
    balance: float = 50000.0,
    unrealized_pl: float = 100.0,
    margin_used: float = 5000.0
) -> Dict[str, Any]:
    """Create a mock account response"""
    return {
        "account": {
            "id": account_id,
            "alias": f"Account {account_id}",
            "currency": "USD",
            "balance": str(balance),
            "unrealizedPL": str(unrealized_pl),
            "marginUsed": str(margin_used),
            "marginAvailable": str(balance - margin_used),
            "marginRate": "0.02"
        }
    }


def create_mock_trade(
    trade_id: str = "trade-123",
    instrument: str = "EUR_USD",
    units: int = 1000,
    price: float = 1.08500,
    unrealized_pl: float = 100.0
) -> Dict[str, Any]:
    """Create a mock trade response"""
    return {
        "trade": {
            "id": trade_id,
            "instrument": instrument,
            "price": str(price),
            "openTime": "2025-01-01T00:00:00Z",
            "state": "OPEN",
            "units": str(units),
            "unrealizedPL": str(unrealized_pl),
            "marginRequired": "50.00"
        }
    }


def create_mock_order(
    order_id: str = "order-123",
    instrument: str = "EUR_USD",
    units: int = 1000,
    order_type: str = "MARKET",
    state: str = "PENDING"
) -> Dict[str, Any]:
    """Create a mock order response"""
    return {
        "order": {
            "id": order_id,
            "type": order_type,
            "instrument": instrument,
            "units": str(units),
            "state": state,
            "createTime": "2025-01-01T00:00:00Z"
        }
    }


def create_mock_candle(
    instrument: str = "EUR_USD",
    open_price: float = 1.08000,
    high_price: float = 1.09000,
    low_price: float = 1.07000,
    close_price: float = 1.08500,
    volume: int = 1000
) -> Dict[str, Any]:
    """Create a mock candle response"""
    return {
        "instrument": instrument,
        "granularity": "D",
        "candles": [
            {
                "complete": True,
                "volume": volume,
                "time": "2025-01-01T00:00:00Z",
                "bid": {
                    "o": str(open_price),
                    "h": str(high_price),
                    "l": str(low_price),
                    "c": str(close_price)
                },
                "ask": {
                    "o": str(open_price + 0.0001),
                    "h": str(high_price + 0.0001),
                    "l": str(low_price + 0.0001),
                    "c": str(close_price + 0.0001)
                }
            }
        ]
    }


def create_mock_price(
    instrument: str = "EUR_USD",
    bid: float = 1.08000,
    ask: float = 1.08010
) -> Dict[str, Any]:
    """Create a mock price response"""
    return {
        "prices": [
            {
                "instrument": instrument,
                "time": "2025-01-01T00:00:00Z",
                "bid": str(bid),
                "ask": str(ask),
                "status": "tradeable"
            }
        ]
    }


def create_mock_transaction(
    tx_id: str = "100",
    tx_type: str = "ORDER_FILL",
    instrument: str = "EUR_USD",
    units: int = 1000
) -> Dict[str, Any]:
    """Create a mock transaction response"""
    return {
        "transaction": {
            "id": tx_id,
            "time": "2025-01-01T00:00:00Z",
            "type": tx_type,
            "instrument": instrument,
            "units": str(units),
            "price": "1.08500"
        }
    }


def assert_valid_response(response_data: Dict[str, Any], required_fields: List[str]):
    """Assert that response contains required fields"""
    for field in required_fields:
        assert field in response_data, f"Response missing required field: {field}"


def assert_valid_timestamp(timestamp_str: str):
    """Assert that timestamp is in valid RFC3339 format"""
    try:
        # Try parsing ISO format
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError:
        raise AssertionError(f"Invalid timestamp format: {timestamp_str}")


async def async_noop():
    """No-op async function for testing"""
    return None


class AsyncContextManager:
    """Context manager for test setup/teardown"""

    def __init__(self):
        self.setup_called = False
        self.teardown_called = False

    async def __aenter__(self):
        self.setup_called = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.teardown_called = True
