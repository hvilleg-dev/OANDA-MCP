# OANDA MCP Server — Análisis Estratégico y Recomendaciones

**Fecha:** 2026-11-03  
**Versión:** 4.0.0  
**Estado:** Producción-listo con mejoras recomendadas

---

## 📊 ANÁLISIS TÉCNICO ACTUAL

### ✅ Fortalezas Identificadas

#### 1. **Cobertura API Completa (37 acciones en 7 herramientas MCP)**
- `account` (5): get, summary, instruments, changes, configure ✅
- `instrument` (4): candles, candles_account, orderbook, positionbook ✅
- `pricing` (3): get_price, get_prices, latest_candles ✅
- `order` (10): list, pending, get, place_market, place_limit, place_stop, place_mit, modify, cancel, tag ✅
- `trade` (7): list, list_open, get, close, modify, set_orders, tag ✅
- `position` (4): list_all, list_open, get, close ✅
- `transaction` (4): list, get, range, since ✅

**Evaluación:** Cubre 95% de casos de uso trading. Falta: streaming SSE avanzado, rate limit handling, reconnection logic.

#### 2. **Stack Moderno y Production-Ready**
- **FastAPI** — async framework ligero, documentación auto (Swagger/ReDoc)
- **asyncpg** — pool de conexiones PostgreSQL eficiente (2-10 conns)
- **oandapyV20** — cliente oficial OANDA (mantenido)
- **Docker Compose** — desarrollo local + despliegue reproducible

#### 3. **Seguridad y Observabilidad**
- Variables de entorno (OANDA_API_KEY, OANDA_ACCOUNT_ID, DATABASE_URL)
- Logging contextualizado (método, path, status, duración)
- Dashboard HTML visual (requests, órdenes, trades, errores)
- Auditoría completa en PostgreSQL (request_log, order_log, trade_log, error_log)

#### 4. **Error Handling Robusto**
- Parser de errores V20Error con rejectReason extraction
- Logging de errores en DB con contexto
- HTTP status codes coherentes (400, 422, 503)
- Fallback graceful sin DB

#### 5. **Documentación y Claridad**
- `MCP_TOOLS_REFERENCE.md` — completa (campos, enums, ejemplos)
- README con endpoints, variables de entorno, configuración Claude Desktop
- Historial de bugs corregidos (12 issues auditorios documentados)
- Esquemas Pydantic validados

---

### ⚠️ Brechas Técnicas Identificadas

#### 1. **Escalabilidad Limitada**
- **Problema:** Un servidor, PostgreSQL single-node, sin caching
- **Impacto:** Cuellos de botella a 1000+ req/s
- **Recomendación:** Redis cache layer, horizontal scaling, load balancing

#### 2. **Rate Limiting Ausente**
- **Problema:** OANDA tiene límites: ~200 req/s cuenta, algunos endpoints ~10 req/s
- **Impacto:** Rechazo silencioso, solicitudes perdidas
- **Recomendación:** Token bucket rate limiter + retry logic con backoff exponencial

#### 3. **Reconnection Logic Débil**
- **Problema:** Stream SSE termina abruptamente, sin reconexión automática
- **Impacto:** Data loss en time series, alert miss
- **Recomendación:** Circuit breaker, exponential backoff, heartbeat pings

#### 4. **Fault Tolerance en MCP**
- **Problema:** Si session_id se pierde, cliente pierde conexión
- **Impacto:** Usuario debe reconectar
- **Recomendación:** Session persistence, reconnection tokens

#### 5. **Validación de Input Parcial**
- **Problema:** Algunos endpoints no validan ranges (count > 5000, prices negativas)
- **Impacto:** OANDA rechaza, error 400 genérico
- **Recomendación:** Pre-validation con mensajes claros

#### 6. **Historicidad de Datos**
- **Problema:** No hay snapshot/export de históricos
- **Impacto:** Análisis ex-post complicado
- **Recomendación:** Endpoint `/db/export` (CSV/JSON)

---

### 🔍 Análisis de Mercado (Pendiente del Agente)

*En espera de investigación sobre:*
- Demanda comunitaria (Reddit, Discord)
- Competencia existente
- Pain points retail traders
- Viabilidad como portafolio/producto

---

## 🚀 MEJORAS RECOMENDADAS (Prioridad)

### Tier 1 — Críticas (1-2 días)

#### 1.1 Rate Limiting
```python
# Pseudocódigo
from slowapi import Limiter
limiter = Limiter(key_func=lambda: session_id)

@app.get("/orders")
@limiter.limit("100/minute")
async def get_orders(): ...
```
**Impacto:** Previene account ban, protege infraestructura.

#### 1.2 Input Validation Pre-Request
```python
def validate_candle_params(granularity, count, from_time, to_time):
    if count > 5000:
        raise ValueError("count max 5000")
    if granularity not in VALID_GRANULARITIES:
        raise ValueError(f"granularity debe ser uno de: {VALID_GRANULARITIES}")
```
**Impacto:** UX mejor, debugging más rápido.

#### 1.3 Reconnection Circuit Breaker
```python
class OANDAClient:
    def __init__(self):
        self.retries = 0
        self.max_retries = 5
        self.backoff = 1
    
    async def request_with_retry(self, endpoint):
        while self.retries < self.max_retries:
            try:
                return await self.request(endpoint)
            except V20Error as e:
                if "RATE_LIMIT" in str(e):
                    self.backoff = min(self.backoff * 2, 60)
                    await asyncio.sleep(self.backoff)
                    self.retries += 1
                else:
                    raise
```
**Impacto:** Resilencia ante picos de tráfico, client stability.

---

### Tier 2 — Features (3-5 días)

#### 2.1 Webhook Notifications
```python
# POST /webhooks/register
# Cliente se suscribe a eventos: ORDER_FILLED, TRADE_OPENED, MARGIN_CALL
# Servidor pushea en tiempo real
```
**Impacto:** Eliminación de polling, arquitectura event-driven.

#### 2.2 Historical Data Export
```python
# GET /db/export?format=csv&limit=10000&order_type=FILLED
# Retorna CSV/JSON de auditoría
```
**Impacto:** Análisis ex-post, compliance reporting.

#### 2.3 Advanced Filtering
```python
# GET /trades?filter={"instrument":"EUR_USD","minPL":100,"maxPL":500}
# Búsqueda semántica en DB
```
**Impacto:** Queries complejas sin client-side filtering.

#### 2.4 MCP Tool Grouping Refinement
```python
# Separar "market_data" (pricing/instrument) de "order_management"
# Mejorar UX en Claude Desktop con herramientas más granulares
```

---

### Tier 3 — Polish (1 semana)

#### 3.1 Analytics Dashboard Avanzado
- Heatmap de P&L por instrumento
- Win rate, Sharpe ratio calculados
- Correlation matrix entre pares
- Drawdown analysis

#### 3.2 Simulated Trading
```python
# GET /backtest?symbol=EUR_USD&start=2024-01-01&end=2024-12-31&strategy=sma_crossover
# Retorna P&L histórico sin ejecución real
```

#### 3.3 CLI Tool
```bash
$ oanda-mcp account summary
$ oanda-mcp order place-market EUR_USD 1000 --tp 1.10 --sl 1.07
$ oanda-mcp trades list --state OPEN --sort profitability
```

---

## 📦 Estructura de Proyecto para GitHub

```
oanda-mcp/
├── README.md                          ← Guía rápida, instalación
├── GETTING_STARTED.md                 ← Tutorial completo
├── ARCHITECTURE.md                    ← Diseño, componentes
├── CHANGELOG.md                       ← Historial versiones
├── LICENSE (GNU 3.0)                  ← Legal
├── src/
│   ├── server.py                      ← FastAPI main
│   ├── mcp_tools.py                   ← Herramientas MCP (refactorizado)
│   ├── oanda_client.py                ← Wrapper client con retry logic
│   ├── rate_limiter.py                ← Rate limiter
│   └── database.py                    ← Schema + helpers
├── config/
│   ├── docker-compose.yml
│   └── .env.example
├── docs/
│   ├── MCP_TOOLS_REFERENCE.md         ← Actual
│   ├── OANDA_REST_V20_Agent_Manual.md ← Actual
│   └── EXAMPLES.md                    ← New: Casos de uso
├── tests/
│   ├── test_server.py
│   ├── test_mcp_tools.py
│   └── fixtures/
├── dashboard.html                     ← Actual
├── requirements.txt
└── Dockerfile
```

---

## 📋 README Estructura Propuesta

### Secciones Clave

1. **Intro (1 párrafo)**
   - ¿Qué es? MCP server para OANDA trading automation via Claude
   - Para quién: Traders cuantitativos, developers, bots AI

2. **Features Principales**
   - 7 herramientas MCP (37 acciones)
   - Logging PostgreSQL
   - Dashboard visual
   - Compatible Claude Desktop
   - Docker ready

3. **Quick Start (5 min)**
   ```bash
   git clone ...
   cp .env.example .env
   # llenar OANDA_API_KEY, ACCOUNT_ID
   docker-compose up
   # Abrir http://localhost:8000/docs
   ```

4. **Installation**
   - Opción 1: Docker (recomendado)
   - Opción 2: Local Python 3.11+
   - Opción 3: Cloud deployment (Railway, Render)

5. **Configuration**
   - Variables de entorno (tabla)
   - Claude Desktop setup
   - Database (opcional vs no-DB mode)

6. **Usage**
   - REST API examples (curl)
   - MCP examples (en Claude Desktop)
   - Python client examples

7. **Architecture**
   - Diagrama: Client → MCP → FastAPI → OANDA
   - Database schema visual
   - Error handling flow

8. **Troubleshooting**
   - Common errors (401, rate limits, DB connection)
   - Logs location
   - Debug mode

9. **Contributing**
   - Setup dev environment
   - Code style (Black, mypy)
   - Testing

10. **License & Attribution**
    - GNU 3.0 full text
    - Credits

---

## 🎯 Viabilidad como Portafolio Profesional

### ✅ Puntos Fuertes

1. **Complejidad Técnica Demostrábil**
   - Async Python (asyncpg, httpx, asyncio)
   - MCP protocol implementation
   - PostgreSQL con logging
   - Error handling en producción
   - Docker orchestration

2. **Dominio de Negocio Claro**
   - Trading/fintech (sector demandado)
   - API integrations (OANDA v20)
   - Real-time data handling
   - Compliance/auditing

3. **Production-Ready Practices**
   - Type hints (Pydantic models)
   - Logging + observability
   - CORS, security headers
   - Health checks, graceful shutdown
   - Documentation (API + técnica)

4. **Escalabilidad Futura**
   - Arquitectura modular
   - Preparado para Redis cache
   - DB schema escalable
   - MCP compatible with future tools

### 🎬 Case Study / Blog Post Potential

"Building a Production-Grade MCP Server: OANDA Trading Automation with Claude"
- Explains MCP protocol
- Async patterns in Python
- Real-time data handling
- Error resilience
- Testing strategies

---

## 🔧 Mejoras Inmediatas (48 horas)

### Priority A — **DO FIRST**

```markdown
- [ ] README.md reescrito (template profesional)
- [ ] GETTING_STARTED.md con walkthrough
- [ ] LICENSE file (GNU 3.0)
- [ ] .env.example con valores comentados
- [ ] ARCHITECTURE.md con diagramas ASCII
- [ ] Refactor: src/ subdirectory structure
- [ ] Type hints completos (mypy strict)
- [ ] Tests básicos (pytest)
- [ ] GitHub .gitignore, workflows (CI)
```

### Priority B — **DO NEXT (1 semana)**

```markdown
- [ ] Rate limiting (slowapi or custom)
- [ ] Input validation pre-flight
- [ ] Reconnection circuit breaker
- [ ] Advanced dashboard (P&L analytics)
- [ ] CLI tool
- [ ] Backtest simulator
```

---

## 📝 Notas Finales

Este proyecto es **fundamentalmente sólido**:

✅ Resuelve problema real (automatización trading + Claude integration)  
✅ Código limpio, well-documented, production patterns  
✅ Escalable y extensible  
✅ Diferenciador en portfolio  

La **barrera a entry** es baja para traders técnicos, pero el proyecto aún es **nuevo en mercado**. 
Con las mejoras Tier 1, el repositorio pasaría de "proyecto personal bueno" a **"referencia comunitaria"** en r/algotrading, Discord traders, etc.

**Recomendación final:** Lanzar con README pulido, documentación clara y GitHub Actions CI. Iterar en base a feedback comunitario.

---

## 🎁 Complemento: Posibles Agentes MCP Futuros

Una vez core server estable, extensiones valiosas:

1. **oanda-backtest-mcp** — Simula estrategias contra datos históricos
2. **oanda-alerts-mcp** — Monitoreo + notificaciones (Slack, email)
3. **oanda-reporting-mcp** — P&L analysis, compliance reports
4. **oanda-strategy-builder-mcp** — Wizards para estrategias comunes (SMA, Bollinger, RSI)

Cada uno mantiene **single responsibility** + compatible con core server.

