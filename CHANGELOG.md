# Changelog

All notable changes to the OANDA MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial GitHub repository setup
- CI/CD pipeline with Black, MyPy, and PyTest
- GitHub issue templates (bug, feature, question)
- Pull request template
- Branch protection rules

## [4.0.0] - 2026-11-03

### Added
- **Production-grade MCP Server** for OANDA v20 trading automation
- **7 MCP Tools** with 37 total actions:
  - `account` - Account information and configuration (5 actions)
  - `instrument` - Historical candles, orderbook, positionbook (4 actions)
  - `pricing` - Real-time pricing and latest candles (3 actions)
  - `order` - Complete order management (10 actions)
  - `trade` - Trade operations: open, close, modify (7 actions)
  - `position` - Position querying and closing (4 actions)
  - `transaction` - Transaction history (4 actions)
- **Complete REST API** with 50+ endpoints across 9 categories:
  - Health checks
  - Account management
  - Instrument data
  - Real-time pricing (with SSE streaming)
  - Order management
  - Trade management
  - Position management
  - Transaction history
  - Dashboard and database logging
- **Database Audit Logging** with asyncpg + PostgreSQL
- **Interactive Documentation**:
  - Swagger UI at `/docs`
  - ReDoc at `/redoc`
  - HTML Dashboard at `/dashboard`
- **Claude Desktop Integration** via MCP protocol (SSE + JSON-RPC)
- **Docker Support** with docker-compose for local development
- **Environment Configuration** with `.env.example` template
- **Error Handling** with comprehensive V20Error catching
- **Rate Limiting** support for API call throttling
- **Retry Logic** with exponential backoff
- **CORS Support** for cross-origin requests

### Features
- ✅ Market orders with SL/TP/trailing stops
- ✅ Limit orders with expiration
- ✅ Stop orders (breakout trades)
- ✅ Market-If-Touched orders
- ✅ Order modification and cancellation
- ✅ Trade close (full/partial)
- ✅ Trade SL/TP/trailing modifications
- ✅ Position closing (long/short/both)
- ✅ Real-time price streaming
- ✅ Historical candle data (OHLCV)
- ✅ Account configuration changes
- ✅ Client extensions for custom tagging
- ✅ Request/order/trade audit logging

### Security
- ✅ API key validation
- ✅ Environment variable protection
- ✅ `.gitignore` for sensitive files
- ✅ OANDA practice/live environment support
- ✅ No hardcoded credentials

### Documentation
- ✅ Comprehensive README
- ✅ MCP Tools Reference Guide
- ✅ OANDA REST v20 Manual
- ✅ Getting Started Guide
- ✅ REST API endpoint documentation
- ✅ Environment setup instructions

### Testing
- ✅ Docker Compose test environment
- ✅ PostgreSQL integration
- ✅ Server startup validation

## Migration Guide

### From v3.x to v4.0.0
- Server now requires Python 3.10+
- `DATABASE_URL` is optional (server runs without DB)
- MCP endpoint moved to `/sse` and `/messages`
- Swagger docs now at `/docs` instead of `/swagger`

### Environment Variables
Ensure these are set in your `.env`:
- `OANDA_API_KEY` (required)
- `OANDA_ACCOUNT_ID` (required)
- `OANDA_ENVIRONMENT` (required, default: practice)
- `DATABASE_URL` (optional)

## Release Schedule

- **v4.0.0** - Current stable release
- **v4.1.0** - Planned: Advanced order types, portfolio analytics
- **v5.0.0** - Planned: WebSocket streaming, multi-account support

## How to Contribute

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## Support

- Documentation: See README.md and MCP_TOOLS_REFERENCE.md
- Issues: https://github.com/BJLG-92/oanda-mcp-server/issues
- Discussions: https://github.com/BJLG-92/oanda-mcp-server/discussions

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
