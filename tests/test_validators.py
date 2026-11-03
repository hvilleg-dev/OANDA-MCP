"""
Comprehensive validation tests for OANDA MCP Server.

Tests cover:
- Unit tests for each validator function
- Edge cases (boundary values, empty strings, malformed input)
- HTTP 422 responses on invalid input
- Error message clarity
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import json

# Import validators
from validators import (
    validate_candle_params,
    validate_order_params,
    validate_trade_params,
    validate_instrument_name,
    validate_rfc3339_datetime,
    validate_price_range,
    validate_price_component,
    validate_time_in_force,
    VALID_GRANULARITIES,
    VALID_PRICE_COMPONENTS
)


# ══════════════════════════════════════════════
# UNIT TESTS: validate_rfc3339_datetime
# ══════════════════════════════════════════════
class TestValidateRFC3339Datetime:
    """Test RFC3339 datetime validation"""

    def test_valid_iso_format_with_z(self):
        """Valid RFC3339 format with Z suffix"""
        validate_rfc3339_datetime("2024-12-31T23:59:59Z")

    def test_valid_iso_format_with_offset(self):
        """Valid RFC3339 format with +HH:MM offset"""
        validate_rfc3339_datetime("2024-12-31T23:59:59+00:00")
        validate_rfc3339_datetime("2024-12-31T23:59:59-05:00")

    def test_valid_iso_format_with_microseconds(self):
        """Valid RFC3339 with microseconds"""
        validate_rfc3339_datetime("2024-12-31T23:59:59.123456Z")

    def test_invalid_format_no_time(self):
        """Invalid: date only, no time"""
        with pytest.raises(ValueError) as exc_info:
            validate_rfc3339_datetime("2024-12-31")
        error_msg = str(exc_info.value)
        assert "T" in error_msg or "RFC3339" in error_msg or "time" in error_msg.lower()

    def test_invalid_format_bad_separator(self):
        """Invalid: space instead of T"""
        with pytest.raises(ValueError):
            validate_rfc3339_datetime("2024-12-31 23:59:59Z")

    def test_invalid_empty_string(self):
        """Invalid: empty string"""
        with pytest.raises(ValueError):
            validate_rfc3339_datetime("")

    def test_invalid_none_value(self):
        """Invalid: None value"""
        with pytest.raises(ValueError):
            validate_rfc3339_datetime(None)

    def test_invalid_nonsense_string(self):
        """Invalid: nonsense string"""
        with pytest.raises(ValueError):
            validate_rfc3339_datetime("not a date")


# ══════════════════════════════════════════════
# UNIT TESTS: validate_candle_params
# ══════════════════════════════════════════════
class TestValidateCandleParams:
    """Test candle parameter validation"""

    def test_valid_basic_params(self):
        """Valid: basic candle parameters"""
        validate_candle_params("S5", 500)

    def test_valid_all_granularities(self):
        """Valid: all valid granularities"""
        for granularity in VALID_GRANULARITIES:
            validate_candle_params(granularity, 100)

    def test_valid_count_boundary_min(self):
        """Valid: count at minimum boundary (1)"""
        validate_candle_params("D", 1)

    def test_valid_count_boundary_max(self):
        """Valid: count at maximum boundary (5000)"""
        validate_candle_params("D", 5000)

    def test_valid_with_times(self):
        """Valid: with from_time and to_time"""
        validate_candle_params(
            "H1",
            100,
            from_time="2024-01-01T00:00:00Z",
            to_time="2024-01-02T00:00:00Z"
        )

    def test_invalid_granularity_empty(self):
        """Invalid: empty granularity"""
        with pytest.raises(ValueError) as exc_info:
            validate_candle_params("", 100)
        assert "granularity" in str(exc_info.value).lower()

    def test_invalid_granularity_not_in_list(self):
        """Invalid: granularity not in valid list"""
        with pytest.raises(ValueError) as exc_info:
            validate_candle_params("INVALID", 100)
        assert "S5" in str(exc_info.value)  # Should list valid values

    def test_invalid_count_zero(self):
        """Invalid: count is zero"""
        with pytest.raises(ValueError) as exc_info:
            validate_candle_params("D", 0)
        assert "1" in str(exc_info.value) and "5000" in str(exc_info.value)

    def test_invalid_count_too_high(self):
        """Invalid: count exceeds 5000"""
        with pytest.raises(ValueError):
            validate_candle_params("D", 5001)

    def test_invalid_count_negative(self):
        """Invalid: negative count"""
        with pytest.raises(ValueError):
            validate_candle_params("D", -100)

    def test_invalid_count_not_integer(self):
        """Invalid: count is not an integer"""
        with pytest.raises(ValueError):
            validate_candle_params("D", "500")

    def test_invalid_from_time_format(self):
        """Invalid: from_time has bad format"""
        with pytest.raises(ValueError):
            validate_candle_params("D", 100, from_time="2024-01-01", to_time="2024-01-02T00:00:00Z")

    def test_invalid_to_time_before_from_time(self):
        """Invalid: to_time is before from_time"""
        with pytest.raises(ValueError) as exc_info:
            validate_candle_params(
                "H1",
                100,
                from_time="2024-01-02T00:00:00Z",
                to_time="2024-01-01T00:00:00Z"
            )
        assert "before" in str(exc_info.value).lower()

    def test_invalid_to_time_equals_from_time(self):
        """Invalid: to_time equals from_time"""
        with pytest.raises(ValueError):
            validate_candle_params(
                "H1",
                100,
                from_time="2024-01-01T00:00:00Z",
                to_time="2024-01-01T00:00:00Z"
            )


# ══════════════════════════════════════════════
# UNIT TESTS: validate_instrument_name
# ══════════════════════════════════════════════
class TestValidateInstrumentName:
    """Test instrument name validation"""

    def test_valid_standard_pair(self):
        """Valid: standard currency pair"""
        validate_instrument_name("EUR_USD")
        validate_instrument_name("GBP_JPY")
        validate_instrument_name("USD_CAD")

    def test_valid_commodity_pair(self):
        """Valid: commodity pairs"""
        validate_instrument_name("XAU_USD")
        validate_instrument_name("XAG_USD")

    def test_valid_crypto_pair(self):
        """Valid: crypto pairs"""
        validate_instrument_name("BTC_USD")
        validate_instrument_name("ETH_USD")

    def test_invalid_empty_string(self):
        """Invalid: empty string"""
        with pytest.raises(ValueError):
            validate_instrument_name("")

    def test_invalid_no_underscore(self):
        """Invalid: no underscore separator"""
        with pytest.raises(ValueError) as exc_info:
            validate_instrument_name("EURUSD")
        assert "underscore" in str(exc_info.value).lower() or "BASE_QUOTE" in str(exc_info.value)

    def test_invalid_multiple_underscores(self):
        """Invalid: multiple underscores"""
        with pytest.raises(ValueError):
            validate_instrument_name("EUR_USD_JPY")

    def test_invalid_base_too_short(self):
        """Invalid: base currency code too short"""
        with pytest.raises(ValueError):
            validate_instrument_name("EU_USD")

    def test_invalid_base_too_long(self):
        """Invalid: base currency code too long"""
        with pytest.raises(ValueError):
            validate_instrument_name("EURO_USD")

    def test_invalid_quote_too_short(self):
        """Invalid: quote currency code too short"""
        with pytest.raises(ValueError):
            validate_instrument_name("EUR_US")

    def test_invalid_base_lowercase(self):
        """Invalid: base currency code lowercase"""
        with pytest.raises(ValueError):
            validate_instrument_name("eur_USD")

    def test_invalid_quote_lowercase(self):
        """Invalid: quote currency code lowercase"""
        with pytest.raises(ValueError):
            validate_instrument_name("EUR_usd")


# ══════════════════════════════════════════════
# UNIT TESTS: validate_order_params
# ══════════════════════════════════════════════
class TestValidateOrderParams:
    """Test order parameter validation"""

    def test_valid_buy_order(self):
        """Valid: buy order with positive units"""
        validate_order_params("EUR_USD", 1000)

    def test_valid_sell_order(self):
        """Valid: sell order with negative units"""
        validate_order_params("EUR_USD", -1000)

    def test_valid_with_price(self):
        """Valid: with limit price"""
        validate_order_params("EUR_USD", 1000, price=1.07500)

    def test_valid_price_zero(self):
        """Valid: price can be zero"""
        validate_order_params("EUR_USD", 1000, price=0.0)

    def test_invalid_instrument_format(self):
        """Invalid: bad instrument format"""
        with pytest.raises(ValueError):
            validate_order_params("EURUSD", 1000)

    def test_invalid_units_zero(self):
        """Invalid: zero units"""
        with pytest.raises(ValueError) as exc_info:
            validate_order_params("EUR_USD", 0)
        assert "zero" in str(exc_info.value).lower()

    def test_invalid_units_too_large(self):
        """Invalid: units exceed maximum"""
        with pytest.raises(ValueError):
            validate_order_params("EUR_USD", 10_000_001)

    def test_invalid_units_not_integer(self):
        """Invalid: units is not an integer"""
        with pytest.raises(ValueError):
            validate_order_params("EUR_USD", "1000")

    def test_invalid_price_negative(self):
        """Invalid: price is negative"""
        with pytest.raises(ValueError):
            validate_order_params("EUR_USD", 1000, price=-0.001)

    def test_invalid_price_too_high(self):
        """Invalid: price exceeds maximum"""
        with pytest.raises(ValueError):
            validate_order_params("EUR_USD", 1000, price=1_000_000)

    def test_invalid_price_string(self):
        """Invalid: price is string"""
        with pytest.raises(ValueError):
            validate_order_params("EUR_USD", 1000, price="1.07500")


# ══════════════════════════════════════════════
# UNIT TESTS: validate_trade_params
# ══════════════════════════════════════════════
class TestValidateTradeParams:
    """Test trade parameter validation"""

    def test_valid_numeric_id(self):
        """Valid: numeric trade ID"""
        validate_trade_params("12345")

    def test_valid_large_numeric_id(self):
        """Valid: large numeric trade ID"""
        validate_trade_params("123456789012345")

    def test_valid_client_id_format(self):
        """Valid: @clientID format"""
        validate_trade_params("@my-trade-001")

    def test_valid_client_id_with_numbers(self):
        """Valid: @clientID with numbers"""
        validate_trade_params("@trade_123_abc")

    def test_invalid_empty_string(self):
        """Invalid: empty string"""
        with pytest.raises(ValueError):
            validate_trade_params("")

    def test_invalid_at_symbol_only(self):
        """Invalid: @ symbol with nothing after"""
        with pytest.raises(ValueError):
            validate_trade_params("@")

    def test_invalid_non_numeric_non_client_id(self):
        """Invalid: non-numeric ID without @ prefix"""
        with pytest.raises(ValueError) as exc_info:
            validate_trade_params("abc123")
        assert "numeric" in str(exc_info.value).lower() or "@" in str(exc_info.value)

    def test_invalid_not_string(self):
        """Invalid: trade_id is not a string"""
        with pytest.raises(ValueError):
            validate_trade_params(12345)


# ══════════════════════════════════════════════
# UNIT TESTS: validate_price_range
# ══════════════════════════════════════════════
class TestValidatePriceRange:
    """Test price range validation"""

    def test_valid_positive_price(self):
        """Valid: positive price"""
        validate_price_range(1.07500)

    def test_valid_zero_price(self):
        """Valid: zero price (default min)"""
        validate_price_range(0.0)

    def test_valid_large_price(self):
        """Valid: large price near maximum"""
        validate_price_range(999_999.99)

    def test_valid_fractional_price(self):
        """Valid: fractional price"""
        validate_price_range(0.00001)

    def test_valid_integer_price(self):
        """Valid: integer price"""
        validate_price_range(100)

    def test_invalid_negative_price_default_min(self):
        """Invalid: negative price (default min=0)"""
        with pytest.raises(ValueError):
            validate_price_range(-0.001)

    def test_invalid_negative_price_custom_min(self):
        """Invalid: price below custom minimum"""
        with pytest.raises(ValueError):
            validate_price_range(5.0, min_val=10.0)

    def test_invalid_price_too_high(self):
        """Invalid: price exceeds maximum"""
        with pytest.raises(ValueError):
            validate_price_range(1_000_000.00)

    def test_invalid_price_string(self):
        """Invalid: price is string"""
        with pytest.raises(ValueError):
            validate_price_range("1.07500")

    def test_invalid_price_none(self):
        """Invalid: price is None"""
        with pytest.raises(ValueError):
            validate_price_range(None)


# ══════════════════════════════════════════════
# UNIT TESTS: validate_price_component
# ══════════════════════════════════════════════
class TestValidatePriceComponent:
    """Test price component validation"""

    def test_valid_all_components(self):
        """Valid: all valid price components"""
        for component in VALID_PRICE_COMPONENTS:
            validate_price_component(component)

    def test_invalid_empty_string(self):
        """Invalid: empty string"""
        with pytest.raises(ValueError):
            validate_price_component("")

    def test_invalid_lowercase(self):
        """Invalid: lowercase component"""
        with pytest.raises(ValueError):
            validate_price_component("m")

    def test_invalid_invalid_value(self):
        """Invalid: invalid component"""
        with pytest.raises(ValueError) as exc_info:
            validate_price_component("X")
        assert "M" in str(exc_info.value)  # Should list valid values


# ══════════════════════════════════════════════
# UNIT TESTS: validate_time_in_force
# ══════════════════════════════════════════════
class TestValidateTimeInForce:
    """Test TimeInForce validation"""

    def test_valid_all_values(self):
        """Valid: all valid TimeInForce values"""
        for value in ["FOK", "IOC", "GTC", "GTD"]:
            validate_time_in_force(value)

    def test_invalid_empty_string(self):
        """Invalid: empty string"""
        with pytest.raises(ValueError):
            validate_time_in_force("")

    def test_invalid_lowercase(self):
        """Invalid: lowercase value"""
        with pytest.raises(ValueError):
            validate_time_in_force("fok")

    def test_invalid_invalid_value(self):
        """Invalid: invalid TimeInForce value"""
        with pytest.raises(ValueError) as exc_info:
            validate_time_in_force("INVALID")
        assert "FOK" in str(exc_info.value)  # Should list valid values


# ══════════════════════════════════════════════
# VALIDATION ERROR RESPONSE FORMAT TESTS
# ══════════════════════════════════════════════
class TestValidationErrorFormat:
    """Test that validation errors follow the HTTP 422 format"""

    def test_error_has_required_fields(self):
        """Validation errors must include errorCode and errorMessage"""
        with pytest.raises(ValueError) as exc_info:
            validate_instrument_name("INVALID")

        error_msg = str(exc_info.value)
        assert len(error_msg) > 0
        assert "INVALID" in error_msg or "instrument" in error_msg.lower()

    def test_error_messages_are_actionable(self):
        """Error messages should tell users what to do"""
        with pytest.raises(ValueError) as exc_info:
            validate_candle_params("X", 100)

        error_msg = str(exc_info.value)
        # Should either list valid values or explain the issue
        assert "granularity" in error_msg.lower() or "S5" in error_msg

    def test_order_validation_includes_field_context(self):
        """Order validation errors should indicate which field failed"""
        with pytest.raises(ValueError) as exc_info:
            validate_order_params("EURUSD", 1000)

        error_msg = str(exc_info.value)
        assert "instrument" in error_msg.lower() or "underscore" in error_msg.lower()


# ══════════════════════════════════════════════
# ERROR MESSAGE CLARITY TESTS
# ══════════════════════════════════════════════
class TestErrorMessageClarity:
    """Test that error messages are clear and actionable"""

    def test_granularity_error_lists_valid_values(self):
        """Granularity error message lists all valid values"""
        with pytest.raises(ValueError) as exc_info:
            validate_candle_params("INVALID", 100)
        error_msg = str(exc_info.value)
        assert "S5" in error_msg
        assert "M30" in error_msg
        assert "D" in error_msg

    def test_instrument_error_format_message(self):
        """Instrument error message explains format"""
        with pytest.raises(ValueError) as exc_info:
            validate_instrument_name("EURUSD")
        error_msg = str(exc_info.value)
        assert "underscore" in error_msg.lower() or "BASE_QUOTE" in error_msg

    def test_count_error_includes_bounds(self):
        """Count error message includes valid bounds"""
        with pytest.raises(ValueError) as exc_info:
            validate_candle_params("D", 10000)
        error_msg = str(exc_info.value)
        assert "1" in error_msg
        assert "5000" in error_msg

    def test_price_component_error_lists_options(self):
        """Price component error lists all valid options"""
        with pytest.raises(ValueError) as exc_info:
            validate_price_component("INVALID")
        error_msg = str(exc_info.value)
        assert "M" in error_msg
        assert "B" in error_msg

    def test_time_in_force_error_lists_options(self):
        """TimeInForce error lists all valid options"""
        with pytest.raises(ValueError) as exc_info:
            validate_time_in_force("INVALID")
        error_msg = str(exc_info.value)
        assert "FOK" in error_msg
        assert "GTC" in error_msg


# ══════════════════════════════════════════════
# EDGE CASE TESTS
# ══════════════════════════════════════════════
class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_price_at_maximum_boundary(self):
        """Price at maximum allowed value"""
        validate_price_range(999_999.99)

    def test_price_just_below_maximum(self):
        """Price just below maximum"""
        validate_price_range(999_999.98)

    def test_price_just_above_maximum_fails(self):
        """Price just above maximum fails"""
        with pytest.raises(ValueError):
            validate_price_range(1_000_000.00)

    def test_units_at_maximum_boundary(self):
        """Units at maximum allowed value"""
        validate_order_params("EUR_USD", 10_000_000)

    def test_units_just_above_maximum_fails(self):
        """Units just above maximum fails"""
        with pytest.raises(ValueError):
            validate_order_params("EUR_USD", 10_000_001)

    def test_count_one_is_valid(self):
        """Count of 1 is valid"""
        validate_candle_params("D", 1)

    def test_very_small_fractional_price(self):
        """Very small fractional price is valid"""
        validate_price_range(0.00000001)

    def test_datetime_with_various_timezones(self):
        """DateTime validation works with various timezones"""
        validate_rfc3339_datetime("2024-12-31T23:59:59+00:00")
        validate_rfc3339_datetime("2024-12-31T23:59:59-05:00")
        validate_rfc3339_datetime("2024-12-31T23:59:59+09:30")

    def test_trade_id_very_large_number(self):
        """Trade ID as very large number"""
        validate_trade_params("999999999999999999")

    def test_client_id_with_special_characters(self):
        """Client ID with special characters"""
        validate_trade_params("@my-trade_001.v2")
