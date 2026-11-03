"""Pricing endpoint tests"""

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

class TestPricingEndpoints:
    """Pricing endpoint tests"""

    def test_get_current_price_success(self, client, app_with_mocks):
        """Test GET /price/{instrument} returns current price"""
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_pricing_data

        response = client.get("/pricing")
        assert response.status_code == 200
        data = response.json()
        assert "prices" in data or isinstance(data, list)

    def test_get_multiple_prices_with_instruments(self, client, app_with_mocks, sample_pricing_data):
        """Test GET /pricing with instruments parameter"""
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_pricing_data

        response = client.get("/pricing?instruments=EUR_USD,GBP_USD")
        assert response.status_code == 200

    def test_pricing_endpoint_returns_json(self, client, app_with_mocks, sample_pricing_data):
        """Test pricing endpoint returns JSON"""
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_pricing_data

        response = client.get("/pricing")
        assert "application/json" in response.headers["content-type"]

    def test_get_price_returns_bid_ask(self, client, app_with_mocks):
        """Test GET /price/{instrument} returns bid/ask"""
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_pricing_data

        for _ in range(3):
            response = client.get("/pricing")
            assert response.status_code == 200

    def test_price_endpoint_single_instrument(self, client, app_with_mocks):
        """Test GET /price/{instrument} for single instrument"""
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

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
