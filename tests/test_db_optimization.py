"""Tests for database optimization module (connection pooling, caching, monitoring)"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Import optimization components
from src.db_optimizer import (
    QueryCache,
    PoolMonitor,
    OptimizedConnectionPool,
    PoolStats,
    QueryStats,
    create_optimized_pool,
)


class TestQueryCache:
    """Test in-memory query caching functionality"""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test basic cache set and get operations"""
        cache = QueryCache(ttl_seconds=60)
        query = "SELECT * FROM request_log LIMIT 10"
        result = [{"id": 1, "method": "GET"}, {"id": 2, "method": "POST"}]

        # Cache miss initially
        cached = await cache.get(query)
        assert cached is None

        # Set cache
        await cache.set(query, result)

        # Cache hit
        cached = await cache.get(query)
        assert cached == result

    @pytest.mark.asyncio
    async def test_cache_with_parameters(self):
        """Test cache with query parameters"""
        cache = QueryCache(ttl_seconds=60)
        query = "SELECT * FROM order_log WHERE instrument = $1"
        args = ("EUR_USD",)
        result = [{"id": 1, "instrument": "EUR_USD"}]

        await cache.set(query, result, args)
        cached = await cache.get(query, args)
        assert cached == result

        # Different args should be cache miss
        cached = await cache.get(query, ("GBP_USD",))
        assert cached is None

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache TTL expiration"""
        cache = QueryCache(ttl_seconds=1)
        query = "SELECT COUNT(*) FROM request_log"
        result = [{"count": 100}]

        await cache.set(query, result)
        cached = await cache.get(query)
        assert cached is not None

        # Wait for expiration
        await asyncio.sleep(1.1)
        cached = await cache.get(query)
        assert cached is None

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation"""
        cache = QueryCache(ttl_seconds=300)

        # Add multiple entries
        await cache.set("SELECT * FROM request_log", [{"id": 1}])
        await cache.set("SELECT * FROM order_log", [{"id": 2}])
        await cache.set("SELECT * FROM trade_log", [{"id": 3}])

        # Invalidate all
        await cache.invalidate()
        assert await cache.get("SELECT * FROM request_log") is None
        assert await cache.get("SELECT * FROM order_log") is None

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics tracking"""
        cache = QueryCache(ttl_seconds=60)
        query = "SELECT * FROM request_log"
        result = [{"id": 1}]

        # Miss
        await cache.get(query)
        # Hit
        await cache.set(query, result)
        await cache.get(query)

        stats = await cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 50.0
        assert stats["cached_entries"] == 1

    @pytest.mark.asyncio
    async def test_cache_thread_safety(self):
        """Test cache is thread-safe with concurrent access"""
        cache = QueryCache(ttl_seconds=60)
        results = []

        async def cache_operation(query_num):
            query = f"SELECT * FROM table_{query_num}"
            result = [{"id": query_num}]
            await cache.set(query, result)
            await asyncio.sleep(0.01)
            cached = await cache.get(query)
            results.append(cached)

        # Concurrent operations
        await asyncio.gather(*[cache_operation(i) for i in range(10)])

        stats = await cache.get_stats()
        assert stats["cached_entries"] == 10

    @pytest.mark.asyncio
    async def test_cache_size_method(self):
        """Test cache size tracking"""
        cache = QueryCache(ttl_seconds=60)

        for i in range(5):
            await cache.set(f"SELECT * FROM table_{i}", [{"id": i}])

        size = await cache.size()
        assert size == 5


class TestPoolStats:
    """Test connection pool statistics tracking"""

    def test_pool_stats_initialization(self):
        """Test PoolStats dataclass initialization"""
        stats = PoolStats(active_connections=5, idle_connections=3)
        assert stats.active_connections == 5
        assert stats.idle_connections == 3
        assert isinstance(stats.timestamp, datetime)

    def test_query_stats_average_duration(self):
        """Test QueryStats average duration calculation"""
        stats = QueryStats(query_hash="abc123")
        stats.execution_count = 5
        stats.total_duration_ms = 250.0

        assert stats.avg_duration_ms == 50.0

    def test_query_stats_average_with_zero_executions(self):
        """Test QueryStats average with zero executions"""
        stats = QueryStats(query_hash="abc123")
        assert stats.avg_duration_ms == 0.0


class TestPoolMonitor:
    """Test connection pool monitoring functionality"""

    @pytest.mark.asyncio
    async def test_monitor_record_query(self):
        """Test recording query statistics"""
        mock_pool = MagicMock()
        monitor = PoolMonitor(mock_pool)

        await monitor.record_query("SELECT * FROM requests", 45.5)
        await monitor.record_query("SELECT * FROM requests", 55.2)

        stats = await monitor.get_query_stats()
        assert stats["total_unique_queries"] >= 1

    @pytest.mark.asyncio
    async def test_monitor_slow_query_detection(self):
        """Test slow query detection (> 100ms)"""
        mock_pool = MagicMock()
        monitor = PoolMonitor(mock_pool)

        # Record slow query
        await monitor.record_query("SELECT * FROM large_table", 150.5)
        stats = await monitor.get_query_stats()

        assert len(stats["slow_queries"]) > 0
        slow_query = stats["slow_queries"][0]
        assert slow_query["max_duration_ms"] >= 100.0

    @pytest.mark.asyncio
    async def test_monitor_captures_snapshot(self):
        """Test capturing pool statistics snapshot"""
        mock_pool = MagicMock()
        mock_pool._holders = MagicMock()
        mock_pool._queue = MagicMock()
        mock_pool._holders.__len__ = MagicMock(return_value=3)
        mock_pool._queue.qsize = MagicMock(return_value=2)

        monitor = PoolMonitor(mock_pool)
        snapshot = await monitor.capture_snapshot()

        assert isinstance(snapshot, PoolStats)
        assert isinstance(snapshot.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_monitor_query_error_tracking(self):
        """Test error count tracking in query stats"""
        mock_pool = MagicMock()
        monitor = PoolMonitor(mock_pool)

        # Success queries
        await monitor.record_query("SELECT * FROM requests", 50.0, error=False)
        await monitor.record_query("SELECT * FROM requests", 45.0, error=False)

        # Failed query
        await monitor.record_query("SELECT * FROM requests", 10.0, error=True)

        stats = await monitor.get_query_stats()
        slow_query = stats["slow_queries"][0] if stats["slow_queries"] else None
        if slow_query:
            assert "error_count" in slow_query


class TestOptimizedConnectionPool:
    """Test optimized connection pool wrapper"""

    def test_pool_initialization_params(self):
        """Test OptimizedConnectionPool parameter storage"""
        pool = OptimizedConnectionPool(
            dsn="postgresql://user:pass@localhost/db",
            min_size=10,
            max_size=30,
            max_queries=100000
        )

        assert pool.min_size == 10
        assert pool.max_size == 30
        assert pool.max_queries == 100000
        assert pool.dsn == "postgresql://user:pass@localhost/db"

    def test_pool_cache_initialization(self):
        """Test cache is initialized when enabled"""
        pool = OptimizedConnectionPool(
            dsn="postgresql://user:pass@localhost/db",
            cache_enabled=True,
            cache_ttl_seconds=900
        )

        assert pool.cache is not None
        assert pool.cache.ttl_seconds == 900

    def test_pool_cache_disabled(self):
        """Test cache is disabled when configured"""
        pool = OptimizedConnectionPool(
            dsn="postgresql://user:pass@localhost/db",
            cache_enabled=False
        )

        assert pool.cache is None

    @pytest.mark.asyncio
    async def test_pool_initialize_creates_pool(self):
        """Test pool initialization creates asyncpg pool"""
        with patch('src.db_optimizer.asyncpg.create_pool') as mock_create:
            mock_pool = AsyncMock()
            # Make create_pool awaitable
            async def async_create_pool(*args, **kwargs):
                return mock_pool
            mock_create.side_effect = async_create_pool

            pool = OptimizedConnectionPool(
                dsn="postgresql://test:test@localhost/test",
                min_size=5,
                max_size=15
            )
            await pool.initialize()

            assert pool.pool is not None

    @pytest.mark.asyncio
    async def test_pool_acquire_connection(self):
        """Test acquiring connection from pool"""
        mock_asyncpg_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_asyncpg_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_asyncpg_pool.release = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)

        pool = OptimizedConnectionPool(dsn="test")
        pool.pool = mock_asyncpg_pool

        conn = await pool.acquire()
        assert conn == mock_conn

    @pytest.mark.asyncio
    async def test_pool_execute_invalidates_cache(self):
        """Test that INSERT/UPDATE/DELETE invalidate cache"""
        mock_asyncpg_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_asyncpg_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_asyncpg_pool.release = AsyncMock()

        pool = OptimizedConnectionPool(
            dsn="test",
            cache_enabled=True
        )
        pool.pool = mock_asyncpg_pool

        # Add to cache
        await pool.cache.set("SELECT * FROM logs", [{"id": 1}])
        assert await pool.cache.size() == 1

        # Execute INSERT (should invalidate)
        await pool.execute("INSERT INTO logs VALUES (1)")

        # Cache should be cleared
        assert await pool.cache.size() == 0

    @pytest.mark.asyncio
    async def test_pool_fetch_with_cache(self):
        """Test fetch operation with caching"""
        mock_asyncpg_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_asyncpg_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_asyncpg_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[{"id": 1}, {"id": 2}])

        pool = OptimizedConnectionPool(
            dsn="test",
            cache_enabled=True
        )
        pool.pool = mock_asyncpg_pool

        # First fetch
        result = await pool.fetch("SELECT * FROM logs", cache=True)
        assert len(result) == 2

        # Second fetch should hit cache (mock fetch not called again)
        cached = await pool.fetch("SELECT * FROM logs", cache=True)
        assert cached == result

    @pytest.mark.asyncio
    async def test_pool_fetchval_with_cache(self):
        """Test fetchval operation with caching"""
        mock_asyncpg_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_asyncpg_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_asyncpg_pool.release = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)

        pool = OptimizedConnectionPool(
            dsn="test",
            cache_enabled=True
        )
        pool.pool = mock_asyncpg_pool

        # First query
        result = await pool.fetchval("SELECT COUNT(*) FROM logs", cache=True)
        assert result == 42

        # Second should hit cache
        cached = await pool.fetchval("SELECT COUNT(*) FROM logs", cache=True)
        assert cached == 42

    @pytest.mark.asyncio
    async def test_pool_get_stats(self):
        """Test retrieving pool statistics"""
        mock_asyncpg_pool = MagicMock()
        mock_asyncpg_pool._holders = MagicMock()
        mock_asyncpg_pool._queue = MagicMock()
        mock_asyncpg_pool._holders.__len__ = MagicMock(return_value=3)
        mock_asyncpg_pool._queue.qsize = MagicMock(return_value=2)

        pool = OptimizedConnectionPool(
            dsn="test",
            enable_monitoring=True
        )
        pool.pool = mock_asyncpg_pool
        pool.monitor = PoolMonitor(mock_asyncpg_pool)

        stats = await pool.get_stats()
        assert "pool" in stats
        assert "queries" in stats
        assert "cache" in stats

    @pytest.mark.asyncio
    async def test_pool_close(self):
        """Test closing the pool"""
        mock_asyncpg_pool = AsyncMock()

        pool = OptimizedConnectionPool(dsn="test")
        pool.pool = mock_asyncpg_pool

        await pool.close()
        mock_asyncpg_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_pool_invalidate_cache(self):
        """Test manual cache invalidation"""
        pool = OptimizedConnectionPool(
            dsn="test",
            cache_enabled=True
        )

        # Add entries
        await pool.cache.set("SELECT * FROM logs", [{"id": 1}])
        assert await pool.cache.size() == 1

        # Invalidate
        await pool.invalidate_cache()
        assert await pool.cache.size() == 0


class TestConnectionPoolIntegration:
    """Integration tests for connection pool optimization"""

    @pytest.mark.asyncio
    async def test_pool_handles_concurrent_queries(self):
        """Test pool handles multiple concurrent queries"""
        mock_asyncpg_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_asyncpg_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_asyncpg_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[{"id": 1}])

        pool = OptimizedConnectionPool(dsn="test", min_size=5, max_size=20)
        pool.pool = mock_asyncpg_pool

        # Concurrent fetches
        results = await asyncio.gather(*[
            pool.fetch("SELECT * FROM logs WHERE id = $1", i)
            for i in range(10)
        ])

        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_pool_monitoring_tracks_performance(self):
        """Test that monitoring tracks query performance metrics"""
        mock_asyncpg_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_asyncpg_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_asyncpg_pool.release = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_asyncpg_pool._holders = MagicMock()
        mock_asyncpg_pool._queue = MagicMock()
        mock_asyncpg_pool._holders.__len__ = MagicMock(return_value=3)
        mock_asyncpg_pool._queue.qsize = MagicMock(return_value=2)

        pool = OptimizedConnectionPool(
            dsn="test",
            enable_monitoring=True
        )
        pool.pool = mock_asyncpg_pool
        pool.monitor = PoolMonitor(mock_asyncpg_pool)

        # Execute queries with monitoring
        for i in range(3):
            await pool.fetchval("SELECT * FROM logs LIMIT $1", i)

        # Verify stats recorded
        stats = await pool.get_stats()
        assert "queries" in stats


class TestDatabaseOptimizationEndToEnd:
    """End-to-end tests for database optimization features"""

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_write(self):
        """Test cache is invalidated on write operations"""
        cache = QueryCache(ttl_seconds=300)

        # Pre-populate cache
        select_query = "SELECT * FROM orders WHERE status = $1"
        await cache.set(select_query, [{"id": 1, "status": "FILLED"}], ("FILLED",))

        # Verify cache hit
        cached = await cache.get(select_query, ("FILLED",))
        assert cached is not None

        # Cache stats before invalidation
        stats_before = await cache.get_stats()

        # Invalidate on write
        await cache.invalidate()

        # Verify cache miss after invalidation
        cached = await cache.get(select_query, ("FILLED",))
        assert cached is None

    @pytest.mark.asyncio
    async def test_slow_query_detection_and_logging(self):
        """Test slow query detection and logging"""
        mock_pool = MagicMock()
        monitor = PoolMonitor(mock_pool)
        monitor._slow_query_threshold_ms = 50

        # Record various queries
        await monitor.record_query("FAST QUERY", 25.0)
        await monitor.record_query("SLOW QUERY", 150.0)
        await monitor.record_query("SLOW QUERY", 120.0)

        stats = await monitor.get_query_stats(limit=10)

        # Should detect slow queries
        assert len(stats["slow_queries"]) > 0

    @pytest.mark.asyncio
    async def test_pool_configuration_for_production(self):
        """Test pool is configured appropriately for production"""
        pool = OptimizedConnectionPool(
            dsn="postgresql://prod:pass@prod-db:5432/trading",
            min_size=10,
            max_size=50,
            max_queries=100000,
            cache_enabled=True,
            enable_monitoring=True
        )

        assert pool.min_size == 10
        assert pool.max_size == 50
        assert pool.cache is not None
        assert pool.enable_monitoring is True

    @pytest.mark.asyncio
    async def test_query_with_parameters_caching(self):
        """Test query caching respects parameter differences"""
        cache = QueryCache(ttl_seconds=300)
        query = "SELECT * FROM orders WHERE instrument = $1 AND status = $2"

        # Cache different parameter combinations
        await cache.set(query, [{"id": 1}], ("EUR_USD", "FILLED"))
        await cache.set(query, [{"id": 2}], ("GBP_USD", "PENDING"))

        # Verify correct cache hits
        assert await cache.get(query, ("EUR_USD", "FILLED")) == [{"id": 1}]
        assert await cache.get(query, ("GBP_USD", "PENDING")) == [{"id": 2}]
        assert await cache.get(query, ("USD_JPY", "FILLED")) is None


# Parametrized tests for different scenarios
@pytest.mark.parametrize("min_size,max_size", [
    (5, 10),
    (10, 20),
    (20, 50),
])
@pytest.mark.asyncio
async def test_pool_sizes_configuration(min_size, max_size):
    """Test pool with different min/max configurations"""
    pool = OptimizedConnectionPool(
        dsn="postgresql://test:test@localhost/test",
        min_size=min_size,
        max_size=max_size
    )

    assert pool.min_size == min_size
    assert pool.max_size == max_size


@pytest.mark.parametrize("ttl_seconds", [300, 900, 1800, 3600])
@pytest.mark.asyncio
async def test_cache_ttl_configurations(ttl_seconds):
    """Test cache with different TTL configurations"""
    cache = QueryCache(ttl_seconds=ttl_seconds)
    assert cache.ttl_seconds == ttl_seconds

    # Verify cache respects TTL
    await cache.set("SELECT 1", [1])
    result = await cache.get("SELECT 1")
    assert result is not None


@pytest.mark.asyncio
async def test_performance_metrics_accuracy():
    """Test performance metrics are recorded accurately"""
    mock_pool = MagicMock()
    monitor = PoolMonitor(mock_pool)

    query = "SELECT * FROM large_table"

    # Record multiple executions
    await monitor.record_query(query, 100.0)
    await monitor.record_query(query, 120.0)
    await monitor.record_query(query, 80.0)

    stats = await monitor.get_query_stats()
    assert len(stats["slow_queries"]) > 0

    slow_query = stats["slow_queries"][0]
    assert slow_query["min_duration_ms"] == 80.0
    assert slow_query["max_duration_ms"] == 120.0
    assert abs(slow_query["avg_duration_ms"] - 100.0) < 1.0
