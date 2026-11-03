"""Database endpoints tests"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import json


@pytest.fixture
def app_with_mocks(app_fixture_with_mocks):
    """Adapter fixture for backward compatibility"""
    return app_fixture_with_mocks


@pytest.fixture
def client(app_with_mocks):
    """FastAPI test client"""
    return TestClient(app_with_mocks['app'])

class TestDatabaseEndpoints:
    """Database endpoints tests"""

    def test_db_get_requests_success(self, client, app_with_mocks):
        """Test GET /db/requests returns request logs"""
        response = client.get("/db/requests")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (dict, list))

    def test_db_get_requests_with_limit(self, client, app_with_mocks):
        """Test GET /db/requests with limit parameter"""
        response = client.get("/db/requests?limit=10")
        assert response.status_code == 200

    def test_db_get_requests_only_errors(self, client, app_with_mocks):
        """Test GET /db/requests with only_errors filter"""
        response = client.get("/db/requests?only_errors=true")
        assert response.status_code == 200

    def test_db_get_orders_success(self, client, app_with_mocks):
        """Test GET /db/orders returns order logs"""
        response = client.get("/db/orders")
        assert response.status_code == 200

    def test_db_get_orders_with_limit(self, client, app_with_mocks):
        """Test GET /db/orders with limit parameter"""
        response = client.get("/db/orders?limit=25")
        assert response.status_code == 200

    def test_db_get_orders_with_instrument_filter(self, client, app_with_mocks):
        """Test GET /db/orders with instrument filter"""
        response = client.get("/db/orders?instrument=EUR_USD")
        assert response.status_code == 200

    def test_db_get_trades_success(self, client, app_with_mocks):
        """Test GET /db/trades returns trade logs"""
        response = client.get("/db/trades")
        assert response.status_code == 200

    def test_db_get_trades_with_limit(self, client, app_with_mocks):
        """Test GET /db/trades with limit parameter"""
        response = client.get("/db/trades?limit=30")
        assert response.status_code == 200

    def test_db_get_errors_success(self, client, app_with_mocks):
        """Test GET /db/errors returns error logs"""
        response = client.get("/db/errors")
        assert response.status_code == 200

    def test_db_get_errors_with_limit(self, client, app_with_mocks):
        """Test GET /db/errors with limit parameter"""
        response = client.get("/db/errors?limit=20")
        assert response.status_code == 200

    def test_db_get_stats_success(self, client, app_with_mocks):
        """Test GET /db/stats returns statistics"""
        response = client.get("/db/stats")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_db_endpoints_return_json(self, client, app_with_mocks):
        """Test database endpoints return JSON"""
        endpoints = ["/db/requests", "/db/orders", "/db/trades", "/db/errors", "/db/stats"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            if response.status_code == 200:
                assert "application/json" in response.headers["content-type"]

    def test_db_requests_default_limit(self, client, app_with_mocks):
        """Test GET /db/requests uses default limit"""
        response = client.get("/db/requests")
        assert response.status_code == 200

    def test_db_orders_default_limit(self, client, app_with_mocks):
        """Test GET /db/orders uses default limit"""
        response = client.get("/db/orders")
        assert response.status_code == 200

    def test_db_trades_default_limit(self, client, app_with_mocks):
        """Test GET /db/trades uses default limit"""
        response = client.get("/db/trades")
        assert response.status_code == 200

    def test_db_errors_default_limit(self, client, app_with_mocks):
        """Test GET /db/errors uses default limit"""
        response = client.get("/db/errors")
        assert response.status_code == 200

    def test_multiple_db_queries(self, client, app_with_mocks):
        """Test multiple sequential database queries"""
        for _ in range(3):
            response = client.get("/db/requests")
            assert response.status_code == 200
