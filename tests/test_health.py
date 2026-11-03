"""Health check endpoint tests"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from datetime import datetime


@pytest.fixture
def app_with_mocks():
    """Fixture to create FastAPI app with mocked dependencies"""
    with patch.dict('os.environ', {
        'OANDA_API_KEY': 'test-key',
        'OANDA_ACCOUNT_ID': '123456',
        'OANDA_ENVIRONMENT': 'practice',
        'DATABASE_URL': 'postgresql://test:test@localhost/test_db'
    }):
        # Mock the database pool
        with patch('server.db_pool', new_callable=AsyncMock) as mock_pool:
            # Import after patching environment
            from server import app
            yield app, mock_pool


@pytest.fixture
def client(app_with_mocks):
    """FastAPI test client"""
    app, _ = app_with_mocks
    return TestClient(app)


class TestHealthEndpoints:
    """Health check endpoint tests"""

    def test_root_endpoint_returns_ok(self, client):
        """Test GET / returns health status"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "message" in data

    def test_root_endpoint_response_format(self, client):
        """Test GET / response format is correct"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert isinstance(data, dict)
        assert "status" in data
        assert "timestamp" in data or "message" in data

    def test_health_endpoint_returns_ok(self, client):
        """Test GET /health returns health status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]

    def test_health_endpoint_response_format(self, client):
        """Test GET /health response format includes required fields"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert isinstance(data, dict)
        assert "status" in data
        assert "environment" in data or "mode" in data

    def test_health_endpoint_includes_environment_info(self, client):
        """Test GET /health includes environment information"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        # Should have environment info
        assert any(key in data for key in ["environment", "mode", "env"])

    def test_multiple_health_checks(self, client):
        """Test multiple sequential health checks"""
        for _ in range(3):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "ok"]

    def test_root_and_health_both_accessible(self, client):
        """Test both root and health endpoints are accessible"""
        root_response = client.get("/")
        health_response = client.get("/health")

        assert root_response.status_code == 200
        assert health_response.status_code == 200

        root_data = root_response.json()
        health_data = health_response.json()

        assert "status" in root_data
        assert "status" in health_data

    def test_health_check_response_headers(self, client):
        """Test health check response includes proper headers"""
        response = client.get("/health")
        assert response.status_code == 200
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]

    def test_root_check_response_headers(self, client):
        """Test root check response includes proper headers"""
        response = client.get("/")
        assert response.status_code == 200
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]

    @pytest.mark.parametrize("endpoint", ["/", "/health"])
    def test_health_endpoints_no_params_required(self, client, endpoint):
        """Test health endpoints work without any parameters"""
        response = client.get(endpoint)
        assert response.status_code == 200
        assert response.json() is not None

    def test_health_check_performance(self, client):
        """Test health check responds quickly"""
        import time
        start = time.time()
        response = client.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 1.0  # Should respond within 1 second

    def test_root_check_performance(self, client):
        """Test root check responds quickly"""
        import time
        start = time.time()
        response = client.get("/")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 1.0  # Should respond within 1 second
