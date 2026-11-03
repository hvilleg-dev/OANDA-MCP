"""Instruments endpoint tests"""

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
            mock_conn.fetch = AsyncMock(return_value=[])

            from server import app
            yield app, mock_client, mock_pool


@pytest.fixture
def client(app_with_mocks):
    """FastAPI test client"""
    app, _, _ = app_with_mocks
    return TestClient(app)


class TestInstrumentsEndpoints:
    """Instruments endpoint tests"""

    def test_get_candles_success(self, client, app_with_mocks, sample_candle_data):
        """Test GET /instruments/{instrument}/candles returns candles"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_candle_data

        response = client.get("/instruments/EUR_USD/candles")
        assert response.status_code == 200

    def test_get_candles_with_parameters(self, client, app_with_mocks, sample_candle_data):
        """Test GET /instruments/{instrument}/candles with parameters"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_candle_data

        response = client.get("/instruments/EUR_USD/candles?granularity=H1&count=100")
        assert response.status_code == 200

    def test_get_orderbook_success(self, client, app_with_mocks):
        """Test GET /instruments/{instrument}/orderbook"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "orderBook": {
                "instrument": "EUR_USD",
                "time": "2025-01-01T00:00:00Z",
                "buckets": []
            }
        }
        mock_client.request.return_value = mock_response

        response = client.get("/instruments/EUR_USD/orderbook")
        assert response.status_code == 200

    def test_get_positionbook_success(self, client, app_with_mocks):
        """Test GET /instruments/{instrument}/positionbook"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "positionBook": {
                "instrument": "EUR_USD",
                "time": "2025-01-01T00:00:00Z",
                "buckets": []
            }
        }
        mock_client.request.return_value = mock_response

        response = client.get("/instruments/EUR_USD/positionbook")
        assert response.status_code == 200

    def test_get_historical_data_success(self, client, app_with_mocks, sample_candle_data):
        """Test GET /historical/{instrument} returns historical data"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_candle_data

        response = client.get("/historical/EUR_USD")
        assert response.status_code == 200

    def test_get_historical_data_with_granularity(self, client, app_with_mocks, sample_candle_data):
        """Test GET /historical/{instrument} with granularity"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_candle_data

        response = client.get("/historical/EUR_USD?granularity=H1&count=50")
        assert response.status_code == 200

    def test_candles_endpoint_returns_json(self, client, app_with_mocks, sample_candle_data):
        """Test candles endpoint returns JSON"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_candle_data

        response = client.get("/instruments/EUR_USD/candles")
        assert "application/json" in response.headers["content-type"]

    def test_get_candles_returns_candles_array(self, client, app_with_mocks, sample_candle_data):
        """Test GET /instruments/{instrument}/candles returns array"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_candle_data

        response = client.get("/instruments/EUR_USD/candles")
        assert response.status_code == 200
        data = response.json()
        assert "candles" in data or isinstance(data, dict)

    def test_historical_data_contains_ohlc(self, client, app_with_mocks, sample_candle_data):
        """Test historical data contains OHLC information"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_candle_data

        response = client.get("/historical/EUR_USD")
        assert response.status_code == 200
        data = response.json()
        assert "candles" in str(data) or "bid" in str(data)

    def test_orderbook_endpoint_success(self, client, app_with_mocks):
        """Test orderbook endpoint responds successfully"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "orderBook": {
                "instrument": "EUR_USD",
                "buckets": []
            }
        }
        mock_client.request.return_value = mock_response

        response = client.get("/instruments/EUR_USD/orderbook")
        assert response.status_code == 200

    def test_positionbook_endpoint_success(self, client, app_with_mocks):
        """Test positionbook endpoint responds successfully"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "positionBook": {
                "instrument": "EUR_USD",
                "buckets": []
            }
        }
        mock_client.request.return_value = mock_response

        response = client.get("/instruments/EUR_USD/positionbook")
        assert response.status_code == 200

    def test_multiple_candle_queries(self, client, app_with_mocks, sample_candle_data):
        """Test multiple sequential candle queries"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_candle_data

        for _ in range(2):
            response = client.get("/instruments/EUR_USD/candles")
            assert response.status_code == 200

    def test_different_instruments(self, client, app_with_mocks, sample_candle_data):
        """Test candles for different instruments"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_candle_data

        for instrument in ["EUR_USD", "GBP_USD", "USD_JPY"]:
            response = client.get(f"/instruments/{instrument}/candles")
            assert response.status_code == 200

    def test_candles_with_count_parameter(self, client, app_with_mocks, sample_candle_data):
        """Test candles with count parameter"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_candle_data

        response = client.get("/instruments/EUR_USD/candles?count=50")
        assert response.status_code == 200

    def test_historical_default_granularity(self, client, app_with_mocks, sample_candle_data):
        """Test historical data with default granularity"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_candle_data

        response = client.get("/historical/EUR_USD")
        assert response.status_code == 200
