import os
import json
import time
import asyncio
import asyncpg
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel, Field
from oandapyV20 import API
from oandapyV20.endpoints import (
    accounts, orders, positions, pricing,
    instruments, trades, transactions
)
from oandapyV20.exceptions import V20Error
import uvicorn
import logging

# Circuit breaker imports
from src.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

# Database optimization imports
from src.db_optimizer import OptimizedConnectionPool, create_optimized_pool

# Enhanced logging imports
from src.logging_service import LoggingService, LoggingConfig

from rate_limiter import rate_limit
from validators import (
    validate_candle_params,
    validate_order_params,
    validate_trade_params,
    validate_instrument_name,
    validate_rfc3339_datetime,
    validate_price_range,
    validate_price_component,
    validate_time_in_force
)

# ──────────────────────────────────────────────
# Logging - Initialize Enhanced Logging Service
# ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize enhanced logging service (without DB yet, will update in lifespan)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ENABLE_JSON_LOGGING = os.getenv("ENABLE_JSON_LOGGING", "true").lower() == "true"
logging_config = LoggingConfig(
    log_level=LOG_LEVEL,
    enable_json=ENABLE_JSON_LOGGING,
    enable_console=True,
    enable_file=True,
    log_dir="logs"
)
logging_service = LoggingService(config=logging_config)

# ──────────────────────────────────────────────
# Validation Error Handler
# ──────────────────────────────────────────────
def handle_validation_error(error_msg: str, field: str = None, value: str = None) -> HTTPException:
    """
    Creates an HTTP 422 response for validation errors.

    Args:
        error_msg: The validation error message
        field: The field that failed validation (optional)
        value: The invalid value (optional)

    Returns:
        HTTPException with 422 status code and detailed error info
    """
    detail = {
        "errorCode": "INVALID_PARAMETER",
        "errorMessage": error_msg,
    }

    if field or value:
        detail["details"] = {}
        if field:
            detail["details"]["field"] = field
        if value is not None:
            detail["details"]["value"] = value

    return HTTPException(status_code=422, detail=detail)

# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────

class MarketOrderRequest(BaseModel):
    """Market order request. Places an order at current market price."""
    instrument: str             = Field(..., example="EUR_USD", description="Instrument/currency pair (e.g., EUR_USD, GBP_USD, XAU_USD)")
    units: int                  = Field(..., example=1000, description="Order size. Positive=buy, negative=sell")
    stop_loss: Optional[float]  = Field(None, example=1.07000, description="Stop loss price (optional)")
    take_profit: Optional[float]= Field(None, example=1.10000, description="Take profit price (optional)")
    trailing_stop: Optional[float] = Field(None, example=0.0050, description="Trailing stop distance in pips (optional)")
    time_in_force: Optional[str]= Field("FOK", example="FOK", description="FOK (fill-or-kill) or IOC (immediate-or-cancel)")
    client_id: Optional[str]    = Field(None, example="my-order-001", description="Custom order ID for client-side tracking")

class LimitOrderRequest(BaseModel):
    """Limit order request. Executes when price reaches specified level."""
    instrument: str             = Field(..., example="EUR_USD", description="Instrument/currency pair")
    units: int                  = Field(..., example=1000, description="Order size. Positive=buy, negative=sell")
    price: float                = Field(..., example=1.07500, description="Limit price at which order executes")
    stop_loss: Optional[float]  = Field(None, example=1.07000, description="Stop loss price (optional)")
    take_profit: Optional[float]= Field(None, example=1.10000, description="Take profit price (optional)")
    trailing_stop: Optional[float] = Field(None, example=0.0050, description="Trailing stop distance (optional)")
    expiry: Optional[str]       = Field(None, example="2024-12-31T23:59:59Z", description="Order expiry RFC3339. Omit for GTC")
    client_id: Optional[str]    = Field(None, example="my-limit-001", description="Custom order ID")

class StopOrderRequest(BaseModel):
    """Stop order request. Activates when price exceeds specified level."""
    instrument: str             = Field(..., example="EUR_USD", description="Instrument/currency pair")
    units: int                  = Field(..., example=1000, description="Order size. Positive=buy, negative=sell")
    price: float                = Field(..., example=1.09000, description="Stop activation price")
    stop_loss: Optional[float]  = Field(None, example=1.08500, description="Stop loss price (optional)")
    take_profit: Optional[float]= Field(None, example=1.11000, description="Take profit price (optional)")
    expiry: Optional[str]       = Field(None, example="2024-12-31T23:59:59Z", description="Order expiry RFC3339")

class ModifyOrderRequest(BaseModel):
    """Modify order request. Updates parameters of pending order."""
    price: Optional[float]      = Field(None, example=1.08000, description="New order price")
    units: Optional[int]        = Field(None, example=2000, description="New order size")
    stop_loss: Optional[float]  = Field(None, example=1.07000, description="New stop loss price")
    take_profit: Optional[float]= Field(None, example=1.10000, description="New take profit price")
    timeInForce: Optional[str]  = Field(None, example="GTC", description="GTC/GTD/FOK/IOC")
    gtdTime: Optional[str]      = Field(None, example="2024-12-31T23:59:59Z", description="Required if timeInForce=GTD")

class ModifyTradeRequest(BaseModel):
    """Modify trade request. Updates SL/TP/trailing stop. Null value removes."""
    stop_loss: Optional[float]  = Field(None, example=1.07000, description="Stop loss price. null=remove SL")
    take_profit: Optional[float]= Field(None, example=1.10000, description="Take profit price. null=remove TP")
    trailing_stop: Optional[float] = Field(None, example=0.0050, description="Trailing stop distance. null=remove TSL")

class ClosePositionRequest(BaseModel):
    """Close position request. Closes position with optional side filter."""
    units: Optional[str]        = Field("ALL", example="ALL", description="ALL closes all, or specify number")
    side: Optional[str]         = Field("both", example="both", description="long/short/both")

class AccountConfigRequest(BaseModel):
    """Account configuration request. Updates account settings."""
    alias: Optional[str]        = Field(None, example="My Trading Account", description="Account nickname")
    marginRate: Optional[str]   = Field(None, example="0.02", description="Margin rate (0.02 = 50:1 leverage)")

class CloseTradeRequest(BaseModel):
    """Close trade request. Closes trade fully or partially."""
    units: Optional[str] = Field(None, example="200", description="Units to close. null/ALL=full close")

class TradeOrdersRequest(BaseModel):
    """Trade dependent orders request. Sets/modifies/cancels TP/SL/TSL/GSL."""
    takeProfit: Optional[dict]       = Field(None, description='{"price":"1.15","timeInForce":"GTC"} or null')
    stopLoss: Optional[dict]         = Field(None, description='{"price":"1.10","timeInForce":"GTC"} or null')
    trailingStopLoss: Optional[dict] = Field(None, description='{"distance":"0.005","timeInForce":"GTC"} or null')
    guaranteedStopLoss: Optional[dict] = Field(None, description='GSL (UK/EU only). {"price":"1.09","timeInForce":"GTC"} or null')

class ClientExtensionsRequest(BaseModel):
    """Client extensions request. Adds custom metadata tags."""
    clientExtensions: Optional[dict] = Field(None, description='{"id":"id","tag":"tag","comment":"comment"}')
    tradeClientExtensions: Optional[dict] = Field(None, description="Trade extensions for orders")

class MITOrderRequest(BaseModel):
    """MIT (Market-If-Touched) order request. Becomes market order when touched."""
    instrument: str             = Field(..., example="EUR_USD", description="Instrument/currency pair")
    units: int                  = Field(..., example=1000, description="Order size. Positive=buy, negative=sell")
    price: float                = Field(..., example=1.07500, description="Price that triggers market execution")
    stop_loss: Optional[float]  = Field(None, example=1.07000, description="Stop loss price (optional)")
    take_profit: Optional[float]= Field(None, example=1.10000, description="Take profit price (optional)")
    expiry: Optional[str]       = Field(None, example="2024-12-31T23:59:59Z", description="Order expiry RFC3339")
    client_id: Optional[str]    = Field(None, example="my-mit-001", description="Custom order ID")

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
OANDA_API_KEY     = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID  = os.getenv("OANDA_ACCOUNT_ID")
OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice").strip().lower()
DATABASE_URL      = os.getenv("DATABASE_URL", "postgresql://oanda:oanda@db:5432/oanda_mcp")

# Circuit breaker configuration
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", 5))
CIRCUIT_BREAKER_TIMEOUT = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", 60))
CIRCUIT_BREAKER_BACKOFF_MULTIPLIER = int(os.getenv("CIRCUIT_BREAKER_BACKOFF_MULTIPLIER", 100))

if not OANDA_API_KEY or not OANDA_ACCOUNT_ID:
    raise ValueError("OANDA_API_KEY and OANDA_ACCOUNT_ID are required.")
if OANDA_ENVIRONMENT not in ("practice", "live"):
    raise ValueError(f"OANDA_ENVIRONMENT must be 'practice' or 'live', received: '{OANDA_ENVIRONMENT}'")

if OANDA_ENVIRONMENT == "live":
    logger.warning("LIVE MODE — operations affect real money.")
else:
    logger.info("PRACTICE MODE (demo).")

oanda_client = API(access_token=OANDA_API_KEY, environment=OANDA_ENVIRONMENT)
stream_client = API(access_token=OANDA_API_KEY, environment=OANDA_ENVIRONMENT)  # dedicated client for SSE streaming

# Initialize circuit breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=CIRCUIT_BREAKER_THRESHOLD,
    recovery_timeout=CIRCUIT_BREAKER_TIMEOUT,
    backoff_multiplier=CIRCUIT_BREAKER_BACKOFF_MULTIPLIER
)

# ──────────────────────────────────────────────
# Pool PostgreSQL
# ──────────────────────────────────────────────
db_pool: asyncpg.Pool = None
db_optimizer: Optional[OptimizedConnectionPool] = None
use_optimized_pool: bool = os.getenv("USE_OPTIMIZED_POOL", "false").lower() == "true"

async def init_db(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS request_log (
                id            SERIAL PRIMARY KEY,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                environment   TEXT NOT NULL,
                method        TEXT NOT NULL,
                path          TEXT NOT NULL,
                query_params  JSONB,
                request_body  JSONB,
                status_code   INTEGER NOT NULL,
                duration_ms   NUMERIC(10,2),
                response_body JSONB,
                error_code    TEXT,
                error_message TEXT,
                is_error      BOOLEAN NOT NULL DEFAULT FALSE
            );
            CREATE TABLE IF NOT EXISTS order_log (
                id              SERIAL PRIMARY KEY,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                environment     TEXT NOT NULL,
                order_type      TEXT,
                instrument      TEXT,
                units           TEXT,
                price           TEXT,
                time_in_force   TEXT,
                stop_loss       TEXT,
                take_profit     TEXT,
                trailing_stop   TEXT,
                status          TEXT,
                oanda_order_id  TEXT,
                oanda_trade_id  TEXT,
                reject_reason   TEXT,
                raw_request     JSONB,
                raw_response    JSONB
            );
            CREATE TABLE IF NOT EXISTS trade_log (
                id           SERIAL PRIMARY KEY,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                environment  TEXT NOT NULL,
                action       TEXT NOT NULL,
                trade_id     TEXT,
                instrument   TEXT,
                units        TEXT,
                price        TEXT,
                realized_pl  TEXT,
                raw_request  JSONB,
                raw_response JSONB
            );
            CREATE TABLE IF NOT EXISTS error_log (
                id            SERIAL PRIMARY KEY,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                environment   TEXT NOT NULL,
                method        TEXT NOT NULL,
                path          TEXT NOT NULL,
                error_code    TEXT,
                error_message TEXT,
                reject_reason TEXT,
                request_body  JSONB,
                raw_response  JSONB
            );
            CREATE INDEX IF NOT EXISTS idx_req_created   ON request_log (created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_ord_created   ON order_log   (created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_ord_instr     ON order_log   (instrument);
            CREATE INDEX IF NOT EXISTS idx_trd_created   ON trade_log   (created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_err_created   ON error_log   (created_at DESC);
        """)
    logger.info("Database initialized.")

# ──────────────────────────────────────────────
# Helpers DB
# ──────────────────────────────────────────────
async def log_request(pool, method, path, query_params, request_body,
                      status_code, duration_ms, response_body,
                      error_code=None, error_message=None, is_error=False):
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO request_log
                    (environment,method,path,query_params,request_body,
                     status_code,duration_ms,response_body,error_code,error_message,is_error)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            """, OANDA_ENVIRONMENT, method, path,
                json.dumps(query_params) if query_params else None,
                json.dumps(request_body) if request_body else None,
                status_code, duration_ms,
                json.dumps(response_body, default=str) if response_body else None,
                error_code, error_message, is_error)
    except Exception as e:
        logger.error(f"log_request error: {e}")

async def log_order(pool, order_type, instrument, units, price, time_in_force,
                    stop_loss, take_profit, trailing_stop, status,
                    oanda_order_id, oanda_trade_id, reject_reason, raw_request, raw_response):
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO order_log
                    (environment,order_type,instrument,units,price,time_in_force,
                     stop_loss,take_profit,trailing_stop,status,
                     oanda_order_id,oanda_trade_id,reject_reason,raw_request,raw_response)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
            """, OANDA_ENVIRONMENT, order_type, instrument,
                str(units) if units else None, str(price) if price else None,
                time_in_force,
                str(stop_loss) if stop_loss else None,
                str(take_profit) if take_profit else None,
                str(trailing_stop) if trailing_stop else None,
                status, oanda_order_id, oanda_trade_id, reject_reason,
                json.dumps(raw_request), json.dumps(raw_response, default=str))
    except Exception as e:
        logger.error(f"log_order error: {e}")

async def log_trade_action(pool, action, trade_id, instrument,
                           units, price, realized_pl, raw_request, raw_response):
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO trade_log
                    (environment,action,trade_id,instrument,units,price,realized_pl,raw_request,raw_response)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            """, OANDA_ENVIRONMENT, action, trade_id, instrument,
                str(units) if units else None, str(price) if price else None,
                str(realized_pl) if realized_pl else None,
                json.dumps(raw_request), json.dumps(raw_response, default=str))
    except Exception as e:
        logger.error(f"log_trade_action error: {e}")

async def log_error(pool, method, path, error_code,
                    error_message, reject_reason, request_body, raw_response):
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO error_log
                    (environment,method,path,error_code,error_message,
                     reject_reason,request_body,raw_response)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            """, OANDA_ENVIRONMENT, method, path, error_code, error_message, reject_reason,
                json.dumps(request_body) if request_body else None,
                json.dumps(raw_response, default=str) if raw_response else None)
    except Exception as e:
        logger.error(f"log_error error: {e}")

# ──────────────────────────────────────────────
# OANDA error parser
# ──────────────────────────────────────────────
def parse_v20_error(e: V20Error) -> Dict[str, Any]:
    try:
        body = json.loads(str(e))
    except Exception:
        body = {"errorMessage": str(e)}

    error_code    = body.get("errorCode", "UNKNOWN_ERROR")
    error_message = body.get("errorMessage", str(e))
    reject_reason = None
    for key in ("orderRejectTransaction", "tradeOrderRejectTransaction"):
        if key in body:
            reject_reason = body[key].get("rejectReason")
            break

    return {
        "errorCode":    error_code,
        "errorMessage": error_message,
        "rejectReason": reject_reason,
        "raw":          body
    }

# ──────────────────────────────────────────────
# Lifespan
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, db_optimizer, logging_service

    for i in range(5):
        try:
            if use_optimized_pool:
                # Use optimized pool with caching and monitoring
                db_optimizer = await create_optimized_pool(
                    DATABASE_URL,
                    min_size=int(os.getenv("DB_POOL_MIN_SIZE", 5)),
                    max_size=int(os.getenv("DB_POOL_MAX_SIZE", 20)),
                    enable_cache=os.getenv("DB_CACHE_ENABLED", "true").lower() == "true"
                )
                db_pool = db_optimizer.pool
                logger.info("PostgreSQL optimized pool initialized (with caching and monitoring).")
            else:
                # Standard pool
                db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
                logger.info("PostgreSQL standard pool initialized.")

            await init_db(db_pool)
            logger.info("PostgreSQL connection established.")

            # Re-initialize logging service with database pool
            logging_service = LoggingService(config=logging_config, db_pool=db_pool, force_reinit=True)
            await logging_service.init_audit_table()
            logging_service.logger.info("Enhanced logging service initialized with database pool")

            break
        except Exception as e:
            logger.warning(f"PostgreSQL unavailable ({i+1}/5): {e}")
            await asyncio.sleep(3)
    else:
        logger.error("Could not connect to PostgreSQL. Server continues without DB logging.")

    yield

    if db_optimizer:
        await db_optimizer.close()
    elif db_pool:
        await db_pool.close()

# ──────────────────────────────────────────────
# App
# ──────────────────────────────────────────────
app = FastAPI(
    title="Oanda MCP Server",
    description="REST API OANDA v20 con logging a PostgreSQL, compatible con MCP",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ──────────────────────────────────────────────
# Enhanced Middleware logging with Metrics
# ──────────────────────────────────────────────
SKIP_LOG_PATHS = {"/", "/health", "/metrics", "/docs", "/openapi.json", "/redoc"}

@app.middleware("http")
async def enhanced_logging_middleware(request: Request, call_next):
    """Enhanced middleware with structured logging and metrics collection"""
    import uuid

    start  = time.time()
    path   = request.url.path
    method = request.method
    query  = dict(request.query_params)
    correlation_id = str(uuid.uuid4())
    skip   = path in SKIP_LOG_PATHS or path.startswith("/dashboard") or path.startswith("/db/") or path.startswith("/pricing/stream")

    # Log incoming request
    if not skip:
        try:
            body = None
            if method in ("POST", "PATCH", "PUT"):
                try:
                    raw  = await request.body()
                    body = json.loads(raw) if raw else None
                except Exception:
                    body = None

            headers = dict(request.headers)
            logging_service.request_logger.log_request(
                method=method,
                path=path,
                query_params=query if query else None,
                headers=headers,
                body=body,
                correlation_id=correlation_id
            )
        except Exception as e:
            logger.error(f"Error logging request: {e}")

    # Process request
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)

    # Log response and collect metrics
    if not skip:
        try:
            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk)
            resp_bytes = b"".join(chunks)
            resp_size = len(resp_bytes)
            resp_body  = json.loads(resp_bytes.decode()) if resp_bytes else None
            is_error   = response.status_code >= 400

            # Log response
            logging_service.request_logger.log_response(
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration,
                response_size=resp_size,
                body=resp_body if not is_error else None
            )

            # Record metrics
            await logging_service.metrics.record_request(
                endpoint=path,
                method=method,
                duration_ms=duration,
                status_code=response.status_code,
                response_size=resp_size
            )

            # Log error details if applicable
            if is_error:
                logging_service.request_logger.log_error(
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    error_code=resp_body.get("errorCode") if resp_body else None,
                    error_message=resp_body.get("errorMessage") if resp_body else None,
                    duration_ms=duration
                )

            # Also log to database for audit trail (legacy support)
            if db_pool:
                asyncio.ensure_future(log_request(
                    db_pool, method, path, query, body,
                    response.status_code, duration, resp_body,
                    resp_body.get("errorCode")    if resp_body and is_error else None,
                    resp_body.get("errorMessage") if resp_body and is_error else None,
                    is_error
                ))

            return Response(content=resp_bytes, status_code=response.status_code,
                            headers=dict(response.headers), media_type=response.media_type)
        except Exception as e:
            logger.error(f"Enhanced middleware logging error: {e}")

    return response


# ══════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════
@app.get("/", tags=["Health"], summary="Server Status")
async def root():
    """
    Root endpoint. Returns basic server health and environment info.

    **Response:**
    - message: Confirmation message
    - environment: 'practice' or 'live'
    - mode: LIVE or PRACTICE
    - status: Server health status
    - timestamp: Server time (ISO 8601)
    """
    return {"message": "Oanda MCP Server running!", "environment": OANDA_ENVIRONMENT,
            "mode": "LIVE" if OANDA_ENVIRONMENT == "live" else "PRACTICE",
            "status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/health", tags=["Health"], summary="Health Check")
async def health_check():
    """
    Comprehensive health check. Tests OANDA API connection, database, and circuit breaker status.

    **Returns:**
    - status: 'healthy' or 'unhealthy'
    - oanda_connection: 'ok' if OANDA reachable
    - db_connection: 'ok' or 'unavailable'
    - environment: Current environment
    - mode: LIVE or PRACTICE
    - currency: Account base currency
    - balance: Current account balance
    - circuit_breaker_state: CLOSED, OPEN, or HALF_OPEN

    **Error scenarios:**
    - Circuit breaker OPEN: Returns 503 if too many failures
    - Database unavailable: Noted in db_connection field
    - OANDA unreachable: Error field populated
    """
    try:
        r = accounts.AccountDetails(accountID=OANDA_ACCOUNT_ID)
        await circuit_breaker.call(oanda_client.request, r)
        a = r.response["account"]
        return {"status": "healthy", "oanda_connection": "ok",
                "db_connection": "ok" if db_pool else "unavailable",
                "environment": OANDA_ENVIRONMENT,
                "mode": "LIVE" if OANDA_ENVIRONMENT == "live" else "PRACTICE",
                "currency": a.get("currency"), "balance": a.get("balance"),
                "circuit_breaker_state": circuit_breaker.get_state().value}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "circuit_breaker_state": circuit_breaker.get_state().value}


@app.get("/metrics", tags=["Health"], summary="System Metrics")
async def get_metrics():
    """
    Returns detailed circuit breaker, logging, and system metrics.

    **Metrics:**
    - circuit_breaker: Failure count, state, recovery attempts
    - logging: Request metrics per endpoint (count, latency, error rates)
    - environment: Current environment
    - mode: LIVE or PRACTICE
    - timestamp: Current time (ISO 8601)

    **Use cases:**
    - Monitor circuit breaker health
    - Track API performance and error rates
    - Analyze request patterns by endpoint
    - Detect when system is recovering
    """
    return {
        "circuit_breaker": circuit_breaker.get_metrics(),
        "logging": logging_service.get_metrics_summary(),
        "environment": OANDA_ENVIRONMENT,
        "mode": "LIVE" if OANDA_ENVIRONMENT == "live" else "PRACTICE",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ══════════════════════════════════════════════
# ACCOUNT
# ══════════════════════════════════════════════
@app.get("/account", tags=["Account"], summary="Get Full Account Details")
@rate_limit(50)
async def get_account_info():
    """
    Retrieves complete account information including balance, margin, positions, and trades.

    **Response includes:**
    - id: Account ID
    - alias: Account name/alias
    - currency: Base currency (usually USD)
    - balance: Current account balance
    - unrealizedPL: Unrealized profit/loss on open trades
    - realizedPL: Realized profit/loss (lifetime)
    - marginUsed: Margin currently in use
    - marginAvailable: Available margin for new positions
    - marginRate: Account leverage ratio
    - positions: Open positions for each instrument
    - trades: Open trades
    - orders: Pending orders

    **HTTP Status:**
    - 200: Success
    - 400: Invalid parameters or API error
    - 503: Circuit breaker open (too many failures)

    **Rate limit:** 50 req/min per account
    """
    try:
        r = accounts.AccountDetails(accountID=OANDA_ACCOUNT_ID)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={"errorMessage": str(e)})
    except V20Error as e:
        err = parse_v20_error(e)
        if db_pool: asyncio.ensure_future(log_error(db_pool,"GET","/account",err["errorCode"],err["errorMessage"],err["rejectReason"],None,err["raw"]))
        raise HTTPException(status_code=400, detail=err)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/account/summary", tags=["Account"], summary="Get Account Summary")
@rate_limit(50)
async def get_account_summary():
    """
    Retrieves lightweight account summary (balance, margin, P&L only).

    **Response includes:**
    - id, alias: Account identifiers
    - balance: Current balance
    - unrealizedPL: Open P&L
    - realizedPL: Closed P&L
    - marginUsed, marginAvailable: Margin metrics
    - marginRate: Leverage
    - createdByUserID: Admin who created account
    - createdTime: Account creation time
    - lastTransactionID: Most recent transaction ID

    **Difference from /account:**
    - Lighter response (no detailed position/trade arrays)
    - Faster response time
    - Same rate limit

    **Rate limit:** 50 req/min
    """
    try:
        r = accounts.AccountSummary(accountID=OANDA_ACCOUNT_ID)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={"errorMessage": str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/account/instruments", tags=["Account"], summary="List Available Instruments")
@rate_limit(50)
async def get_account_instruments(
    instruments: Optional[str] = Query(None, description="CSV filter: EUR_USD,GBP_USD,XAU_USD. Empty = all available")
):
    """
    Lists all instruments (currency pairs, metals, indices, etc.) available for trading on this account.

    **Query Parameters:**
    - instruments: Optional CSV list to filter specific instruments. Ex: EUR_USD,GBP_USD,XAU_USD

    **Response (array) includes for each instrument:**
    - name: Instrument code (e.g., EUR_USD)
    - type: CURRENCY, METAL, INDEX, COMMODITY
    - displayName: Human-readable name
    - pipLocation: Decimal position of pip (usually -4)
    - maximumOrderUnits: Max trade size allowed
    - minimumTradeSize: Minimum order size
    - maximumTrailingStopDistance: Max trailing stop distance
    - minimumTrailingStopDistance: Min trailing stop distance
    - financing: Interest rates for holding positions
    - marginRate: Leverage factor

    **Use cases:**
    - Discover what's available for trading
    - Get instrument metadata (pip location, max size)
    - Verify instrument exists before placing order

    **Rate limit:** 50 req/min
    """
    try:
        params = {"instruments": instruments} if instruments else {}
        r = accounts.AccountInstruments(accountID=OANDA_ACCOUNT_ID, params=params or None)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={"errorMessage": str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


# ══════════════════════════════════════════════
# INSTRUMENTS
# ══════════════════════════════════════════════
@app.get("/instruments/{instrument}/candles", tags=["Instruments"], summary="Get Historical Candles")
@rate_limit(50)
async def get_candles(
    instrument: str,
    price: str = Query("M", description="M=mid, B=bid, A=ask, BA=bid+ask, MBA=all. Can combine: 'BM' for bid+mid"),
    granularity: str = Query("S5", description="S5 S10 S15 S30 M1 M2 M4 M5 M10 M15 M30 H1 H2 H3 H4 H6 H8 H12 D W M"),
    count: int = Query(500, le=5000, description="Candles to return [1-5000]. Default: 500"),
    from_time: Optional[str] = Query(None, alias="from", description="RFC3339 start time. Ex: 2024-01-15T10:00:00Z"),
    to_time: Optional[str] = Query(None, alias="to", description="RFC3339 end time (required if from specified)"),
    smooth: bool = Query(False, description="True: use previous close as open. False: default open"),
    includeFirst: bool = Query(True, description="Include candle at 'from' timestamp"),
    dailyAlignment: int = Query(17, ge=0, le=23, description="Hour (0-23) for daily candle boundary"),
    alignmentTimezone: str = Query("America/New_York", description="Timezone for daily alignment (IANA name)"),
    weeklyAlignment: str = Query("Friday", description="Day for weekly alignment (Monday-Sunday)"),
):
    """
    Retrieves OHLCV (Open, High, Low, Close, Volume) historical candles for an instrument.

    **Path Parameters:**
    - instrument: EUR_USD, GBP_USD, XAU_USD, etc.

    **Query Parameters:**

    **Time selection (use one method):**
    1. count only: Gets last N candles
    2. from + to: Gets candles in time range
    3. from + count: Gets count candles starting from time

    **Example queries:**
    - `?granularity=M5&count=100` - Last 100 5-minute candles
    - `?granularity=D&from=2024-01-01T00:00:00Z&to=2024-01-31T23:59:59Z` - Daily candles in January
    - `?price=MBA&granularity=H1` - Bid, mid, ask data hourly

    **Price components:**
    - M: Midpoint (bid + ask) / 2
    - B: Bid prices
    - A: Ask prices
    - BA: Both bid and ask
    - MBA: All three (bid, mid, ask)

    **Granularities:**
    - S5, S10, S15, S30: Seconds
    - M1-M30: Minutes
    - H1-H12: Hours
    - D: Daily
    - W: Weekly
    - M: Monthly

    **Response (per candle):**
    - time: Candle open time (RFC3339)
    - bid/mid/ask: {o, h, l, c} (open, high, low, close)
    - volume: Tick count
    - complete: true if candle closed, false if current/incomplete

    **Use cases:**
    - Technical analysis, backtesting
    - Drawing charts
    - Computing indicators (MA, RSI, MACD, etc.)

    **Rate limit:** 50 req/min

    **Note:** Alignment parameters (dailyAlignment, alignmentTimezone, weeklyAlignment) control
    when daily/weekly candles "roll" (e.g., NYSE closes at 5pm NY time, so dailyAlignment=17).
    """
    try:
        # Pre-flight validation
        try:
            validate_instrument_name(instrument)
            validate_candle_params(granularity, count, from_time, to_time)
            validate_price_component(price)
        except ValueError as e:
            raise handle_validation_error(str(e))
        params: Dict[str, Any] = {
            "granularity":       granularity,
            "price":             price,
            "smooth":            str(smooth).lower(),
            "dailyAlignment":    str(dailyAlignment),
            "alignmentTimezone": alignmentTimezone,
            "weeklyAlignment":   weeklyAlignment,
        }
        if from_time and to_time:
            params["from"]        = from_time
            params["to"]          = to_time
            params["includeFirst"] = str(includeFirst).lower()
        elif from_time:
            params["from"]        = from_time
            params["count"]       = str(min(count, 5000))
            params["includeFirst"] = str(includeFirst).lower()
        else:
            # Without "from": count only, never send includeFirst
            params["count"] = str(min(count, 5000))
        r = instruments.InstrumentsCandles(instrument=instrument, params=params)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={"errorMessage": str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/instruments/{instrument}/orderbook", tags=["Instruments"])
@rate_limit(50)
async def get_orderbook(instrument: str, time: Optional[str] = Query(None)):
    try:
        r = instruments.InstrumentsOrderBook(instrument=instrument, params={"time": time} if time else {})
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={"errorMessage": str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/instruments/{instrument}/positionbook", tags=["Instruments"])
@rate_limit(50)
async def get_positionbook(instrument: str, time: Optional[str] = Query(None)):
    try:
        r = instruments.InstrumentsPositionBook(instrument=instrument, params={"time": time} if time else {})
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={"errorMessage": str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/historical/{instrument}", tags=["Instruments"])
@rate_limit(50)
async def get_historical_data(instrument: str, granularity: str = "D", count: int = 100):
    return await get_candles(instrument=instrument, granularity=granularity,
                             count=count, price="MBA", from_time=None, to_time=None)


# ══════════════════════════════════════════════
# PRICING
# ══════════════════════════════════════════════
@app.get("/price/{instrument}", tags=["Pricing"], summary="Get Single Instrument Price")
@rate_limit(100)
async def get_current_price(instrument: str):
    """
    Retrieves current bid/ask prices for a single instrument.

    **Path Parameters:**
    - instrument: Currency pair (EUR_USD, GBP_USD, etc.)

    **Response includes:**
    - instrument: Requested instrument
    - time: Quote timestamp (RFC3339)
    - bid: Current bid price (price to sell)
    - ask: Current ask price (price to buy)
    - closeoutBid: Close-out bid price (if different)
    - closeoutAsk: Close-out ask price
    - tradeable: true if instrument available for trading
    - quoteHomeConversionFactors: Conversion to account currency (if requested)

    **Use cases:**
    - Get current market price before placing order
    - Monitor spread (ask - bid)
    - Real-time price monitoring

    **Rate limit:** 100 req/min

    **Note:** For continuous real-time prices, use `/pricing/stream` (Server-Sent Events).
    """
    try:
        # Pre-flight validation
        try:
            validate_instrument_name(instrument)
        except ValueError as e:
            raise handle_validation_error(str(e))

        r = pricing.PricingInfo(accountID=OANDA_ACCOUNT_ID, params={"instruments": instrument})
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={"errorMessage": str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/pricing", tags=["Pricing"], summary="Get Multiple Prices")
@rate_limit(100)
async def get_multiple_prices(
    instruments_param: str = Query(..., alias="instruments", description="CSV: EUR_USD,GBP_USD,XAU_USD"),
    since: Optional[str] = Query(None, description="RFC3339 timestamp. Only return prices changed after this"),
    includeHomeConversions: bool = Query(False, description="Include conversion factors to base currency")
):
    """
    Retrieves current bid/ask prices for multiple instruments in one request.

    **Query Parameters:**
    - instruments (required): CSV list of instruments. Ex: EUR_USD,GBP_USD,XAU_USD,SPX500_USD
    - since: Optional RFC3339 timestamp. Only returns prices that changed after this time
    - includeHomeConversions: true to include conversion factors to account base currency

    **Response:**
    - prices: Array of price objects (same structure as /price/{instrument})
    - homeConversions: Optional conversion rates to base currency

    **Use cases:**
    - Batch price lookup (more efficient than multiple /price calls)
    - Dashboard/monitoring multiple instruments
    - Snapshot for algo trading

    **Example:**
    ```
    GET /pricing?instruments=EUR_USD,GBP_USD,XAU_USD&includeHomeConversions=true
    ```

    **Performance:**
    - Faster than calling /price/{instrument} multiple times
    - Single API request vs N requests
    - Use for monitoring dashboards

    **Rate limit:** 100 req/min
    """
    try:
        # Pre-flight validation
        try:
            # Validate each instrument in CSV list
            for inst in instruments_param.split(","):
                validate_instrument_name(inst.strip())
            if since:
                validate_rfc3339_datetime(since)
        except ValueError as e:
            raise handle_validation_error(str(e))

        params: Dict[str, Any] = {"instruments": instruments_param}
        if since:                           params["since"]                  = since
        if includeHomeConversions:          params["includeHomeConversions"] = "true"
        r = pricing.PricingInfo(accountID=OANDA_ACCOUNT_ID, params=params)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={"errorMessage": str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/pricing/stream", tags=["Pricing"])
@rate_limit(100)
async def stream_prices(
    instruments_param: str = Query(..., alias="instruments", description="CSV of instruments: EUR_USD,USD_CAD"),
    snapshot: bool = Query(True, description="Send initial price snapshot on connect"),
    includeHomeConversions: bool = Query(False, description="Include conversion factors to base currency"),
    max_ticks: int = Query(9999)
):
    """
    Real-time price stream via Server-Sent Events (SSE).
    Uses a separate thread to avoid blocking FastAPI event loop.
    """
    import queue
    import threading

    q: queue.Queue = queue.Queue(maxsize=500)
    STOP = object()

    def _stream_thread():
        """Runs blocking oandapyV20 stream in a separate thread."""
        try:
            s = pricing.PricingStream(
                accountID=OANDA_ACCOUNT_ID,
                params={"instruments": instruments_param}
            )
            n = 0
            for tick in stream_client.request(s):
                q.put(tick)
                if tick.get("type") == "PRICE":
                    n += 1
                    if max_ticks < 9999 and n >= max_ticks:
                        s.terminate("max_ticks reached")
                        break
        except Exception as e:
            q.put({"type": "error", "message": str(e)})
        finally:
            q.put(STOP)

    t = threading.Thread(target=_stream_thread, daemon=True)
    t.start()

    async def event_generator():
        loop = asyncio.get_event_loop()
        try:
            while True:
                # Get tick from queue without blocking event loop
                tick = await loop.run_in_executor(None, lambda: q.get(timeout=30))
                if tick is STOP:
                    break
                yield f"data: {json.dumps(tick)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','message':str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


# ══════════════════════════════════════════════
# ORDERS
# ══════════════════════════════════════════════
@app.get("/orders", tags=["Orders"])
@rate_limit(100)
async def get_orders(
    state:      str           = Query("PENDING", description="Order state: PENDING (default), FILLED, TRIGGERED, CANCELLED"),
    instrument: Optional[str] = Query(None,      description="Filter by instrument. Ex: EUR_USD"),
    count:      int           = Query(50,         description="Maximum number of orders [default=50, max=500]"),
    ids:        Optional[str] = Query(None,       description="CSV of OrderIDs to filter. Ex: 1,2,3"),
    beforeID:   Optional[str] = Query(None,       description="Pagination: returns orders before this OrderID")
):
    """Lists account orders with filters. GET /v3/accounts/{accountID}/orders"""
    try:
        params: Dict[str, Any] = {"state": state, "count": min(count, 500)}
        if instrument: params["instrument"] = instrument
        if ids:        params["ids"]        = ids
        if beforeID:   params["beforeID"]   = beforeID
        r = orders.OrderList(accountID=OANDA_ACCOUNT_ID, params=params)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={"errorMessage": str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/orders/pending", tags=["Orders"])
@rate_limit(100)
async def get_pending_orders():
    try:
        r = orders.OrdersPending(accountID=OANDA_ACCOUNT_ID)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={'errorMessage': str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/order/{order_id}", tags=["Orders"])
@rate_limit(100)
async def get_order_details(order_id: str):
    try:
        r = orders.OrderDetails(accountID=OANDA_ACCOUNT_ID, orderID=order_id)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={'errorMessage': str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

def _build_order_payload(req: Dict[str, Any], order_type: str) -> Dict[str, Any]:
    order: Dict[str, Any] = {
        "type": order_type, "instrument": req["instrument"],
        "units": str(req["units"]), "positionFill": "DEFAULT",
    }
    if order_type == "MARKET":
        order["timeInForce"] = req.get("time_in_force", "FOK")
    elif order_type in ("LIMIT", "STOP", "MARKET_IF_TOUCHED"):
        order["price"]      = str(req["price"])
        order["timeInForce"]= "GTD" if req.get("expiry") else "GTC"
        if req.get("expiry"): order["gtdTime"] = req["expiry"]
    if req.get("stop_loss"):
        order["stopLossOnFill"] = {"price": str(req["stop_loss"]), "timeInForce": "GTC"}
    if req.get("take_profit"):
        order["takeProfitOnFill"] = {"price": str(req["take_profit"]), "timeInForce": "GTC"}
    if req.get("trailing_stop"):
        order["trailingStopLossOnFill"] = {"distance": str(req["trailing_stop"]), "timeInForce": "GTC"}
    if req.get("client_id"):
        order["clientExtensions"] = {"id": req["client_id"]}
    return {"order": order}

async def _place_order(req: Dict[str, Any], order_type: str, request: Request):
    required = ["instrument", "units"] + (["price"] if order_type != "MARKET" else [])
    for f in required:
        if f not in req:
            raise HTTPException(status_code=422, detail={"errorMessage": f"Required field: {f}"})

    # Pre-flight validation
    try:
        validate_order_params(
            req["instrument"],
            req["units"],
            req.get("price")
        )
        if req.get("time_in_force"):
            validate_time_in_force(req["time_in_force"])
        if req.get("stop_loss"):
            validate_price_range(req["stop_loss"], min_val=0)
        if req.get("take_profit"):
            validate_price_range(req["take_profit"], min_val=0)
        if req.get("trailing_stop"):
            validate_price_range(req["trailing_stop"], min_val=0)
        if req.get("expiry"):
            validate_rfc3339_datetime(req["expiry"])
    except ValueError as e:
        raise handle_validation_error(str(e))

    payload = _build_order_payload(req, order_type)
    try:
        r = orders.OrderCreate(accountID=OANDA_ACCOUNT_ID, data=payload)
        await circuit_breaker.call(oanda_client.request, r)
        resp = r.response

        status         = "FILLED"   if "orderFillTransaction"   in resp else \
                         "REJECTED" if "orderRejectTransaction" in resp else "CREATED"
        oanda_order_id = resp.get("orderCreateTransaction", {}).get("id")
        oanda_trade_id = resp.get("orderFillTransaction",   {}).get("tradeOpened", {}).get("tradeID")
        reject_reason  = resp.get("orderRejectTransaction", {}).get("rejectReason")

        if db_pool:
            asyncio.ensure_future(log_order(
                db_pool, order_type, req["instrument"], req["units"], req.get("price"),
                req.get("time_in_force", "FOK" if order_type == "MARKET" else "GTC"),
                req.get("stop_loss"), req.get("take_profit"), req.get("trailing_stop"),
                status, oanda_order_id, oanda_trade_id, reject_reason, payload, resp))

        if status == "REJECTED":
            if db_pool:
                asyncio.ensure_future(log_error(db_pool, "POST", request.url.path,
                    "ORDER_REJECTED", "Order was rejected by OANDA", reject_reason, payload, resp))
            raise HTTPException(status_code=422, detail={
                "errorCode": "ORDER_REJECTED", "rejectReason": reject_reason, "raw": resp})

        return resp

    except HTTPException:
        raise
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={'errorMessage': str(e)})
    except V20Error as e:
        err = parse_v20_error(e)
        if db_pool:
            asyncio.ensure_future(log_error(db_pool, "POST", request.url.path,
                err["errorCode"], err["errorMessage"], err["rejectReason"], payload, err["raw"]))
            asyncio.ensure_future(log_order(
                db_pool, order_type, req.get("instrument"), req.get("units"), req.get("price"),
                None, None, None, None, "ERROR", None, None, err["errorCode"], payload, err["raw"]))
        raise HTTPException(status_code=400, detail=err)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.post("/order/market", tags=["Orders"], summary="Place Market Order", status_code=201)
@rate_limit(100)
async def place_market_order(order_request: MarketOrderRequest, request: Request):
    """
    Places a market order. Executes immediately at current market price.

    **Request Body:**
    - instrument: Currency pair (EUR_USD, GBP_USD, etc.)
    - units: Order size. Positive=long, negative=short
    - stop_loss: Optional stop loss price
    - take_profit: Optional take profit price
    - trailing_stop: Optional trailing stop distance
    - time_in_force: FOK (fill-or-kill) or IOC (immediate-or-cancel) - default: FOK
    - client_id: Optional custom ID for tracking

    **Response on success (201):**
    - orderCreateTransaction: Order creation details including ID, price, timestamp
    - orderFillTransaction: Fill details (only if FOK and immediate fill)
    - trades: Array of resulting trades

    **Response on rejection (422):**
    - errorCode: ORDER_REJECTED
    - rejectReason: Why order was rejected (insufficient margin, invalid size, etc.)

    **Examples of rejection reasons:**
    - INSUFFICIENT_MARGIN: Not enough margin for position
    - INVALID_ORDER: Order parameters invalid
    - MAX_ORDERS_FOR_ACCOUNT: Too many pending orders
    - FIFO_VIOLATION: FIFO rule violation (cannot open new position while losses open)

    **Rate limit:** 100 req/min

    **Error scenarios:**
    - 400: API error from OANDA
    - 422: Order rejected (insufficient margin, invalid parameters)
    - 503: Circuit breaker open (service unavailable)
    """
    return await _place_order(order_request.model_dump(), "MARKET", request)

@app.post("/order/limit", tags=["Orders"], summary="Place Limit Order", status_code=201)
@rate_limit(100)
async def place_limit_order(order_request: LimitOrderRequest, request: Request):
    """
    Places a limit order. Executes when price reaches or crosses the specified level.

    **Request Body:**
    - instrument: Currency pair
    - units: Order size
    - price: Limit entry price (order executes at this price or better)
    - stop_loss, take_profit: Optional protective orders
    - trailing_stop: Optional trailing stop
    - expiry: Optional expiration time (RFC3339). Omit for GTC (Good-til-Cancelled)
    - client_id: Optional custom ID

    **Order Lifetime:**
    - If expiry omitted: GTC (Good-til-Cancelled) - remains until filled/canceled
    - If expiry set: GTD (Good-til-Date) - expires at specified time

    **Response:**
    - Same as market order
    - Note: Order not immediately filled (PENDING status until price reached)

    **Common rejection reasons:**
    - Invalid price for instrument
    - Insufficient margin
    - Price in wrong direction (buy limit too high, sell limit too low)

    **Rate limit:** 100 req/min
    """
    return await _place_order(order_request.model_dump(), "LIMIT", request)

@app.post("/order/stop", tags=["Orders"], summary="Place Stop Order", status_code=201)
@rate_limit(100)
async def place_stop_order(order_request: StopOrderRequest, request: Request):
    """
    Places a stop order. Activates and becomes a market order when price touches/crosses specified level.

    **Request Body:**
    - instrument: Currency pair
    - units: Order size
    - price: Stop activation price (order activates when touched)
    - stop_loss, take_profit: Optional protective orders
    - expiry: Optional expiration time

    **Behavior:**
    - Order remains PENDING until price touches/crosses stop price
    - Once triggered, becomes market order at market price (not guaranteed at stop price)
    - Useful for entering breakout trades

    **Stop Order vs Stop Loss:**
    - Stop Order: Pending order that becomes market when triggered
    - Stop Loss: Risk management on open trade

    **Response:**
    - Same as market/limit orders

    **Rate limit:** 100 req/min
    """
    return await _place_order(order_request.model_dump(), "STOP", request)

@app.patch("/order/{order_id}", tags=["Orders"])
@rate_limit(100)
async def modify_order(order_id: str, order_update: ModifyOrderRequest):
    try:
        # OANDA OrderReplace requires the original order type in the body
        # Get current order to obtain it
        r_detail = orders.OrderDetails(accountID=OANDA_ACCOUNT_ID, orderID=order_id)
        await circuit_breaker.call(oanda_client.request, r_detail)
        original = r_detail.response.get("order", {})
        order_type = original.get("type", "LIMIT")

        data = order_update.model_dump(exclude_none=True)
        order_body: Dict[str, Any] = {
            "type":        order_type,
            "instrument":  original.get("instrument", ""),
            "units":       str(data["units"]) if "units" in data else original.get("units", "0"),
            "timeInForce": data.get("timeInForce", original.get("timeInForce", "GTC")),
        }
        # price: required for LIMIT, STOP, MARKET_IF_TOUCHED
        if order_type in ("LIMIT", "STOP", "MARKET_IF_TOUCHED"):
            order_body["price"] = str(data["price"]) if "price" in data else original.get("price", "0")
        if "gtdTime" in data:
            order_body["gtdTime"] = data["gtdTime"]
        if data.get("stop_loss"):
            order_body["stopLossOnFill"] = {"price": f"{float(data['stop_loss']):.5f}", "timeInForce": "GTC"}
        elif "stopLossOnFill" in original:
            order_body["stopLossOnFill"] = original["stopLossOnFill"]
        if data.get("take_profit"):
            order_body["takeProfitOnFill"] = {"price": f"{float(data['take_profit']):.5f}", "timeInForce": "GTC"}
        elif "takeProfitOnFill" in original:
            order_body["takeProfitOnFill"] = original["takeProfitOnFill"]

        r = orders.OrderReplace(accountID=OANDA_ACCOUNT_ID, orderID=order_id, data={"order": order_body})
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={'errorMessage': str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.delete("/order/{order_id}", tags=["Orders"])
@rate_limit(100)
async def cancel_order(order_id: str):
    try:
        r = orders.OrderCancel(accountID=OANDA_ACCOUNT_ID, orderID=order_id)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={'errorMessage': str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


# ══════════════════════════════════════════════
# TRADES
# ══════════════════════════════════════════════
@app.get("/trades", tags=["Trades"])
@rate_limit(100)
async def get_trades(state: str = Query("OPEN"),
                     instrument: Optional[str] = Query(None),
                     count: int = Query(50, description="Maximum number of trades [default=50, max=500]"),
                     ids: Optional[str] = Query(None, description="CSV of TradeIDs to filter. Ex: 1,2,3"),
                     beforeID: Optional[str] = Query(None, description="Pagination: returns trades before this TradeID")):
    try:
        params: Dict[str, Any] = {"state": state, "count": min(count, 500)}
        if instrument: params["instrument"] = instrument
        if ids:       params["ids"] = ids          # CSV: "1,2,3"
        if beforeID:  params["beforeID"] = beforeID
        r = trades.TradesList(accountID=OANDA_ACCOUNT_ID, params=params)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/trades/open", tags=["Trades"])
@rate_limit(100)
async def get_open_trades():
    try:
        r = trades.OpenTrades(accountID=OANDA_ACCOUNT_ID)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/trade/{trade_id}", tags=["Trades"])
@rate_limit(100)
async def get_trade_details(trade_id: str):
    try:
        r = trades.TradeDetails(accountID=OANDA_ACCOUNT_ID, tradeID=trade_id)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.patch("/trade/{trade_id}", tags=["Trades"], summary="Modify Trade (PATCH)")
@rate_limit(100)
async def modify_trade(trade_id: str, trade_update: ModifyTradeRequest):
    """
    Modifies stop loss, take profit, or trailing stop of an open trade using PATCH.

    **Path Parameters:**
    - trade_id: ID of open trade to modify

    **Request Body:**
    - stop_loss: New SL price. null or omit to remove SL. Field must be present to update
    - take_profit: New TP price. null to remove TP
    - trailing_stop: New TSL distance. null to remove TSL

    **Behavior:**
    - Each field is independent (can update just SL, or just TP, etc.)
    - Pass null (not missing) to remove an order
    - Omit field entirely to leave unchanged

    **Examples:**

    1. Update just stop loss:
    ```json
    {"stop_loss": 1.0500}
    ```

    2. Remove stop loss but keep take profit:
    ```json
    {"stop_loss": null}
    ```

    3. Update SL and TP:
    ```json
    {"stop_loss": 1.0500, "take_profit": 1.0800}
    ```

    **Response:**
    - tradeOrdersFilledTransaction: Details of orders created/modified/closed
    - tradeOrdersCancelledTransaction: If closing orders

    **Alternative:** Use PUT /trade/{id}/orders for more control over all four order types (TP, SL, TSL, GSL).

    **Rate limit:** 100 req/min

    **Note:** Use this endpoint when modifying trade SL/TP. Use DELETE /order/{id} to cancel pending orders.
    """
    try:
        # Pre-flight validation
        try:
            validate_trade_params(trade_id)
        except ValueError as e:
            raise handle_validation_error(str(e))

        data: Dict[str, Any] = {}
        # exclude_unset=True: only include fields client explicitly sent
        update = trade_update.model_dump(exclude_unset=True)
        if "stop_loss" in update:
            val = update["stop_loss"]
            if val is not None:
                try:
                    validate_price_range(val, min_val=0)
                except ValueError as e:
                    raise handle_validation_error(str(e))
            # OANDA: send null to cancel, or the price object to set/modify
            data["stopLoss"] = None if val is None else {"price": f"{val:.5f}", "timeInForce": "GTC"}
        if "take_profit" in update:
            val = update["take_profit"]
            if val is not None:
                try:
                    validate_price_range(val, min_val=0)
                except ValueError as e:
                    raise handle_validation_error(str(e))
            data["takeProfit"] = None if val is None else {"price": f"{val:.5f}", "timeInForce": "GTC"}
        if "trailing_stop" in update:
            val = update["trailing_stop"]
            if val is not None:
                try:
                    validate_price_range(val, min_val=0)
                except ValueError as e:
                    raise handle_validation_error(str(e))
            data["trailingStopLoss"] = None if val is None else {"distance": f"{val:.5f}", "timeInForce": "GTC"}
        if not data:
            raise HTTPException(status_code=400,
                detail={"errorMessage": "Must send at least stop_loss, take_profit or trailing_stop"})
        r = trades.TradeCRCDO(accountID=OANDA_ACCOUNT_ID, tradeID=trade_id, data=data)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.put("/trade/{trade_id}/close", tags=["Trades"])
@rate_limit(100)
async def close_trade(trade_id: str, body: CloseTradeRequest = CloseTradeRequest()):
    """
    Closes a trade partially or fully.
    PUT /v3/accounts/{accountID}/trades/{tradeID}/close
    Body: { "units": "200" }  — omit or "ALL" for full close.
    IMPORTANT: units goes in JSON body (not query string) per OANDA docs.
    """
    try:
        units = body.units
        # Build body per OANDA spec: send {"units": N} for partial, {} for full close
        if units and str(units).upper() != "ALL":
            data = {"units": str(units)}
        else:
            data = {}  # OANDA default: closes ALL units
        r = trades.TradeClose(accountID=OANDA_ACCOUNT_ID, tradeID=trade_id, data=data)
        await circuit_breaker.call(oanda_client.request, r)
        resp = r.response
        if db_pool:
            fill = resp.get("orderFillTransaction", {})
            asyncio.ensure_future(log_trade_action(
                db_pool, "CLOSE", trade_id, fill.get("instrument"),
                fill.get("units"), fill.get("price"), fill.get("pl"),
                {"tradeID": trade_id, "units": units or "ALL"}, resp))
        return resp
    except CircuitBreakerOpenError as e:
        raise HTTPException(status_code=503, detail={'errorMessage': str(e)})
    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


# ══════════════════════════════════════════════
# POSITIONS
# ══════════════════════════════════════════════
@app.get("/positions", tags=["Positions"])
@rate_limit(100)
async def get_all_positions():
    try:
        r = positions.PositionList(accountID=OANDA_ACCOUNT_ID)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/positions/open", tags=["Positions"])
@rate_limit(100)
async def get_open_positions():
    try:
        r = positions.OpenPositions(accountID=OANDA_ACCOUNT_ID)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/position/{instrument}", tags=["Positions"])
@rate_limit(100)
async def get_position_detail(instrument: str):
    try:
        r = positions.PositionDetails(accountID=OANDA_ACCOUNT_ID, instrument=instrument)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.post("/position/close/{instrument}", tags=["Positions"])
@rate_limit(100)
async def close_position(instrument: str, body: ClosePositionRequest = ClosePositionRequest()):
    """Closes a position for an instrument. Automatically detects direction."""
    try:
        side = (body.side or "both").lower()

        # Query current position to determine which sides exist
        pos_req = positions.PositionDetails(accountID=OANDA_ACCOUNT_ID, instrument=instrument)
        try:
            await circuit_breaker.call(oanda_client.request, pos_req)
            pos = pos_req.response.get("position", {})
            long_units  = float(pos.get("long",  {}).get("units", "0"))
            short_units = float(pos.get("short", {}).get("units", "0"))
        except Exception:
            long_units, short_units = 0.0, 0.0

        has_long  = long_units  > 0
        has_short = short_units < 0

        # OANDA rejects field if side doesn't exist — omit it, don't set to "0"
        if side in ("both", ""):
            close_data = {}
            if has_long:  close_data["longUnits"]  = "ALL"
            if has_short: close_data["shortUnits"] = "ALL"
            if not close_data:
                raise HTTPException(status_code=400,
                    detail={"errorMessage": f"No open positions in {instrument}"})
        elif side == "long":
            if not has_long:
                raise HTTPException(status_code=400,
                    detail={"errorMessage": f"No long position in {instrument}"})
            close_data = {"longUnits": "ALL"}
        elif side == "short":
            if not has_short:
                raise HTTPException(status_code=400,
                    detail={"errorMessage": f"No short position in {instrument}"})
            close_data = {"shortUnits": "ALL"}
        else:
            close_data = {}
            if has_long:  close_data["longUnits"]  = "ALL"
            if has_short: close_data["shortUnits"] = "ALL"
            if not close_data:
                raise HTTPException(status_code=400,
                    detail={"errorMessage": f"No open positions in {instrument}"})

        r = positions.PositionClose(accountID=OANDA_ACCOUNT_ID, instrument=instrument, data=close_data)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


# ══════════════════════════════════════════════
# TRANSACTIONS
# ══════════════════════════════════════════════
@app.get("/transactions", tags=["Transactions"])
@rate_limit(50)
async def get_transactions(
    from_time: Optional[str] = Query(None, alias="from", description="Start time RFC3339 [default=Account Creation Time]"),
    to_time:   Optional[str] = Query(None, alias="to",   description="End time RFC3339 [default=Request Time]"),
    pageSize:  int           = Query(100, alias="pageSize", description="Number of transactions per page [default=100, max=1000]"),
    type:      Optional[str] = Query(None, description="CSV filter of TransactionFilter: ORDER_FILL,ORDER_CANCEL,TRADE_UPDATE,TRADE_CLOSE,DAILY_FINANCING,etc.")
):
    try:
        params: Dict[str, Any] = {"pageSize": min(pageSize, 1000)}
        if from_time: params["from"] = from_time
        if to_time:   params["to"]   = to_time
        if type:      params["type"] = type
        r = transactions.TransactionList(accountID=OANDA_ACCOUNT_ID, params=params)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/transaction/{transaction_id}", tags=["Transactions"])
@rate_limit(50)
async def get_transaction_detail(transaction_id: str):
    try:
        r = transactions.TransactionDetails(accountID=OANDA_ACCOUNT_ID, transactionID=transaction_id)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/transactions/range", tags=["Transactions"])
@rate_limit(50)
async def get_transactions_by_range(from_id: str = Query(...), to_id: str = Query(...),
                                    type: Optional[str] = Query(None)):
    try:
        params: Dict[str, Any] = {"from": from_id, "to": to_id}
        if type: params["type"] = type
        r = transactions.TransactionIDRange(accountID=OANDA_ACCOUNT_ID, params=params)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})

@app.get("/transactions/since/{transaction_id}", tags=["Transactions"])
@rate_limit(50)
async def get_transactions_since(transaction_id: str):
    try:
        r = transactions.TransactionsSinceID(accountID=OANDA_ACCOUNT_ID, params={"id": transaction_id})
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


# ══════════════════════════════════════════════
# ACCOUNT — additional endpoints
# ══════════════════════════════════════════════

@app.patch("/account/configuration", tags=["Account"])
@rate_limit(50)
async def configure_account(body: AccountConfigRequest):
    """
    Configures account: alias and/or marginRate.
    PATCH /v3/accounts/{accountID}/configuration
    """
    try:
        data: Dict[str, Any] = {}
        if body.alias:      data["alias"]      = body.alias
        if body.marginRate: data["marginRate"]  = body.marginRate
        if not data:
            raise HTTPException(status_code=400, detail={"errorMessage": "Provide alias or marginRate"})
        r = accounts.AccountConfiguration(accountID=OANDA_ACCOUNT_ID, data=data)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


@app.get("/account/changes", tags=["Account"])
@rate_limit(50)
async def get_account_changes(sinceTransactionID: str = Query(..., description="Transaction ID from which to get changes")):
    """
    Polling account changes since a TransactionID.
    GET /v3/accounts/{accountID}/changes?sinceTransactionID=XXXX
    Useful for efficient state synchronization.
    """
    try:
        r = accounts.AccountChanges(accountID=OANDA_ACCOUNT_ID,
                                     params={"sinceTransactionID": sinceTransactionID})
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


# ══════════════════════════════════════════════
# PRICING — additional endpoints
# ══════════════════════════════════════════════

@app.get("/pricing/latest-candles", tags=["Pricing"])
@rate_limit(100)
async def get_latest_candles(
    candleSpecifications: str = Query(..., description="CSV of specs: EUR_USD:S5:M,USD_CAD:M1:BM"),
    units: float = Query(1.0),
    smooth: bool = Query(False),
    dailyAlignment: int = Query(17, ge=0, le=23),
    alignmentTimezone: str = Query("America/New_York"),
    weeklyAlignment: str = Query("Friday")
):
    """
    Latest completed candles for instrument/granularity/price combinations.
    GET /v3/accounts/{accountID}/candles/latest
    """
    try:
        import requests as req_lib
        base_url = "https://api-fxpractice.oanda.com" if OANDA_ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        url = f"{base_url}/v3/accounts/{OANDA_ACCOUNT_ID}/candles/latest"
        headers = {"Authorization": f"Bearer {OANDA_API_KEY}", "Content-Type": "application/json"}
        params: Dict[str, Any] = {
            "candleSpecifications": candleSpecifications,
            "units":                str(units),
            "smooth":               str(smooth).lower(),
            "dailyAlignment":       str(dailyAlignment),
            "alignmentTimezone":    alignmentTimezone,
            "weeklyAlignment":      weeklyAlignment,
        }
        resp = req_lib.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


@app.get("/instruments/{instrument}/candles/account", tags=["Instruments"])
@rate_limit(100)
async def get_account_candles(
    instrument: str,
    granularity: str = Query("M5", description="Granularity: S5 M1 M5 M15 M30 H1 H4 D W M"),
    price: str = Query("M", description="Component: M=mid B=bid A=ask BA=bid+ask MBA=all"),
    count: int = Query(50, le=5000),
    units: float = Query(1.0, description="Units for weighted bid/ask VWAP calculation"),
    smooth: bool = Query(False),
    from_time: Optional[str] = Query(None, alias="from"),
    to_time: Optional[str] = Query(None, alias="to"),
    includeFirst: bool = Query(True),
    dailyAlignment: int = Query(17, ge=0, le=23),
    alignmentTimezone: str = Query("America/New_York"),
    weeklyAlignment: str = Query("Friday")
):
    """
    Candles with account context — uses units to calculate weighted bid/ask VWAP.
    Redirects to GET /v3/accounts/{accountID}/candles/latest with candleSpecifications.
    Documented in pricing-ep: GET /v3/accounts/{accountID}/candles/latest
    NOTE: The /v3/accounts/{id}/instruments/{id}/candles endpoint is NOT in official
    OANDA documentation. Candles-with-units functionality obtained via
    /v3/accounts/{accountID}/candles/latest (pricing-ep).
    """
    try:
        import requests as req_lib
        base_url = "https://api-fxpractice.oanda.com" if OANDA_ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        # Use documented endpoint: GET /v3/accounts/{accountID}/candles/latest
        url = f"{base_url}/v3/accounts/{OANDA_ACCOUNT_ID}/candles/latest"
        headers = {"Authorization": f"Bearer {OANDA_API_KEY}", "Content-Type": "application/json"}
        # candleSpecifications format: INSTRUMENT:GRANULARITY:PRICE  (pricing-df: CandleSpecification)
        spec = f"{instrument}:{granularity}:{price}"
        params: Dict[str, Any] = {
            "candleSpecifications": spec,
            "units":                str(units),
            "smooth":               str(smooth).lower(),
            "dailyAlignment":       str(dailyAlignment),
            "alignmentTimezone":    alignmentTimezone,
            "weeklyAlignment":      weeklyAlignment,
        }
        resp = req_lib.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Normalize response: extract first (and only) element from latestCandles
        # and return in same format as normal candles for MCP compatibility
        latest = data.get("latestCandles", [])
        if latest:
            entry = latest[0]
            return {
                "instrument": entry.get("instrument", instrument),
                "granularity": entry.get("granularity", granularity),
                "candles": entry.get("candles", []),
                "_source": "candles/latest",
                "_units": units,
            }
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


# ══════════════════════════════════════════════
# ORDERS — additional endpoints
# ══════════════════════════════════════════════

@app.post("/order/mit", tags=["Orders"])
@rate_limit(100)
async def place_mit_order(order_request: MITOrderRequest, request: Request):
    """
    Places a MARKET_IF_TOUCHED order.
    Executes when price touches specified level (market entry).
    """
    return await _place_order(order_request.model_dump(), "MARKET_IF_TOUCHED", request)


@app.put("/order/{order_id}/client-extensions", tags=["Orders"])
@rate_limit(100)
async def update_order_client_extensions(order_id: str, body: ClientExtensionsRequest):
    """
    Updates client extensions of an order.
    PUT /v3/accounts/{accountID}/orders/{orderID}/clientExtensions
    """
    try:
        data: Dict[str, Any] = {}
        if body.clientExtensions:      data["clientExtensions"]      = body.clientExtensions
        if body.tradeClientExtensions: data["tradeClientExtensions"] = body.tradeClientExtensions
        r = orders.OrderClientExtensions(accountID=OANDA_ACCOUNT_ID, orderID=order_id, data=data)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


# ══════════════════════════════════════════════
# TRADES — additional endpoints
# ══════════════════════════════════════════════

@app.put("/trade/{trade_id}/orders", tags=["Trades"])
@rate_limit(100)
async def set_trade_orders(trade_id: str, body: TradeOrdersRequest):
    """
    Creates, modifies or cancels dependent trade orders (TP, SL, Trailing SL).
    PUT /v3/accounts/{accountID}/trades/{tradeID}/orders
    Send null to cancel existing order.
    More robust than PATCH /trade/{id} for managing SL/TP independently.
    """
    try:
        data: Dict[str, Any] = {}
        # If field comes explicitly, include it (even if null/None → cancels)
        body_dict = body.model_dump(exclude_unset=True)
        if "takeProfit" in body_dict:
            data["takeProfit"] = body_dict["takeProfit"]  # None = cancel
        if "stopLoss" in body_dict:
            data["stopLoss"] = body_dict["stopLoss"]
        if "trailingStopLoss" in body_dict:
            data["trailingStopLoss"] = body_dict["trailingStopLoss"]
        if "guaranteedStopLoss" in body_dict:
            data["guaranteedStopLoss"] = body_dict["guaranteedStopLoss"]  # GSLO enabled accounts only
        r = trades.TradeCRCDO(accountID=OANDA_ACCOUNT_ID, tradeID=trade_id, data=data)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


@app.put("/trade/{trade_id}/client-extensions", tags=["Trades"])
@rate_limit(100)
async def update_trade_client_extensions(trade_id: str, body: ClientExtensionsRequest):
    """
    Updates client extensions of a trade.
    PUT /v3/accounts/{accountID}/trades/{tradeID}/clientExtensions
    """
    try:
        data: Dict[str, Any] = {}
        if body.clientExtensions: data["clientExtensions"] = body.clientExtensions
        r = trades.TradeClientExtensions(accountID=OANDA_ACCOUNT_ID, tradeID=trade_id, data=data)
        await circuit_breaker.call(oanda_client.request, r)
        return r.response
    except CircuitBreakerOpenError as e:
         raise HTTPException(status_code=503, detail={'errorMessage': str(e)})

    except V20Error as e:
        raise HTTPException(status_code=400, detail=parse_v20_error(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"errorMessage": str(e)})


# ══════════════════════════════════════════════
# DATABASE ENDPOINTS (for dashboard)
# ══════════════════════════════════════════════
def _db_check():
    if not db_pool:
        raise HTTPException(status_code=503, detail={"errorMessage": "Database unavailable"})

@app.get("/db/requests", tags=["Database"])
async def db_get_requests(limit: int = Query(50), only_errors: bool = Query(False)):
    _db_check()
    async with db_pool.acquire() as conn:
        where = "WHERE is_error = TRUE" if only_errors else ""
        rows = await conn.fetch(f"SELECT * FROM request_log {where} ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

@app.get("/db/orders", tags=["Database"])
async def db_get_orders(limit: int = Query(50), instrument: Optional[str] = Query(None)):
    _db_check()
    async with db_pool.acquire() as conn:
        if instrument:
            rows = await conn.fetch("SELECT * FROM order_log WHERE instrument=$1 ORDER BY created_at DESC LIMIT $2", instrument, limit)
        else:
            rows = await conn.fetch("SELECT * FROM order_log ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

@app.get("/db/trades", tags=["Database"])
async def db_get_trades(limit: int = Query(50)):
    _db_check()
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM trade_log ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

@app.get("/db/errors", tags=["Database"])
async def db_get_errors(limit: int = Query(50)):
    _db_check()
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM error_log ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

@app.get("/db/stats", tags=["Database"])
async def db_get_stats():
    _db_check()
    async with db_pool.acquire() as conn:
        return {
            "total_requests":  await conn.fetchval("SELECT COUNT(*) FROM request_log"),
            "total_errors":    await conn.fetchval("SELECT COUNT(*) FROM error_log"),
            "total_orders":    await conn.fetchval("SELECT COUNT(*) FROM order_log"),
            "filled_orders":   await conn.fetchval("SELECT COUNT(*) FROM order_log WHERE status='FILLED'"),
            "rejected_orders": await conn.fetchval("SELECT COUNT(*) FROM order_log WHERE status='REJECTED'"),
            "total_trades":    await conn.fetchval("SELECT COUNT(*) FROM trade_log"),
        }

@app.get("/db-stats", tags=["Database"])
async def db_optimization_stats():
    """Enhanced database statistics including connection pool, cache, and query performance metrics"""
    _db_check()

    stats = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pool_config": {
            "min_size": db_optimizer.min_size if db_optimizer else "N/A",
            "max_size": db_optimizer.max_size if db_optimizer else "N/A",
            "optimized": use_optimized_pool,
        },
        "cache": {
            "enabled": db_optimizer is not None and db_optimizer.cache is not None,
        }
    }

    # Get basic database stats
    async with db_pool.acquire() as conn:
        stats["database"] = {
            "total_requests": await conn.fetchval("SELECT COUNT(*) FROM request_log"),
            "total_errors": await conn.fetchval("SELECT COUNT(*) FROM error_log"),
            "total_orders": await conn.fetchval("SELECT COUNT(*) FROM order_log"),
            "filled_orders": await conn.fetchval("SELECT COUNT(*) FROM order_log WHERE status='FILLED'"),
            "rejected_orders": await conn.fetchval("SELECT COUNT(*) FROM order_log WHERE status='REJECTED'"),
            "total_trades": await conn.fetchval("SELECT COUNT(*) FROM trade_log"),
        }

    # Add optimization stats if using optimized pool
    if db_optimizer:
        try:
            opt_stats = await db_optimizer.get_stats()
            stats["optimization"] = opt_stats
        except Exception as e:
            logger.warning(f"Could not retrieve optimization stats: {e}")
            stats["optimization"] = {"error": str(e)}
    else:
        stats["optimization"] = {"status": "Optimized pool not enabled (USE_OPTIMIZED_POOL=false)"}

    return stats


# ══════════════════════════════════════════════
# GLOBAL ERROR HANDLER
# ══════════════════════════════════════════════
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception at {request.url.path}: {exc}")
    return JSONResponse(status_code=500,
                        content={"errorCode": "INTERNAL_ERROR", "errorMessage": str(exc)})


# ══════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════
from fastapi.responses import HTMLResponse
import pathlib

@app.get("/dashboard", tags=["Dashboard"], response_class=HTMLResponse)
async def dashboard():
    """Server visual dashboard."""
    html_path = pathlib.Path(__file__).parent / "dashboard.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h2>dashboard.html not found</h2>", status_code=404)


# ══════════════════════════════════════════════
# MCP — Model Context Protocol
# Correct MCP protocol implementation over SSE
# compatible with Claude Desktop.
#
# Flow:
#   1. Claude Desktop does GET /sse
#   2. Server sends "endpoint" event with channel URL
#   3. Claude Desktop does POST /messages with JSON-RPC
#   4. Server responds via SSE to client channel
# ══════════════════════════════════════════════

import uuid
from collections import defaultdict

# Message queue per session_id
mcp_queues: dict = {}

MCP_TOOLS = [
    {
        "name": "account",
        "description": "Manages OANDA account. Query balance/NAV/margin, available instruments, recent changes and configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "get=full account, summary=summary, instruments=list instruments, changes=changes since transactionID, configure=modify alias/margin",
                    "enum": ["get", "summary", "instruments", "changes", "configure"]
                },
                "sinceTransactionID": {"type": "string", "description": "[changes] Transaction ID from which to get changes"},
                "instruments":        {"type": "string", "description": "[instruments] Comma-separated list. Empty = all"},
                "alias":              {"type": "string", "description": "[configure] New account alias"},
                "marginRate":         {"type": "string", "description": "[configure] New margin rate. Ex: '0.02' for 2%"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "instrument",
        "description": "Instrument market data: historical OHLCV candles, order book and position book.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "candles=OHLCV candles (GET /v3/instruments/{id}/candles), candles_account=latest candle with units-weighted VWAP (GET /v3/accounts/{id}/candles/latest), orderbook=pending orders by price, positionbook=open positions by price",
                    "enum": ["candles", "candles_account", "orderbook", "positionbook"]
                },
                "instrument":  {"type": "string",  "description": "Required. Ex: EUR_USD, XAU_USD, SPX500_USD"},
                "granularity": {"type": "string",  "description": "[candles] S5 S10 S15 S30 M1 M2 M4 M5 M10 M15 M30 H1 H2 H3 H4 H6 H8 H12 D W M. Default: S5 (OANDA default)"},
                "price":       {"type": "string",  "description": "[candles/candles_account] Price component: M=mid (default), B=bid, A=ask, BA=bid+ask, MBA=all. Free combinations of M B A"},
                "count":       {"type": "integer", "description": "[candles] Number of candles. Default: 500, max: 5000. Do not use with from+to"},
                "from_time":   {"type": "string",  "description": "[candles] Start date RFC3339. Ex: 2024-01-15T00:00:00Z"},
                "to_time":     {"type": "string",  "description": "[candles] End date RFC3339"},
                "units":       {"type": "string",  "description": "[candles_account] Position size for VWAP. Default: 1"},
                "time":        {"type": "string",  "description": "[orderbook/positionbook] RFC3339 timestamp for historical snapshot"}
            },
            "required": ["action", "instrument"]
        }
    },
    {
        "name": "pricing",
        "description": "Real-time bid/ask prices for one or multiple instruments. Latest completed candle multi-instrument.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "get_price=price of one instrument, get_prices=prices of multiple, latest_candles=latest completed candle of multiple",
                    "enum": ["get_price", "get_prices", "latest_candles"]
                },
                "instrument":           {"type": "string", "description": "[get_price] Single instrument. Ex: EUR_USD"},
                "instruments":          {"type": "string", "description": "[get_prices/latest_candles] Comma-separated list. Ex: EUR_USD,GBP_USD"},
                "candleSpecifications": {"type": "string", "description": "[latest_candles] CSV format INSTRUMENT:GRAN:PRICE. Ex: EUR_USD:M5:M,GBP_USD:M1:BA. Priority over instruments"},
                "granularity":          {"type": "string", "description": "[latest_candles] Default: S5"},
                "price":                {"type": "string", "description": "[latest_candles] M=mid B=bid A=ask BA=bid+ask. Default: M"},
                "since":                {"type": "string", "description": "[get_prices] Only prices updated since this RFC3339 timestamp"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "order",
        "description": "Manages OANDA orders: query, create (market/limit/stop/MIT), modify and cancel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "list=list orders, pending=pending orders, get=detail by ID, place_market=market order, place_limit=limit order, place_stop=stop order, place_mit=market-if-touched, modify=modify order, cancel=cancel order, tag=tag with client extensions",
                    "enum": ["list", "pending", "get", "place_market", "place_limit", "place_stop", "place_mit", "modify", "cancel", "tag"]
                },
                "order_id":     {"type": "string",  "description": "[get/modify/cancel] Order ID"},
                "instrument":   {"type": "string",  "description": "[place_*] Ex: EUR_USD"},
                "units":        {"type": "integer", "description": "[place_*] Positive=buy long, negative=sell short"},
                "price":        {"type": "number",  "description": "[place_limit/stop/mit, modify] Entry or activation price"},
                "stop_loss":    {"type": "number",  "description": "Stop loss price"},
                "take_profit":  {"type": "number",  "description": "Take profit price"},
                "trailing_stop":{"type": "number",  "description": "[place_market] Trailing stop distance in pips"},
                "state":        {"type": "string",  "description": "[list] PENDING, FILLED, CANCELLED. Default: PENDING"},
                "count":        {"type": "integer", "description": "[list] Maximum orders. Default: 50"},
                "client_id":    {"type": "string",  "description": "[tag] Custom ID to identify order. Ex: my-strategy-001"},
                "client_tag":   {"type": "string",  "description": "[tag] Free tag. Ex: breakout"},
                "client_comment":{"type": "string", "description": "[tag] Free comment"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "trade",
        "description": "Manages active and closed OANDA trades: query, close full/partial, modify SL/TP/trailing stop.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "list=list trades, list_open=open trades, get=detail by ID, close=close trade, modify=modify SL/TP via PATCH, set_orders=set SL/TP via direct PUT, tag=tag with client extensions",
                    "enum": ["list", "list_open", "get", "close", "modify", "set_orders", "tag"]
                },
                "trade_id":      {"type": "string",  "description": "[get/close/modify/set_orders] Trade ID"},
                "units":         {"type": "string",  "description": "[close] Units to close (positive). Default: ALL (full close)"},
                "stop_loss":       {"type": "number",  "description": "[modify/set_orders] SL price (omit=no change, null=cancel)"},
                "take_profit":     {"type": "number",  "description": "[modify/set_orders] TP price (omit=no change, null=cancel)"},
                "trailing_stop":   {"type": "number",  "description": "[modify/set_orders] Trailing stop distance in price (omit=no change, null=cancel)"},
                "guaranteed_stop": {"type": "number",  "description": "[set_orders] Guaranteed SL price. Only accounts with GSLO enabled (UK/EU). null=cancel"},
                "state":         {"type": "string",  "description": "[list] State: OPEN (default), CLOSED, CLOSE_WHEN_TRADEABLE, ALL"},
                "instrument":    {"type": "string",  "description": "[list] Filter by instrument. Ex: EUR_USD"},
                "count":         {"type": "integer", "description": "[list] Maximum trades. Default: 50, max: 500"},
                "ids":           {"type": "string",  "description": "[list] Filter by specific IDs (CSV). Ex: '1,2,3'"},
                "before_id":     {"type": "string",  "description": "[list] Pagination: returns trades before this TradeID"},
                "client_id":     {"type": "string",  "description": "[tag] Custom ID. Ex: my-trade-001"},
                "client_tag":    {"type": "string",  "description": "[tag] Free tag. Ex: scalp"},
                "client_comment":{"type": "string",  "description": "[tag] Free comment"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "position",
        "description": "Query and close OANDA positions. A position can have long and short sides simultaneously.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "list_all=all positions, list_open=open positions, get=detail of one instrument, close=close position",
                    "enum": ["list_all", "list_open", "get", "close"]
                },
                "instrument": {"type": "string", "description": "[get/close] Ex: EUR_USD"},
                "side":       {"type": "string", "description": "[close] long, short or both. Default: both (closes what exists)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "transaction",
        "description": "OANDA transaction history: executed operations, orders, daily financing and margin changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "list=latest N transactions with detail, get=specific transaction by ID, range=transactions between two IDs, since=transactions since an ID",
                    "enum": ["list", "get", "range", "since"]
                },
                "transaction_id": {"type": "string",  "description": "[get/since] Transaction ID. Ex: 29307"},
                "from_id":        {"type": "string",  "description": "[range] Initial ID inclusive. Ex: 29200"},
                "to_id":          {"type": "string",  "description": "[range] Final ID inclusive. Ex: 29307"},
                "count":          {"type": "integer", "description": "[list] Number of recent transactions. Default: 50"},
                "from_time":      {"type": "string",  "description": "[list] Start date RFC3339"},
                "to_time":        {"type": "string",  "description": "[list] End date RFC3339"},
                "type":           {"type": "string",  "description": "Type filter: ORDER_FILL, TRADE_UPDATE, DAILY_FINANCING, MARGIN_CALL_ENTER, etc"}
            },
            "required": ["action"]
        }
    },
]


async def _execute_tool(name: str, args: dict) -> dict:
    """Executes an MCP tool grouped by OANDA category."""
    import httpx, re
    base   = f"http://localhost:{int(os.getenv('PORT', 8000))}"
    action = args.get("action", "")

    async with httpx.AsyncClient(timeout=30) as client:

        # ── ACCOUNT ──────────────────────────────────────────────────────────
        if name == "account":
            if action == "get":
                return (await client.get(f"{base}/account")).json()
            elif action == "summary":
                return (await client.get(f"{base}/account/summary")).json()
            elif action == "instruments":
                params = {}
                if args.get("instruments"): params["instruments"] = args["instruments"]
                return (await client.get(f"{base}/account/instruments", params=params)).json()
            elif action == "changes":
                return (await client.get(f"{base}/account/changes",
                    params={"sinceTransactionID": args["sinceTransactionID"]})).json()
            elif action == "configure":
                body = {}
                if args.get("alias"):      body["alias"]      = args["alias"]
                if args.get("marginRate"): body["marginRate"] = args["marginRate"]
                return (await client.patch(f"{base}/account/configuration", json=body)).json()

        # ── INSTRUMENT ───────────────────────────────────────────────────────
        elif name == "instrument":
            inst = args["instrument"]
            if action == "candles":
                params = {
                    "granularity": args.get("granularity", "S5"),
                    "price":       args.get("price", "M"),
                    "count":       args.get("count", 500),
                }
                if args.get("from_time"): params["from"] = args["from_time"]
                if args.get("to_time"):   params["to"]   = args["to_time"]
                return (await client.get(f"{base}/instruments/{inst}/candles", params=params)).json()
            elif action == "candles_account":
                # Uses GET /v3/accounts/{id}/candles/latest internally (documented pricing-ep)
                params = {
                    "granularity": args.get("granularity", "M5"),
                    "price":       args.get("price", "M"),
                    "count":       args.get("count", 50),
                    "units":       str(args.get("units", "1")),
                }
                if args.get("from_time"): params["from"] = args["from_time"]
                if args.get("to_time"):   params["to"]   = args["to_time"]
                return (await client.get(f"{base}/instruments/{inst}/candles/account", params=params)).json()
            elif action == "orderbook":
                params = {}
                if args.get("time"): params["time"] = args["time"]
                return (await client.get(f"{base}/instruments/{inst}/orderbook", params=params)).json()
            elif action == "positionbook":
                params = {}
                if args.get("time"): params["time"] = args["time"]
                return (await client.get(f"{base}/instruments/{inst}/positionbook", params=params)).json()

        # ── PRICING ──────────────────────────────────────────────────────────
        elif name == "pricing":
            if action == "get_price":
                return (await client.get(f"{base}/price/{args['instrument']}")).json()
            elif action == "get_prices":
                params = {"instruments": args["instruments"]}
                if args.get("since"): params["since"] = args["since"]
                return (await client.get(f"{base}/pricing", params=params)).json()
            elif action == "latest_candles":
                if args.get("candleSpecifications"):
                    specs = args["candleSpecifications"]
                else:
                    gran  = args.get("granularity", "S5")
                    price = args.get("price", "M")
                    specs = ",".join(f"{i.strip()}:{gran}:{price}"
                                     for i in args.get("instruments", "").split(",") if i.strip())
                return (await client.get(f"{base}/pricing/latest-candles",
                    params={"candleSpecifications": specs})).json()

        # ── ORDER ────────────────────────────────────────────────────────────
        elif name == "order":
            if action == "list":
                params = {"state": args.get("state", "PENDING"), "count": args.get("count", 50)}
                if args.get("instrument"): params["instrument"] = args["instrument"]
                return (await client.get(f"{base}/orders", params=params)).json()
            elif action == "pending":
                return (await client.get(f"{base}/orders/pending")).json()
            elif action == "get":
                return (await client.get(f"{base}/order/{args['order_id']}")).json()
            elif action == "place_market":
                return (await client.post(f"{base}/order/market", json=args)).json()
            elif action == "place_limit":
                return (await client.post(f"{base}/order/limit", json=args)).json()
            elif action == "place_stop":
                return (await client.post(f"{base}/order/stop", json=args)).json()
            elif action == "place_mit":
                return (await client.post(f"{base}/order/mit", json=args)).json()
            elif action == "modify":
                order_id = args.pop("order_id")
                return (await client.patch(f"{base}/order/{order_id}", json=args)).json()
            elif action == "cancel":
                return (await client.delete(f"{base}/order/{args['order_id']}")).json()
            elif action == "tag":
                order_id = args["order_id"]
                ext: dict = {}
                if args.get("client_id"):      ext["id"]      = args["client_id"]
                if args.get("client_tag"):     ext["tag"]     = args["client_tag"]
                if args.get("client_comment"): ext["comment"] = args["client_comment"]
                body = {"clientExtensions": ext}
                return (await client.put(f"{base}/order/{order_id}/client-extensions", json=body)).json()

        # ── TRADE ────────────────────────────────────────────────────────────
        elif name == "trade":
            if action == "list":
                params = {"state": args.get("state", "OPEN"), "count": args.get("count", 50)}
                if args.get("instrument"): params["instrument"] = args["instrument"]
                if args.get("ids"):        params["ids"]      = args["ids"]       # CSV: "1,2,3"
                if args.get("before_id"):  params["beforeID"] = args["before_id"] # pagination
                return (await client.get(f"{base}/trades", params=params)).json()
            elif action == "list_open":
                return (await client.get(f"{base}/trades/open")).json()
            elif action == "get":
                return (await client.get(f"{base}/trade/{args['trade_id']}")).json()
            elif action == "close":
                trade_id = args["trade_id"]
                # OANDA PUT /trades/{id}/close expects units in JSON body, not query string
                units_val = args.get("units", "ALL")
                body = {"units": str(units_val)} if str(units_val).upper() != "ALL" else {}
                return (await client.put(f"{base}/trade/{trade_id}/close", json=body)).json()
            elif action == "modify":
                trade_id = args.pop("trade_id")
                return (await client.patch(f"{base}/trade/{trade_id}", json=args)).json()
            elif action == "set_orders":
                trade_id = args.pop("trade_id")
                # Build clean OANDA body — the four dependent-order fields (GSLO only for enabled accounts)
                body: dict = {}
                if "take_profit" in args:
                    val = args["take_profit"]
                    body["takeProfit"] = None if val is None else {"price": f"{float(val):.5f}", "timeInForce": "GTC"}
                if "stop_loss" in args:
                    val = args["stop_loss"]
                    body["stopLoss"] = None if val is None else {"price": f"{float(val):.5f}", "timeInForce": "GTC"}
                if "trailing_stop" in args:
                    val = args["trailing_stop"]
                    body["trailingStopLoss"] = None if val is None else {"distance": f"{float(val):.5f}", "timeInForce": "GTC"}
                if "guaranteed_stop" in args:
                    val = args["guaranteed_stop"]
                    body["guaranteedStopLoss"] = None if val is None else {"price": f"{float(val):.5f}", "timeInForce": "GTC"}
                return (await client.put(f"{base}/trade/{trade_id}/orders", json=body)).json()
            elif action == "tag":
                trade_id = args["trade_id"]
                ext: dict = {}
                if args.get("client_id"):      ext["id"]      = args["client_id"]
                if args.get("client_tag"):     ext["tag"]     = args["client_tag"]
                if args.get("client_comment"): ext["comment"] = args["client_comment"]
                body = {"clientExtensions": ext}
                return (await client.put(f"{base}/trade/{trade_id}/client-extensions", json=body)).json()

        # ── POSITION ─────────────────────────────────────────────────────────
        elif name == "position":
            if action == "list_all":
                return (await client.get(f"{base}/positions")).json()
            elif action == "list_open":
                return (await client.get(f"{base}/positions/open")).json()
            elif action == "get":
                return (await client.get(f"{base}/position/{args['instrument']}")).json()
            elif action == "close":
                instrument = args["instrument"]
                return (await client.post(f"{base}/position/close/{instrument}",
                    json={"side": args.get("side", "both")})).json()

        # ── TRANSACTION ──────────────────────────────────────────────────────
        elif name == "transaction":
            if action == "list":
                count = int(args.get("count") or 50)
                meta_params: dict = {}
                if args.get("from_time"): meta_params["from"] = args["from_time"]
                if args.get("to_time"):   meta_params["to"]   = args["to_time"]
                if args.get("type"):      meta_params["type"] = args["type"]
                meta = (await client.get(f"{base}/transactions", params=meta_params)).json()
                last_id = int(meta.get("lastTransactionID", 0))
                from_id = max(1, last_id - count + 1)
                if meta.get("pages"):
                    first_page = meta["pages"][0]
                    last_page  = meta["pages"][-1]
                    m_from = re.search(r"from=(\d+)", first_page)
                    m_to   = re.search(r"to=(\d+)",   last_page)
                    if m_from and m_to:
                        range_from = int(m_from.group(1))
                        range_to   = int(m_to.group(1))
                        from_id = max(range_from, range_to - count + 1)
                        last_id = range_to
                range_params = {"from_id": str(from_id), "to_id": str(last_id)}
                if args.get("type"): range_params["type"] = args["type"]
                return (await client.get(f"{base}/transactions/range", params=range_params)).json()
            elif action == "get":
                return (await client.get(f"{base}/transaction/{args['transaction_id']}")).json()
            elif action == "range":
                params = {"from_id": args["from_id"], "to_id": args["to_id"]}
                if args.get("type"): params["type"] = args["type"]
                return (await client.get(f"{base}/transactions/range", params=params)).json()
            elif action == "since":
                return (await client.get(f"{base}/transactions/since/{args['transaction_id']}")).json()

        return {"error": f"Unknown action: {name}.{action}"}



async def _handle_jsonrpc(message: dict, session_id: str) -> dict:
    """Processes a JSON-RPC message and returns the response."""
    method = message.get("method", "")
    msg_id = message.get("id")
    params = message.get("params", {})

    # initialize — initial handshake
    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "oanda-mcp-server", "version": "4.0.0"},
                "capabilities": {"tools": {"listChanged": False}}
            }
        }

    # initialized — notification, no response required
    elif method == "notifications/initialized":
        return None

    # tools/list — list of tools
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {"tools": MCP_TOOLS}
        }

    # tools/call — execute tool
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            result = await _execute_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                    "isError": False
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True
                }
            }

    # ping
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    # unknown method
    else:
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }


# ── MCP REST endpoints ─────────────────────────

@app.get("/mcp", tags=["MCP"])
async def mcp_info():
    """MCP server information."""
    return {
        "name": "oanda-mcp-server", "version": "4.0.0",
        "environment": OANDA_ENVIRONMENT,
        "tools": len(MCP_TOOLS),
        "endpoints": {"sse": "/sse", "messages": "/messages", "tools": "/mcp/tools", "call": "/mcp/call"}
    }


@app.get("/mcp/tools", tags=["MCP"])
async def mcp_list_tools():
    return {"tools": MCP_TOOLS}


class McpCallRequest(BaseModel):
    name:      str  = Field(...)
    arguments: dict = Field(default={})

@app.post("/mcp/call", tags=["MCP"])
async def mcp_call_tool(req: McpCallRequest):
    try:
        result = await _execute_tool(req.name, req.arguments)
        return {"tool": req.name, "result": result, "isError": False}
    except Exception as e:
        return {"tool": req.name, "result": {"error": str(e)}, "isError": True}


# ── SSE endpoint — GET /sse ────────────────────
# Claude Desktop connects here. Server sends
# an "endpoint" event with URL where Claude should
# post its JSON-RPC messages.

@app.get("/sse", tags=["MCP"])
async def mcp_sse(request: Request):
    """SSE endpoint for Claude Desktop (MCP protocol)."""
    session_id = str(uuid.uuid4())
    q: asyncio.Queue = asyncio.Queue()
    mcp_queues[session_id] = q
    logger.info(f"MCP SSE connected: session={session_id}")

    async def event_stream():
        try:
            # Mandatory event: tell Claude where to post messages
            yield f"event: endpoint\ndata: /messages?session_id={session_id}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat to keep connection alive
                    yield f": heartbeat\n\n"
        finally:
            mcp_queues.pop(session_id, None)
            logger.info(f"MCP SSE disconnected: session={session_id}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        }
    )


# ── Messages endpoint — POST /messages ────────
# Claude Desktop posts its JSON-RPC messages here.
# Server processes and sends response via SSE.

@app.post("/messages", tags=["MCP"])
async def mcp_messages(request: Request, session_id: str = None):
    """Receives JSON-RPC messages from Claude Desktop and responds via SSE."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    logger.info(f"MCP message session={session_id}: {body.get('method','?')}")

    response = await _handle_jsonrpc(body, session_id)

    # If active SSE session, send response via that channel
    if session_id and session_id in mcp_queues and response:
        await mcp_queues[session_id].put(response)
        return JSONResponse(status_code=202, content={"status": "accepted"})

    # No SSE session, respond directly (fallback mode)
    if response:
        return JSONResponse(content=response)
    return JSONResponse(status_code=202, content={"status": "ok"})


# ── Skip middleware for MCP endpoints ─────────
SKIP_LOG_PATHS.update({"/mcp", "/mcp/tools", "/sse", "/messages"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
