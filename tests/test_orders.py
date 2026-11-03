"""Orders endpoint tests"""

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


class TestOrdersEndpoints:
    """Orders endpoint tests"""

    def test_get_orders_success(self, client, app_with_mocks, sample_pending_orders):
        """Test GET /orders returns list of orders"""
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_pending_orders

        response = client.get("/orders")
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data or isinstance(data, list)

    def test_get_pending_orders_success(self, client, app_with_mocks, sample_pending_orders):
        """Test GET /orders/pending returns pending orders"""
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_pending_orders

        response = client.get("/orders/pending")
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data or isinstance(data, list)

    def test_get_order_details_success(self, client, app_with_mocks, sample_order_data):
        """Test GET /order/{order_id} returns order details"""
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_order_data

        response = client.get("/order/order-123")
        assert response.status_code == 200
        data = response.json()
        assert "order" in data or data.get("id") == "order-123"

    def test_place_market_order_success(self, client, app_with_mocks, sample_order_data):
        """Test POST /order/market places market order"""
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

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
        payload = {
            "units": 1000
        }

        response = client.post("/order/market", json=payload)
        assert response.status_code in [400, 422]

    def test_place_market_order_missing_units(self, client, app_with_mocks):
        """Test POST /order/market fails without units"""
        payload = {
            "instrument": "EUR_USD"
        }

        response = client.post("/order/market", json=payload)
        assert response.status_code in [400, 422]

    def test_place_limit_order_success(self, client, app_with_mocks, sample_order_data):
        """Test POST /order/limit places limit order"""
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_order_data

        payload = {
            "price": 1.08000
        }

        response = client.patch("/order/order-123", json=payload)
        assert response.status_code == 200

    def test_modify_order_units(self, client, app_with_mocks, sample_order_data):
        """Test PATCH /order/{order_id} modifies units"""
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_order_data

        payload = {
            "units": 2000
        }

        response = client.patch("/order/order-123", json=payload)
        assert response.status_code == 200

    def test_delete_order_success(self, client, app_with_mocks):
        """Test DELETE /order/{order_id} cancels order"""
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_pending_orders

        response = client.get("/orders?state=PENDING")
        assert response.status_code == 200

    def test_place_market_order_buy(self, client, app_with_mocks, sample_order_data):
        """Test place market order with positive units (buy)"""
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": 1000
        }

        response = client.post("/order/market", json=payload)
        assert response.status_code == 200

    def test_place_market_order_sell(self, client, app_with_mocks, sample_order_data):
        """Test place market order with negative units (sell)"""
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": -1000
        }

        response = client.post("/order/market", json=payload)
        assert response.status_code == 200

    def test_place_stop_order_success(self, client, app_with_mocks, sample_order_data):
        """Test POST /order/stop places stop order"""
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_pending_orders

        response = client.get("/orders")
        assert "application/json" in response.headers["content-type"]

    def test_place_order_returns_json(self, client, app_with_mocks, sample_order_data):
        """Test place order endpoint returns JSON"""
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_order_data

        payload = {
            "instrument": "EUR_USD",
            "units": 1000
        }

        response = client.post("/order/market", json=payload)
        assert "application/json" in response.headers["content-type"]
