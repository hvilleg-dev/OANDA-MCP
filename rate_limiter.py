"""
Token Bucket Rate Limiter for OANDA MCP Server

Provides thread-safe rate limiting with per-client tracking and auto-cleanup.
Supports custom rate limits per endpoint with 429 response codes and standard headers.
"""

import time
import threading
from typing import Tuple, Dict, Optional, Callable, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class TokenBucketLimiter:
    """
    Token Bucket Rate Limiter

    Thread-safe implementation that tracks tokens per client+endpoint.
    Auto-cleanup of inactive clients after 24 hours.
    """

    # Cleanup interval in seconds (run cleanup every 1 hour)
    CLEANUP_INTERVAL = 3600
    # Client expiry time in seconds (24 hours)
    CLIENT_TTL = 86400

    def __init__(self, rate_per_minute: int, burst_size: int):
        """
        Initialize the rate limiter

        Args:
            rate_per_minute: Tokens refilled per minute (requests/min limit)
            burst_size: Maximum tokens in bucket (burst capacity)
        """
        self.rate_per_minute = rate_per_minute
        self.burst_size = burst_size
        self.tokens_per_second = rate_per_minute / 60.0

        # Per-client state: {client_id: {endpoint: {tokens, last_update}}}
        self.client_state: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._lock = threading.Lock()

        # Track last cleanup time
        self._last_cleanup = time.time()

    def _cleanup_inactive_clients(self) -> None:
        """Remove clients inactive for > 24 hours (non-blocking, best-effort)"""
        now = time.time()
        if now - self._last_cleanup < self.CLEANUP_INTERVAL:
            return

        self._last_cleanup = now
        expired = []

        for client_id, endpoints in self.client_state.items():
            for endpoint, state in endpoints.items():
                if now - state.get('last_update', now) > self.CLIENT_TTL:
                    expired.append((client_id, endpoint))

        for client_id, endpoint in expired:
            try:
                del self.client_state[client_id][endpoint]
                if not self.client_state[client_id]:
                    del self.client_state[client_id]
            except KeyError:
                pass

    def is_allowed(self, client_id: str, endpoint: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a request is allowed for the given client+endpoint

        Args:
            client_id: Unique identifier for the client (IP, API key, etc)
            endpoint: Optional endpoint path for per-endpoint tracking

        Returns:
            Tuple of (allowed: bool, headers: dict with rate limit info)
        """
        endpoint = endpoint or "default"
        now = time.time()

        with self._lock:
            # Initialize client state if needed
            if client_id not in self.client_state:
                self.client_state[client_id] = {}

            if endpoint not in self.client_state[client_id]:
                self.client_state[client_id][endpoint] = {
                    'tokens': float(self.burst_size),
                    'last_update': now
                }

            state = self.client_state[client_id][endpoint]

            # Refill tokens based on time elapsed
            time_passed = now - state['last_update']
            tokens_to_add = time_passed * self.tokens_per_second
            state['tokens'] = min(self.burst_size, state['tokens'] + tokens_to_add)
            state['last_update'] = now

            # Calculate when tokens will reset
            reset_time = int(now + (self.burst_size / self.tokens_per_second))

            headers = {
                'X-RateLimit-Limit': str(self.rate_per_minute),
                'X-RateLimit-Remaining': str(int(state['tokens'])),
                'X-RateLimit-Reset': str(reset_time)
            }

            # Check if request is allowed
            if state['tokens'] >= 1:
                state['tokens'] -= 1
                return (True, headers)
            else:
                # Calculate retry_after
                tokens_needed = 1 - state['tokens']
                retry_after = int(tokens_needed / self.tokens_per_second) + 1
                headers['Retry-After'] = str(retry_after)
                return (False, headers)

    def get_headers(self, client_id: str, endpoint: Optional[str] = None) -> Dict[str, str]:
        """
        Get current rate limit headers for a client+endpoint without consuming tokens

        Args:
            client_id: Unique identifier for the client
            endpoint: Optional endpoint path

        Returns:
            Dictionary of rate limit headers
        """
        endpoint = endpoint or "default"
        now = time.time()

        with self._lock:
            if client_id not in self.client_state or endpoint not in self.client_state[client_id]:
                return {
                    'X-RateLimit-Limit': str(self.rate_per_minute),
                    'X-RateLimit-Remaining': str(self.rate_per_minute),
                    'X-RateLimit-Reset': str(int(now + 60))
                }

            state = self.client_state[client_id][endpoint]

            # Calculate current tokens
            time_passed = now - state['last_update']
            tokens = min(self.burst_size, state['tokens'] + time_passed * self.tokens_per_second)
            reset_time = int(now + (self.burst_size / self.tokens_per_second))

            return {
                'X-RateLimit-Limit': str(self.rate_per_minute),
                'X-RateLimit-Remaining': str(int(tokens)),
                'X-RateLimit-Reset': str(reset_time)
            }

    def reset(self, client_id: str, endpoint: Optional[str] = None) -> None:
        """
        Reset the rate limit counter for a specific client or all endpoints

        Args:
            client_id: Unique identifier for the client
            endpoint: Optional specific endpoint to reset. If None, resets all.
        """
        with self._lock:
            if client_id not in self.client_state:
                return

            if endpoint is None:
                del self.client_state[client_id]
            elif endpoint in self.client_state[client_id]:
                del self.client_state[client_id][endpoint]


# Global rate limiters by endpoint
_rate_limiters: Dict[str, TokenBucketLimiter] = {}
_limiter_lock = threading.Lock()


def get_rate_limiter(rate_per_minute: int, burst_size: Optional[int] = None) -> TokenBucketLimiter:
    """Get or create a rate limiter with specified parameters"""
    burst_size = burst_size or rate_per_minute
    key = f"{rate_per_minute}:{burst_size}"

    if key not in _rate_limiters:
        _rate_limiters[key] = TokenBucketLimiter(rate_per_minute, burst_size)

    return _rate_limiters[key]


def rate_limit(rate_per_minute: int, burst_size: Optional[int] = None):
    """
    Decorator for FastAPI endpoints to apply rate limiting

    Args:
        rate_per_minute: Request rate limit (requests/minute)
        burst_size: Maximum burst capacity (defaults to rate_per_minute)

    Returns:
        Decorated async function with rate limiting

    Usage:
        @app.get("/orders")
        @rate_limit(100)
        async def get_orders(request: Request):
            ...
    """
    burst_size = burst_size or rate_per_minute
    limiter = get_rate_limiter(rate_per_minute, burst_size)

    def decorator(func: Callable) -> Callable:
        import asyncio
        import inspect

        # Get function signature
        sig = inspect.signature(func)
        has_request_param = 'request' in sig.parameters

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Extract request from kwargs
            request = kwargs.get('request')

            if request is not None:
                client_ip = request.client.host if request.client else "unknown"
                endpoint = request.url.path
            else:
                client_ip = "unknown"
                endpoint = "default"

            # Check rate limit
            allowed, headers = limiter.is_allowed(client_ip, endpoint)

            if not allowed:
                from fastapi.responses import JSONResponse
                retry_after = int(headers.get('Retry-After', '1'))
                response = JSONResponse(
                    status_code=429,
                    content={
                        'errorCode': 'RATE_LIMIT_EXCEEDED',
                        'errorMessage': f'Rate limit exceeded. Retry after {retry_after} seconds',
                        'retryAfter': retry_after
                    }
                )
                for key, value in headers.items():
                    response.headers[key] = value
                return response

            # Call the endpoint function
            response = await func(*args, **kwargs)

            # Add rate limit headers to response
            # FastAPI automatically wraps dict responses in JSONResponse
            if hasattr(response, 'headers'):
                for key, value in headers.items():
                    response.headers[key] = value
            elif isinstance(response, dict):
                # Convert dict to JSONResponse with headers
                from fastapi.responses import JSONResponse
                response = JSONResponse(content=response)
                for key, value in headers.items():
                    response.headers[key] = value

            return response

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # Extract request from kwargs
            request = kwargs.get('request')

            if request is not None:
                client_ip = request.client.host if request.client else "unknown"
                endpoint = request.url.path
            else:
                client_ip = "unknown"
                endpoint = "default"

            # Check rate limit
            allowed, headers = limiter.is_allowed(client_ip, endpoint)

            if not allowed:
                from fastapi.responses import JSONResponse
                retry_after = int(headers.get('Retry-After', '1'))
                response = JSONResponse(
                    status_code=429,
                    content={
                        'errorCode': 'RATE_LIMIT_EXCEEDED',
                        'errorMessage': f'Rate limit exceeded. Retry after {retry_after} seconds',
                        'retryAfter': retry_after
                    }
                )
                for key, value in headers.items():
                    response.headers[key] = value
                return response

            # Call the endpoint function
            response = func(*args, **kwargs)

            # Add rate limit headers to response
            if hasattr(response, 'headers'):
                for key, value in headers.items():
                    response.headers[key] = value
            elif isinstance(response, dict):
                from fastapi.responses import JSONResponse
                response = JSONResponse(content=response)
                for key, value in headers.items():
                    response.headers[key] = value

            return response

        # Choose wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
