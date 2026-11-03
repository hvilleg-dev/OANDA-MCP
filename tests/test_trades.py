"""Trades endpoint tests"""

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


class TestTradesEndpoints:
    """Trades endpoint tests"""

    def test_get_trades_success(self, client, app_with_mocks, sample_open_trades):
        """Test GET /trades returns list of trades"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_open_trades

        response = client.get("/trades")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data or isinstance(data, list)

    def test_get_open_trades_success(self, client, app_with_mocks, sample_open_trades):
        """Test GET /trades/open returns open trades"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_open_trades

        response = client.get("/trades/open")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data or isinstance(data, list)

    def test_get_trade_details_success(self, client, app_with_mocks, sample_trade_data):
        """Test GET /trade/{trade_id} returns trade details"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_trade_data

        response = client.get("/trade/trade-123")
        assert response.status_code == 200
        data = response.json()
        assert "trade" in data or data.get("id") == "trade-123"

    def test_modify_trade_stop_loss_success(self, client, app_with_mocks, sample_trade_data):
        """Test PATCH /trade/{trade_id} modifies stop loss"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_trade_data

        payload = {
            "stop_loss": 1.07500
        }

        response = client.patch("/trade/trade-123", json=payload)
        assert response.status_code == 200

    def test_modify_trade_take_profit_success(self, client, app_with_mocks, sample_trade_data):
        """Test PATCH /trade/{trade_id} modifies take profit"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_trade_data

        payload = {
            "take_profit": 1.11000
        }

        response = client.patch("/trade/trade-123", json=payload)
        assert response.status_code == 200

    def test_modify_trade_trailing_stop_success(self, client, app_with_mocks, sample_trade_data):
        """Test PATCH /trade/{trade_id} modifies trailing stop"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_trade_data

        payload = {
            "trailing_stop": 0.0075
        }

        response = client.patch("/trade/trade-123", json=payload)
        assert response.status_code == 200

    def test_modify_trade_multiple_fields(self, client, app_with_mocks, sample_trade_data):
        """Test PATCH /trade/{trade_id} modifies multiple fields"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_trade_data

        payload = {
            "stop_loss": 1.07500,
            "take_profit": 1.11000,
            "trailing_stop": 0.0050
        }

        response = client.patch("/trade/trade-123", json=payload)
        assert response.status_code == 200

    def test_close_trade_full_success(self, client, app_with_mocks):
        """Test PUT /trade/{trade_id}/close closes trade fully"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "orderCreateTransaction": {
                "id": "order-close-123",
                "type": "MARKET_ORDER"
            },
            "orderFillTransaction": {
                "id": "fill-123",
                "type": "ORDER_FILL",
                "realizedPL": "500.00"
            }
        }
        mock_client.request.return_value = mock_response

        response = client.put("/trade/trade-123/close", json={})
        assert response.status_code == 200

    def test_close_trade_partial_units(self, client, app_with_mocks):
        """Test PUT /trade/{trade_id}/close closes partial units"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "orderCreateTransaction": {
                "id": "order-close-123"
            },
            "orderFillTransaction": {
                "id": "fill-123",
                "realizedPL": "250.00"
            }
        }
        mock_client.request.return_value = mock_response

        payload = {
            "units": "500"
        }

        response = client.put("/trade/trade-123/close", json=payload)
        assert response.status_code == 200

    def test_get_trades_with_state_filter(self, client, app_with_mocks, sample_open_trades):
        """Test GET /trades with state parameter"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_open_trades

        response = client.get("/trades?state=OPEN")
        assert response.status_code == 200

    def test_get_trades_returns_list(self, client, app_with_mocks, sample_open_trades):
        """Test GET /trades returns list of trades"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_open_trades

        response = client.get("/trades")
        assert response.status_code == 200
        data = response.json()
        trades = data.get("trades", data)
        assert isinstance(trades, list)

    def test_get_open_trades_returns_list(self, client, app_with_mocks, sample_open_trades):
        """Test GET /trades/open returns list"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_open_trades

        response = client.get("/trades/open")
        assert response.status_code == 200
        data = response.json()
        trades = data.get("trades", data)
        assert isinstance(trades, list)

    def test_get_trade_details_contains_id(self, client, app_with_mocks, sample_trade_data):
        """Test trade details contains ID"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_trade_data

        response = client.get("/trade/trade-123")
        assert response.status_code == 200
        data = response.json()
        trade = data.get("trade", data)
        assert "id" in trade or trade.get("id") is not None

    def test_modify_trade_empty_payload(self, client, app_with_mocks, sample_trade_data):
        """Test PATCH /trade/{trade_id} with empty payload"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_trade_data

        response = client.patch("/trade/trade-123", json={})
        assert response.status_code in [200, 400, 422]

    def test_close_trade_all_units(self, client, app_with_mocks):
        """Test PUT /trade/{trade_id}/close with ALL units"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "orderCreateTransaction": {},
            "orderFillTransaction": {"realizedPL": "500.00"}
        }
        mock_client.request.return_value = mock_response

        payload = {
            "units": "ALL"
        }

        response = client.put("/trade/trade-123/close", json=payload)
        assert response.status_code == 200

    def test_trades_endpoints_return_json(self, client, app_with_mocks, sample_open_trades):
        """Test trades endpoints return JSON"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_open_trades

        response = client.get("/trades")
        assert "application/json" in response.headers["content-type"]

    def test_modify_trade_returns_json(self, client, app_with_mocks, sample_trade_data):
        """Test modify trade endpoint returns JSON"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_trade_data

        payload = {
            "stop_loss": 1.07500
        }

        response = client.patch("/trade/trade-123", json=payload)
        assert "application/json" in response.headers["content-type"]

    def test_close_trade_returns_json(self, client, app_with_mocks):
        """Test close trade endpoint returns JSON"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "orderCreateTransaction": {},
            "orderFillTransaction": {"realizedPL": "500.00"}
        }
        mock_client.request.return_value = mock_response

        response = client.put("/trade/trade-123/close", json={})
        assert "application/json" in response.headers["content-type"]

    def test_get_trade_contains_instrument(self, client, app_with_mocks, sample_trade_data):
        """Test trade details contains instrument"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_trade_data

        response = client.get("/trade/trade-123")
        assert response.status_code == 200
        data = response.json()
        trade = data.get("trade", data)
        assert "instrument" in trade or "instrument" in str(data)

    def test_get_open_trades_multiple_records(self, client, app_with_mocks, sample_open_trades):
        """Test GET /trades/open returns multiple trades"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_open_trades

        response = client.get("/trades/open")
        assert response.status_code == 200
        data = response.json()
        trades = data.get("trades", data)
        assert len(trades) > 0
