"""Tests for enhanced logging service"""

import pytest
import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from pathlib import Path

from src.logging_service import (
    LoggingService,
    LoggingConfig,
    StructuredLogger,
    RequestLogger,
    DatabaseLogger,
    MetricsCollector,
    AuditLogger,
    LogLevel,
)


class TestLoggingConfig:
    """Tests for LoggingConfig"""

    def test_default_config_creation(self):
        """Test default configuration creation"""
        config = LoggingConfig()
        assert config.log_level == "INFO"
        assert config.enable_json is True
        assert config.enable_file is True
        assert config.enable_console is True
        assert config.backup_count == 10
        assert config.max_bytes == 10 * 1024 * 1024

    def test_custom_config_creation(self):
        """Test custom configuration creation"""
        config = LoggingConfig(
            log_level="DEBUG",
            enable_json=False,
            backup_count=5,
        )
        assert config.log_level == "DEBUG"
        assert config.enable_json is False
        assert config.backup_count == 5

    def test_log_directory_creation(self):
        """Test log directory is created on config init"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "logs")
            config = LoggingConfig(log_dir=log_dir)
            assert os.path.exists(log_dir)


class TestStructuredLogger:
    """Tests for StructuredLogger"""

    def test_logger_setup(self):
        """Test logger setup with config"""
        config = LoggingConfig(
            log_dir="logs",
            enable_json=False,
            enable_console=True,
            enable_file=False,  # Disable file to avoid Windows locking issues in tests
        )
        logger = StructuredLogger("test", config)
        assert logger.name == "test"
        assert logger.config == config
        assert logger.logger is not None

    def test_correlation_id_tracking(self):
        """Test setting and tracking correlation ID"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        logger = StructuredLogger("test", config)

        correlation_id = "test-correlation-123"
        logger.set_correlation_id(correlation_id)
        assert logger.correlation_id == correlation_id

    def test_json_format_message(self):
        """Test JSON message formatting"""
        config = LoggingConfig(enable_json=True, enable_console=False, enable_file=False)
        logger = StructuredLogger("test", config)
        logger.set_correlation_id("test-123")

        msg = logger._format_message("INFO", "Test message", custom_field="value")
        parsed = json.loads(msg)

        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert parsed["correlation_id"] == "test-123"
        assert parsed["custom_field"] == "value"

    def test_plaintext_format_message(self):
        """Test plaintext message formatting"""
        config = LoggingConfig(enable_json=False, enable_console=False, enable_file=False)
        logger = StructuredLogger("test", config)

        msg = logger._format_message("INFO", "Test message", custom_field="value")
        assert msg == "Test message"

    def test_logging_methods(self):
        """Test all logging methods work without exception"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        logger = StructuredLogger("test", config)

        # Should not raise
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")


class TestRequestLogger:
    """Tests for RequestLogger"""

    def test_request_logging(self):
        """Test logging incoming request"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        logger = StructuredLogger("test", config)
        req_logger = RequestLogger(logger)

        # Should not raise
        req_logger.log_request(
            method="GET",
            path="/account",
            query_params={"include": "summary"},
            headers={"User-Agent": "test-client"},
            correlation_id="test-123",
        )
        assert logger.correlation_id == "test-123"

    def test_response_logging(self):
        """Test logging response"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        logger = StructuredLogger("test", config)
        req_logger = RequestLogger(logger)

        # Should not raise
        req_logger.log_response(
            method="GET",
            path="/account",
            status_code=200,
            duration_ms=45.2,
            response_size=1024,
        )

    def test_error_logging(self):
        """Test logging error response"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        logger = StructuredLogger("test", config)
        req_logger = RequestLogger(logger)

        # Should not raise
        req_logger.log_error(
            method="POST",
            path="/order/market",
            status_code=400,
            error_code="INVALID_PARAMETER",
            error_message="Invalid instrument",
        )

    def test_header_sanitization(self):
        """Test sensitive headers are redacted"""
        headers = {
            "User-Agent": "test",
            "Authorization": "Bearer token123",
            "X-API-Key": "secret-key",
            "X-CSRF-Token": "csrf123",
            "Content-Type": "application/json",
        }

        sanitized = RequestLogger._sanitize_headers(headers)

        assert sanitized["User-Agent"] == "test"
        assert sanitized["Content-Type"] == "application/json"
        assert sanitized["Authorization"] == "<redacted>"
        assert sanitized["X-API-Key"] == "<redacted>"
        assert sanitized["X-CSRF-Token"] == "<redacted>"

    def test_empty_headers_sanitization(self):
        """Test sanitization with empty headers"""
        sanitized = RequestLogger._sanitize_headers({})
        assert sanitized == {}


class TestDatabaseLogger:
    """Tests for DatabaseLogger"""

    def test_query_logging(self):
        """Test logging database query"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        logger = StructuredLogger("test", config)
        db_logger = DatabaseLogger(logger)

        # Should not raise
        db_logger.log_query(
            operation="SELECT",
            table="request_log",
            duration_ms=2.5,
            row_count=150,
        )

    def test_insert_logging(self):
        """Test logging INSERT operation"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        logger = StructuredLogger("test", config)
        db_logger = DatabaseLogger(logger)

        # Should not raise
        db_logger.log_query(
            operation="INSERT",
            table="order_log",
            duration_ms=1.2,
            rows_affected=1,
        )

    def test_pool_stats_logging(self):
        """Test logging connection pool statistics"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        logger = StructuredLogger("test", config)
        db_logger = DatabaseLogger(logger)

        # Should not raise
        db_logger.log_pool_stats(
            min_size=2,
            max_size=10,
            current_size=5,
            idle_connections=3,
        )


@pytest.mark.asyncio
class TestMetricsCollector:
    """Tests for MetricsCollector"""

    async def test_record_request(self):
        """Test recording request metrics"""
        config = LoggingConfig(enable_console=False, enable_file=False)
        logger = StructuredLogger("test", config)
        metrics = MetricsCollector(logger)

        await metrics.record_request(
            endpoint="/account",
            method="GET",
            duration_ms=50.0,
            status_code=200,
            request_size=100,
            response_size=1024,
        )

        result = metrics.get_metrics("/account")
        assert result["endpoint"] == "GET /account"
        assert result["count"] == 1
        assert result["avg_duration_ms"] == 50.0
        assert result["status_codes"][200] == 1
        assert result["error_count"] == 0

    async def test_multiple_requests(self):
        """Test recording multiple requests"""
        config = LoggingConfig(enable_console=False, enable_file=False)
        logger = StructuredLogger("test", config)
        metrics = MetricsCollector(logger)

        for i in range(5):
            await metrics.record_request(
                endpoint="/account",
                method="GET",
                duration_ms=50.0 + i * 10,
                status_code=200,
            )

        result = metrics.get_metrics("/account")
        assert result["count"] == 5
        assert result["min_duration_ms"] == 50.0
        assert result["max_duration_ms"] == 90.0

    async def test_error_tracking(self):
        """Test tracking errors in metrics"""
        config = LoggingConfig(enable_console=False, enable_file=False)
        logger = StructuredLogger("test", config)
        metrics = MetricsCollector(logger)

        # Record successful requests
        for _ in range(8):
            await metrics.record_request(
                endpoint="/account",
                method="GET",
                duration_ms=50.0,
                status_code=200,
            )

        # Record error requests
        for _ in range(2):
            await metrics.record_request(
                endpoint="/account",
                method="GET",
                duration_ms=100.0,
                status_code=500,
            )

        result = metrics.get_metrics("/account")
        assert result["count"] == 10
        assert result["error_count"] == 2
        assert result["error_rate"] == 0.2

    async def test_status_code_distribution(self):
        """Test status code distribution in metrics"""
        config = LoggingConfig(enable_console=False, enable_file=False)
        logger = StructuredLogger("test", config)
        metrics = MetricsCollector(logger)

        status_codes = [200, 200, 201, 400, 500, 200]
        for status in status_codes:
            await metrics.record_request(
                endpoint="/order/market",
                method="POST",
                duration_ms=50.0,
                status_code=status,
            )

        result = metrics.get_metrics("/order/market")
        assert result["status_codes"][200] == 3
        assert result["status_codes"][201] == 1
        assert result["status_codes"][400] == 1
        assert result["status_codes"][500] == 1

    async def test_clear_metrics(self):
        """Test clearing all metrics"""
        config = LoggingConfig(enable_console=False, enable_file=False)
        logger = StructuredLogger("test", config)
        metrics = MetricsCollector(logger)

        await metrics.record_request(
            endpoint="/account",
            method="GET",
            duration_ms=50.0,
            status_code=200,
        )

        result = metrics.get_metrics("/account")
        assert result["count"] == 1

        await metrics.clear_metrics()
        result = metrics.get_metrics("/account")
        assert result == {}


@pytest.mark.asyncio
class TestAuditLogger:
    """Tests for AuditLogger"""

    async def test_audit_logging_without_db(self):
        """Test audit logging without database"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        logger = StructuredLogger("test", config)
        audit_logger = AuditLogger(logger)

        # Should not raise
        await audit_logger.log_operation(
            operation="CREATE_ORDER",
            resource="order-123",
            user_id="user-456",
            changes={"status": "FILLED"},
            status="SUCCESS",
        )

    async def test_audit_logging_with_db(self):
        """Test audit logging with database pool"""
        config = LoggingConfig(enable_console=False, enable_file=False)
        logger = StructuredLogger("test", config)

        # Mock database pool
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=None)

        audit_logger = AuditLogger(logger, mock_pool)

        await audit_logger.log_operation(
            operation="CLOSE_TRADE",
            resource="trade-789",
            user_id="user-123",
            changes={"status": "CLOSED", "realized_pl": "150.00"},
            status="SUCCESS",
            details={"method": "api_call"},
        )

        # Verify database was called
        mock_conn.execute.assert_called_once()

    async def test_audit_logging_failure_handling(self):
        """Test audit logging handles database errors gracefully"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        logger = StructuredLogger("test", config)

        # Mock database pool that raises error
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(side_effect=Exception("DB Error"))

        audit_logger = AuditLogger(logger, mock_pool)

        # Should not raise
        await audit_logger.log_operation(
            operation="DELETE_ORDER",
            resource="order-999",
            status="FAILED",
        )


class TestLoggingService:
    """Tests for LoggingService singleton"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton between tests"""
        LoggingService._instance = None
        LoggingService._initialized = False
        yield
        LoggingService._instance = None
        LoggingService._initialized = False

    def test_singleton_creation(self):
        """Test LoggingService is a singleton"""
        service1 = LoggingService()
        service2 = LoggingService()
        assert service1 is service2

    def test_service_initialization(self):
        """Test service initialization"""
        service = LoggingService()
        assert service.logger is not None
        assert service.request_logger is not None
        assert service.database_logger is not None
        assert isinstance(service.metrics, MetricsCollector)
        assert isinstance(service.audit, AuditLogger)

    def test_service_with_config(self):
        """Test service with custom config"""
        config = LoggingConfig(
            log_level="DEBUG",
            enable_json=True,
        )
        service = LoggingService(config=config)
        assert service.config.log_level == "DEBUG"

    def test_service_with_db_pool(self):
        """Test service with database pool"""
        mock_pool = MagicMock()
        service = LoggingService(db_pool=mock_pool)
        assert service.db_pool == mock_pool
        assert service.audit.db_pool == mock_pool

    def test_configure_service(self):
        """Test reconfiguring service"""
        service = LoggingService()
        original_level = service.config.log_level

        service.configure(log_level="DEBUG", enable_json=False)

        assert service.config.log_level == "DEBUG"
        assert service.config.enable_json is False

    def test_get_metrics_summary(self):
        """Test getting metrics summary"""
        service = LoggingService()
        summary = service.get_metrics_summary()

        assert "endpoints" in summary
        assert "logger_name" in summary
        assert "config" in summary
        assert summary["logger_name"] == "oanda_mcp"

    @pytest.mark.asyncio
    async def test_init_audit_table_without_pool(self):
        """Test audit table init without pool"""
        service = LoggingService(db_pool=None)
        # Should not raise
        await service.init_audit_table()

    @pytest.mark.asyncio
    async def test_init_audit_table_with_pool(self):
        """Test audit table initialization with pool"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=None)

        service = LoggingService(db_pool=mock_pool)
        await service.init_audit_table()

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0][0]
        assert "CREATE TABLE" in call_args
        assert "audit_log" in call_args


class TestLogLevelEnum:
    """Tests for LogLevel enum"""

    def test_log_level_values(self):
        """Test all log level values are defined"""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for logging service"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton between tests"""
        LoggingService._instance = None
        LoggingService._initialized = False
        yield
        LoggingService._instance = None
        LoggingService._initialized = False

    async def test_full_request_lifecycle(self):
        """Test logging a full request lifecycle"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        service = LoggingService(config=config)

        # Log request
        service.request_logger.log_request(
            method="GET",
            path="/account",
            query_params={"include": "summary"},
            headers={"User-Agent": "test"},
            correlation_id="req-123",
        )

        # Record metrics
        await service.metrics.record_request(
            endpoint="/account",
            method="GET",
            duration_ms=45.2,
            status_code=200,
            response_size=1024,
        )

        # Log response
        service.request_logger.log_response(
            method="GET",
            path="/account",
            status_code=200,
            duration_ms=45.2,
            response_size=1024,
        )

        # Check metrics were recorded
        metrics = service.metrics.get_metrics("/account")
        assert metrics["count"] == 1
        assert metrics["avg_duration_ms"] == 45.2

    async def test_error_request_lifecycle(self):
        """Test logging error request lifecycle"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        service = LoggingService(config=config)

        # Log request
        service.request_logger.log_request(
            method="POST",
            path="/order/market",
            body={"instrument": "INVALID"},
            correlation_id="req-456",
        )

        # Record error metrics
        await service.metrics.record_request(
            endpoint="/order/market",
            method="POST",
            duration_ms=12.3,
            status_code=400,
        )

        # Log error
        service.request_logger.log_error(
            method="POST",
            path="/order/market",
            status_code=400,
            error_code="INVALID_INSTRUMENT",
            error_message="Instrument not found",
        )

        # Check error was recorded
        metrics = service.metrics.get_metrics("/order/market")
        assert metrics["error_count"] == 1
        assert metrics["status_codes"][400] == 1

    async def test_database_operation_logging(self):
        """Test logging database operations"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        service = LoggingService(config=config)

        # Log SELECT
        service.database_logger.log_query(
            operation="SELECT",
            table="request_log",
            duration_ms=2.5,
            row_count=100,
        )

        # Log INSERT
        service.database_logger.log_query(
            operation="INSERT",
            table="order_log",
            duration_ms=1.2,
            rows_affected=1,
        )

        # Log pool stats
        service.database_logger.log_pool_stats(
            min_size=2,
            max_size=10,
            current_size=5,
            idle_connections=3,
        )

    async def test_audit_trail(self):
        """Test audit trail logging"""
        config = LoggingConfig(enable_console=True, enable_file=False)
        service = LoggingService(config=config)

        # Log sensitive operation
        await service.audit.log_operation(
            operation="CREATE_ORDER",
            resource="order-123",
            user_id="user-456",
            changes={
                "instrument": "EUR_USD",
                "units": "1000",
                "type": "MARKET",
            },
            status="SUCCESS",
            details={"method": "api", "client_version": "1.0"},
        )

        # Log another operation
        await service.audit.log_operation(
            operation="MODIFY_TRADE",
            resource="trade-789",
            user_id="user-456",
            changes={
                "stop_loss": "1.07000",
            },
            status="SUCCESS",
        )
