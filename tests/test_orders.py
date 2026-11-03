"""Orders endpoint tests"""

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


class TestOrdersEndpoints:
    """Orders endpoint tests"""

    def test_get_orders_success(self, client, app_with_mocks, sample_pending_orders):
        """Test GET /orders returns list of orders"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_pending_orders

        response = client.get("/orders")
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data or isinstance(data, list)

    def test_get_pending_orders_success(self, client, app_with_mocks, sample_pending_orders):
        """Test GET /orders/pending returns pending orders"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_pending_orders

        response = client.get("/orders/pending")
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data or isinstance(data, list)

    def test_get_order_details_success(self, client, app_with_mocks, sample_order_data):
        """Test GET /order/{order_id} returns order details"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        response = client.get("/order/order-123")
        assert response.status_code == 200
        data = response.json()
        assert "order" in data or data.get("id") == "order-123"

    def test_place_market_order_success(self, client, app_with_mocks, sample_order_data):
        """Test POST /order/market places market order"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": 1000
        }

        response = client.post("/order/market", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "order" in data or "id" in data

    def test_place_market_order_with_stop_loss(self, client, app_with_mocks, sample_order_data):
        """Test POST /order/market with stop loss"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": 1000,
            "stop_loss": 1.07000
        }

        response = client.post("/order/market", json=payload)
        assert response.status_code == 200

    def test_place_market_order_with_take_profit(self, client, app_with_mocks, sample_order_data):
        """Test POST /order/market with take profit"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": 1000,
            "take_profit": 1.10000
        }

        response = client.post("/order/market", json=payload)
        assert response.status_code == 200

    def test_place_market_order_missing_instrument(self, client, app_with_mocks):
        """Test POST /order/market fails without instrument"""
        app, mock_client, _ = app_with_mocks

        payload = {
            "units": 1000
        }

        response = client.post("/order/market", json=payload)
        assert response.status_code in [400, 422]

    def test_place_market_order_missing_units(self, client, app_with_mocks):
        """Test POST /order/market fails without units"""
        app, mock_client, _ = app_with_mocks

        payload = {
            "instrument": "EUR_USD"
        }

        response = client.post("/order/market", json=payload)
        assert response.status_code in [400, 422]

    def test_place_limit_order_success(self, client, app_with_mocks, sample_order_data):
        """Test POST /order/limit places limit order"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": 1000,
            "price": 1.07500
        }

        response = client.post("/order/limit", json=payload)
        assert response.status_code == 200

    def test_place_limit_order_with_all_options(self, client, app_with_mocks, sample_order_data):
        """Test POST /order/limit with all optional parameters"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": 1000,
            "price": 1.07500,
            "stop_loss": 1.07000,
            "take_profit": 1.10000,
            "trailing_stop": 0.0050
        }

        response = client.post("/order/limit", json=payload)
        assert response.status_code == 200

    def test_modify_order_success(self, client, app_with_mocks, sample_order_data):
        """Test PATCH /order/{order_id} modifies order"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        payload = {
            "price": 1.08000
        }

        response = client.patch("/order/order-123", json=payload)
        assert response.status_code == 200

    def test_modify_order_units(self, client, app_with_mocks, sample_order_data):
        """Test PATCH /order/{order_id} modifies units"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        payload = {
            "units": 2000
        }

        response = client.patch("/order/order-123", json=payload)
        assert response.status_code == 200

    def test_delete_order_success(self, client, app_with_mocks):
        """Test DELETE /order/{order_id} cancels order"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "orderCancelTransaction": {
                "id": "cancel-123",
                "orderID": "order-123",
                "type": "ORDER_CANCEL"
            }
        }
        mock_client.request.return_value = mock_response

        response = client.delete("/order/order-123")
        assert response.status_code == 200

    def test_get_orders_with_state_filter(self, client, app_with_mocks, sample_pending_orders):
        """Test GET /orders with state parameter"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_pending_orders

        response = client.get("/orders?state=PENDING")
        assert response.status_code == 200

    def test_place_market_order_buy(self, client, app_with_mocks, sample_order_data):
        """Test place market order with positive units (buy)"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": 1000
        }

        response = client.post("/order/market", json=payload)
        assert response.status_code == 200

    def test_place_market_order_sell(self, client, app_with_mocks, sample_order_data):
        """Test place market order with negative units (sell)"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": -1000
        }

        response = client.post("/order/market", json=payload)
        assert response.status_code == 200

    def test_place_stop_order_success(self, client, app_with_mocks, sample_order_data):
        """Test POST /order/stop places stop order"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": 1000,
            "price": 1.09000
        }

        response = client.post("/order/stop", json=payload)
        assert response.status_code == 200

    def test_orders_endpoints_return_json(self, client, app_with_mocks, sample_pending_orders):
        """Test orders endpoints return JSON"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_pending_orders

        response = client.get("/orders")
        assert "application/json" in response.headers["content-type"]

    def test_place_order_returns_json(self, client, app_with_mocks, sample_order_data):
        """Test place order endpoint returns JSON"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": 1000
        }

        response = client.post("/order/market", json=payload)
        assert "application/json" in response.headers["content-type"]
