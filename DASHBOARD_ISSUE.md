# Dashboard Data Issue - Analysis

## Problem

The dashboard at `http://localhost:8000/dashboard` shows incomplete data because it tries to load from **database-dependent endpoints** that require PostgreSQL:

### Endpoints that FAIL without Database ❌
```
/db/requests        - HTTP request log
/db/orders          - Order audit log
/db/trades          - Trade audit log
/db/errors          - Error log
/db/stats           - Database statistics
```

**Result:** These tabs show error messages instead of live data.

### Endpoints that WORK without Database ✅
```
/health             - Server health (JSON)
/account            - Account details (JSON)
/account/summary    - Account summary (JSON)
/trades/open        - Open trades (JSON, live from OANDA)
/orders             - Pending orders (JSON, live from OANDA)
/positions/open     - Open positions (JSON, live from OANDA)
/pricing            - Real-time prices (JSON, live from OANDA)
/metrics            - Performance stats (JSON, in-memory) ⭐
```

**Result:** These are all JSON endpoints that work without a database.

**Note on `/metrics`:**
- ✅ Returns performance statistics in JSON format
- ✅ No database required (keeps data in memory)
- ❌ NOT a visual page (it's raw JSON in browser)
- Use it for: Monitoring via scripts, DevOps tools, or curl

---

## Root Cause

The dashboard was designed with full audit logging in mind:

**Architecture:**
```
Dashboard
├── Live Data (from OANDA API) ✅
│   ├── Account
│   ├── Trades
│   ├── Orders
│   └── Positions
│
└── Audit Data (from PostgreSQL) ❌
    ├── Request Logs
    ├── Order Logs
    ├── Trade Logs
    └── Error Logs
```

**Issue:** When `DATABASE_URL` is empty (Quick Start mode), audit features fail silently.

---

## Why MCP Operations Don't Show in Logs

When you make MCP calls like:
```bash
curl http://localhost:8000/mcp/call -d '{"name":"account","arguments":{"action":"summary"}}'
```

**Without Database:**
- ✅ The operation executes correctly
- ✅ Returns data from OANDA
- ❌ NOT logged to database
- ❌ Dashboard audit tabs show "Database unavailable"

**With Database:**
- ✅ The operation executes correctly
- ✅ Returns data from OANDA
- ✅ Logged to PostgreSQL
- ✅ Dashboard audit tabs show the request

---

## Solutions

### Option 1: Use Dashboard Without Audit Logs (Current)
✅ Works fine for live trading data (Trades, Orders, Positions, Prices)
❌ No audit trail available (request logs, error logs)

**Access:**
- `http://localhost:8000/dashboard` 
- Focus on: Trades, Orders, Positions tabs
- Ignore: Requests, Orders Log, Trade Log tabs

### Option 2: Add PostgreSQL Database (Full Features)

**Method A: Docker Compose (Easiest)**
```bash
docker-compose up
```
This automatically:
- Starts PostgreSQL
- Starts the server with `DATABASE_URL` configured
- Enables all dashboard features

**Method B: Local PostgreSQL**
```bash
# 1. Install PostgreSQL locally

# 2. Create database
psql -U postgres -c "CREATE DATABASE oanda_mcp;"

# 3. Update .env
DATABASE_URL=postgresql://postgres:password@localhost:5432/oanda_mcp

# 4. Start server
python server.py
```

---

## Current Status

**Quick Start Mode (no database):**
- ✅ API works (all OANDA endpoints)
- ✅ MCP tools work (Claude Desktop)
- ✅ Dashboard works partially (live data only)
- ❌ Audit logs unavailable

**To Enable Full Dashboard Features:**
- Use `docker-compose up` instead
- Or setup local PostgreSQL and configure `DATABASE_URL`

---

## Recommendation

For the GETTING_STARTED guide, add a NOTE:

```markdown
### ⚠️ Dashboard Note

**Without Database:**
- Live data works: Trades, Orders, Positions, Prices ✅
- Audit logs unavailable: Request logs, error history ❌

**To enable full dashboard:**
Use Docker Compose instead:
```bash
docker-compose up
```
```

---

## Potential Improvement

**For future versions:** The dashboard could integrate `/metrics` visualization to show:
- Request count by endpoint
- Average latency per endpoint
- Error rates
- Performance trends

This would provide real-time performance monitoring **without requiring a database**, making it valuable for development and testing.

---

Generated: 2026-11-04
