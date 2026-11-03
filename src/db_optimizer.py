"""
Database optimization module for connection pooling, query caching, and monitoring.

Features:
- Optimized connection pool configuration
- In-memory query result caching with TTL
- Query performance tracking
- Slow query detection and logging
- Connection health monitoring
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional, Callable, TypeVar
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncpg

logger = logging.getLogger(__name__)

# Type variable for caching
T = TypeVar('T')


@dataclass
class PoolStats:
    """Statistics for connection pool health monitoring"""
    active_connections: int = 0
    idle_connections: int = 0
    waiting_count: int = 0
    total_acquired: int = 0
    total_released: int = 0
    peak_size: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QueryStats:
    """Statistics for individual query performance"""
    query_hash: str
    execution_count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    last_executed: Optional[datetime] = None
    error_count: int = 0

    @property
    def avg_duration_ms(self) -> float:
        """Calculate average execution duration"""
        return self.total_duration_ms / max(self.execution_count, 1)


class QueryCache:
    """In-memory cache for frequently executed queries with TTL"""

    def __init__(self, ttl_seconds: int = 1800):
        """
        Initialize query cache

        Args:
            ttl_seconds: Time-to-live for cached results (default 30 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0
        }
        self._lock = asyncio.Lock()

    def _make_key(self, query: str, args: tuple = None) -> str:
        """Generate cache key from query and arguments"""
        key_data = f"{query}:{json.dumps(args or [], default=str)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def get(self, query: str, args: tuple = None) -> Optional[Any]:
        """
        Get cached query result if exists and not expired

        Args:
            query: SQL query string
            args: Query parameters

        Returns:
            Cached result or None if expired/not found
        """
        async with self._lock:
            key = self._make_key(query, args)
            if key in self._cache:
                result, cached_time = self._cache[key]
                if datetime.utcnow() - cached_time < timedelta(seconds=self.ttl_seconds):
                    self._stats["hits"] += 1
                    return result
                else:
                    # Expired
                    del self._cache[key]

            self._stats["misses"] += 1
            return None

    async def set(self, query: str, result: Any, args: tuple = None) -> None:
        """
        Cache a query result

        Args:
            query: SQL query string
            result: Query result to cache
            args: Query parameters
        """
        async with self._lock:
            key = self._make_key(query, args)
            self._cache[key] = (result, datetime.utcnow())

    async def invalidate(self, query_pattern: str = None) -> None:
        """
        Invalidate cache entries. If query_pattern is None, clears all cache.

        Args:
            query_pattern: Optional pattern to invalidate specific queries
        """
        async with self._lock:
            if query_pattern is None:
                self._cache.clear()
                self._stats["invalidations"] += 1
            else:
                # Remove entries matching pattern
                keys_to_delete = [
                    key for key, (_, query_str) in self._cache.items()
                    if query_pattern.lower() in query_str.lower()
                ]
                for key in keys_to_delete:
                    del self._cache[key]
                if keys_to_delete:
                    self._stats["invalidations"] += 1

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate_percent": round(hit_rate, 2),
                "invalidations": self._stats["invalidations"],
                "cached_entries": len(self._cache),
                "size_bytes": sum(
                    len(json.dumps(result, default=str).encode())
                    for result, _ in self._cache.values()
                )
            }

    async def size(self) -> int:
        """Get number of cached entries"""
        async with self._lock:
            return len(self._cache)


class PoolMonitor:
    """Monitor connection pool health and performance"""

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize pool monitor

        Args:
            pool: asyncpg connection pool to monitor
        """
        self.pool = pool
        self._stats_history: list[PoolStats] = []
        self._query_stats: Dict[str, QueryStats] = {}
        self._lock = asyncio.Lock()
        self._slow_query_threshold_ms = 100

    async def capture_snapshot(self) -> PoolStats:
        """Capture current pool statistics"""
        async with self._lock:
            stats = PoolStats(
                active_connections=self.pool._holders.__len__() if hasattr(self.pool, '_holders') else 0,
                idle_connections=self.pool._queue.qsize() if hasattr(self.pool, '_queue') else 0,
                timestamp=datetime.utcnow()
            )
            self._stats_history.append(stats)

            # Keep only last 1000 snapshots
            if len(self._stats_history) > 1000:
                self._stats_history = self._stats_history[-1000:]

            return stats

    async def record_query(self, query: str, duration_ms: float, error: bool = False) -> None:
        """
        Record query execution statistics

        Args:
            query: SQL query string
            duration_ms: Query execution time in milliseconds
            error: Whether query resulted in error
        """
        query_hash = hashlib.md5(query.encode()).hexdigest()[:12]

        async with self._lock:
            if query_hash not in self._query_stats:
                self._query_stats[query_hash] = QueryStats(query_hash=query_hash)

            stats = self._query_stats[query_hash]
            stats.execution_count += 1
            stats.total_duration_ms += duration_ms
            stats.min_duration_ms = min(stats.min_duration_ms, duration_ms)
            stats.max_duration_ms = max(stats.max_duration_ms, duration_ms)
            stats.last_executed = datetime.utcnow()

            if error:
                stats.error_count += 1

            # Log slow queries
            if duration_ms > self._slow_query_threshold_ms:
                logger.warning(
                    f"Slow query detected: {duration_ms:.2f}ms - {query[:100]}..."
                )

    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get current pool statistics"""
        latest = await self.capture_snapshot()
        return {
            "active_connections": latest.active_connections,
            "idle_connections": latest.idle_connections,
            "timestamp": latest.timestamp.isoformat(),
        }

    async def get_query_stats(self, limit: int = 10) -> Dict[str, Any]:
        """Get top slow queries by average duration"""
        async with self._lock:
            sorted_queries = sorted(
                self._query_stats.values(),
                key=lambda x: x.avg_duration_ms,
                reverse=True
            )[:limit]

            return {
                "total_unique_queries": len(self._query_stats),
                "slow_queries": [
                    {
                        "hash": q.query_hash,
                        "execution_count": q.execution_count,
                        "avg_duration_ms": round(q.avg_duration_ms, 2),
                        "min_duration_ms": round(q.min_duration_ms, 2),
                        "max_duration_ms": round(q.max_duration_ms, 2),
                        "error_count": q.error_count,
                        "last_executed": q.last_executed.isoformat() if q.last_executed else None
                    }
                    for q in sorted_queries
                ]
            }


class OptimizedConnectionPool:
    """
    Wrapper around asyncpg pool with optimization features:
    - Tuned connection pool parameters
    - Query result caching
    - Performance monitoring
    - Dead connection detection
    """

    def __init__(
        self,
        dsn: str,
        min_size: int = 5,
        max_size: int = 20,
        max_queries: int = 50000,
        cache_enabled: bool = True,
        cache_ttl_seconds: int = 1800,
        enable_monitoring: bool = True
    ):
        """
        Initialize optimized connection pool

        Args:
            dsn: Database connection string
            min_size: Minimum pool size (default 5)
            max_size: Maximum pool size (default 20)
            max_queries: Max queries per connection before recycle (default 50000)
            cache_enabled: Enable result caching (default True)
            cache_ttl_seconds: Cache TTL in seconds (default 1800 = 30 min)
            enable_monitoring: Enable performance monitoring (default True)
        """
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.max_queries = max_queries
        self.pool: Optional[asyncpg.Pool] = None

        self.cache = QueryCache(ttl_seconds=cache_ttl_seconds) if cache_enabled else None
        self.monitor = None
        self.enable_monitoring = enable_monitoring

    async def initialize(self) -> None:
        """Initialize the connection pool with optimized settings"""
        connection_class = self._get_optimized_connection_class()

        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=self.min_size,
            max_size=self.max_size,
            max_queries=self.max_queries,
            # Connection initialization and validation
            init=self._init_connection,
            record_class=dict,
            # Performance tuning
            command_timeout=30.0,
            idle_in_transaction_session_timeout=30000,  # 30 seconds
            connection_class=connection_class,
        )

        if self.enable_monitoring and self.pool:
            self.monitor = PoolMonitor(self.pool)
            logger.info(f"Optimized connection pool initialized: min={self.min_size}, max={self.max_size}")
        else:
            logger.info("Connection pool initialized (monitoring disabled)")

    @staticmethod
    def _get_optimized_connection_class():
        """Get optimized asyncpg connection class with validation"""
        class OptimizedConnection(asyncpg.connection.Connection):
            async def _init(self):
                await super()._init()
                # Set connection-level parameters
                await self.execute("SET application_name = 'oanda-mcp'")
                await self.execute("SET jit = off")  # Disable JIT for predictable performance

        return OptimizedConnection

    @staticmethod
    async def _init_connection(conn: asyncpg.Connection) -> None:
        """
        Initialize each connection with optimized settings

        Args:
            conn: Database connection
        """
        try:
            # Performance optimizations
            await conn.execute("SET application_name = 'oanda-mcp'")
            await conn.execute("SET jit = off")
            await conn.execute("SET random_page_cost = 1.1")  # SSD-friendly

            # Connection pool validation: test query
            await conn.fetchval("SELECT 1")
            logger.debug("Connection validated successfully")
        except Exception as e:
            logger.error(f"Connection initialization failed: {e}")
            raise

    async def acquire(self) -> asyncpg.Connection:
        """
        Acquire a connection from the pool with health check

        Returns:
            Database connection
        """
        if not self.pool:
            raise RuntimeError("Pool not initialized. Call initialize() first.")

        conn = await self.pool.acquire()

        # Test connection validity
        try:
            await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=2.0)
        except Exception as e:
            logger.warning(f"Dead connection detected, releasing: {e}")
            await self.pool.release(conn)
            # Retry once
            conn = await self.pool.acquire()

        return conn

    async def execute(
        self,
        query: str,
        *args,
        cache: bool = False,
        **kwargs
    ) -> None:
        """
        Execute a query (no return value)

        Args:
            query: SQL query
            *args: Query parameters
            cache: Whether to cache result (for SELECT only)
            **kwargs: Additional asyncpg parameters
        """
        conn = await self.acquire()
        try:
            start = time.time()
            await conn.execute(query, *args, **kwargs)
            duration_ms = (time.time() - start) * 1000

            # Invalidate cache on modifications
            if self.cache and any(query.strip().upper().startswith(op) for op in ['INSERT', 'UPDATE', 'DELETE']):
                await self.cache.invalidate()

            if self.monitor:
                await self.monitor.record_query(query, duration_ms)
        finally:
            await self.pool.release(conn)

    async def fetch(
        self,
        query: str,
        *args,
        cache: bool = False,
        **kwargs
    ) -> list:
        """
        Execute query and return all rows

        Args:
            query: SQL query
            *args: Query parameters
            cache: Whether to cache result
            **kwargs: Additional asyncpg parameters

        Returns:
            List of rows as dicts
        """
        # Check cache first
        if cache and self.cache:
            cached = await self.cache.get(query, args)
            if cached is not None:
                return cached

        conn = await self.acquire()
        try:
            start = time.time()
            result = await conn.fetch(query, *args, **kwargs)
            duration_ms = (time.time() - start) * 1000

            # Convert records to dicts if needed
            if result and hasattr(result[0], 'keys'):
                result = [dict(row) for row in result]

            # Cache result
            if cache and self.cache:
                await self.cache.set(query, result, args)

            if self.monitor:
                await self.monitor.record_query(query, duration_ms)

            return result
        finally:
            await self.pool.release(conn)

    async def fetchval(
        self,
        query: str,
        *args,
        cache: bool = False,
        **kwargs
    ) -> Any:
        """
        Execute query and return single scalar value

        Args:
            query: SQL query
            *args: Query parameters
            cache: Whether to cache result
            **kwargs: Additional asyncpg parameters

        Returns:
            Single scalar value
        """
        # Check cache first
        if cache and self.cache:
            cached = await self.cache.get(query, args)
            if cached is not None:
                return cached

        conn = await self.acquire()
        try:
            start = time.time()
            result = await conn.fetchval(query, *args, **kwargs)
            duration_ms = (time.time() - start) * 1000

            # Cache result
            if cache and self.cache:
                await self.cache.set(query, result, args)

            if self.monitor:
                await self.monitor.record_query(query, duration_ms)

            return result
        finally:
            await self.pool.release(conn)

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics"""
        stats = {
            "pool": await self.monitor.get_pool_stats() if self.monitor else {},
            "queries": await self.monitor.get_query_stats() if self.monitor else {},
            "cache": await self.cache.get_stats() if self.cache else {}
        }
        return stats

    async def close(self) -> None:
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Connection pool closed")

    async def invalidate_cache(self) -> None:
        """Manually invalidate all cached queries"""
        if self.cache:
            await self.cache.invalidate()
            logger.debug("Query cache invalidated")


async def create_optimized_pool(
    database_url: str,
    min_size: int = 5,
    max_size: int = 20,
    enable_cache: bool = True
) -> OptimizedConnectionPool:
    """
    Factory function to create and initialize an optimized connection pool

    Args:
        database_url: PostgreSQL connection string
        min_size: Minimum pool size
        max_size: Maximum pool size
        enable_cache: Enable query result caching

    Returns:
        Initialized OptimizedConnectionPool instance
    """
    pool = OptimizedConnectionPool(
        dsn=database_url,
        min_size=min_size,
        max_size=max_size,
        cache_enabled=enable_cache,
    )
    await pool.initialize()
    return pool
