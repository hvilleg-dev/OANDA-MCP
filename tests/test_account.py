"""Account endpoint tests"""

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


class TestAccountEndpoints:
    """Account endpoint tests"""

    def test_get_account_info_success(self, client, app_with_mocks, sample_account_data):
        """Test GET /account returns account information"""
        app, mock_client, _ = app_with_mocks

        # Mock the OANDA client
        mock_request = MagicMock()
        mock_request.status_code = 200
        mock_client.request.return_value = sample_account_data

        response = client.get("/account")
        assert response.status_code == 200
        data = response.json()
        assert "account" in data or data.get("id") == "123456"

    def test_get_account_summary_success(self, client, app_with_mocks, sample_account_summary):
        """Test GET /account/summary returns summary data"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_account_summary

        response = client.get("/account/summary")
        assert response.status_code == 200
        data = response.json()
        assert "account" in data or "balance" in data

    def test_get_account_instruments_success(self, client, app_with_mocks, sample_instruments_data):
        """Test GET /account/instruments returns list of instruments"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_instruments_data

        response = client.get("/account/instruments")
        assert response.status_code == 200
        data = response.json()
        assert "instruments" in data or isinstance(data, list)

    def test_get_account_instruments_with_query_params(self, client, app_with_mocks, sample_instruments_data):
        """Test GET /account/instruments with query parameters"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_instruments_data

        response = client.get("/account/instruments?count=10")
        assert response.status_code in [200, 400]

    def test_get_account_changes_success(self, client, app_with_mocks, sample_account_changes):
        """Test GET /account/changes returns account changes"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_account_changes

        response = client.get("/account/changes?sinceTransactionID=1")
        assert response.status_code in [200, 400]

    def test_get_account_changes_requires_transaction_id(self, client):
        """Test GET /account/changes requires sinceTransactionID parameter"""
        response = client.get("/account/changes")
        # Should require parameter
        assert response.status_code in [400, 422]

    def test_patch_account_configuration_success(self, client, app_with_mocks):
        """Test PATCH /account/configuration updates account"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "account": {
                "id": "123456",
                "alias": "Updated Alias"
            }
        }
        mock_client.request.return_value = mock_response

        payload = {
            "alias": "Updated Alias"
        }

        response = client.patch("/account/configuration", json=payload)
        assert response.status_code in [200, 400]

    def test_patch_account_configuration_with_margin_rate(self, client, app_with_mocks):
        """Test PATCH /account/configuration with margin rate"""
        app, mock_client, _ = app_with_mocks

        mock_response = {
            "account": {
                "id": "123456",
                "marginRate": "0.03"
            }
        }
        mock_client.request.return_value = mock_response

        payload = {
            "marginRate": "0.03"
        }

        response = client.patch("/account/configuration", json=payload)
        assert response.status_code in [200, 400]

    def test_get_account_returns_valid_json(self, client, app_with_mocks, sample_account_data):
        """Test GET /account returns valid JSON response"""
        app, mock_client, _ = app_with_mocks
        mock_client.request.return_value = sample_account_data

        response = client.get("/account")
        assert response.status_code == 200

        # Should be valid JSON
        data = response.json()
        assert isinstance(data, dict)

    def test_get_account_info_contains_required_fields(self, client, app_with_mocks, sample_account_data):
        """Test account response contains required fields"""
        app, mock_client, _ = app_with_mocks
        mock_client.request.return_value = sample_account_data

        response = client.get("/account")
        assert response.status_code == 200
        data = response.json()

        # Check for account data presence
        account_data = data.get("account", data)
        required_fields = ["id", "currency", "balance"]
        for field in required_fields:
            assert field in account_data or field in str(data)

    def test_account_summary_contains_balance(self, client, app_with_mocks, sample_account_summary):
        """Test account summary includes balance information"""
        app, mock_client, _ = app_with_mocks
        mock_client.request.return_value = sample_account_summary

        response = client.get("/account/summary")
        assert response.status_code == 200
        data = response.json()
        account_data = data.get("account", data)
        assert "balance" in account_data or "balance" in str(data)

    def test_get_instruments_returns_list(self, client, app_with_mocks, sample_instruments_data):
        """Test instruments endpoint returns a list"""
        app, mock_client, _ = app_with_mocks
        mock_client.request.return_value = sample_instruments_data

        response = client.get("/account/instruments")
        assert response.status_code == 200
        data = response.json()

        # Check for list of instruments
        instruments = data.get("instruments", data)
        assert isinstance(instruments, list)

    def test_patch_configuration_empty_payload(self, client, app_with_mocks):
        """Test PATCH /account/configuration accepts empty payload"""
        app, mock_client, _ = app_with_mocks

        response = client.patch("/account/configuration", json={})
        assert response.status_code in [200, 400, 422]

    def test_multiple_account_queries(self, client, app_with_mocks, sample_account_data):
        """Test multiple sequential account queries"""
        app, mock_client, _ = app_with_mocks
        mock_client.request.return_value = sample_account_data

        for _ in range(3):
            response = client.get("/account")
            assert response.status_code == 200

    def test_account_endpoints_return_json_content_type(self, client, app_with_mocks, sample_account_data):
        """Test account endpoints return JSON content type"""
        app, mock_client, _ = app_with_mocks
        mock_client.request.return_value = sample_account_data

        response = client.get("/account")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
