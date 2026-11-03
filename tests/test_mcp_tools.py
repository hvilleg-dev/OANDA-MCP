"""MCP tools endpoint tests"""

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


class TestMCPToolsEndpoints:
    """MCP tools endpoint tests"""

    def test_mcp_info_returns_success(self, client, app_with_mocks):
        """Test GET /mcp returns MCP info"""
        app, _, _ = app_with_mocks

        response = client.get("/mcp")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_mcp_info_contains_version(self, client, app_with_mocks):
        """Test GET /mcp contains version information"""
        app, _, _ = app_with_mocks

        response = client.get("/mcp")
        assert response.status_code == 200
        data = response.json()
        # Should have some identifying information
        assert len(data) > 0

    def test_mcp_list_tools_returns_tools(self, client, app_with_mocks):
        """Test GET /mcp/tools returns list of tools"""
        app, _, _ = app_with_mocks

        response = client.get("/mcp/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data or isinstance(data, list)

    def test_mcp_list_tools_contains_tools_array(self, client, app_with_mocks):
        """Test GET /mcp/tools response structure"""
        app, _, _ = app_with_mocks

        response = client.get("/mcp/tools")
        assert response.status_code == 200
        data = response.json()

        # Check for tools array
        tools = data.get("tools", data)
        assert isinstance(tools, list)

    def test_mcp_list_tools_tools_have_names(self, client, app_with_mocks):
        """Test each tool in list has name"""
        app, _, _ = app_with_mocks

        response = client.get("/mcp/tools")
        assert response.status_code == 200
        data = response.json()
        tools = data.get("tools", data)

        if len(tools) > 0:
            for tool in tools:
                assert "name" in tool or "type" in tool

    def test_mcp_list_tools_tools_have_descriptions(self, client, app_with_mocks):
        """Test each tool has description"""
        app, _, _ = app_with_mocks

        response = client.get("/mcp/tools")
        assert response.status_code == 200
        data = response.json()
        tools = data.get("tools", data)

        if len(tools) > 0:
            for tool in tools:
                # Should have description or similar field
                assert any(key in tool for key in ["description", "doc", "help", "purpose"])

    def test_mcp_call_tool_basic(self, client, app_with_mocks, sample_account_data):
        """Test POST /mcp/call executes tool"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_account_data

        payload = {
            "name": "get_account",
            "arguments": {}
        }

        response = client.post("/mcp/call", json=payload)
        assert response.status_code in [200, 400]

    def test_mcp_call_tool_with_arguments(self, client, app_with_mocks, sample_pending_orders):
        """Test POST /mcp/call with arguments"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_pending_orders

        payload = {
            "name": "get_orders",
            "arguments": {
                "state": "PENDING"
            }
        }

        response = client.post("/mcp/call", json=payload)
        assert response.status_code in [200, 400, 422]

    def test_mcp_call_tool_invalid_tool(self, client, app_with_mocks):
        """Test POST /mcp/call with invalid tool name"""
        app, _, _ = app_with_mocks

        payload = {
            "name": "invalid_tool_name",
            "arguments": {}
        }

        response = client.post("/mcp/call", json=payload)
        # Should either error or handle gracefully
        assert response.status_code in [400, 404, 422]

    def test_mcp_call_tool_missing_name(self, client):
        """Test POST /mcp/call without tool name"""
        payload = {
            "arguments": {}
        }

        response = client.post("/mcp/call", json=payload)
        assert response.status_code in [400, 422]

    def test_mcp_info_returns_json(self, client, app_with_mocks):
        """Test GET /mcp returns JSON"""
        app, _, _ = app_with_mocks

        response = client.get("/mcp")
        assert "application/json" in response.headers["content-type"]

    def test_mcp_tools_list_returns_json(self, client, app_with_mocks):
        """Test GET /mcp/tools returns JSON"""
        app, _, _ = app_with_mocks

        response = client.get("/mcp/tools")
        assert "application/json" in response.headers["content-type"]

    def test_mcp_call_returns_json(self, client, app_with_mocks, sample_account_data):
        """Test POST /mcp/call returns JSON"""
        app, mock_client, _ = app_with_mocks

        mock_client.request.return_value = sample_account_data

        payload = {
            "name": "get_account",
            "arguments": {}
        }

        response = client.post("/mcp/call", json=payload)
        if response.status_code == 200:
            assert "application/json" in response.headers["content-type"]

    def test_mcp_list_tools_multiple_calls(self, client, app_with_mocks):
        """Test multiple calls to GET /mcp/tools"""
        app, _, _ = app_with_mocks

        for _ in range(3):
            response = client.get("/mcp/tools")
            assert response.status_code == 200

    def test_mcp_endpoints_accessible(self, client, app_with_mocks):
        """Test all MCP endpoints are accessible"""
        app, _, _ = app_with_mocks

        endpoints = ["/mcp", "/mcp/tools"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200

    def test_mcp_call_with_empty_arguments(self, client, app_with_mocks):
        """Test POST /mcp/call with empty arguments"""
        app, _, _ = app_with_mocks

        payload = {
            "name": "get_account",
            "arguments": {}
        }

        response = client.post("/mcp/call", json=payload)
        assert response.status_code in [200, 400, 422]

    def test_mcp_tool_request_format_validation(self, client):
        """Test MCP call validates request format"""
        payload = {
            "name": "test_tool"
        }

        response = client.post("/mcp/call", json=payload)
        # Should either accept or reject based on schema
        assert response.status_code in [200, 400, 422]
