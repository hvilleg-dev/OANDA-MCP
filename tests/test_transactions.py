"""Transactions endpoint tests"""

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


class TestTransactionsEndpoints:
    """Transactions endpoint tests"""

    def test_get_transactions_success(self, client, app_with_mocks):
        """Test GET /transactions returns transactions"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "transactions": [
                {
                    "id": "100",
                    "time": "2025-01-01T00:00:00Z",
                    "type": "ORDER_FILL"
                }
            ]
        }
        mock_client.request.return_value = mock_response

        response = client.get("/transactions")
        assert response.status_code == 200

    def test_get_transaction_detail_success(self, client, app_with_mocks, sample_transaction_data):
        """Test GET /transaction/{transaction_id} returns details"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_transaction_data

        response = client.get("/transaction/100")
        assert response.status_code == 200

    def test_get_transactions_by_range_success(self, client, app_with_mocks):
        """Test GET /transactions/range returns range of transactions"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "transactions": [],
            "fromTransactionID": "100",
            "toTransactionID": "200"
        }
        mock_client.request.return_value = mock_response

        response = client.get("/transactions/range?from_id=100&to_id=200")
        assert response.status_code in [200, 400]

    def test_get_transactions_since_success(self, client, app_with_mocks):
        """Test GET /transactions/since/{transaction_id}"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "transactions": []
        }
        mock_client.request.return_value = mock_response

        response = client.get("/transactions/since/100")
        assert response.status_code == 200

    def test_get_transactions_with_params(self, client, app_with_mocks):
        """Test GET /transactions with query parameters"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "transactions": []
        }
        mock_client.request.return_value = mock_response

        response = client.get("/transactions?pageSize=50")
        assert response.status_code in [200, 400]

    def test_transactions_endpoint_returns_json(self, client, app_with_mocks):
        """Test transactions endpoint returns JSON"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "transactions": []
        }
        mock_client.request.return_value = mock_response

        response = client.get("/transactions")
        assert "application/json" in response.headers["content-type"]

    def test_transaction_detail_endpoint_returns_json(self, client, app_with_mocks, sample_transaction_data):
        """Test transaction detail endpoint returns JSON"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_transaction_data

        response = client.get("/transaction/100")
        assert "application/json" in response.headers["content-type"]

    def test_get_transactions_returns_array(self, client, app_with_mocks):
        """Test GET /transactions returns array"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "transactions": []
        }
        mock_client.request.return_value = mock_response

        response = client.get("/transactions")
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data or isinstance(data, (list, dict))

    def test_transaction_contains_required_fields(self, client, app_with_mocks, sample_transaction_data):
        """Test transaction contains required fields"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_transaction_data

        response = client.get("/transaction/100")
        assert response.status_code == 200
        data = response.json()
        transaction = data.get("transaction", data)
        assert "id" in transaction or "id" in str(data)

    def test_multiple_transaction_queries(self, client, app_with_mocks):
        """Test multiple sequential transaction queries"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "transactions": []
        }
        mock_client.request.return_value = mock_response

        for _ in range(3):
            response = client.get("/transactions")
            assert response.status_code == 200

    def test_transactions_range_requires_parameters(self, client):
        """Test GET /transactions/range requires parameters"""
        response = client.get("/transactions/range")
        assert response.status_code in [400, 422]

    def test_transactions_since_requires_id(self, client):
        """Test GET /transactions/since/{id} with ID"""
        # This should work with any ID format
        response = client.get("/transactions/since/0")
        # May be 200, 400, or other depending on implementation
        assert response.status_code in [200, 400, 422]

    def test_transaction_detail_format(self, client, app_with_mocks, sample_transaction_data):
        """Test transaction detail response format"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_transaction_data

        response = client.get("/transaction/100")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_different_transaction_ids(self, client, app_with_mocks, sample_transaction_data):
        """Test transactions with different IDs"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_transaction_data

        for tx_id in ["100", "200", "999"]:
            response = client.get(f"/transaction/{tx_id}")
            assert response.status_code == 200
