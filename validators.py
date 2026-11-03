"""
Input validation functions for OANDA MCP Server.

Provides pre-flight validation for all user inputs before passing to OANDA API.
Raises ValueError with actionable error messages including valid values.
"""

from datetime import datetime
from typing import Optional, List


# Valid granularities for candlestick data
VALID_GRANULARITIES = {
    "S5", "S10", "S15", "S30",
    "M1", "M2", "M4", "M5", "M10", "M15", "M30",
    "H1", "H2", "H3", "H4", "H6", "H8", "H12",
    "D", "W", "M"
}

# Valid price components
VALID_PRICE_COMPONENTS = {"M", "B", "A", "BA", "MBA"}

# Common valid instrument currency codes (3-letter ISO codes)
VALID_CURRENCY_CODES = {
    "AUD", "CAD", "CHE", "CHF", "CNH", "CNY", "CZK", "DKK", "EUR",
    "GBP", "HKD", "HUF", "INR", "JPY", "MXN", "NOK", "NZD", "PLN",
    "RON", "RUB", "SEK", "SGD", "THB", "TRY", "USD", "ZAR", "XAG", "XAU"
}


def validate_rfc3339_datetime(datetime_str: str) -> None:
    """
    Validate RFC3339 datetime format.

    Args:
        datetime_str: Datetime string in RFC3339 format (e.g., "2024-12-31T23:59:59Z")

    Raises:
        ValueError: If datetime_str is not valid RFC3339 format
    """
    if not datetime_str:
        raise ValueError("Datetime string cannot be empty")

    try:
        # Check for required components: T separator and timezone indicator
        if 'T' not in datetime_str:
            raise ValueError("Missing 'T' separator between date and time")

        has_tz = datetime_str.endswith('Z') or '+' in datetime_str or datetime_str.count('-') > 2
        if not has_tz:
            raise ValueError("Missing timezone indicator (Z or +/-HH:MM)")

        # Try parsing RFC3339 format
        # Python's fromisoformat() handles most RFC3339 formats
        # Replace 'Z' with '+00:00' for compatibility
        normalized = datetime_str.replace('Z', '+00:00')
        datetime.fromisoformat(normalized)
    except ValueError as e:
        # Re-raise ValueError as-is if it already has our message
        if "RFC3339" in str(e) or "T" in str(e) or "timezone" in str(e):
            raise
        raise ValueError(
            f"Invalid RFC3339 datetime format: '{datetime_str}'. "
            f"Expected format: YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS+HH:MM"
        )


def validate_candle_params(
    granularity: str,
    count: int,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None
) -> None:
    """
    Validate candlestick parameters.

    Args:
        granularity: Timeframe (S5, S10, ..., M30, H1, ..., H12, D, W, M)
        count: Number of candles requested [1, 5000]
        from_time: Start time in RFC3339 format (optional)
        to_time: End time in RFC3339 format (optional)

    Raises:
        ValueError: If any parameter is invalid
    """
    # Validate granularity
    if not granularity:
        raise ValueError("granularity cannot be empty")
    if granularity not in VALID_GRANULARITIES:
        valid_list = ", ".join(sorted(VALID_GRANULARITIES))
        raise ValueError(
            f"Invalid granularity: '{granularity}'. "
            f"Valid values: {valid_list}"
        )

    # Validate count
    if not isinstance(count, int):
        raise ValueError(f"count must be an integer, got {type(count).__name__}")
    if count < 1 or count > 5000:
        raise ValueError(
            f"count must be between 1 and 5000, got {count}"
        )

    # Validate datetime format if provided
    if from_time:
        validate_rfc3339_datetime(from_time)

    if to_time:
        validate_rfc3339_datetime(to_time)

    # Validate from_time < to_time if both provided
    if from_time and to_time:
        try:
            from_dt = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
            to_dt = datetime.fromisoformat(to_time.replace('Z', '+00:00'))

            # Ensure both are timezone-aware or both are naive
            if from_dt.tzinfo is None and to_dt.tzinfo is not None:
                # Make to_dt naive
                to_dt = to_dt.replace(tzinfo=None)
            elif from_dt.tzinfo is not None and to_dt.tzinfo is None:
                # Make from_dt naive
                from_dt = from_dt.replace(tzinfo=None)

            if from_dt >= to_dt:
                raise ValueError(
                    f"from_time ({from_time}) must be before to_time ({to_time})"
                )
        except ValueError as e:
            if "before to_time" in str(e):
                raise
            raise ValueError(
                f"from_time ({from_time}) must be before to_time ({to_time})"
            )


def validate_instrument_name(instrument: str) -> None:
    """
    Validate instrument name format (BASE_QUOTE).

    Args:
        instrument: Instrument name (e.g., "EUR_USD", "BTC_USD")

    Raises:
        ValueError: If instrument format is invalid
    """
    if not instrument:
        raise ValueError("Instrument cannot be empty")

    if "_" not in instrument:
        raise ValueError(
            f"Invalid instrument format: '{instrument}'. "
            f"Expected format: BASE_QUOTE (e.g., EUR_USD)"
        )

    parts = instrument.split("_")

    if len(parts) != 2:
        raise ValueError(
            f"Invalid instrument format: '{instrument}'. "
            f"Expected exactly one underscore (e.g., EUR_USD)"
        )

    base, quote = parts

    # Check that both parts are 3 letters (allowing for commodities like XAU, XAG)
    if not (len(base) == 3 and base.isupper()):
        raise ValueError(
            f"Invalid base currency: '{base}'. "
            f"Expected 3-letter uppercase code (e.g., EUR, BTC)"
        )

    if not (len(quote) == 3 and quote.isupper()):
        raise ValueError(
            f"Invalid quote currency: '{quote}'. "
            f"Expected 3-letter uppercase code (e.g., USD, JPY)"
        )


def validate_order_params(
    instrument: str,
    units: int,
    price: Optional[float] = None
) -> None:
    """
    Validate order parameters.

    Args:
        instrument: Instrument name (e.g., "EUR_USD")
        units: Number of units (positive for buy, negative for sell)
        price: Price for limit/stop orders (optional)

    Raises:
        ValueError: If any parameter is invalid
    """
    # Validate instrument
    validate_instrument_name(instrument)

    # Validate units
    if not isinstance(units, int):
        raise ValueError(f"units must be an integer, got {type(units).__name__}")

    if units == 0:
        raise ValueError("units cannot be zero")

    if abs(units) > 10_000_000:
        raise ValueError(
            f"units out of range: {units}. Maximum allowed: 10,000,000"
        )

    # Validate price if provided
    if price is not None:
        validate_price_range(price, min_val=0)


def validate_trade_params(trade_id: str) -> None:
    """
    Validate trade ID format.

    Args:
        trade_id: Trade ID (numeric or @clientID pattern)

    Raises:
        ValueError: If trade_id is invalid
    """
    if not trade_id:
        raise ValueError("trade_id cannot be empty")

    if not isinstance(trade_id, str):
        raise ValueError(f"trade_id must be a string, got {type(trade_id).__name__}")

    # Allow numeric IDs or @clientID pattern
    if trade_id.startswith("@"):
        if len(trade_id) < 2:
            raise ValueError(
                f"Invalid trade_id: '{trade_id}'. "
                f"Client ID format should be @<id>"
            )
    else:
        # Numeric ID
        try:
            int(trade_id)
        except ValueError:
            raise ValueError(
                f"Invalid trade_id: '{trade_id}'. "
                f"Expected numeric ID or @clientID format"
            )


def validate_price_range(
    price: float,
    min_val: float = 0
) -> None:
    """
    Validate price value.

    Args:
        price: Price value
        min_val: Minimum allowed value (default: 0)

    Raises:
        ValueError: If price is invalid
    """
    if not isinstance(price, (int, float)):
        raise ValueError(
            f"price must be numeric, got {type(price).__name__}"
        )

    if price < min_val:
        raise ValueError(
            f"price must be >= {min_val}, got {price}"
        )

    if price > 999_999.99:
        raise ValueError(
            f"price out of range: {price}. Maximum: 999,999.99"
        )


def validate_price_component(price_component: str) -> None:
    """
    Validate price component (M, B, A, BA, MBA).

    Args:
        price_component: Price component code

    Raises:
        ValueError: If price_component is invalid
    """
    if not price_component:
        raise ValueError("price component cannot be empty")

    if price_component not in VALID_PRICE_COMPONENTS:
        valid_list = ", ".join(sorted(VALID_PRICE_COMPONENTS))
        raise ValueError(
            f"Invalid price component: '{price_component}'. "
            f"Valid values: {valid_list}"
        )


def validate_time_in_force(time_in_force: str) -> None:
    """
    Validate TimeInForce parameter.

    Args:
        time_in_force: TimeInForce value (FOK, IOC, GTC, GTD)

    Raises:
        ValueError: If time_in_force is invalid
    """
    valid_values = {"FOK", "IOC", "GTC", "GTD"}

    if not time_in_force:
        raise ValueError("timeInForce cannot be empty")

    if time_in_force not in valid_values:
        valid_list = ", ".join(sorted(valid_values))
        raise ValueError(
            f"Invalid timeInForce: '{time_in_force}'. "
            f"Valid values: {valid_list}"
        )
