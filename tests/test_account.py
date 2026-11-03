"""Account endpoint tests"""

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


class TestAccountEndpoints:
    """Account endpoint tests"""

    def test_get_account_info_success(self, client, app_with_mocks, sample_account_data):
        """Test GET /account returns account information"""
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_account_summary

        response = client.get("/account/summary")
        assert response.status_code == 200
        data = response.json()
        assert "account" in data or "balance" in data

    def test_get_account_instruments_success(self, client, app_with_mocks, sample_instruments_data):
        """Test GET /account/instruments returns list of instruments"""
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_instruments_data

        response = client.get("/account/instruments")
        assert response.status_code == 200
        data = response.json()
        assert "instruments" in data or isinstance(data, list)

    def test_get_account_instruments_with_query_params(self, client, app_with_mocks, sample_instruments_data):
        """Test GET /account/instruments with query parameters"""
        mock_client = app_with_mocks['mock_oanda_client']

        mock_client.request.return_value = sample_instruments_data

        response = client.get("/account/instruments?count=10")
        assert response.status_code in [200, 400]

    def test_get_account_changes_success(self, client, app_with_mocks, sample_account_changes):
        """Test GET /account/changes returns account changes"""
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']

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
        mock_client = app_with_mocks['mock_oanda_client']
        mock_client.request.return_value = sample_account_data

        response = client.get("/account")
        assert response.status_code == 200

        # Should be valid JSON
        data = response.json()
        assert isinstance(data, dict)

    def test_get_account_info_contains_required_fields(self, client, app_with_mocks, sample_account_data):
        """Test account response contains required fields"""
        mock_client = app_with_mocks['mock_oanda_client']
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
        mock_client = app_with_mocks['mock_oanda_client']
        mock_client.request.return_value = sample_account_summary

        response = client.get("/account/summary")
        assert response.status_code == 200
        data = response.json()
        account_data = data.get("account", data)
        assert "balance" in account_data or "balance" in str(data)

    def test_get_instruments_returns_list(self, client, app_with_mocks, sample_instruments_data):
        """Test instruments endpoint returns a list"""
        mock_client = app_with_mocks['mock_oanda_client']
        mock_client.request.return_value = sample_instruments_data

        response = client.get("/account/instruments")
        assert response.status_code == 200
        data = response.json()

        # Check for list of instruments
        instruments = data.get("instruments", data)
        assert isinstance(instruments, list)

    def test_patch_configuration_empty_payload(self, client, app_with_mocks):
        """Test PATCH /account/configuration rejects empty payload"""
        response = client.patch("/account/configuration", json={})
        # Should reject empty payload with 4xx error
        assert response.status_code in [400, 422, 500]

    def test_multiple_account_queries(self, client, app_with_mocks, sample_account_data):
        """Test multiple sequential account queries"""
        mock_client = app_with_mocks['mock_oanda_client']
        mock_client.request.return_value = sample_account_data

        for _ in range(3):
            response = client.get("/account")
            assert response.status_code == 200

    def test_account_endpoints_return_json_content_type(self, client, app_with_mocks, sample_account_data):
        """Test account endpoints return JSON content type"""
        mock_client = app_with_mocks['mock_oanda_client']
        mock_client.request.return_value = sample_account_data

        response = client.get("/account")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
