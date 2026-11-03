# OANDA MCP Server 🚀

**Production-grade Model Context Protocol (MCP) server for OANDA v20 trading automation with Claude AI.**

![Version](https://img.shields.io/badge/version-4.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-GNU%203.0-blue)
![Status](https://img.shields.io/badge/status-production-brightgreen)

---

## 🎯 What is OANDA MCP Server?

A **Model Context Protocol (MCP) server** that exposes the complete OANDA v20 trading API as intelligent tools for **Claude AI**. 

### Problem Solved

- ✅ **Automation Gap**: Control OANDA trading directly from Claude (no UI clicking)
- ✅ **MCP Integration**: Native support for Claude Desktop & Claude API
- ✅ **REST API**: Traditional HTTP access + comprehensive logging
- ✅ **Production Ready**: Async, typed, tested, documented

### Use Cases

| Use Case | Example |
|----------|---------|
| **Algorithmic Trading** | "Execute SMA crossover strategy on EUR_USD with 1000 units, SL 50 pips" |
| **Portfolio Monitoring** | "Show all open trades, calculate weighted P&L, alert if drawdown > 5%" |
| **Order Management** | "Place limit order EUR_USD at 1.0850, TP 1.0950, SL 1.0750" |
| **Data Analysis** | "Get 1000 candles EUR_USD H1, calculate RSI and Bollinger Bands" |
| **Risk Management** | "Close all short positions immediately, check margin status" |

---

## 🌟 Key Features

### 7 MCP Tools — 37 Total Actions

| Tool | Actions | Purpose |
|------|---------|---------|
| **account** | 5 | Account info, instruments, changes, configuration |
| **instrument** | 4 | Historical candles, orderbook, positionbook |
| **pricing** | 3 | Real-time bid/ask, latest candles |
| **order** | 10 | Place (market/limit/stop/MIT), modify, cancel, tag |
| **trade** | 7 | Open, close (partial), modify SL/TP, tag |
| **position** | 4 | List all/open, get details, close |
| **transaction** | 4 | Historical transactions, filters, ranges |

### Infrastructure

- 🚀 **FastAPI** — async, auto-docs (Swagger/ReDoc)
- 🐘 **PostgreSQL** — comprehensive audit logging
- 🐳 **Docker Compose** — reproducible deployment
- 📊 **Dashboard** — visual monitoring of trades & errors
- 🔐 **Secure** — env vars, API key isolation, error masking

### Integration

- ✅ **Claude Desktop** — native MCP support
- ✅ **Claude API** — programmatic access
- ✅ **REST HTTP** — 30+ endpoints (Swagger documented)
- ✅ **WebSocket** — real-time pricing streams (SSE)

---

## ⚡ Quick Start

### 1. Prerequisites

- **Docker & Docker Compose** (recommended) OR **Python 3.11+**
- **OANDA Account** (free demo account at [oanda.com](https://www.oanda.com))
- **OANDA API Key** + **Account ID** (from [My Accounts](https://www.oanda.com/account/login))
- **Claude Desktop** (optional, for MCP integration)

### 2. Installation

#### Option A: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/oanda-mcp.git
cd oanda-mcp

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# OANDA_API_KEY=your_api_key_here
# OANDA_ACCOUNT_ID=your_account_id_here
# OANDA_ENVIRONMENT=practice  # or 'live'

# Start services
docker-compose up -d

# Verify health
curl http://localhost:8000/health
```

#### Option B: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OANDA_API_KEY=your_key
export OANDA_ACCOUNT_ID=your_account
export OANDA_ENVIRONMENT=practice

# Run server
python server.py
# Server runs at http://localhost:8000
```

### 3. Configure Claude Desktop

Edit `~/.claude/config.json`:

```json
{
  "mcpServers": {
    "oanda": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

Restart Claude Desktop. OANDA tools should appear in the context menu.

---

## 📖 Usage Examples

### REST API (HTTP)

#### Get Account Summary
```bash
curl -X GET http://localhost:8000/account/summary
```

```json
{
  "account": {
    "balance": "50000.00",
    "unrealizedPL": "125.50",
    "NAV": "50125.50",
    "marginUsed": "2000",
    "marginAvailable": "48125.50"
  }
}
```

#### Place Market Order
```bash
curl -X POST http://localhost:8000/order/market \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "EUR_USD",
    "units": 1000,
    "stop_loss": 1.07000,
    "take_profit": 1.10000
  }'
```

#### Get Historical Candles
```bash
curl "http://localhost:8000/instruments/EUR_USD/candles?granularity=H1&count=100&price=MBA"
```

### Claude Desktop (MCP)

**In Claude:**

> **You:** "I want to trade EUR_USD. Get current price, then place a market order for 1000 units with SL at 1.0700 and TP at 1.1000."

Claude will:
1. Call `pricing.get_price(instrument="EUR_USD")`
2. Call `order.place_market(instrument="EUR_USD", units=1000, stop_loss=1.0700, take_profit=1.1000)`
3. Return filled order details

**Advantages over manual:**
- Natural language → API translation
- Multi-step workflows in single message
- Context memory (prices reference trading decision)
- Error handling + retries built-in

### Python Client

```python
import httpx
import json

async def trade():
    async with httpx.AsyncClient() as client:
        # Get open trades
        resp = await client.get("http://localhost:8000/trades/open")
        open_trades = resp.json()["trades"]
        
        # Close first trade
        if open_trades:
            trade_id = open_trades[0]["id"]
            await client.put(
                f"http://localhost:8000/trade/{trade_id}/close",
                json={}
            )

# Run
import asyncio
asyncio.run(trade())
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         Claude Desktop / API            │
└────────────────────┬────────────────────┘
                     │
                   MCP Protocol (JSON-RPC over SSE)
                     │
┌────────────────────▼────────────────────┐
│    OANDA MCP Server (FastAPI)           │
│  ├─ MCP Tools (7 categories)            │
│  ├─ REST API (30+ endpoints)            │
│  ├─ Rate Limiting & Retry Logic         │
│  └─ Request/Response Pipeline           │
└────────────────────┬────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────────┐     ┌──────────────────┐
│  OANDA v20 API   │     │  PostgreSQL DB   │
│ (practice/live)  │     │  (Audit Logging) │
└──────────────────┘     └──────────────────┘
```

### Components

| Component | Role | Technology |
|-----------|------|-----------|
| **MCP Handler** | Protocol translation | JSON-RPC, SSE streaming |
| **REST Router** | HTTP endpoints | FastAPI endpoints |
| **OANDA Client** | API wrapper | oandapyV20 |
| **Rate Limiter** | Quota enforcement | Token bucket (configurable) |
| **Database** | Audit logging | asyncpg, PostgreSQL |
| **Dashboard** | Monitoring UI | HTML5, vanilla JS |

---

## 📊 Endpoints Reference

### Health & Info
```
GET  /                    → Server health
GET  /health              → Detailed status
GET  /docs                → Swagger UI
GET  /redoc               → ReDoc
GET  /dashboard           → Visual dashboard
```

### Account Management
```
GET  /account             → Full account details
GET  /account/summary     → Compact summary
GET  /account/instruments → Available instruments
GET  /account/changes     → Changes since TransactionID
PATCH /account/configuration → Modify alias/margin
```

### Trading
```
# Orders
GET  /orders              → List orders
POST /order/market        → Market order
POST /order/limit         → Limit order
POST /order/stop          → Stop order
POST /order/mit           → Market-If-Touched
PATCH /order/{id}         → Modify order
DELETE /order/{id}        → Cancel order

# Trades
GET  /trades              → List trades
GET  /trades/open         → Open trades only
PUT  /trade/{id}/close    → Close trade
PATCH /trade/{id}         → Modify SL/TP
PUT  /trade/{id}/orders   → Set SL/TP/Trailing

# Positions
GET  /positions           → All positions
GET  /positions/open      → Open positions
POST /position/close/{inst} → Close position
```

### Data & Analysis
```
GET  /instruments/{inst}/candles    → OHLCV bars
GET  /instruments/{inst}/orderbook  → Order distribution
GET  /pricing/stream                → Real-time prices (SSE)
GET  /transactions                  → Transaction history
```

Full reference: `MCP_TOOLS_REFERENCE.md`

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OANDA_API_KEY` | ✅ | — | API key from OANDA account |
| `OANDA_ACCOUNT_ID` | ✅ | — | Account ID (format: `001-011-xxxxx-001`) |
| `OANDA_ENVIRONMENT` | ✅ | `practice` | `practice` (demo) or `live` (real money) ⚠️ |
| `DATABASE_URL` | ❌ | `postgres://oanda:oanda@db:5432/oanda_mcp` | PostgreSQL connection |
| `PORT` | ❌ | `8000` | Server port |
| `LOG_LEVEL` | ❌ | `INFO` | Python logging level |

### Example `.env`

```bash
# OANDA Credentials
OANDA_API_KEY=1234567890abcdef1234567890abcdef-1234567890abcdef1234567890abcdef
OANDA_ACCOUNT_ID=001-011-5838423-001
OANDA_ENVIRONMENT=practice

# Database
DATABASE_URL=postgresql://oanda:oanda@localhost:5432/oanda_mcp

# Server
PORT=8000
LOG_LEVEL=INFO
```

---

## 🚨 Security & Best Practices

### ⚠️ WARNING: Live Trading

This server can execute **REAL TRADES** with real money if `OANDA_ENVIRONMENT=live`.

**Never:**
- Commit `.env` files to Git
- Share API keys publicly
- Run live trading without rate limits
- Use live account on unsecured networks

**Always:**
- Start with `practice` environment
- Use strong API key permissions in OANDA account settings
- Monitor `/dashboard` and logs
- Test strategies with small positions first
- Keep secrets in environment variables, not code

### Rate Limiting

OANDA limits: ~200 req/s per account, some endpoints ~10 req/s.

Server includes automatic retry logic with exponential backoff. Monitor logs for rate limit errors.

### Database

PostgreSQL password should be strong and database should not be publicly accessible.

```bash
# Don't do this in production
POSTGRES_PASSWORD=oanda  # ❌ Weak!

# Do this
POSTGRES_PASSWORD=$(openssl rand -base64 32)
```

---

## 📈 Monitoring & Troubleshooting

### Dashboard

Open http://localhost:8000/dashboard

Shows:
- Account balance, P&L, margin
- Recent trades & orders
- Request logs (success/errors)
- Order statistics
- Real-time pricing (if streaming active)

### Logs

#### Application Logs
```bash
docker logs oanda-mcp-server
```

#### Database Logs
```bash
docker logs oanda-db
```

#### Request Logs (via API)
```bash
curl http://localhost:8000/db/requests?limit=50
```

### Common Issues

#### 401 Unauthorized
**Cause:** Invalid API key or account ID  
**Fix:**
1. Verify credentials in `.env`
2. Check OANDA account permissions
3. Restart server: `docker-compose restart`

#### 429 Too Many Requests
**Cause:** Rate limit exceeded  
**Fix:**
1. Wait 60 seconds before retry
2. Reduce request frequency
3. Check rate limiter configuration

#### Database Connection Failed
**Cause:** PostgreSQL not running  
**Fix:**
```bash
docker-compose up db -d
# Wait for healthcheck to pass
docker-compose up -d
```

#### MCP Tools Not Appearing in Claude
**Cause:** Claude Desktop not configured  
**Fix:**
1. Verify ~/.claude/config.json exists
2. Restart Claude Desktop
3. Check server is running: `curl http://localhost:8000/health`

---

## 🧪 Testing

### Run Tests
```bash
pytest tests/ -v
```

### Test Coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

### Manual Testing (cURL)
```bash
# Health check
curl http://localhost:8000/health

# Get account
curl http://localhost:8000/account

# Place order (test)
curl -X POST http://localhost:8000/order/market \
  -H "Content-Type: application/json" \
  -d '{"instrument":"EUR_USD","units":100}'
```

---

## 🚀 Deployment

### Docker (Local)
```bash
docker-compose up -d
```

### Cloud Platforms

#### Render
```bash
git push heroku main
# Auto-deploys with Dockerfile
```

#### Railway
```bash
railway init
railway up
```

#### AWS ECS
```bash
aws ecs create-service --cluster trading --task-definition oanda-mcp
```

---

## 🛠️ Development

### Setup Dev Environment
```bash
git clone https://github.com/yourusername/oanda-mcp.git
cd oanda-mcp
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # pytest, black, mypy
```

### Code Style
```bash
black src/
mypy src/ --strict
pytest tests/
```

### Contributing
See `CONTRIBUTING.md`

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `README.md` (this file) | Quick start & overview |
| `GETTING_STARTED.md` | Detailed tutorial |
| `ARCHITECTURE.md` | Technical design |
| `MCP_TOOLS_REFERENCE.md` | Tool schemas & parameters |
| `API_REFERENCE.md` | REST endpoints |
| `CHANGELOG.md` | Version history |

---

## 📝 Changelog

### v4.0.0 (2026-11-03)
- Complete MCP implementation (7 tools, 37 actions)
- PostgreSQL audit logging
- Dashboard UI
- Rate limiting & retry logic
- Full documentation

### v3.0.0 (2026-10-15)
- Initial REST API
- FastAPI setup
- Docker support

---

## 📄 License

GNU General Public License v3.0 — See `LICENSE` file.

This project is **open source** and free for personal & commercial use with attribution.

---

## 💬 Community

- 💬 **Discussions:** GitHub Discussions
- 🐛 **Issues:** Report bugs on GitHub Issues
- 🙋 **Questions:** Ask in Discussions or r/algotrading

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -am 'Add feature'`)
4. Push to branch (`git push origin feature/my-feature`)
5. Open Pull Request

See `CONTRIBUTING.md` for guidelines.

---

## 👨‍💻 Author

**[Your Name]**

- 🔗 GitHub: [@yourusername](https://github.com/yourusername)
- 💼 LinkedIn: [Your Profile](https://linkedin.com/in/yourprofile)
- 🌐 Website: [yourwebsite.com](https://yourwebsite.com)

---

## 🙏 Acknowledgments

- OANDA for the v20 API & documentation
- Anthropic for Model Context Protocol
- Community feedback & contributions

---

## ⭐ Support

If this project helped you, please **star** ⭐ the repo and share with fellow traders!

---

**Questions? Open an issue or discussion!**

[← Go to Issues](https://github.com/yourusername/oanda-mcp/issues)  
[← Go to Discussions](https://github.com/yourusername/oanda-mcp/discussions)

