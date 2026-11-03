# Getting Started with OANDA MCP Server

**Time estimate:** 15 minutes ⏱️

This guide walks you through setting up and using OANDA MCP Server step by step.

---

## Step 1: Prerequisites ✅

Check that you have installed:

```bash
# Docker + Docker Compose (recommended)
docker --version        # Should be 20+
docker-compose --version # Should be 2+

# OR Python 3.11+
python --version        # Should be 3.11+
```

**macOS:**
```bash
brew install docker
```

**Windows:**
Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)

**Linux:**
```bash
sudo apt-get install docker.io docker-compose-plugin
```

---

## Step 2: Get OANDA Credentials 🔑

### Option A: Create Free Demo Account (Recommended for Testing)

1. Visit [oanda.com](https://www.oanda.com)
2. Click **"Open Account"** → **"Practice Account"**
3. Complete registration (email, name, country)
4. You'll get instant access to a demo account with $50,000 play money

### Option B: Existing OANDA Account

Skip to Step 3.

### Get API Credentials

1. Log in to [OANDA MyAccounts](https://www.oanda.com/account/login)
2. Navigate to **"Account Settings"** → **"API Access"**
3. Click **"Enable API Access"** if not already enabled
4. Generate API Key:
   - Click **"Generate New API Key"**
   - Save the key somewhere safe (you won't see it again!)
5. Find your Account ID:
   - In MyAccounts, look for **"Account Number"** (format: `001-011-5838423-001`)

**Example:**
```
API Key:      1234567890abcdef1234567890abcdef-1234567890abcdef1234567890abcdef
Account ID:   001-011-5838423-001
Environment:  practice  (for demo account)
```

---

## Step 3: Clone Repository 📦

```bash
# Clone the repo
git clone https://github.com/yourusername/oanda-mcp.git
cd oanda-mcp

# Verify files exist
ls -la  # Should see: README.md, docker-compose.yml, server.py, .env.example
```

---

## Step 4: Configure Environment 🔧

### Create `.env` file

```bash
# Copy template
cp .env.example .env

# Edit .env with your credentials
# Use your favorite editor (nano, vim, VS Code, etc.)
```

### Fill in `.env`

```bash
# Paste your credentials here:
OANDA_API_KEY=1234567890abcdef1234567890abcdef-1234567890abcdef1234567890abcdef
OANDA_ACCOUNT_ID=001-011-5838423-001
OANDA_ENVIRONMENT=practice

# Leave DATABASE_URL as-is if using Docker Compose
DATABASE_URL=postgresql://oanda:oanda@db:5432/oanda_mcp
```

✅ **Never commit `.env` to Git!** It's already in `.gitignore`.

---

## Step 5: Start Server 🚀

### Option A: Docker Compose (Easiest)

```bash
# Start all services (server + database)
docker-compose up -d

# Verify services are running
docker ps
# Should show: oanda-db, oanda-mcp-server

# Check logs
docker-compose logs -f oanda-mcp-server
# Wait for: "Iniciando servidor en puerto 8000"
```

### Option B: Local Python

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python server.py

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 6: Verify Server is Running ✔️

### Test 1: Health Check

```bash
curl http://localhost:8000/health

# Should return:
# {
#   "status": "healthy",
#   "oanda_connection": "ok",
#   "environment": "practice",
#   "balance": "50000.00"
# }
```

### Test 2: Open Swagger Documentation

Visit: [http://localhost:8000/docs](http://localhost:8000/docs)

You should see:
- Blue "Execute" buttons next to each endpoint
- Account, Orders, Trades, Positions, etc. sections
- Try it out! Click **GET /account** → **"Try it out"** → **"Execute"**

### Test 3: Open Dashboard

Visit: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)

You should see:
- Account balance, margin, P&L
- Tabs for Trades, Orders, Recent Activity
- Charts and tables

---

## Step 7: Make Your First API Call 🎯

### Using cURL

```bash
# Get account summary
curl http://localhost:8000/account/summary

# Get current price
curl "http://localhost:8000/price/EUR_USD"

# List all open trades
curl http://localhost:8000/trades/open

# Get last 10 transactions
curl "http://localhost:8000/transactions?count=10"
```

### Using Python

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Get account
        resp = await client.get("http://localhost:8000/account/summary")
        account = resp.json()
        print(f"Balance: {account['account']['balance']}")
        
        # Get price
        resp = await client.get("http://localhost:8000/price/EUR_USD")
        price = resp.json()
        print(f"EUR/USD Bid: {price['prices'][0]['bids'][0]['price']}")

asyncio.run(main())
```

### Using JavaScript/Node.js

```javascript
// Fetch account
fetch('http://localhost:8000/account/summary')
  .then(r => r.json())
  .then(data => console.log('Balance:', data.account.balance))
  .catch(err => console.error(err));
```

---

## Step 8: Configure Claude Desktop (MCP) 🤖

### Edit Claude Desktop Config

**macOS/Linux:**
```bash
nano ~/.claude/config.json
```

**Windows:**
```
C:\Users\YourUsername\AppData\Roaming\.claude\config.json
```

### Paste Configuration

```json
{
  "mcpServers": {
    "oanda": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

### Restart Claude Desktop

Close and reopen Claude Desktop completely (don't just refresh).

### Verify MCP Connection

In Claude, you should see OANDA tools in the context menu:
- Look for a paperclip icon or "+" button
- Search for "account", "order", "trade", etc.
- Should show 7 tool categories

---

## Step 9: Try Your First Claude Trade 🤝

### In Claude Desktop

**You:**
> Get my current account balance and tell me the EUR/USD price

**Claude** will:
1. Call `account.summary` to get balance
2. Call `pricing.get_price` with EUR_USD
3. Return both pieces of information

**Example conversation:**

```
You: "I want to trade EUR/USD. What's the current price?"

Claude: *[Uses pricing tool]*
The current EUR/USD price is:
- Bid: 1.08950
- Ask: 1.08955

You: "Place a market order for 1000 units with SL at 1.0850 and TP at 1.0950"

Claude: *[Uses order.place_market tool]*
✅ Order placed successfully:
- OrderID: 15234
- Instrument: EUR_USD
- Units: 1000
- Entry: 1.08953 (ask price)
- Stop Loss: 1.08500
- Take Profit: 1.09500
```

---

## Step 10: Monitor Your Activity 📊

### Dashboard

Go to [http://localhost:8000/dashboard](http://localhost:8000/dashboard)

Shows:
- Account status (balance, margin, P&L)
- Recent trades & orders
- Error logs
- Request activity

### REST API Logs

```bash
# Get last 50 requests
curl http://localhost:8000/db/requests?limit=50

# Get only errors
curl "http://localhost:8000/db/requests?only_errors=true"

# Get recent orders
curl http://localhost:8000/db/orders?limit=20

# Get statistics
curl http://localhost:8000/db/stats
```

---

## Common First-Time Issues 🐛

### Issue: "Connection refused" when accessing localhost:8000

**Solution:**
```bash
# Check if server is running
curl http://localhost:8000/

# If not, start it
docker-compose up -d  # or python server.py locally
```

### Issue: 401 Unauthorized (Invalid API Key)

**Solution:**
1. Double-check your API key in `.env` (copy-paste carefully)
2. Verify in OANDA account: Is API access enabled?
3. Restart server: `docker-compose restart oanda-mcp-server`

### Issue: "database connection failed"

**Solution:**
```bash
# Ensure database is healthy
docker-compose up db -d

# Wait 10 seconds, then restart server
docker-compose up oanda-mcp-server -d
```

### Issue: Claude Desktop doesn't show OANDA tools

**Solution:**
1. Verify config.json syntax is valid (use JSON validator)
2. Restart Claude Desktop completely
3. Check server is running: `curl http://localhost:8000/health`
4. Try restarting server: `docker-compose restart`

---

## Next Steps 🎓

### 1. Learn the API

Read: `MCP_TOOLS_REFERENCE.md` for all 37 tool actions

### 2. Try Advanced Workflows

```
"Get all open EUR trades, calculate total P&L, 
and close any trades with P&L > 500"
```

### 3. Build a Strategy

```
"Get 200 4-hour candles of EUR_USD, 
calculate 20-period SMA, 
and if current price > SMA, place a buy order for 1000 units"
```

### 4. Integrate with Your App

Use the REST API in your Python/Node/Go application:
```python
import httpx

async with httpx.AsyncClient() as client:
    trades = await client.get("http://localhost:8000/trades/open")
```

### 5. Deploy to Production

See `DEPLOYMENT.md` for cloud deployment (Railway, Render, AWS)

---

## Additional Resources 📚

| Resource | Link |
|----------|------|
| Full Documentation | `README.md` |
| Tool Reference | `MCP_TOOLS_REFERENCE.md` |
| Architecture | `ARCHITECTURE.md` |
| Troubleshooting | `TROUBLESHOOTING.md` |
| API Swagger | http://localhost:8000/docs |
| Dashboard | http://localhost:8000/dashboard |

---

## Support & Help 💬

**Having issues?**

1. Check logs: `docker-compose logs -f`
2. Read troubleshooting guide: `TROUBLESHOOTING.md`
3. Open an issue: [GitHub Issues](https://github.com/yourusername/oanda-mcp/issues)
4. Ask community: [GitHub Discussions](https://github.com/yourusername/oanda-mcp/discussions)

---

## Congratulations! 🎉

You now have a production-grade OANDA trading server integrated with Claude AI.

**What to do next:**
- ✅ Explore the dashboard
- ✅ Try a few API calls
- ✅ Test in Claude with small orders
- ✅ Read the full documentation
- ✅ Build something awesome!

**Happy trading! 📈**

---

*Questions? Feedback? Star the repo! ⭐*

