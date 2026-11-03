# OANDA MCP Server

Servidor REST + MCP para operaciones de trading en OANDA v20. Expone 7 herramientas MCP agrupadas (37 acciones) compatibles con Claude Desktop, y una API REST completa documentada en Swagger.

## Stack

- **FastAPI** + **uvicorn** — servidor HTTP asíncrono
- **oandapyV20** — cliente oficial OANDA REST v20
- **asyncpg** + **PostgreSQL** — logging de requests, órdenes y trades
- **SSE + JSON-RPC** — protocolo MCP para Claude Desktop

---

## Variables de entorno

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `OANDA_API_KEY` | ✅ | — | API key de OANDA |
| `OANDA_ACCOUNT_ID` | ✅ | — | ID de la cuenta OANDA |
| `OANDA_ENVIRONMENT` | ✅ | `practice` | `practice` o `live` |
| `DATABASE_URL` | ✗ | `postgresql://oanda:oanda@db:5432/oanda_mcp` | PostgreSQL connection string. Si no disponible, el servidor arranca sin logging a DB. |

---

## Endpoints REST

### Health
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/health` | Estado detallado del servidor |

### Account
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/account` | Cuenta completa |
| `GET` | `/account/summary` | Resumen compacto |
| `GET` | `/account/instruments` | Instrumentos disponibles |
| `GET` | `/account/changes` | Cambios desde un TransactionID (`?sinceTransactionID=`) |
| `PATCH` | `/account/configuration` | Modificar alias o marginRate |

### Instruments
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/instruments/{instrument}/candles` | Velas históricas OHLCV |
| `GET` | `/instruments/{instrument}/candles/account` | Última vela ajustada a cuenta (→ `/accounts/{id}/candles/latest`) |
| `GET` | `/instruments/{instrument}/orderbook` | Distribución de órdenes por precio |
| `GET` | `/instruments/{instrument}/positionbook` | Distribución de posiciones por precio |
| `GET` | `/historical/{instrument}` | Alias legacy — datos históricos diarios |

### Pricing
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/price/{instrument}` | Precio bid/ask actual de un instrumento |
| `GET` | `/pricing` | Precios múltiples (`?instruments=EUR_USD,GBP_USD`) |
| `GET` | `/pricing/latest-candles` | Última vela completada multi-instrumento |
| `GET` | `/pricing/stream` | Stream SSE de precios en tiempo real |

### Orders
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/orders` | Listar órdenes (`?state=PENDING`) |
| `GET` | `/orders/pending` | Solo órdenes pendientes |
| `GET` | `/order/{order_id}` | Detalle de una orden |
| `POST` | `/order/market` | Orden de mercado |
| `POST` | `/order/limit` | Orden límite |
| `POST` | `/order/stop` | Orden stop (breakout) |
| `POST` | `/order/mit` | Market-If-Touched |
| `PATCH` | `/order/{order_id}` | Modificar orden pendiente |
| `DELETE` | `/order/{order_id}` | Cancelar orden |
| `PUT` | `/order/{order_id}/client-extensions` | Etiquetar orden (id/tag/comment) |

### Trades
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/trades` | Listar trades (`?state=OPEN&count=50&ids=1,2&beforeID=500`) |
| `GET` | `/trades/open` | Solo trades abiertos |
| `GET` | `/trade/{trade_id}` | Detalle de un trade (soporta `@clientID`) |
| `PATCH` | `/trade/{trade_id}` | Modificar SL/TP/trailing (→ TradeCRCDO internamente) |
| `PUT` | `/trade/{trade_id}/close` | Cerrar trade total o parcial (units en JSON body) |
| `PUT` | `/trade/{trade_id}/orders` | Establecer TP/SL/trailing/GSLO via PUT directo |
| `PUT` | `/trade/{trade_id}/client-extensions` | Etiquetar trade (id/tag/comment) |

### Positions
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/positions` | Todas las posiciones |
| `GET` | `/positions/open` | Solo posiciones abiertas |
| `GET` | `/position/{instrument}` | Detalle de posición de un instrumento |
| `POST` | `/position/close/{instrument}` | Cerrar posición (long/short/both) |

### Transactions
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/transactions` | Últimas N transacciones (`?count=50`) |
| `GET` | `/transaction/{transaction_id}` | Detalle de una transacción |
| `GET` | `/transactions/range` | Transacciones entre dos IDs (`?from_id=&to_id=`) |
| `GET` | `/transactions/since/{transaction_id}` | Transacciones desde un ID |

### MCP
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/mcp` | Info del servidor MCP (versión, herramientas) |
| `GET` | `/mcp/tools` | Lista de herramientas MCP disponibles |
| `POST` | `/mcp/call` | Llamada directa a herramienta MCP (debug) |
| `GET` | `/sse` | Endpoint SSE — Claude Desktop se conecta aquí |
| `POST` | `/messages` | Endpoint JSON-RPC — Claude Desktop envía mensajes aquí |

### Dashboard / DB
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/dashboard` | Dashboard HTML de actividad y logs |
| `GET` | `/db/requests` | Log de requests (`?limit=50&only_errors=false`) |
| `GET` | `/db/orders` | Log de órdenes ejecutadas |
| `GET` | `/db/trades` | Log de trades cerrados |

---

## Herramientas MCP

Consultar `MCP_TOOLS_REFERENCE.md` para documentación completa de cada herramienta.

| Tool | Acciones | Descripción |
|------|----------|-------------|
| `account` | 5 | Información y configuración de la cuenta |
| `instrument` | 4 | Velas históricas, orderbook, positionbook |
| `pricing` | 3 | Precios en tiempo real y última vela |
| `order` | 10 | Gestión completa de órdenes |
| `trade` | 7 | Gestión de trades: abrir, cerrar, modificar |
| `position` | 4 | Consulta y cierre de posiciones |
| `transaction` | 4 | Historial de transacciones |

---

## Configuración Claude Desktop

```json
{
  "mcpServers": {
    "oanda": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## Documentación interactiva

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Dashboard:** `http://localhost:8000/dashboard`
