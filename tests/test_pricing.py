"""Pricing endpoint tests"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import json


@pytest.fixture
def app_with_mocks():
    """Fixture to create FastAPI app with mocked dependencies"""
    with patch.dict('os.environ', {
        'OANDA_API_KEY': 'test-key',
        'OANDA_ACCOUNT_ID': '123456',
        'OANDA_ENVIRONMENT': 'practice',
        'DATABASE_URL': 'postgresql://test:test@localhost/test_db'
    }):
        with patch('server.oanda_client') as mock_client, \
             patch('server.db_pool', new_callable=AsyncMock) as mock_pool, \
             patch('server.stream_client'):

            # Setup mock pool
            mock_conn = AsyncMock()
            mock_pool.acquire = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_conn.execute = AsyncMock()

            from server import app
            yield app, mock_client, mock_pool


@pytest.fixture
def client(app_with_mocks):
    """FastAPI test client"""
    app, _, _ = app_with_mocks
    return TestClient(app)


class TestPricingEndpoints:
    """Pricing endpoint tests"""

    def test_get_current_price_success(self, client, app_with_mocks):
        """Test GET /price/{instrument} returns current price"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "prices": [
                {
                    "instrument": "EUR_USD",
                    "time": "2025-01-01T00:00:00Z",
                    "bid": "1.08000",
                    "ask": "1.08010"
                }
            ]
        }
        mock_client.request.return_value = mock_response

        response = client.get("/price/EUR_USD")
        assert response.status_code == 200

    def test_get_multiple_prices_success(self, client, app_with_mocks, sample_pricing_data):
        """Test GET /pricing returns multiple prices"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_pricing_data

        response = client.get("/pricing")
        assert response.status_code == 200
        data = response.json()
        assert "prices" in data or isinstance(data, list)

    def test_get_multiple_prices_with_instruments(self, client, app_with_mocks, sample_pricing_data):
        """Test GET /pricing with instruments parameter"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_pricing_data

        response = client.get("/pricing?instruments=EUR_USD,GBP_USD")
        assert response.status_code == 200

    def test_pricing_endpoint_returns_json(self, client, app_with_mocks, sample_pricing_data):
        """Test pricing endpoint returns JSON"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_pricing_data

        response = client.get("/pricing")
        assert "application/json" in response.headers["content-type"]

    def test_get_price_returns_bid_ask(self, client, app_with_mocks):
        """Test GET /price/{instrument} returns bid/ask"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "prices": [
                {
                    "instrument": "EUR_USD",
                    "time": "2025-01-01T00:00:00Z",
                    "bid": "1.08000",
                    "ask": "1.08010"
                }
            ]
        }
        mock_client.request.return_value = mock_response

        response = client.get("/price/EUR_USD")
        assert response.status_code == 200
        data = response.json()
        assert "bid" in str(data) or "ask" in str(data)

    def test_multiple_pricing_queries(self, client, app_with_mocks, sample_pricing_data):
        """Test multiple sequential pricing queries"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_pricing_data

        for _ in range(3):
            response = client.get("/pricing")
            assert response.status_code == 200

    def test_price_endpoint_single_instrument(self, client, app_with_mocks):
        """Test GET /price/{instrument} for single instrument"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "prices": [
                {
                    "instrument": "EUR_USD",
                    "bid": "1.08000",
                    "ask": "1.08010"
                }
            ]
        }
        mock_client.request.return_value = mock_response

        response = client.get("/price/EUR_USD")
        assert response.status_code == 200

    def test_pricing_data_contains_timestamp(self, client, app_with_mocks):
        """Test pricing data includes timestamp"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "prices": [
                {
                    "instrument": "EUR_USD",
                    "time": "2025-01-01T00:00:00Z",
                    "bid": "1.08000",
                    "ask": "1.08010"
                }
            ]
        }
        mock_client.request.return_value = mock_response

        response = client.get("/price/EUR_USD")
        assert response.status_code == 200
        data = response.json()
        assert "time" in str(data) or "timestamp" in str(data)
