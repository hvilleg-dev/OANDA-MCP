"""
Enhanced logging service for OANDA MCP Server
Provides structured logging, metrics, and audit trails
"""

import logging
import logging.handlers
import os
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from enum import Enum
import asyncio
import asyncpg


class LogLevel(str, Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingConfig:
    """Configuration for logging service"""

    def __init__(
        self,
        log_level: str = "INFO",
        log_dir: str = "logs",
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 10,
        enable_json: bool = True,
        enable_file: bool = True,
        enable_console: bool = True,
    ):
        """
        Initialize logging configuration

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
            max_bytes: Maximum size of log file before rotation (bytes)
            backup_count: Number of backup files to keep
            enable_json: Enable JSON structured logging
            enable_file: Enable file logging
            enable_console: Enable console logging
        """
        self.log_level = log_level
        self.log_dir = log_dir
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.enable_json = enable_json
        self.enable_file = enable_file
        self.enable_console = enable_console

        # Create log directory if needed
        if enable_file:
            Path(log_dir).mkdir(parents=True, exist_ok=True)


class StructuredLogger:
    """Structured logger for JSON output"""

    def __init__(self, name: str, config: LoggingConfig):
        self.name = name
        self.config = config
        self.logger = self._setup_logger()
        self.correlation_id = None

    def _setup_logger(self) -> logging.Logger:
        """Setup logger with handlers"""
        logger = logging.getLogger(self.name)
        logger.setLevel(self.config.log_level)

        # Close and clear existing handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        # Console handler
        if self.config.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.config.log_level)

            if self.config.enable_json:
                formatter = logging.Formatter(
                    '%(message)s'
                )
            else:
                formatter = logging.Formatter(
                    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # File handler with rotation
        if self.config.enable_file:
            log_file = os.path.join(self.config.log_dir, f"{self.name}.log")
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.config.max_bytes,
                backupCount=self.config.backup_count
            )
            file_handler.setLevel(self.config.log_level)

            if self.config.enable_json:
                formatter = logging.Formatter('%(message)s')
            else:
                formatter = logging.Formatter(
                    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracking"""
        self.correlation_id = correlation_id

    def _format_message(
        self,
        level: str,
        message: str,
        **extra
    ) -> str:
        """Format message as JSON if enabled"""
        if not self.config.enable_json:
            return message

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "logger": self.name,
            "message": message,
        }

        if self.correlation_id:
            log_entry["correlation_id"] = self.correlation_id

        # Add extra fields
        log_entry.update(extra)

        return json.dumps(log_entry)

    def debug(self, message: str, **extra):
        """Log debug message"""
        msg = self._format_message("DEBUG", message, **extra)
        self.logger.debug(msg)

    def info(self, message: str, **extra):
        """Log info message"""
        msg = self._format_message("INFO", message, **extra)
        self.logger.info(msg)

    def warning(self, message: str, **extra):
        """Log warning message"""
        msg = self._format_message("WARNING", message, **extra)
        self.logger.warning(msg)

    def error(self, message: str, exc_info=None, **extra):
        """Log error message"""
        msg = self._format_message("ERROR", message, **extra)
        self.logger.error(msg, exc_info=exc_info)

    def critical(self, message: str, exc_info=None, **extra):
        """Log critical message"""
        msg = self._format_message("CRITICAL", message, **extra)
        self.logger.critical(msg, exc_info=exc_info)


class RequestLogger:
    """Logger for HTTP requests and responses"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def log_request(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        """Log incoming request"""
        if correlation_id:
            self.logger.set_correlation_id(correlation_id)

        # Sanitize sensitive headers
        sanitized_headers = self._sanitize_headers(headers or {})

        self.logger.info(
            f"Incoming request: {method} {path}",
            method=method,
            path=path,
            query_params=query_params,
            headers=sanitized_headers,
            body=body if method != "POST" else "<redacted>",
        )

    def log_response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        response_size: int = 0,
        body: Optional[Dict[str, Any]] = None,
    ):
        """Log response"""
        self.logger.info(
            f"Response: {method} {path} {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            response_size=response_size,
            body=body if status_code < 400 else "<redacted>",
        )

    def log_error(
        self,
        method: str,
        path: str,
        status_code: int,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        exception: Optional[Exception] = None,
        duration_ms: float = 0,
    ):
        """Log error response"""
        self.logger.error(
            f"Error response: {method} {path} {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            error_code=error_code,
            error_message=error_message,
            duration_ms=round(duration_ms, 2),
            exc_info=exception is not None,
        )

    @staticmethod
    def _sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive headers from logging"""
        sensitive_headers = {
            "authorization", "x-api-key", "x-auth-token",
            "cookie", "x-csrf-token", "x-access-token"
        }

        sanitized = {}
        for key, value in headers.items():
            if key.lower() not in sensitive_headers:
                sanitized[key] = value
            else:
                sanitized[key] = "<redacted>"

        return sanitized


class DatabaseLogger:
    """Logger for database operations"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def log_query(
        self,
        operation: str,
        table: str,
        duration_ms: float,
        rows_affected: int = 0,
        row_count: int = 0,
        query: Optional[str] = None,
    ):
        """Log database query operation"""
        self.logger.debug(
            f"Database {operation}: {table}",
            operation=operation,
            table=table,
            duration_ms=round(duration_ms, 2),
            rows_affected=rows_affected,
            row_count=row_count,
            query="<redacted>" if query else None,
        )

    def log_pool_stats(
        self,
        min_size: int,
        max_size: int,
        current_size: int,
        idle_connections: int,
    ):
        """Log connection pool statistics"""
        self.logger.debug(
            "Connection pool stats",
            min_size=min_size,
            max_size=max_size,
            current_size=current_size,
            idle_connections=idle_connections,
        )


class MetricsCollector:
    """Collect metrics for requests and responses"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    async def record_request(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        request_size: int = 0,
        response_size: int = 0,
    ):
        """Record request metrics"""
        async with self.lock:
            key = f"{method} {endpoint}"

            if key not in self.metrics:
                self.metrics[key] = {
                    "count": 0,
                    "total_duration": 0,
                    "min_duration": float('inf'),
                    "max_duration": 0,
                    "status_codes": {},
                    "errors": 0,
                    "total_request_size": 0,
                    "total_response_size": 0,
                }

            m = self.metrics[key]
            m["count"] += 1
            m["total_duration"] += duration_ms
            m["min_duration"] = min(m["min_duration"], duration_ms)
            m["max_duration"] = max(m["max_duration"], duration_ms)
            m["status_codes"][status_code] = m["status_codes"].get(status_code, 0) + 1
            m["total_request_size"] += request_size
            m["total_response_size"] += response_size

            if status_code >= 400:
                m["errors"] += 1

    def get_metrics(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get collected metrics"""
        if endpoint:
            key = next((k for k in self.metrics if endpoint in k), None)
            if key:
                return self._calculate_percentiles(self.metrics[key], key)
            return {}

        result = {}
        for endpoint, metrics in self.metrics.items():
            result[endpoint] = self._calculate_percentiles(metrics, endpoint)

        return result

    @staticmethod
    def _calculate_percentiles(
        metrics: Dict[str, Any],
        endpoint: str
    ) -> Dict[str, Any]:
        """Calculate percentiles for response times"""
        if metrics["count"] == 0:
            return {}

        avg_duration = metrics["total_duration"] / metrics["count"]
        error_rate = metrics["errors"] / metrics["count"]

        return {
            "endpoint": endpoint,
            "count": metrics["count"],
            "avg_duration_ms": round(avg_duration, 2),
            "min_duration_ms": round(metrics["min_duration"], 2),
            "max_duration_ms": round(metrics["max_duration"], 2),
            "status_codes": metrics["status_codes"],
            "error_count": metrics["errors"],
            "error_rate": round(error_rate, 4),
            "avg_request_size": round(
                metrics["total_request_size"] / metrics["count"], 2
            ) if metrics["total_request_size"] > 0 else 0,
            "avg_response_size": round(
                metrics["total_response_size"] / metrics["count"], 2
            ) if metrics["total_response_size"] > 0 else 0,
        }

    async def clear_metrics(self):
        """Clear all metrics"""
        async with self.lock:
            self.metrics.clear()


class AuditLogger:
    """Logger for sensitive operations audit trail"""

    def __init__(self, logger: StructuredLogger, db_pool: Optional[asyncpg.Pool] = None):
        self.logger = logger
        self.db_pool = db_pool

    async def log_operation(
        self,
        operation: str,
        resource: str,
        user_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log sensitive operation to audit trail"""
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "resource": resource,
            "user_id": user_id,
            "status": status,
            "changes": changes,
            "details": details,
        }

        self.logger.info(
            f"Audit: {operation} on {resource}",
            operation=operation,
            resource=resource,
            user_id=user_id,
            status=status,
            changes=changes,
        )

        # Log to database if pool available
        if self.db_pool:
            await self._log_to_db(audit_entry)

    async def _log_to_db(self, entry: Dict[str, Any]):
        """Store audit log in database"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO audit_log
                        (timestamp, operation, resource, user_id, status, changes, details)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    entry["timestamp"],
                    entry["operation"],
                    entry["resource"],
                    entry["user_id"],
                    entry["status"],
                    json.dumps(entry["changes"]) if entry["changes"] else None,
                    json.dumps(entry["details"]) if entry["details"] else None,
                )
        except Exception as e:
            self.logger.error(
                "Failed to log audit entry to database",
                error=str(e),
            )


class LoggingService:
    """Main logging service combining all components"""

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        config: Optional[LoggingConfig] = None,
        db_pool: Optional[asyncpg.Pool] = None,
        force_reinit: bool = False,
    ):
        # Only initialize once unless force_reinit is True
        if LoggingService._initialized and not force_reinit:
            return

        self.config = config or LoggingConfig()
        self.db_pool = db_pool

        # Initialize structured logger
        self.logger = StructuredLogger("oanda_mcp", self.config)

        # Initialize component loggers
        self.request_logger = RequestLogger(self.logger)
        self.database_logger = DatabaseLogger(self.logger)
        self.metrics = MetricsCollector(self.logger)
        self.audit = AuditLogger(self.logger, db_pool)

        LoggingService._initialized = True

    def configure(
        self,
        log_level: str = "INFO",
        enable_json: bool = True,
        log_dir: str = "logs",
    ):
        """Reconfigure logging service"""
        self.config = LoggingConfig(
            log_level=log_level,
            enable_json=enable_json,
            log_dir=log_dir,
        )
        self.logger = StructuredLogger("oanda_mcp", self.config)
        self.request_logger = RequestLogger(self.logger)
        self.database_logger = DatabaseLogger(self.logger)

    async def init_audit_table(self):
        """Initialize audit log table in database"""
        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id              SERIAL PRIMARY KEY,
                        timestamp       TIMESTAMPTZ NOT NULL,
                        operation       TEXT NOT NULL,
                        resource        TEXT NOT NULL,
                        user_id         TEXT,
                        status          TEXT NOT NULL,
                        changes         JSONB,
                        details         JSONB,
                        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                        ON audit_log(timestamp DESC);
                    CREATE INDEX IF NOT EXISTS idx_audit_operation
                        ON audit_log(operation);
                    CREATE INDEX IF NOT EXISTS idx_audit_resource
                        ON audit_log(resource);
                """)
            self.logger.info("Audit log table initialized")
        except Exception as e:
            self.logger.error("Failed to initialize audit log table", error=str(e))

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        return {
            "endpoints": self.metrics.get_metrics(),
            "logger_name": self.logger.name,
            "config": {
                "level": self.config.log_level,
                "json_enabled": self.config.enable_json,
                "file_enabled": self.config.enable_file,
                "console_enabled": self.config.enable_console,
            }
        }
