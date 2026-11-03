# OANDA MCP Server — Referencia de Herramientas
**Versión:** 4.0.0 | **Tools MCP:** 7 agrupadas (37 acciones) | **Servidor:** `http://localhost:8000`

Las tools siguen la misma agrupación que la API oficial de OANDA. Cada tool recibe un parámetro `action` que selecciona la operación específica.

---

## Estado de verificación

| Tool | Acciones | Estado |
|------|----------|--------|
| `account` | get, summary, instruments, changes, configure | ✅ Verificado |
| `instrument` | candles, candles_account, orderbook, positionbook | ✅ Verificado |
| `pricing` | get_price, get_prices, latest_candles | ✅ Verificado |
| `order` | list, pending, get, place_market, place_limit, place_stop, place_mit, modify, cancel, tag | ✅ Verificado |
| `trade` | list, list_open, get, close, modify, set_orders, tag | ✅ Verificado |
| `position` | list_all, list_open, get, close | ✅ Verificado |
| `transaction` | list, get, range, since | ✅ Verificado |

**Fuera de scope:** `pricing/stream`, `transactions/stream` — streaming SSE, complejidad alta.

---

## `account`

Gestiona la cuenta OANDA.

| action | Descripción | Parámetros adicionales |
|--------|-------------|------------------------|
| `get` | Cuenta completa: balance, NAV, margen, P&L, leverage | — |
| `summary` | Resumen compacto de la cuenta | — |
| `instruments` | Lista instrumentos disponibles (FX, metales, índices) | `instruments` *(opcional)* — CSV filtro. Ej: `EUR_USD,XAU_USD` |
| `changes` | Cambios desde un TransactionID: órdenes, trades, posiciones | `sinceTransactionID` *(requerido)* — Ej: `"29300"` |
| `configure` | Modifica alias o tasa de margen | `alias` *(opcional)*, `marginRate` *(opcional)* — Ej: `"0.02"` |

---

## `instrument`

Datos de mercado históricos de un instrumento.

**Parámetro requerido en todas las acciones:** `instrument` — Ej: `EUR_USD`, `XAU_USD`, `SPX500_USD`

| action | Descripción | Parámetros adicionales |
|--------|-------------|------------------------|
| `candles` | Velas OHLCV históricas | `granularity` `count` `from_time` `to_time` `price` |
| `candles_account` | Última vela con precio ajustado al tamaño de cuenta | `granularity` `count` `units` |
| `orderbook` | Distribución de órdenes pendientes de clientes OANDA por precio | `time` *(snapshot histórico RFC3339)* |
| `positionbook` | Distribución de posiciones abiertas de clientes OANDA por precio | `time` *(snapshot histórico RFC3339)* |

**Granularidades disponibles:** `S5 S10 S15 S30 M1 M2 M4 M5 M10 M15 M30 H1 H2 H3 H4 H6 H8 H12 D W M`

**Parámetros de `candles`:**

| Parámetro | Tipo | Default OANDA | Descripción |
|-----------|------|---------------|-------------|
| `granularity` | string | `S5` | Temporalidad. Ver tabla arriba |
| `count` | integer | `500` (max 5000) | Número de velas. No usar con `from_time`+`to_time` |
| `from_time` | string | — | RFC3339. Ej: `2024-01-15T00:00:00Z` |
| `to_time` | string | — | RFC3339. Ej: `2024-01-15T23:59:59Z` |
| `price` | string | `M` | Componentes: `M` (mid), `B` (bid), `A` (ask). Combinar: `MBA`, `BA`, `MA` |

> **Nota `candles`:** Cuando se especifican `from_time` + `to_time`, NO se envía `count` (comportamiento OANDA). `includeFirst` solo se envía cuando se especifica `from_time`.

> **Nota `candles_account`:** Usa el endpoint `GET /v3/accounts/{id}/candles/latest` internamente con formato `candleSpecifications`. Default granularity: `M5`.

---

## `pricing`

Precios en tiempo real para uno o múltiples instrumentos.

| action | Descripción | Parámetros |
|--------|-------------|------------|
| `get_price` | Precio bid/ask de un instrumento | `instrument` *(requerido)* |
| `get_prices` | Precios de múltiples instrumentos | `instruments` *(requerido)* CSV. `since` *(opcional)* RFC3339 |
| `latest_candles` | Última vela completada multi-instrumento | `candleSpecifications` **o** `instruments`+`granularity`+`price` |

**`latest_candles` — formato candleSpecifications:** `INSTRUMENT:GRANULARITY:PRICE`
```
EUR_USD:M5:M            → EUR/USD, 5 min, mid
GBP_USD:M1:BA           → GBP/USD, 1 min, bid+ask
EUR_USD:S5:M,XAU_USD:H1:M   → múltiples en una llamada
```
Si se pasa `instruments` en lugar de `candleSpecifications`, el servidor construye el spec automáticamente con `granularity` y `price` indicados.

---

## `order`

Gestiona órdenes. Todas las acciones de creación requieren `instrument` y `units`.

| action | Descripción | Parámetros clave |
|--------|-------------|------------------|
| `list` | Lista órdenes con filtros | `state` (PENDING/FILLED/CANCELLED, default: PENDING) `instrument` `count` (default: 50) |
| `pending` | Solo órdenes PENDING | — |
| `get` | Detalle completo de una orden | `order_id` *(requerido)* |
| `place_market` | Orden de mercado — se ejecuta inmediatamente | `instrument` `units` `stop_loss` `take_profit` `trailing_stop` |
| `place_limit` | Límite — ejecuta al precio o mejor | `instrument` `units` `price` `stop_loss` `take_profit` |
| `place_stop` | Stop — ejecuta como mercado al alcanzar el precio (breakout) | `instrument` `units` `price` `stop_loss` `take_profit` |
| `place_mit` | Market-If-Touched — mercado al tocar el precio (reversión) | `instrument` `units` `price` `stop_loss` `take_profit` |
| `modify` | Modifica orden pendiente (consulta tipo original automáticamente) | `order_id` `price` `units` `stop_loss` `take_profit` |
| `cancel` | Cancela orden pendiente | `order_id` *(requerido)* |
| `tag` | Etiqueta una orden con ID/tag/comentario personalizado | `order_id` `client_id` `client_tag` `client_comment` |

**`units`:** positivo = compra long, negativo = venta short. Ej: `1000`, `-500`

> **Nota `tag`:** Las client extensions permiten asociar metadatos propios a órdenes y trades. `client_id` es un identificador único (útil para reconciliación), `client_tag` para clasificar estrategias, `client_comment` para notas libres. Los campos aparecen en las transacciones de OANDA.

---

## `trade`

Gestiona trades abiertos y cerrados.

| action | Descripción | Parámetros clave |
|--------|-------------|------------------|
| `list` | Lista trades con filtros | `state` `instrument` `count` `ids` `before_id` |
| `list_open` | Solo trades actualmente abiertos | — |
| `get` | Detalle completo: entrada, SL, TP, P&L, financiamiento | `trade_id` *(requerido)* |
| `close` | Cierra trade total o parcialmente | `trade_id` *(requerido)* `units` (default: ALL) |
| `modify` | Modifica SL/TP/trailing | `trade_id` `stop_loss` `take_profit` `trailing_stop` |
| `set_orders` | Establece SL/TP/trailing via PUT directo OANDA (más robusto) | `trade_id` `stop_loss` `take_profit` `trailing_stop` `guaranteed_stop` |
| `tag` | Etiqueta un trade con ID/tag/comentario personalizado | `trade_id` `client_id` `client_tag` `client_comment` |

**Parámetros de `list`:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `state` | string | `OPEN` | `OPEN`, `CLOSED`, `CLOSE_WHEN_TRADEABLE`, `ALL` |
| `instrument` | string | — | Filtrar por instrumento. Ej: `EUR_USD` |
| `count` | integer | `50` (max 500) | Número máximo de trades a devolver |
| `ids` | string | — | Filtrar por IDs específicos (CSV). Ej: `"1,2,3"` |
| `before_id` | string | — | Paginación: devuelve trades anteriores a este TradeID |

**Parámetros de `close`:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `trade_id` | string | ID del trade *(requerido)* |
| `units` | string | Unidades a cerrar (positivo). Omitir o `"ALL"` para cierre total |

> **`modify` vs `set_orders`:** Ambos modifican SL/TP/trailing. `set_orders` usa el endpoint `PUT /orders` directo de OANDA y es más fiable para operaciones críticas. Para pasar `null` y cancelar una orden dependiente, usar `set_orders`.

> **`guaranteed_stop` en `set_orders`:** Solo disponible en cuentas con GSLO habilitado (ciertas jurisdicciones UK/EU). En cuentas estándar (practice, US, Asia) el modo GSLO está `DISABLED` y este campo se ignora.

> **`trade_id` con `@clientID`:** OANDA soporta identificar trades por su client ID prefijado con `@`. Ej: `trade_id="@mi-trade-001"`.

---

## `position`

Consulta y cierra posiciones. Una posición puede tener lados long y short simultáneamente.

| action | Descripción | Parámetros |
|--------|-------------|------------|
| `list_all` | Todas las posiciones (abiertas y cerradas recientes) | — |
| `list_open` | Solo posiciones actualmente abiertas | — |
| `get` | Detalle de un instrumento: unidades long/short, precio promedio, P&L | `instrument` *(requerido)* |
| `close` | Cierra posición de un instrumento | `instrument` *(requerido)*, `side` (long/short/both, default: both) |

> **Nota `close`:** El servidor consulta la posición actual antes de cerrar y **omite el campo del lado que no existe**. OANDA rechaza el campo si el lado no está abierto.

---

## `transaction`

Historial de transacciones con detalle completo.

| action | Descripción | Parámetros |
|--------|-------------|------------|
| `list` | Últimas N transacciones con detalle real | `count` (default: 50) `from_time` `to_time` `type` |
| `get` | Detalle de una transacción específica | `transaction_id` *(requerido)* |
| `range` | Transacciones entre dos IDs (inclusive) | `from_id` `to_id` *(requeridos)* `type` |
| `since` | Todas las transacciones desde un ID | `transaction_id` *(requerido)* |

> **Nota `list`:** OANDA no soporta `pageSize` directo. El servidor obtiene los metadatos, extrae el rango de IDs y llama a `/transactions/range` internamente para devolver el detalle real de cada transacción.

**Tipos de transacción (`type`):**

| Valor | Descripción |
|-------|-------------|
| `ORDER_FILL` | Ejecución de orden — trade abierto |
| `ORDER_CANCEL` | Cancelación de orden |
| `TRADE_UPDATE` | Modificación de trade (SL/TP) |
| `TRADE_CLOSE` | Cierre de trade |
| `DAILY_FINANCING` | Cargo/abono de financiamiento diario |
| `MARGIN_CALL_ENTER` | Entrada en margin call |
| `MARGIN_CALL_EXIT` | Salida de margin call |
| `TRANSFER_FUNDS` | Transferencia de fondos |

---

## Instrumentos de referencia

**FX Majors:** `EUR_USD` `GBP_USD` `USD_JPY` `USD_CHF` `AUD_USD` `NZD_USD` `USD_CAD`
**FX Minors:** `EUR_GBP` `EUR_JPY` `GBP_JPY` `AUD_JPY` `EUR_AUD` `GBP_AUD`
**Metales:** `XAU_USD` (oro) `XAG_USD` (plata) `XPT_USD` (platino)
**Energía:** `WTICO_USD` (WTI) `BRENT_USD` (Brent) `NATGAS_USD`
**Índices:** `SPX500_USD` `NAS100_USD` `US30_USD` `UK100_USD` `DE30_USD` `JP225_USD`

---

## Timestamps RFC3339

```
2024-01-15T00:00:00Z
2024-01-15T14:30:00.000000000Z
```

---

## Bugs corregidos (historial de auditoría)

| # | Componente | Bug | Fix |
|---|-----------|-----|-----|
| 1 | `trade.set_orders` | Body enviaba args sucios → MALFORMED_REQUEST | Construir body limpio con solo TP/SL/TS formateados |
| 2 | `instrument.candles_account` | Llamaba endpoint no documentado | Redirigido a `GET /accounts/{id}/candles/latest` |
| 3 | `instrument.candles` MCP | No enviaba parámetro `price` | Añadido `price` al dispatcher |
| 4 | `trade.close` | `units` enviado como query string → siempre ALL | Cambiado a JSON body (`CloseTradeRequest`) |
| 5 | `trade.modify` | Usaba `price: "0"` para cancelar TP/SL | Cambiado a `null` |
| 6 | `order.modify` | SL/TP formateados sin `.5f` | Corregido a `f"{val:.5f}"` |
| 7 | `pricing.latest_candles` | Línea `PricingInfo` muerta | Eliminada |
| 8 | MCP schema `candles` | `granularity` default `M5` → debía ser `S5` | Corregido |
| 9 | MCP schema `candles` | `count` default `50` → debía ser `500` | Corregido |
| 10 | `trade` MCP schema | `state` solo mostraba OPEN/CLOSED | Añadidos `CLOSE_WHEN_TRADEABLE` y `ALL` |
| 11 | `trade` MCP schema | Faltaban `ids` y `before_id` en `list` | Añadidos |
| 12 | `trade.set_orders` | Faltaba `guaranteedStopLoss` (4º campo OANDA) | Añadido con nota de jurisdicción |
