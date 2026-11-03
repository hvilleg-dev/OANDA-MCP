# OANDA REST-V20 — Manual de Referencia para Agente Programador (Python)

> **Versión:** oandapyV20 v0.6.3 + developer.oanda.com (actualizado 2025)
> **Entornos:**
> - `practice` → `https://api-fxpractice.oanda.com`
> - `live` → `https://api-fxtrade.oanda.com`
> - `stream (practice)` → `https://stream-fxpractice.oanda.com`
> - `stream (live)` → `https://stream-fxtrade.oanda.com`
>
> **Autenticación:** `Authorization: Bearer {access_token}` en header HTTP de cada request.

---

## [NÚCLEO ONTOLÓGICO] — Primitivos y Tipos Base

### Glosario Técnico de Tipos Primitivos

| Tipo | Formato | Ejemplo |
|------|---------|---------|
| `AccountID` | `"{siteID}-{divisionID}-{userID}-{accountNumber}"` | `"001-011-5838423-001"` |
| `TransactionID` | Integer string positivo | `"2304"` |
| `OrderID` | Integer string positivo (derivado de TransactionID) | `"1523"` |
| `TradeID` | Integer string positivo (derivado de TransactionID que abrió el trade) | `"1523"` |
| `InstrumentName` | `"{base}_{quote}"` ISO 4217 | `"EUR_USD"`, `"DE30_EUR"` |
| `PriceValue` | Decimal codificado como string | `"1.12345"` |
| `DecimalNumber` | Decimal codificado como string | `"10000"`, `"0.05"` |
| `AccountUnits` | Decimal codificado como string (moneda home del Account) | `"44876.2548"` |
| `DateTime` | RFC3339 o UNIX epoch con decimales (hasta 9 decimales) | `"2016-07-21T15:47:05.170212014Z"` |
| `Currency` | ISO 4217 | `"EUR"`, `"USD"` |
| `ClientID` | String ≤ 128 chars | `"myID"` |
| `ClientTag` | String ≤ 128 chars | `"mytag"` |
| `ClientComment` | String ≤ 128 chars | `"myComment"` |
| `OrderSpecifier` | OrderID OANDA o `@{clientID}` | `"1523"` o `"@my_order"` |
| `TradeSpecifier` | TradeID OANDA o `@{clientID}` | `"@my_trade_id"` |
| `RequestID` | String | Identificador único de request HTTP |

### Tipos Enum Globales

#### `InstrumentType`
| Valor | Descripción |
|-------|-------------|
| `CURRENCY` | Par de divisas |
| `CFD` | Contrato por diferencia |
| `METAL` | Metal precioso |

#### `Direction`
| Valor | Condición |
|-------|-----------|
| `LONG` | `units > 0` → compra |
| `SHORT` | `units < 0` → venta |

#### `AcceptDatetimeFormat`
| Valor | Formato |
|-------|---------|
| `UNIX` | `"12345678.000000123"` |
| `RFC3339` | `"YYYY-MM-DDTHH:MM:SS.nnnnnnnnnZ"` |

#### `DayOfWeek`
`SUNDAY` | `MONDAY` | `TUESDAY` | `WEDNESDAY` | `THURSDAY` | `FRIDAY` | `SATURDAY`

### Fórmulas Clave

**Posición decimal del pip:**

$$\text{pip\_value} = 10^{\text{pipLocation}}$$

> Si `pipLocation = -4` → pip $= 10^{-4} = 0.0001$

**Conversión a moneda home:**

$$\text{amount\_home} = \text{amount\_foreign} \times \text{factor}$$

**Precio promedio ponderado por volumen (VWAP) de posición:**

$$\text{averagePrice} = \frac{\sum_{i} (\text{price}_i \times |\text{units}_i|)}{\sum_{i} |\text{units}_i|}$$

---

## [NÚCLEO ONTOLÓGICO] — Schemas de Objetos Base

### `Instrument` (Schema Completo)

```json
{
  "name": "(InstrumentName)",
  "type": "(InstrumentType)",
  "displayName": "(string)",
  "pipLocation": "(integer)",
  "displayPrecision": "(integer)",
  "tradeUnitsPrecision": "(integer)",
  "minimumTradeSize": "(DecimalNumber)",
  "maximumTrailingStopDistance": "(DecimalNumber)",
  "minimumGuaranteedStopLossDistance": "(DecimalNumber)",
  "minimumTrailingStopDistance": "(DecimalNumber)",
  "maximumPositionSize": "(DecimalNumber)",
  "maximumOrderUnits": "(DecimalNumber)",
  "marginRate": "(DecimalNumber)",
  "commission": "(InstrumentCommission)",
  "guaranteedStopLossOrderMode": "(GuaranteedStopLossOrderModeForInstrument)",
  "guaranteedStopLossOrderExecutionPremium": "(DecimalNumber)",
  "guaranteedStopLossOrderLevelRestriction": "(GuaranteedStopLossOrderLevelRestriction)",
  "financing": "(InstrumentFinancing)",
  "tags": "(Array[Tag])"
}
```

### `Tag`
```json
{ "type": "(string)", "name": "(string)" }
```

### `InstrumentCommission`
```json
{
  "commission": "(DecimalNumber)",
  "unitsTraded": "(DecimalNumber)",
  "minimumCommission": "(DecimalNumber)"
}
```

### `InstrumentFinancing`
```json
{
  "longRate": "(DecimalNumber)",
  "shortRate": "(DecimalNumber)",
  "financingDaysOfWeek": "(Array[FinancingDayOfWeek])"
}
```
> `longRate` / `shortRate`: fracción decimal. $5\% \rightarrow 0.05$

### `FinancingDayOfWeek`
```json
{ "dayOfWeek": "(DayOfWeek)", "daysCharged": "(integer)" }
```

### `GuaranteedStopLossOrderLevelRestriction`
```json
{ "volume": "(DecimalNumber)", "priceRange": "(DecimalNumber)" }
```

### `HomeConversionFactors`
```json
{
  "gainQuoteHome": { "factor": "(DecimalNumber)" },
  "lossQuoteHome": { "factor": "(DecimalNumber)" },
  "gainBaseHome":  { "factor": "(DecimalNumber)" },
  "lossBaseHome":  { "factor": "(DecimalNumber)" }
}
```

### `ConversionFactor`
```json
{ "factor": "(DecimalNumber)" }
```

### `HomeConversions`
```json
{
  "currency": "(Currency)",
  "accountGain": "(DecimalNumber)",
  "accountLoss": "(DecimalNumber)",
  "positionValue": "(DecimalNumber)"
}
```

---

## [NÚCLEO ONTOLÓGICO] — Account Definitions

### Axiomas de Account

> $\text{NAV} = \text{balance} + \text{unrealizedPL}$
> $\text{marginCloseoutPercent} \geq 1.0$ → estado de **margin closeout** (cierre forzado)
> $\text{marginCallPercent} \geq 1.0$ → estado de **margin call**

### `Account` (Schema Completo)

```json
{
  "id": "(AccountID)",
  "alias": "(string)",
  "currency": "(Currency)",
  "createdByUserID": "(integer)",
  "createdTime": "(DateTime)",
  "guaranteedStopLossOrderParameters": "(GuaranteedStopLossOrderParameters)",
  "guaranteedStopLossOrderMode": "(GuaranteedStopLossOrderMode)",
  "resettablePLTime": "(DateTime)",
  "marginRate": "(DecimalNumber)",
  "openTradeCount": "(integer)",
  "openPositionCount": "(integer)",
  "pendingOrderCount": "(integer)",
  "hedgingEnabled": "(boolean)",
  "unrealizedPL": "(AccountUnits)",
  "NAV": "(AccountUnits)",
  "marginUsed": "(AccountUnits)",
  "marginAvailable": "(AccountUnits)",
  "positionValue": "(AccountUnits)",
  "marginCloseoutUnrealizedPL": "(AccountUnits)",
  "marginCloseoutNAV": "(AccountUnits)",
  "marginCloseoutMarginUsed": "(AccountUnits)",
  "marginCloseoutPercent": "(DecimalNumber)",
  "marginCloseoutPositionValue": "(DecimalNumber)",
  "withdrawalLimit": "(AccountUnits)",
  "marginCallMarginUsed": "(AccountUnits)",
  "marginCallPercent": "(DecimalNumber)",
  "balance": "(AccountUnits)",
  "pl": "(AccountUnits)",
  "resettablePL": "(AccountUnits)",
  "financing": "(AccountUnits)",
  "commission": "(AccountUnits)",
  "dividendAdjustment": "(AccountUnits)",
  "guaranteedExecutionFees": "(AccountUnits)",
  "marginCallEnterTime": "(DateTime)",
  "marginCallExtensionCount": "(integer)",
  "lastMarginCallExtensionTime": "(DateTime)",
  "lastTransactionID": "(TransactionID)",
  "trades": "(Array[TradeSummary])",
  "positions": "(Array[Position])",
  "orders": "(Array[Order])"
}
```

> **`AccountSummary`**: Schema idéntico a `Account` sin los arrays `trades`, `positions`, `orders`.

### `AccountChanges`
```json
{
  "ordersCreated": "(Array[Order])",
  "ordersCancelled": "(Array[Order])",
  "ordersFilled": "(Array[Order])",
  "ordersTriggered": "(Array[Order])",
  "tradesOpened": "(Array[TradeSummary])",
  "tradesReduced": "(Array[TradeSummary])",
  "tradesClosed": "(Array[TradeSummary])",
  "positions": "(Array[Position])",
  "transactions": "(Array[Transaction])"
}
```

### `AccountProperties` (listado de cuentas)
```json
{ "id": "(AccountID)", "tags": "(Array[string])" }
```

### Enums de Account

#### `GuaranteedStopLossOrderMode`
| Valor | Comportamiento |
|-------|---------------|
| `DISABLED` | No se permite crear GSLO |
| `ALLOWED` | GSLO opcional para trades abiertos |
| `REQUIRED` | GSLO obligatorio para todos los trades abiertos |

#### `GuaranteedStopLossOrderModeForInstrument`
| Valor | Descripción |
|-------|-------------|
| `DISABLED` | No permitido para este instrumento |
| `ALLOWED` | Opcional para este instrumento |
| `REQUIRED` | Obligatorio para este instrumento |

#### `GuaranteedStopLossOrderMutability`
| Valor | Restricción |
|-------|------------|
| `FIXED` | No puede reemplazarse ni cancelarse |
| `REPLACEABLE` | Solo puede reemplazarse |
| `CANCELABLE` | Puede reemplazarse o cancelarse |
| `PRICE_WIDEN_ONLY` | Solo puede reemplazarse ampliando distancia del precio actual |

#### `AccountFinancingMode`
| Valor | Comportamiento |
|-------|---------------|
| `NO_FINANCING` | Sin cobro de financiación |
| `SECOND_BY_SECOND` | Financiación por segundo, diaria y al cierre |
| `DAILY` | Cargo diario completo a las 5pm hora Nueva York |

#### `PositionAggregationMode`
| Valor | Método de cálculo |
|-------|------------------|
| `ABSOLUTE_SUM` | Suma absoluta de ambos lados (long + short) |
| `MAXIMAL_SIDE` | Máximo valor absoluto entre long y short |
| `NET_SUM` | Neto de unidades (long - short) |

### Fórmulas de Margen

$$\text{margin\_requerido} = \text{notional\_value} \times \text{marginRate}$$

$$\text{notional\_value} = \text{units} \times \text{precio\_actual}$$

$$\text{leverage} = \frac{1}{\text{marginRate}}$$

$$\text{leverage\_efectivo} = \frac{\text{marginUsed}}{\text{NAV}}$$

---

## [NÚCLEO ONTOLÓGICO] — Order Definitions

### Axiomas de Órdenes

> - **MARKET**: ejecución inmediata al precio de mercado vigente
> - **LIMIT**: ejecución solo si precio $\leq$ threshold (long) o $\geq$ threshold (short)
> - **STOP**: ejecución solo si precio $\geq$ threshold (long) o $\leq$ threshold (short)
> - **TAKE_PROFIT / STOP_LOSS / TRAILING_STOP_LOSS**: no abren posiciones nuevas; solo cierran trades existentes
> - `units > 0` → orden LONG; `units < 0` → orden SHORT

### `OrderType`
| Valor | Descripción |
|-------|-------------|
| `MARKET` | Ejecución inmediata al precio de mercado |
| `LIMIT` | Precio igual o mejor que threshold |
| `STOP` | Precio igual o peor que threshold |
| `MARKET_IF_TOUCHED` | Activación al tocar precio; luego ejecuta como mercado |
| `TAKE_PROFIT` | Cierre de trade al alcanzar precio objetivo |
| `STOP_LOSS` | Cierre de trade al alcanzar precio de pérdida máxima |
| `GUARANTEED_STOP_LOSS` | Stop Loss garantizado sin slippage (cobra premium) |
| `TRAILING_STOP_LOSS` | Stop Loss dinámico que sigue el precio ganador |
| `FIXED_PRICE` | Ejecución inmediata a precio fijo especificado |

### `OrderState`
| Valor | Condición |
|-------|-----------|
| `PENDING` | Orden en espera de ejecución |
| `FILLED` | Orden ejecutada completamente |
| `TRIGGERED` | Orden activada (MIT orders) |
| `CANCELLED` | Orden cancelada |

### `OrderStateFilter` (para filtros en GET)
| Valor | Descripción |
|-------|-------------|
| `PENDING` | Solo órdenes pendientes (default) |
| `FILLED` | Solo órdenes ejecutadas |
| `TRIGGERED` | Solo órdenes activadas |
| `CANCELLED` | Solo órdenes canceladas |
| `ALL` | Todas las órdenes |

### `TimeInForce`
| Valor | Descripción | Aplica a |
|-------|-------------|----------|
| `GTC` | Good unTil Cancelled | LIMIT, STOP, MIT, TP, SL, TSL |
| `GTD` | Good unTil Date (requiere `gtdTime`) | LIMIT, STOP, MIT, TP, SL, TSL |
| `GFD` | Good For Day (cancela 5pm NY) | LIMIT, STOP, MIT, TP, SL, TSL |
| `FOK` | Fill Or Kill (inmediato o cancela total) | MARKET (default) |
| `IOC` | Immediately partial fill Or Cancel | MARKET |

### `OrderPositionFill`
| Valor | Comportamiento al llenar |
|-------|------------------------|
| `OPEN_ONLY` | Solo abre o extiende posición existente |
| `REDUCE_FIRST` | Primero reduce posición existente, luego abre nueva |
| `REDUCE_ONLY` | Solo reduce posición existente |
| `DEFAULT` | `REDUCE_FIRST` sin hedging; `OPEN_ONLY` con hedging |

### `OrderTriggerCondition`
| Valor | Comparación de precio |
|-------|----------------------|
| `DEFAULT` | Ask para órdenes long; Bid para órdenes short |
| `INVERSE` | Bid para órdenes long; Ask para órdenes short |
| `BID` | Siempre compara con Bid |
| `ASK` | Siempre compara con Ask |
| `MID` | Siempre compara con Midpoint |

> **Restricción GSLO:** `triggerCondition` solo acepta `DEFAULT` o lado natural. Long GSLO: `DEFAULT` o `BID`. Short GSLO: `DEFAULT` o `ASK`.

---

## [NÚCLEO ONTOLÓGICO] — Trade Definitions

### `TradeState`
| Valor | Condición |
|-------|-----------|
| `OPEN` | Trade activo, `currentUnits > 0` |
| `CLOSED` | Trade completamente cerrado, `currentUnits = 0` |
| `CLOSE_WHEN_TRADEABLE` | Se cerrará cuando el instrumento vuelva a ser tradeable |

### `TradeStateFilter` (para filtros en GET)
| Valor | Descripción |
|-------|-------------|
| `OPEN` | Solo trades abiertos (default) |
| `CLOSED` | Solo trades cerrados |
| `CLOSE_WHEN_TRADEABLE` | Solo trades pendientes de cierre |
| `ALL` | Todos los trades |

### `Trade` (Schema Completo)
```json
{
  "id": "(TradeID)",
  "instrument": "(InstrumentName)",
  "price": "(PriceValue)",
  "openTime": "(DateTime)",
  "state": "(TradeState)",
  "initialUnits": "(DecimalNumber)",
  "initialMarginRequired": "(AccountUnits)",
  "currentUnits": "(DecimalNumber)",
  "realizedPL": "(AccountUnits)",
  "unrealizedPL": "(AccountUnits)",
  "marginUsed": "(AccountUnits)",
  "averageClosePrice": "(PriceValue)",
  "closingTransactionIDs": "(Array[TransactionID])",
  "financing": "(AccountUnits)",
  "dividendAdjustment": "(AccountUnits)",
  "closeTime": "(DateTime)",
  "clientExtensions": "(ClientExtensions)",
  "takeProfitOrder": "(TakeProfitOrder)",
  "stopLossOrder": "(StopLossOrder)",
  "guaranteedStopLossOrder": "(GuaranteedStopLossOrder)",
  "trailingStopLossOrder": "(TrailingStopLossOrder)"
}
```

### `TradeSummary`
Schema idéntico a `Trade` pero con IDs en lugar de objetos de orden:
```json
{
  "takeProfitOrderID": "(OrderID)",
  "stopLossOrderID": "(OrderID)",
  "guaranteedStopLossOrderID": "(OrderID)",
  "trailingStopLossOrderID": "(OrderID)"
}
```

---

## [NÚCLEO ONTOLÓGICO] — Position Definitions

### `Position`
```json
{
  "instrument": "(InstrumentName)",
  "pl": "(AccountUnits)",
  "unrealizedPL": "(AccountUnits)",
  "marginUsed": "(AccountUnits)",
  "resettablePL": "(AccountUnits)",
  "financing": "(AccountUnits)",
  "commission": "(AccountUnits)",
  "dividendAdjustment": "(AccountUnits)",
  "guaranteedExecutionFees": "(AccountUnits)",
  "long": "(PositionSide)",
  "short": "(PositionSide)"
}
```

### `PositionSide`
```json
{
  "units": "(DecimalNumber)",
  "averagePrice": "(PriceValue)",
  "tradeIDs": "(Array[TradeID])",
  "pl": "(AccountUnits)",
  "unrealizedPL": "(AccountUnits)",
  "resettablePL": "(AccountUnits)",
  "financing": "(AccountUnits)",
  "dividendAdjustment": "(AccountUnits)",
  "guaranteedExecutionFees": "(AccountUnits)"
}
```
> `averagePrice` = VWAP de los trades abiertos en esa dirección.

---

## [NÚCLEO ONTOLÓGICO] — Pricing Definitions

### `ClientPrice`
```json
{
  "type": "PRICE",
  "instrument": "(InstrumentName)",
  "time": "(DateTime)",
  "tradeable": "(boolean)",
  "bids": "(Array[PriceBucket])",
  "asks": "(Array[PriceBucket])",
  "closeoutBid": "(PriceValue)",
  "closeoutAsk": "(PriceValue)"
}
```

### `PriceBucket`
```json
{ "price": "(PriceValue)", "liquidity": "(integer)" }
```

### `PricingHeartbeat`
```json
{ "type": "HEARTBEAT", "time": "(DateTime)" }
```

### `PriceStatus`
| Valor | Estado |
|-------|--------|
| `tradeable` | Precio ejecutable |
| `non-tradeable` | Precio no ejecutable |
| `invalid` | Instrumento inválido o sin precio |

### `CandleSpecification` (string format)
```
"{InstrumentName}:{CandlestickGranularity}:{PricingComponent}"
```
Ejemplo: `"EUR_USD:S10:BM"` → EUR_USD, 10 segundos, Bid+Mid

### `PricingComponent`
| Char | Tipo de Vela |
|------|-------------|
| `M` | Midpoint |
| `B` | Bid |
| `A` | Ask |

### `CandlestickGranularity`
| Valor | Período | Valor | Período |
|-------|---------|-------|---------|
| `S5` | 5 seg | `H1` | 1 hora |
| `S10` | 10 seg | `H2` | 2 horas |
| `S15` | 15 seg | `H3` | 3 horas |
| `S30` | 30 seg | `H4` | 4 horas |
| `M1` | 1 min | `H6` | 6 horas |
| `M2` | 2 min | `H8` | 8 horas |
| `M4` | 4 min | `H12` | 12 horas |
| `M5` | 5 min | `D` | 1 día |
| `M10` | 10 min | `W` | 1 semana |
| `M15` | 15 min | `M` | 1 mes |
| `M30` | 30 min | | |

### `Candlestick` (Schema respuesta)
```json
{
  "time": "(DateTime)",
  "volume": "(integer)",
  "complete": "(boolean)",
  "mid": { "o": "(PriceValue)", "h": "(PriceValue)", "l": "(PriceValue)", "c": "(PriceValue)" },
  "bid": { "o": "(PriceValue)", "h": "(PriceValue)", "l": "(PriceValue)", "c": "(PriceValue)" },
  "ask": { "o": "(PriceValue)", "h": "(PriceValue)", "l": "(PriceValue)", "c": "(PriceValue)" }
}
```
> `complete = false` → vela en curso (no finalizada). Solo usar velas con `complete = true` para backtesting.

### `WeeklyAlignment`
`Monday` | `Tuesday` | `Wednesday` | `Thursday` | `Friday` | `Saturday` | `Sunday`

---

## [NÚCLEO ONTOLÓGICO] — Transaction Definitions

### `Transaction` (Base)
```json
{
  "id": "(TransactionID)",
  "time": "(DateTime)",
  "userID": "(integer)",
  "accountID": "(AccountID)",
  "batchID": "(TransactionID)",
  "requestID": "(RequestID)"
}
```

### `TransactionType` — Enumeración Completa
| Valor | Evento |
|-------|--------|
| `CREATE` | Creación de Account |
| `CLOSE` | Cierre de Account |
| `REOPEN` | Reapertura de Account |
| `CLIENT_CONFIGURE` | Configuración de Account por cliente |
| `CLIENT_CONFIGURE_REJECT` | Rechazo de configuración |
| `TRANSFER_FUNDS` | Transferencia de fondos |
| `TRANSFER_FUNDS_REJECT` | Rechazo de transferencia |
| `MARKET_ORDER` | Creación de Market Order |
| `MARKET_ORDER_REJECT` | Rechazo de Market Order |
| `FIXED_PRICE_ORDER` | Creación de Fixed Price Order |
| `LIMIT_ORDER` | Creación de Limit Order |
| `LIMIT_ORDER_REJECT` | Rechazo de Limit Order |
| `STOP_ORDER` | Creación de Stop Order |
| `STOP_ORDER_REJECT` | Rechazo de Stop Order |
| `MARKET_IF_TOUCHED_ORDER` | Creación de MIT Order |
| `MARKET_IF_TOUCHED_ORDER_REJECT` | Rechazo de MIT Order |
| `TAKE_PROFIT_ORDER` | Creación de Take Profit Order |
| `TAKE_PROFIT_ORDER_REJECT` | Rechazo de Take Profit |
| `STOP_LOSS_ORDER` | Creación de Stop Loss Order |
| `STOP_LOSS_ORDER_REJECT` | Rechazo de Stop Loss |
| `GUARANTEED_STOP_LOSS_ORDER` | Creación de GSLO |
| `GUARANTEED_STOP_LOSS_ORDER_REJECT` | Rechazo de GSLO |
| `TRAILING_STOP_LOSS_ORDER` | Creación de Trailing SL |
| `TRAILING_STOP_LOSS_ORDER_REJECT` | Rechazo de Trailing SL |
| `ORDER_FILL` | Orden ejecutada |
| `ORDER_CANCEL` | Orden cancelada |
| `ORDER_CANCEL_REJECT` | Rechazo de cancelación |
| `ORDER_CLIENT_EXTENSIONS_MODIFY` | Modificación de client extensions de orden |
| `ORDER_CLIENT_EXTENSIONS_MODIFY_REJECT` | Rechazo de modificación |
| `TRADE_CLIENT_EXTENSIONS_MODIFY` | Modificación de client extensions de trade |
| `TRADE_CLIENT_EXTENSIONS_MODIFY_REJECT` | Rechazo de modificación |
| `MARGIN_CALL_ENTER` | Account entra en margin call |
| `MARGIN_CALL_EXTEND` | Extensión de margin call |
| `MARGIN_CALL_EXIT` | Account sale de margin call |
| `DELAYED_TRADE_CLOSURE` | Cierre de trade diferido |
| `DAILY_FINANCING` | Cargo/abono de financiación diaria |
| `DIVIDEND_ADJUSTMENT` | Ajuste por dividendo |
| `RESET_RESETTABLE_PL` | Reset de P&L resettable |

### `OrderFillTransaction` (Schema Key)
```json
{
  "type": "ORDER_FILL",
  "orderID": "(OrderID)",
  "clientOrderID": "(ClientID)",
  "instrument": "(InstrumentName)",
  "units": "(DecimalNumber)",
  "gainQuoteHomeConversionFactor": "(DecimalNumber)",
  "lossQuoteHomeConversionFactor": "(DecimalNumber)",
  "homeConversionFactors": "(HomeConversionFactors)",
  "price": "(PriceValue)",
  "fullVWAP": "(PriceValue)",
  "fullPrice": "(ClientPrice)",
  "reason": "(OrderFillReason)",
  "pl": "(AccountUnits)",
  "guaranteedExecutionFee": "(AccountUnits)",
  "commission": "(AccountUnits)",
  "accountBalance": "(AccountUnits)",
  "tradeOpened": "(TradeOpen)",
  "tradesClosed": "(Array[TradeReduce])",
  "tradeReduced": "(TradeReduce)",
  "halfSpreadCost": "(AccountUnits)"
}
```

### `MarketOrderReason`
| Valor | Origen |
|-------|--------|
| `CLIENT_ORDER` | Orden manual del cliente |
| `TRADE_CLOSE` | Cierre de trade solicitado |
| `POSITION_CLOSEOUT` | Cierre completo de posición |
| `MARGIN_CLOSEOUT` | Cierre forzado por margin |
| `DELAYED_TRADE_CLOSE` | Cierre diferido |

### `OrderFillReason`
| Valor | Tipo de orden ejecutada |
|-------|------------------------|
| `MARKET_ORDER` | Market Order |
| `MARKET_ORDER_TRADE_CLOSE` | Market Order cerrando trade |
| `MARKET_ORDER_POSITION_CLOSEOUT` | Market Order cerrando posición |
| `MARKET_ORDER_MARGIN_CLOSEOUT` | Market Order por margin closeout |
| `MARKET_ORDER_DELAYED_TRADE_CLOSE` | Market Order cierre diferido |
| `LIMIT_ORDER` | Limit Order |
| `STOP_ORDER` | Stop Order |
| `MARKET_IF_TOUCHED_ORDER` | MIT Order |
| `TAKE_PROFIT_ORDER` | Take Profit |
| `STOP_LOSS_ORDER` | Stop Loss |
| `GUARANTEED_STOP_LOSS_ORDER` | Guaranteed Stop Loss |
| `TRAILING_STOP_LOSS_ORDER` | Trailing Stop Loss |
| `FIXED_PRICE_ORDER` | Fixed Price Order |

### `OrderCancelReason`
| Valor | Causa |
|-------|-------|
| `CLIENT_REQUEST` | Cancelación manual |
| `CLIENT_REQUEST_REPLACED` | Reemplazada por otra orden |
| `TIME_IN_FORCE_EXPIRED` | TIF expirado |
| `LINKED_TRADE_CLOSED` | Trade vinculado se cerró |
| `MARKET_HALTED` | Mercado detenido |
| `INSUFFICIENT_MARGIN` | Margen insuficiente |
| `INSUFFICIENT_LIQUIDITY` | Liquidez insuficiente |
| `BOUNDS_VIOLATION` | Precio fuera de límites |
| `LOSING_TAKE_PROFIT` | Take profit resultaría en pérdida |

### `TransactionRejectReason` (errores de validación)
| Valor | Condición |
|-------|-----------|
| `INSUFFICIENT_FUNDS` | Fondos insuficientes |
| `INSUFFICIENT_MARGIN` | Margen insuficiente |
| `INSTRUMENT_NOT_TRADEABLE` | Instrumento no tradeable |
| `INSTRUMENT_UNKNOWN` | Instrumento desconocido |
| `UNITS_MISSING` | Unidades no especificadas |
| `UNITS_INVALID` | Unidades con formato inválido |
| `UNITS_LIMIT_EXCEEDED` | Supera límite de unidades del instrumento |
| `PRICE_MISSING` | Precio no especificado |
| `PRICE_INVALID` | Precio con formato inválido |
| `PRICE_PRECISION_EXCEEDED` | Precisión de precio excedida |
| `TIME_IN_FORCE_INVALID` | TIF no válido para el tipo de orden |
| `TRADE_DOESNT_EXIST` | Trade referenciado no existe |
| `ORDER_DOESNT_EXIST` | Orden referenciada no existe |
| `STOP_LOSS_ON_FILL_PRICE_MISSING` | SL requerido pero no especificado |
| `ACCOUNT_NOT_ACTIVE` | Account inactivo |
| `ACCOUNT_LOCKED` | Account bloqueado |
| `INTERNAL_SERVER_ERROR` | Error interno del servidor |

---

## [LÓGICA PROCEDIMENTAL] — Python SDK: Instalación y Cliente

### Instalación

```bash
pip install oandapyV20
# o desde source:
pip install git+https://github.com/hootnot/oanda-api-v20.git
```

### Cliente API

```python
from oandapyV20 import API
from oandapyV20.exceptions import V20Error

# Inicialización
api = API(
    access_token="your_token_here",
    environment="practice",           # "practice" | "live"
    headers=None,                     # dict opcional de headers adicionales
    request_params={"timeout": 10}    # timeout en segundos
)

# Ejecución de request
rv = api.request(endpoint_instance)
# rv es dict con respuesta JSON
# endpoint_instance.response también contiene la respuesta
```

### Manejo de Excepciones

```python
from oandapyV20.exceptions import V20Error

try:
    rv = api.request(r)
except V20Error as e:
    if e.code == 400:
        # Parámetros inválidos — revisar TransactionRejectReason
        import json
        try:
            err_data = json.loads(e.msg)
            print(f"Razón: {err_data.get('errorMessage')}")
            print(f"Reject reason: {err_data.get('rejectReason')}")
        except Exception:
            print(e.msg)
    elif e.code == 401:
        print("Token inválido o expirado / accountID incorrecto")
    elif e.code == 403:
        print("Account no tradeable — contactar soporte OANDA")
    elif e.code == 404:
        print("Recurso no encontrado (Account/Trade/Order/Transaction)")
    elif e.code == 405:
        print("Método HTTP incorrecto para este endpoint")
    elif e.code >= 500:
        print("Error del servidor OANDA — reintentar con backoff exponencial")
```

### Logging

```python
import logging
logging.basicConfig(
    filename="v20.log",
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s : %(message)s',
)
```

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Account

### Referencia de Endpoints

| HTTP | URL | Clase Python | Resp. HTTP |
|------|-----|--------------|-----------|
| GET | `/v3/accounts` | `AccountList()` | 200 |
| GET | `/v3/accounts/{accountID}` | `AccountDetails(accountID)` | 200 |
| GET | `/v3/accounts/{accountID}/summary` | `AccountSummary(accountID)` | 200 |
| GET | `/v3/accounts/{accountID}/instruments` | `AccountInstruments(accountID, params)` | 200 |
| PATCH | `/v3/accounts/{accountID}/configuration` | `AccountConfiguration(accountID, data)` | 200 |
| GET | `/v3/accounts/{accountID}/changes` | `AccountChanges(accountID, params)` | 200 |

### Código Python

```python
import oandapyV20.endpoints.accounts as accounts

# Listar todas las cuentas autorizadas
r = accounts.AccountList()
rv = api.request(r)
# rv → {"accounts": [{"id": "001-011-...", "tags": []}]}

# Detalles completos de cuenta (incluye trades, positions, orders)
r = accounts.AccountDetails(accountID)
rv = api.request(r)
# rv → {"account": {...}, "lastTransactionID": "6356"}

# Resumen de cuenta (sin arrays de trades/positions/orders)
r = accounts.AccountSummary(accountID)
rv = api.request(r)
acc = rv["account"]
balance = float(acc["balance"])
nav = float(acc["NAV"])
margin_pct = float(acc["marginCloseoutPercent"])

# Instrumentos disponibles (opcional: filtrar)
r = accounts.AccountInstruments(accountID, params={"instruments": "EUR_USD,GBP_USD"})
rv = api.request(r)
instruments = rv["instruments"]

# Configurar cuenta (marginRate en decimal, ej: 5% = "0.05")
r = accounts.AccountConfiguration(accountID, data={"marginRate": "0.05"})
rv = api.request(r)

# Cambios desde una transacción dada
r = accounts.AccountChanges(accountID, params={"sinceTransactionID": "2308"})
rv = api.request(r)
changes = rv["changes"]
state = rv["state"]
```

### Headers de Request Account
| Header | Requerido | Descripción |
|--------|-----------|-------------|
| `Authorization` | Sí | `Bearer {token}` |
| `Accept-Datetime-Format` | No | `UNIX` o `RFC3339` |

### Errores comunes Account
| HTTP | Causa |
|------|-------|
| 401 | Token inválido / accountID incorrecto → `"The provided request was forbidden."` |
| 405 | Método HTTP incorrecto para el endpoint |

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Orders

### Referencia de Endpoints

| HTTP | URL | Clase Python | Resp. HTTP |
|------|-----|--------------|-----------|
| POST | `/v3/accounts/{accountID}/orders` | `OrderCreate(accountID, data)` | **201** |
| GET | `/v3/accounts/{accountID}/orders` | `OrderList(accountID, params)` | 200 |
| GET | `/v3/accounts/{accountID}/pendingOrders` | `OrdersPending(accountID)` | 200 |
| GET | `/v3/accounts/{accountID}/orders/{orderSpecifier}` | `OrderDetails(accountID, orderID)` | 200 |
| PUT | `/v3/accounts/{accountID}/orders/{orderSpecifier}` | `OrderReplace(accountID, orderID, data)` | **201** |
| PUT | `/v3/accounts/{accountID}/orders/{orderSpecifier}/cancel` | `OrderCancel(accountID, orderID)` | 200 |
| PUT | `/v3/accounts/{accountID}/orders/{orderSpecifier}/clientExtensions` | `OrderClientExtensions(accountID, orderID, data)` | 200 |

### Parámetros de Listado de Órdenes (`OrderList`)
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `ids` | List[OrderID] csv | — | IDs específicos a recuperar |
| `state` | `OrderStateFilter` | `PENDING` | Filtro por estado |
| `instrument` | `InstrumentName` | — | Filtro por instrumento |
| `count` | integer | 50 | Máximo de órdenes (max=500) |
| `beforeID` | `OrderID` | — | Máximo OrderID a retornar |

### Código Python: Órdenes

```python
import oandapyV20.endpoints.orders as orders

# Crear Market Order (long 100 unidades EUR_USD)
r = orders.OrderCreate(accountID, data={
    "order": {
        "type": "MARKET",
        "instrument": "EUR_USD",
        "units": "100",
        "timeInForce": "FOK",
        "positionFill": "DEFAULT"
    }
})
rv = api.request(r)
trade_id = rv["orderFillTransaction"]["tradeOpened"]["tradeID"]
fill_price = rv["orderFillTransaction"]["price"]

# Crear Market Order (short -100 unidades EUR_USD)
r = orders.OrderCreate(accountID, data={
    "order": {
        "type": "MARKET",
        "instrument": "EUR_USD",
        "units": "-100",
        "timeInForce": "FOK",
        "positionFill": "DEFAULT"
    }
})

# Crear Limit Order con SL y TP adjuntos
r = orders.OrderCreate(accountID, data={
    "order": {
        "type": "LIMIT",
        "instrument": "USD_CAD",
        "units": "-1000",
        "price": "1.5000",
        "timeInForce": "GTC",
        "positionFill": "DEFAULT",
        "stopLossOnFill": {"timeInForce": "GTC", "price": "1.7000"},
        "takeProfitOnFill": {"price": "1.14530"}
    }
})

# Crear Take Profit Order para trade existente
r = orders.OrderCreate(accountID, data={
    "order": {
        "type": "TAKE_PROFIT",
        "tradeID": "6368",
        "price": "1.6000",
        "timeInForce": "GTC"
    }
})

# Crear MIT Order con ClientExtensions
r = orders.OrderCreate(accountID, data={
    "order": {
        "type": "MARKET_IF_TOUCHED",
        "instrument": "EUR_CAD",
        "units": "10000",
        "price": "1.2000",
        "timeInForce": "GTC",
        "positionFill": "DEFAULT",
        "clientExtensions": {
            "id": "my_order_100",
            "tag": "strategy_9",
            "comment": "New idea for trading"
        }
    }
})

# Listar órdenes pendientes
r = orders.OrderList(accountID, params={"state": "PENDING", "count": 500})
rv = api.request(r)
pending = rv["orders"]

# Órdenes pendientes (shortcut)
r = orders.OrdersPending(accountID)
rv = api.request(r)

# Detalles de una orden
r = orders.OrderDetails(accountID, orderID="2304")
rv = api.request(r)

# Reemplazar orden existente
r = orders.OrderReplace(accountID, orderID="2304", data={
    "order": {
        "type": "LIMIT",
        "instrument": "EUR_USD",
        "units": "-500000",
        "price": "1.25000",
        "timeInForce": "GTC"
    }
})
rv = api.request(r)
new_order_id = rv["orderCreateTransaction"]["id"]
cancelled_id = rv["orderCancelTransaction"]["orderID"]

# Cancelar orden
r = orders.OrderCancel(accountID, orderID="2304")
rv = api.request(r)

# Modificar ClientExtensions de una orden (NO usar en cuentas MT4)
r = orders.OrderClientExtensions(accountID, orderID="2304", data={
    "clientExtensions": {"comment": "myComment", "id": "myID", "tag": "mytag"},
    "tradeClientExtensions": {"comment": "tradeComment"}
})
```

### Schemas de Order Requests (Creación)

#### `MarketOrderRequest`
```json
{
  "order": {
    "type": "MARKET",
    "instrument": "(InstrumentName, required)",
    "units": "(DecimalNumber, required)",
    "timeInForce": "(FOK|IOC, default=FOK)",
    "priceBound": "(PriceValue)",
    "positionFill": "(OrderPositionFill, default=DEFAULT)",
    "clientExtensions": "(ClientExtensions)",
    "takeProfitOnFill": "(TakeProfitDetails)",
    "stopLossOnFill": "(StopLossDetails)",
    "guaranteedStopLossOnFill": "(GuaranteedStopLossDetails)",
    "trailingStopLossOnFill": "(TrailingStopLossDetails)",
    "tradeClientExtensions": "(ClientExtensions)"
  }
}
```

#### `LimitOrderRequest`
```json
{
  "order": {
    "type": "LIMIT",
    "instrument": "(InstrumentName, required)",
    "units": "(DecimalNumber, required)",
    "price": "(PriceValue, required)",
    "timeInForce": "(GTC|GTD|GFD, default=GTC)",
    "gtdTime": "(DateTime)",
    "positionFill": "(OrderPositionFill, default=DEFAULT)",
    "triggerCondition": "(OrderTriggerCondition, default=DEFAULT)",
    "clientExtensions": "(ClientExtensions)",
    "takeProfitOnFill": "(TakeProfitDetails)",
    "stopLossOnFill": "(StopLossDetails)",
    "guaranteedStopLossOnFill": "(GuaranteedStopLossDetails)",
    "trailingStopLossOnFill": "(TrailingStopLossDetails)",
    "tradeClientExtensions": "(ClientExtensions)"
  }
}
```

#### `StopOrderRequest`
```json
{
  "order": {
    "type": "STOP",
    "instrument": "(InstrumentName, required)",
    "units": "(DecimalNumber, required)",
    "price": "(PriceValue, required)",
    "priceBound": "(PriceValue)",
    "timeInForce": "(GTC|GTD|GFD, default=GTC)",
    "gtdTime": "(DateTime)",
    "positionFill": "(OrderPositionFill, default=DEFAULT)",
    "triggerCondition": "(OrderTriggerCondition, default=DEFAULT)",
    "clientExtensions": "(ClientExtensions)",
    "takeProfitOnFill": "(TakeProfitDetails)",
    "stopLossOnFill": "(StopLossDetails)",
    "guaranteedStopLossOnFill": "(GuaranteedStopLossDetails)",
    "trailingStopLossOnFill": "(TrailingStopLossDetails)",
    "tradeClientExtensions": "(ClientExtensions)"
  }
}
```

#### `MarketIfTouchedOrderRequest`
```json
{
  "order": {
    "type": "MARKET_IF_TOUCHED",
    "instrument": "(InstrumentName, required)",
    "units": "(DecimalNumber, required)",
    "price": "(PriceValue, required)",
    "priceBound": "(PriceValue)",
    "timeInForce": "(GTC|GTD|GFD, default=GTC)",
    "gtdTime": "(DateTime)",
    "positionFill": "(OrderPositionFill, default=DEFAULT)",
    "triggerCondition": "(OrderTriggerCondition, default=DEFAULT)",
    "clientExtensions": "(ClientExtensions)",
    "takeProfitOnFill": "(TakeProfitDetails)",
    "stopLossOnFill": "(StopLossDetails)",
    "guaranteedStopLossOnFill": "(GuaranteedStopLossDetails)",
    "trailingStopLossOnFill": "(TrailingStopLossDetails)",
    "tradeClientExtensions": "(ClientExtensions)"
  }
}
```

#### `TakeProfitOrderRequest`
```json
{
  "order": {
    "type": "TAKE_PROFIT",
    "tradeID": "(TradeID, required)",
    "clientTradeID": "(ClientID)",
    "price": "(PriceValue, required)",
    "timeInForce": "(GTC|GTD|GFD, default=GTC)",
    "gtdTime": "(DateTime)",
    "triggerCondition": "(OrderTriggerCondition, default=DEFAULT)",
    "clientExtensions": "(ClientExtensions)"
  }
}
```

#### `StopLossOrderRequest`
```json
{
  "order": {
    "type": "STOP_LOSS",
    "tradeID": "(TradeID, required)",
    "clientTradeID": "(ClientID)",
    "price": "(PriceValue)",
    "distance": "(DecimalNumber)",
    "timeInForce": "(GTC|GTD|GFD, default=GTC)",
    "gtdTime": "(DateTime)",
    "triggerCondition": "(OrderTriggerCondition, default=DEFAULT)",
    "clientExtensions": "(ClientExtensions)"
  }
}
```
> `price` y `distance` son **mutuamente excluyentes**. Especificar solo uno.

#### `GuaranteedStopLossOrderRequest`
```json
{
  "order": {
    "type": "GUARANTEED_STOP_LOSS",
    "tradeID": "(TradeID, required)",
    "clientTradeID": "(ClientID)",
    "price": "(PriceValue)",
    "distance": "(DecimalNumber)",
    "timeInForce": "(GTC|GTD|GFD, default=GTC)",
    "gtdTime": "(DateTime)",
    "triggerCondition": "(OrderTriggerCondition: DEFAULT|BID para long, DEFAULT|ASK para short)",
    "clientExtensions": "(ClientExtensions)"
  }
}
```

#### `TrailingStopLossOrderRequest`
```json
{
  "order": {
    "type": "TRAILING_STOP_LOSS",
    "tradeID": "(TradeID, required)",
    "clientTradeID": "(ClientID)",
    "distance": "(DecimalNumber, required)",
    "timeInForce": "(GTC|GTD|GFD, default=GTC)",
    "gtdTime": "(DateTime)",
    "triggerCondition": "(OrderTriggerCondition, default=DEFAULT)",
    "clientExtensions": "(ClientExtensions)"
  }
}
```

### Respuestas de OrderCreate

**HTTP 201 — Orden creada y ejecutada (MARKET):**
```json
{
  "orderCreateTransaction": {
    "type": "MARKET_ORDER", "id": "6367", "batchID": "6367",
    "instrument": "EUR_USD", "units": "100", "timeInForce": "FOK",
    "positionFill": "DEFAULT", "reason": "CLIENT_ORDER",
    "time": "2016-06-22T18:41:29.264030555Z"
  },
  "orderFillTransaction": {
    "type": "ORDER_FILL", "id": "6368", "orderID": "6367",
    "instrument": "EUR_USD", "units": "100", "price": "1.13027",
    "pl": "0.00000", "financing": "0.00000",
    "accountBalance": "43650.75945",
    "reason": "MARKET_ORDER",
    "tradeOpened": { "tradeID": "6368", "units": "100" }
  },
  "relatedTransactionIDs": ["6367", "6368"],
  "lastTransactionID": "6368"
}
```

**HTTP 400 — Orden rechazada:**
```json
{
  "orderRejectTransaction": { "type": "MARKET_ORDER_REJECT", ... },
  "relatedTransactionIDs": ["..."],
  "lastTransactionID": "...",
  "errorCode": "(string)",
  "errorMessage": "(string)"
}
```

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Trades

### Referencia de Endpoints

| HTTP | URL | Clase Python | Resp. HTTP |
|------|-----|--------------|-----------|
| GET | `/v3/accounts/{accountID}/trades` | `TradesList(accountID, params)` | 200 |
| GET | `/v3/accounts/{accountID}/openTrades` | `OpenTrades(accountID)` | 200 |
| GET | `/v3/accounts/{accountID}/trades/{tradeSpecifier}` | `TradeDetails(accountID, tradeID)` | 200 |
| PUT | `/v3/accounts/{accountID}/trades/{tradeSpecifier}/close` | `TradeClose(accountID, tradeID, data)` | 200 |
| PUT | `/v3/accounts/{accountID}/trades/{tradeSpecifier}/clientExtensions` | `TradeClientExtensions(accountID, tradeID, data)` | 200 |
| PUT | `/v3/accounts/{accountID}/trades/{tradeSpecifier}/orders` | `TradeCRCDO(accountID, tradeID, data)` | 200 |

### Parámetros de Listado de Trades
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `ids` | List[TradeID] csv | — | IDs específicos |
| `state` | `TradeStateFilter` | `OPEN` | Filtro por estado |
| `instrument` | `InstrumentName` | — | Filtro por instrumento |
| `count` | integer | 50 | Máximo (max=500) |
| `beforeID` | `TradeID` | — | Máximo TradeID |

### Código Python: Trades

```python
import oandapyV20.endpoints.trades as trades

# Listar trades (filtros opcionales)
r = trades.TradesList(accountID, params={"instrument": "USD_CAD", "state": "OPEN"})
rv = api.request(r)
trade_list = rv["trades"]

# Trades abiertos (shortcut)
r = trades.OpenTrades(accountID)
rv = api.request(r)
open_trades = rv["trades"]

# Detalles de un trade (por ID numérico o ClientID con @)
r = trades.TradeDetails(accountID, tradeID="6395")
rv = api.request(r)

# Por clientID
r = trades.TradeDetails(accountID, tradeID="@my_eur_usd_trade")
rv = api.request(r)

# Cerrar trade completo
r = trades.TradeClose(accountID, tradeID="1030")
rv = api.request(r)
pl = rv["orderFillTransaction"]["pl"]

# Cerrar trade parcial (especificar unidades positivas)
r = trades.TradeClose(accountID, tradeID="1030", data={"units": "5"})
rv = api.request(r)

# Modificar ClientExtensions de un trade (NO usar en cuentas MT4)
r = trades.TradeClientExtensions(accountID, tradeID="1030", data={
    "clientExtensions": {"id": "myID2315", "comment": "myComment"}
})

# Crear/Reemplazar/Cancelar órdenes dependientes (TakeProfit, StopLoss, TrailingStopLoss)
r = trades.TradeCRCDO(accountID, tradeID="1030", data={
    "takeProfit": {"timeInForce": "GTC", "price": "1.10"},
    "stopLoss": {"timeInForce": "GTC", "price": "1.05"},
    "trailingStopLoss": {"timeInForce": "GTC", "distance": "0.020"}
})
# Para cancelar un TP/SL existente: pasar null en el campo
# "takeProfit": null  → cancela el Take Profit

rv = api.request(r)
```

### Request Body TradeClose
```json
{
  "units": "(string: 'ALL' | DecimalNumber positivo)"
}
```
> Omitir `data` equivale a cierre total (`ALL`). Unidades parciales deben ser positivas y $\leq$ `currentUnits`.

### Respuesta TradeClose (HTTP 200)
```json
{
  "orderCreateTransaction": { "type": "MARKET_ORDER", ... },
  "orderFillTransaction": {
    "type": "ORDER_FILL",
    "price": "10131.6",
    "pl": "14.0000",
    "financing": "-0.1519",
    "accountBalance": "44876.2548",
    "tradeReduced": {
      "tradeID": "1030", "units": "5",
      "realizedPL": "14.0000", "financing": "-0.1519"
    }
  },
  "relatedTransactionIDs": ["1041", "1042"],
  "lastTransactionID": "1042"
}
```

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Positions

### Referencia de Endpoints

| HTTP | URL | Clase Python | Resp. HTTP |
|------|-----|--------------|-----------|
| GET | `/v3/accounts/{accountID}/positions` | `PositionList(accountID)` | 200 |
| GET | `/v3/accounts/{accountID}/openPositions` | `OpenPositions(accountID)` | 200 |
| GET | `/v3/accounts/{accountID}/positions/{instrument}` | `PositionDetails(accountID, instrument)` | 200 |
| PUT | `/v3/accounts/{accountID}/positions/{instrument}/close` | `PositionClose(accountID, instrument, data)` | 200 |

### Código Python: Positions

```python
import oandapyV20.endpoints.positions as positions

# Listar todas las posiciones
r = positions.PositionList(accountID)
rv = api.request(r)

# Posiciones abiertas
r = positions.OpenPositions(accountID)
rv = api.request(r)

# Detalles de posición en instrumento específico
r = positions.PositionDetails(accountID, instrument="EUR_USD")
rv = api.request(r)
pos = rv["position"]
long_units = pos["long"]["units"]
short_units = pos["short"]["units"]

# Cerrar posición long completa
r = positions.PositionClose(accountID, instrument="EUR_USD",
                             data={"longUnits": "ALL"})
rv = api.request(r)

# Cerrar posición short parcial
r = positions.PositionClose(accountID, instrument="EUR_USD",
                             data={"shortUnits": "100"})

# Cerrar ambas direcciones
r = positions.PositionClose(accountID, instrument="EUR_USD",
                             data={"longUnits": "ALL", "shortUnits": "ALL"})
```

### Request Body PositionClose
```json
{
  "longUnits": "(string: 'ALL' | DecimalNumber positivo | 'NONE')",
  "shortUnits": "(string: 'ALL' | DecimalNumber positivo | 'NONE')",
  "longClientExtensions": "(ClientExtensions)",
  "shortClientExtensions": "(ClientExtensions)"
}
```

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Pricing

### Referencia de Endpoints

| HTTP | URL | Clase Python | Resp. HTTP |
|------|-----|--------------|-----------|
| GET | `/v3/accounts/{accountID}/candles/latest` | `PricingInfo` con `candleSpecifications` | 200 |
| GET | `/v3/accounts/{accountID}/pricing` | `PricingInfo(accountID, params)` | 200 |
| GET | `/v3/accounts/{accountID}/pricing/stream` | `PricingStream(accountID, params)` **[STREAM]** | 200 |

> **STREAM endpoints:** Servidos por URLs de streaming (`stream-fxpractice.oanda.com` / `stream-fxtrade.oanda.com`), NO por las URLs REST estándar.

### Código Python: Pricing

```python
import oandapyV20.endpoints.pricing as pricing
from oandapyV20.exceptions import StreamTerminated

# Precio actual de instrumentos
r = pricing.PricingInfo(accountID, params={
    "instruments": "EUR_USD,USD_CAD",
    "includeHomeConversions": True
})
rv = api.request(r)
prices = rv["prices"]
for p in prices:
    bid = p["bids"][0]["price"]
    ask = p["asks"][0]["price"]
    spread = float(ask) - float(bid)
    print(f"{p['instrument']}: bid={bid} ask={ask} spread={spread:.5f}")

# Stream de precios en tiempo real (max 4 ticks/segundo por instrumento)
r = pricing.PricingStream(accountID, params={
    "instruments": "EUR_USD,USD_CAD",
    "snapshot": True          # enviar snapshot inicial al conectar
})
api.request(r)

maxrecs = 100
try:
    for tick in r:
        if tick.get("type") == "PRICE":
            if tick.get("tradeable"):
                bid = tick["bids"][0]["price"]
                ask = tick["asks"][0]["price"]
                mid = (float(bid) + float(ask)) / 2
                print(f"{tick['instrument']}: bid={bid} ask={ask} mid={mid:.5f}")
        elif tick.get("type") == "HEARTBEAT":
            pass  # heartbeat cada 5 segundos — confirma conexión activa
        maxrecs -= 1
        if maxrecs == 0:
            r.terminate("limit reached")
except StreamTerminated as e:
    print(f"Stream terminado: {e}")
```

### Parámetros `PricingInfo`
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `instruments` | List[InstrumentName] csv | — | Instrumentos a consultar (requerido) |
| `since` | `DateTime` | — | Solo precios posteriores a esta fecha |
| `includeUnitsAvailable` | boolean | True | Incluir `unitsAvailable` (deprecated) |
| `includeHomeConversions` | boolean | False | Incluir factores de conversión a moneda home |

### Respuesta `PricingInfo`
```json
{
  "prices": [
    {
      "instrument": "EUR_USD",
      "tradeable": true,
      "time": "2016-06-22T18:41:36.201836422Z",
      "bids": [{"price": "1.13015", "liquidity": 10000000}],
      "asks": [{"price": "1.13028", "liquidity": 10000000}],
      "closeoutBid": "1.13011",
      "closeoutAsk": "1.13032",
      "status": "tradeable"
    }
  ],
  "homeConversions": [...],
  "time": "(DateTime)"
}
```

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Instruments

### Referencia de Endpoints

| HTTP | URL | Clase Python | Resp. HTTP |
|------|-----|--------------|-----------|
| GET | `/v3/instruments/{instrument}/candles` | `InstrumentsCandles(instrument, params)` | 200 |
| GET | `/v3/instruments/{instrument}/orderBook` | `InstrumentsOrderBook(instrument, params)` | 200 |
| GET | `/v3/instruments/{instrument}/positionBook` | `InstrumentsPositionBook(instrument, params)` | 200 |

### Código Python: Instruments

```python
import oandapyV20.endpoints.instruments as instruments

# Velas (parámetros completos)
r = instruments.InstrumentsCandles(
    instrument="EUR_USD",
    params={
        "count": 6,
        "granularity": "M5",
        "price": "MBA",           # M=mid, B=bid, A=ask (combinable)
        "from": "2017-01-01T00:00:00Z",
        "to": "2017-12-31T23:59:59Z",
        "smooth": False,
        "includeFirst": True,
        "dailyAlignment": 17,
        "alignmentTimezone": "America/New_York",
        "weeklyAlignment": "Friday"
    }
)
rv = api.request(r)
candles = rv["candles"]
# Solo procesar velas completas
complete = [c for c in candles if c["complete"]]

# Order Book
r = instruments.InstrumentsOrderBook(instrument="EUR_USD",
                                      params={"time": "2016-10-17T15:00:00Z"})
rv = api.request(r)

# Position Book
r = instruments.InstrumentsPositionBook(instrument="EUR_USD")
rv = api.request(r)
```

### Parámetros de Velas (`InstrumentsCandles`)
| Parámetro | Tipo | Default | Max | Descripción |
|-----------|------|---------|-----|-------------|
| `price` | `PricingComponent` | `M` | — | `M`, `B`, `A` (combinables) |
| `granularity` | `CandlestickGranularity` | `S5` | — | Período de la vela |
| `count` | integer | 500 | 5000 | Número de velas |
| `from` | `DateTime` | — | — | Inicio del rango |
| `to` | `DateTime` | — | — | Fin del rango |
| `smooth` | boolean | False | — | Usar close anterior como open |
| `includeFirst` | boolean | True | — | Incluir vela que cubre `from` |
| `dailyAlignment` | integer | 17 | 0-23 | Hora de alineación diaria |
| `alignmentTimezone` | string | `America/New_York` | — | Zona horaria |
| `weeklyAlignment` | `WeeklyAlignment` | `Friday` | — | Día de alineación semanal |

> **Regla:** Si `from` y `to` se especifican, NO especificar `count` — el rango temporal determina las velas. Si solo `from`, usar `count` para limitar cantidad.

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Transactions

### Referencia de Endpoints

| HTTP | URL | Clase Python | Resp. HTTP |
|------|-----|--------------|-----------|
| GET | `/v3/accounts/{accountID}/transactions` | `TransactionList(accountID, params)` | 200 |
| GET | `/v3/accounts/{accountID}/transactions/{transactionID}` | `TransactionDetails(accountID, transactionID)` | 200 |
| GET | `/v3/accounts/{accountID}/transactions/idrange` | `TransactionIDRange(accountID, params)` | 200 |
| GET | `/v3/accounts/{accountID}/transactions/sinceid` | `TransactionsSinceID(accountID, params)` | 200 |
| GET | `/v3/accounts/{accountID}/transactions/stream` | `TransactionsStream(accountID)` **[STREAM]** | 200 |

### Código Python: Transactions

```python
import oandapyV20.endpoints.transactions as transactions

# Listar transacciones (respuesta paginada)
r = transactions.TransactionList(accountID, params={"pageSize": 200})
rv = api.request(r)
# rv → {"count": 2124, "pages": [...], "lastTransactionID": "2124"}

# Detalles de una transacción específica
r = transactions.TransactionDetails(accountID, transactionID="2304")
rv = api.request(r)

# Rango de transacciones por ID
r = transactions.TransactionIDRange(accountID, params={"from": "2304", "to": "2400"})
rv = api.request(r)

# Transacciones desde un ID dado
r = transactions.TransactionsSinceID(accountID, params={"id": "2304"})
rv = api.request(r)
txns = rv["transactions"]

# Stream de transacciones en tiempo real
r = transactions.TransactionsStream(accountID)
api.request(r)
for T in r:
    if T.get("type") != "HEARTBEAT":
        print(f"Transacción: {T['type']} id={T.get('id')}")
```

### Respuesta `TransactionList` (paginada)
```json
{
  "count": 2124,
  "from": "2016-06-24T21:03:50.914647476Z",
  "to": "2016-10-05T06:54:14.025946546Z",
  "pageSize": 100,
  "lastTransactionID": "2124",
  "pages": ["https://api.../transactions/idrange?from=1&to=100", "..."]
}
```

---

## [LÓGICA PROCEDIMENTAL] — contrib.requests (Order Builder)

### Imports

```python
from oandapyV20.contrib.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    MITOrderRequest,
    TakeProfitOrderRequest,
    StopLossOrderRequest,
    TrailingStopLossOrderRequest,
    TradeCloseRequest,
    PositionCloseRequest,
    TakeProfitDetails,
    StopLossDetails,
    TrailingStopLossDetails,
    ClientExtensions
)
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.positions as positions
```

### MarketOrderRequest

```python
mo = MarketOrderRequest(
    instrument="EUR_USD",
    units=10000,                   # positivo=LONG, negativo=SHORT
    priceBound=None,               # PriceValue opcional
    positionFill="DEFAULT",
    timeInForce="FOK",
    clientExtensions=None,
    takeProfitOnFill=None,
    stopLossOnFill=None,
    trailingStopLossOnFill=None,
    tradeClientExtensions=None
)
r = orders.OrderCreate(accountID, data=mo.data)
rv = api.request(r)
```

### LimitOrderRequest

```python
lo = LimitOrderRequest(
    instrument="EUR_USD",
    units=10000,
    price=1.08,
    positionFill="DEFAULT",
    timeInForce="GTC",
    gtdTime=None,
    stopLossOnFill=None,
    takeProfitOnFill=None,
    trailingStopLossOnFill=None,
    tradeClientExtensions=None,
    clientExtensions=None
)
r = orders.OrderCreate(accountID, data=lo.data)
```

### StopOrderRequest

```python
so = StopOrderRequest(
    instrument="EUR_USD",
    units=10000,
    price=1.07,
    priceBound=None,
    positionFill="DEFAULT",
    timeInForce="GTC"
)
```

### MITOrderRequest

```python
mit = MITOrderRequest(
    instrument="EUR_USD",
    units=10000,
    price=1.08,
    priceBound=None,
    positionFill="DEFAULT",
    timeInForce="GTC"
)
```

### TakeProfitOrderRequest

```python
tp = TakeProfitOrderRequest(
    tradeID="1234",
    price=1.22,
    clientTradeID=None,
    timeInForce="GTC",
    gtdTime=None,
    clientExtensions=None
)
r = orders.OrderCreate(accountID, data=tp.data)
```

### StopLossOrderRequest

```python
sl = StopLossOrderRequest(
    tradeID="1234",
    price=1.07,           # usar price O distance, no ambos
    clientTradeID=None,
    timeInForce="GTC"
)
```

### TrailingStopLossOrderRequest

```python
tsl = TrailingStopLossOrderRequest(
    tradeID="1234",
    distance=20,          # price units de distancia (positivo)
    clientTradeID=None,
    timeInForce="GTC"
)
```

### TradeCloseRequest

```python
tc = TradeCloseRequest(units="ALL")     # cierre total
tc = TradeCloseRequest(units=5000)      # cierre parcial
r = trades.TradeClose(accountID, tradeID="1234", data=tc.data)
```

### PositionCloseRequest

```python
pc = PositionCloseRequest(longUnits="ALL")
pc = PositionCloseRequest(shortUnits=100)
pc = PositionCloseRequest(longUnits="ALL", shortUnits="ALL")
r = positions.PositionClose(accountID, instrument="EUR_USD", data=pc.data)
```

### TakeProfitDetails / StopLossDetails / TrailingStopLossDetails (OnFill)

```python
# Adjuntar automáticamente al abrir posición
tp_details = TakeProfitDetails(
    price=1.10,
    timeInForce="GTC",
    gtdTime=None,
    clientExtensions=None
)

sl_details = StopLossDetails(
    price=1.06,
    timeInForce="GTC"
)

tsl_details = TrailingStopLossDetails(
    distance=0.002,
    timeInForce="GTC"
)

mo = MarketOrderRequest(
    instrument="EUR_USD",
    units=10000,
    takeProfitOnFill=tp_details.data,
    stopLossOnFill=sl_details.data,
    trailingStopLossOnFill=tsl_details.data
)
r = orders.OrderCreate(accountID, data=mo.data)
```

### ClientExtensions

```python
ce = ClientExtensions(
    clientID="myID",
    clientTag="mytag",
    clientComment="myComment"
)
# ce.data → {"id": "myID", "tag": "mytag", "comment": "myComment"}
```

---

## [LÓGICA PROCEDIMENTAL] — InstrumentsCandlesFactory

```python
from oandapyV20.contrib.factories import InstrumentsCandlesFactory
import json

client = API(access_token="...", environment="practice")

params = {
    "from": "2020-01-01T00:00:00Z",
    "to": "2020-12-31T23:59:59Z",
    "granularity": "H1",
    "count": 5000,      # tamaño de batch por request (no límite total)
    "price": "MBA"
}

all_candles = []
for r in InstrumentsCandlesFactory(instrument="EUR_USD", params=params):
    client.request(r)
    all_candles.extend(r.response.get("candles", []))

# Solo velas completas
complete_candles = [c for c in all_candles if c["complete"]]
print(f"Total velas descargadas: {len(all_candles)}")
print(f"Velas completas: {len(complete_candles)}")

# Guardar a archivo
with open("/tmp/EUR_USD.H1.json", "w") as OUT:
    json.dump(complete_candles, OUT, indent=2)
```

> **Lógica interna:** `InstrumentsCandlesFactory` calcula automáticamente el número total de velas entre `from` y `to`, genera múltiples requests de `count` velas cada uno, fuerza `includeFirst=True` para evitar gaps entre batches.

---

## [LÓGICA PROCEDIMENTAL] — Tipos del SDK y Utilidades

### oandapyV20.types

```python
from oandapyV20.types import (
    AccountID, AccountUnits, ClientComment, ClientID, ClientTag,
    DateTime, OrderID, OrderIdentifier, OrderSpecifier, PriceValue,
    TradeID, Units
)

pv = PriceValue(1.23456)        # → pv.value = "1.23456"
pv = PriceValue("1.23456")      # → pv.value = "1.23456"
oid = OrderID(1234)              # → oid.value = "1234"
tid = TradeID(1234)              # → tid.value = "1234"
u   = Units(10000)               # → u.value = "10000"

# DateTime acepta: RFC3339 string, dict de partes, datetime.datetime
from datetime import datetime
dt = DateTime(datetime.now())
dt = DateTime("2014-07-02T04:00:00.000000Z")
dt = DateTime({"year": 2014, "month": 12, "day": 2,
               "hour": 13, "minute": 48, "second": 12})
# → dt.value siempre es string RFC3339

# OrderIdentifier
oi = OrderIdentifier(orderID="1234", clientID="myOrder")
# → oi.value = {"orderID": "1234", "clientOrderID": "myOrder"}
```

### contrib.generic

```python
from oandapyV20.contrib.generic import granularity_to_time, secs2time

# Convertir granularidad a segundos
secs = granularity_to_time("M5")   # → 300
secs = granularity_to_time("H1")   # → 3600
secs = granularity_to_time("D")    # → 86400

# Convertir epoch a datetime
from datetime import datetime
dt = secs2time(1497499200)
# dt → datetime.datetime(2017, 6, 15, 4, 0)
dt.strftime("%Y%m%d-%H:%M:%S")    # → "20170615-04:00:00"
```

### oandapyV20.definitions

```python
import oandapyV20.definitions.orders as deforders
import oandapyV20.definitions.instruments as definstruments

# Acceso a constantes
deforders.OrderType.MARKET          # → "MARKET"
deforders.TimeInForce.GTC           # → "GTC"
deforders.OrderState.CANCELLED      # → "CANCELLED"

# Obtener descripción de un valor
c = deforders.OrderType()
c[c.MARKET]                         # → "A Market Order"

# Granularidades
definstruments.CandlestickGranularity.H4      # → "H4"
c = definstruments.CandlestickGranularity()
c[c.H4]                                        # → "4 hour candlesticks, day alignment"
```

---

## [SÍNTESIS DE EVIDENCIA] — Flujos Operativos Completos

### Flujo 1: Abrir Posición LONG con TP y SL (contrib.requests)

```python
from oandapyV20 import API
import oandapyV20.endpoints.orders as orders
from oandapyV20.contrib.requests import (
    MarketOrderRequest, TakeProfitDetails, StopLossDetails
)
from oandapyV20.exceptions import V20Error

api = API(access_token="TOKEN", environment="practice")
accountID = "001-001-1234567-001"

mo = MarketOrderRequest(
    instrument="EUR_USD",
    units=10000,
    takeProfitOnFill=TakeProfitDetails(price=1.10).data,
    stopLossOnFill=StopLossDetails(price=1.06).data
)
r = orders.OrderCreate(accountID, data=mo.data)
try:
    rv = api.request(r)
    trade_id = rv["orderFillTransaction"]["tradeOpened"]["tradeID"]
    fill_price = rv["orderFillTransaction"]["price"]
    balance = rv["orderFillTransaction"]["accountBalance"]
    print(f"Trade abierto: {trade_id} @ {fill_price} | Balance: {balance}")
except V20Error as e:
    print(f"Error {e.code}: {e.msg}")
```

### Flujo 2: Monitoreo de Estado de Account y Riesgo

```python
import oandapyV20.endpoints.accounts as accounts

r = accounts.AccountSummary(accountID)
rv = api.request(r)
acc = rv["account"]

balance = float(acc["balance"])
nav = float(acc["NAV"])
margin_used = float(acc["marginUsed"])
margin_available = float(acc["marginAvailable"])
unrealized_pl = float(acc["unrealizedPL"])
margin_closeout_pct = float(acc["marginCloseoutPercent"])

leverage_efectivo = margin_used / nav if nav > 0 else 0

if margin_closeout_pct >= 1.0:
    print("CRÍTICO: Margin Closeout ACTIVO — posiciones siendo cerradas")
elif margin_closeout_pct >= 0.8:
    print(f"ALERTA: Margin Closeout al {margin_closeout_pct*100:.1f}%")
elif margin_closeout_pct >= 0.5:
    print(f"ADVERTENCIA: Margin Closeout al {margin_closeout_pct*100:.1f}%")

print(f"NAV: {nav} | Balance: {balance} | Unrealized PL: {unrealized_pl}")
print(f"Margin Used: {margin_used} | Margin Available: {margin_available}")
print(f"Leverage efectivo: {leverage_efectivo:.2f}x")
```

### Flujo 3: Listar y Cerrar Trades Abiertos

```python
import oandapyV20.endpoints.trades as trades
from oandapyV20.contrib.requests import TradeCloseRequest

# Obtener todos los trades abiertos
r = trades.OpenTrades(accountID)
rv = api.request(r)

for trade in rv["trades"]:
    trade_id = trade["id"]
    instrument = trade["instrument"]
    units = trade["currentUnits"]
    unrealized_pl = trade["unrealizedPL"]
    print(f"Trade {trade_id}: {instrument} units={units} PnL={unrealized_pl}")

# Cerrar el primer trade completamente
if rv["trades"]:
    first_trade_id = rv["trades"][0]["id"]
    r = trades.TradeClose(accountID, tradeID=first_trade_id,
                           data=TradeCloseRequest(units="ALL").data)
    rv_close = api.request(r)
    print(f"P&L realizado: {rv_close['orderFillTransaction']['pl']}")
```

### Flujo 4: Cerrar Posición Completa

```python
import oandapyV20.endpoints.positions as positions
from oandapyV20.contrib.requests import PositionCloseRequest

r = positions.PositionClose(
    accountID,
    instrument="EUR_USD",
    data=PositionCloseRequest(longUnits="ALL").data
)
try:
    rv = api.request(r)
    pl = rv["relatedTransactionIDs"]
    print(f"Posición cerrada. Transacciones: {pl}")
except V20Error as e:
    print(f"Error al cerrar posición: {e.code} — {e.msg}")
```

### Flujo 5: Stream de Precios con Procesamiento

```python
import oandapyV20.endpoints.pricing as pricing
from oandapyV20.exceptions import StreamTerminated

r = pricing.PricingStream(accountID, params={
    "instruments": "EUR_USD,GBP_USD,USD_JPY",
    "snapshot": True
})
api.request(r)

tick_count = 0
MAX_TICKS = 200

try:
    for tick in r:
        tick_type = tick.get("type")
        if tick_type == "PRICE":
            instrument = tick["instrument"]
            bid = float(tick["bids"][0]["price"])
            ask = float(tick["asks"][0]["price"])
            spread_pips = (ask - bid) * 10000  # para pares 4 decimales
            tradeable = tick.get("tradeable", False)

            if tradeable:
                mid = (bid + ask) / 2
                print(f"{tick['time']} | {instrument}: {mid:.5f} spread={spread_pips:.1f}p")

            tick_count += 1
            if tick_count >= MAX_TICKS:
                r.terminate("max ticks reached")

        elif tick_type == "HEARTBEAT":
            # Heartbeat cada 5 segundos — confirma conexión activa
            pass

except StreamTerminated as e:
    print(f"Stream terminado: {e}")
```

### Flujo 6: Descarga Masiva de Velas Históricas

```python
from oandapyV20.contrib.factories import InstrumentsCandlesFactory
from oandapyV20 import API
import json, os

api = API(access_token="TOKEN", environment="practice")

INSTRUMENT = "EUR_USD"
GRANULARITY = "H4"
FROM_DATE = "2022-01-01T00:00:00Z"
TO_DATE = "2024-12-31T23:59:59Z"
BATCH_SIZE = 5000

params = {
    "from": FROM_DATE,
    "to": TO_DATE,
    "granularity": GRANULARITY,
    "count": BATCH_SIZE,
    "price": "MBA"
}

all_candles = []
for r in InstrumentsCandlesFactory(instrument=INSTRUMENT, params=params):
    api.request(r)
    batch = r.response.get("candles", [])
    all_candles.extend(batch)
    print(f"Descargadas: {len(all_candles)} velas...")

complete = [c for c in all_candles if c["complete"]]
output_path = f"/tmp/{INSTRUMENT}.{GRANULARITY}.json"
with open(output_path, "w") as f:
    json.dump(complete, f)
print(f"Total velas completas: {len(complete)} → {output_path}")
```

### Flujo 7: Reemplazar Limit Order

```python
import oandapyV20.endpoints.orders as orders
from oandapyV20.contrib.requests import LimitOrderRequest

# Crear orden original
lo = LimitOrderRequest(instrument="EUR_USD", units=-1000, price=1.20)
r = orders.OrderCreate(accountID, data=lo.data)
rv = api.request(r)
order_id = rv["orderCreateTransaction"]["id"]
print(f"Orden creada: {order_id}")

# Reemplazar con nuevo precio y unidades
r = orders.OrderReplace(accountID, orderID=order_id, data={
    "order": {
        "type": "LIMIT",
        "instrument": "EUR_USD",
        "units": "-500000",
        "price": "1.25000",
        "timeInForce": "GTC"
    }
})
rv = api.request(r)
new_order_id = rv["orderCreateTransaction"]["id"]
cancelled_id = rv["orderCancelTransaction"]["orderID"]
print(f"Reemplazada: {cancelled_id} → {new_order_id}")
```

### Flujo 8: Modificar SL/TP de Trade Existente (TradeCRCDO)

```python
import oandapyV20.endpoints.trades as trades

# Modificar TP y SL de un trade abierto
r = trades.TradeCRCDO(accountID, tradeID="1030", data={
    "takeProfit": {
        "timeInForce": "GTC",
        "price": "1.15000"
    },
    "stopLoss": {
        "timeInForce": "GTC",
        "price": "1.08000"
    }
})
rv = api.request(r)

# Cancelar solo el TP (mantener SL)
r = trades.TradeCRCDO(accountID, tradeID="1030", data={
    "takeProfit": {}   # objeto vacío = cancelar
})
```

---

## [SÍNTESIS DE EVIDENCIA] — Errores HTTP: Diagnóstico Completo

### Tabla de Errores HTTP

| Código | Nombre | Causas Comunes | Acción |
|--------|--------|----------------|--------|
| 400 | Bad Request | Parámetros inválidos, formato incorrecto, `PRECISION_EXCEEDED` | Verificar `errorMessage` y `rejectReason` en respuesta |
| 401 | Unauthorized | Token inválido/expirado, accountID incorrecto | Verificar token y URL del entorno |
| 403 | Forbidden | Account no tradeable, permisos insuficientes | Contactar soporte OANDA |
| 404 | Not Found | TradeID/OrderID/TransactionID inexistente | Verificar ID; puede haber expirado del listado reciente |
| 405 | Method Not Allowed | Método HTTP incorrecto (GET en lugar de POST, etc.) | Verificar verbo HTTP del endpoint |
| 500+ | Server Error | Error interno OANDA | Reintentar con backoff exponencial |

### Mensajes de Error Específicos

| Error Message | Causa | Solución |
|---------------|-------|----------|
| `"The request was missing required data"` | Parámetros requeridos ausentes o inválidos | Verificar campos requeridos del OrderRequest |
| `"Invalid value specified for 'instrument'"` | Formato de InstrumentName incorrecto | Usar formato `BASE_QUOTE` (ej: `EUR_USD`) |
| `"STOP_LOSS_ON_FILL_PRICE_PRECISION_EXCEEDED"` | Precio con más decimales que los permitidos | Redondear precio al `displayPrecision` del instrumento |
| `"The provided request was forbidden."` | Token inválido o accountID incorrecto | Verificar `Authorization: Bearer {token}` |
| `"Insufficient authorization to perform request."` | Token sin permisos suficientes | Verificar URL correcta (practice vs live) y token válido |
| `"The trade ID specified does not exist"` | TradeID no válido o expirado | Usar `OpenTrades` para obtener IDs actuales |
| `"The transaction ID specified does not exist"` | TransactionID no en lista reciente | Usar `TransactionIDRange` con rango explícito |
| `"The order ID specified does not exist"` | OrderID no en lista reciente | Usar `OrderList` con `state=ALL` para buscar |

### Patrón de Diagnóstico Completo

```python
import json
from oandapyV20.exceptions import V20Error

def safe_request(api, endpoint):
    """Ejecuta request con manejo completo de errores."""
    try:
        rv = api.request(endpoint)
        return rv, None
    except V20Error as e:
        error_info = {"code": e.code, "raw": e.msg}
        try:
            error_data = json.loads(e.msg)
            error_info["errorMessage"] = error_data.get("errorMessage", "")
            error_info["errorCode"] = error_data.get("errorCode", "")
            error_info["rejectReason"] = error_data.get("rejectReason", "")
            # Para rechazos de transacción
            if "orderRejectTransaction" in error_data:
                txn = error_data["orderRejectTransaction"]
                error_info["rejectReason"] = txn.get("rejectReason", "")
        except json.JSONDecodeError:
            pass

        if e.code == 400:
            print(f"[400] Parámetros inválidos: {error_info.get('errorMessage')}")
            print(f"      Reject reason: {error_info.get('rejectReason')}")
        elif e.code == 401:
            print(f"[401] No autorizado: {error_info.get('errorMessage')}")
        elif e.code == 403:
            print(f"[403] Prohibido: {error_info.get('errorMessage')}")
        elif e.code == 404:
            print(f"[404] No encontrado: {error_info.get('errorMessage')}")
        elif e.code == 405:
            print(f"[405] Método HTTP incorrecto")
        elif e.code >= 500:
            print(f"[{e.code}] Error del servidor — reintentar")
        return None, error_info
```

---

## [SÍNTESIS DE EVIDENCIA] — Casos Borde (Edge Cases)

### Restricciones Críticas

| Condición | Restricción / Comportamiento |
|-----------|------------------------------|
| `timeInForce=FOK` + unidades no disponibles | Orden cancelada inmediatamente |
| Market Order con `priceBound` | Si precio de mercado supera `priceBound` → cancelada |
| Stop Order: mercado hace gap cruzando `price` Y `priceBound` | Orden **cancelada** (no ejecutada) |
| `GSLO triggerCondition` inválido | Solo `DEFAULT` o lado natural → cualquier otro valor → REJECT |
| `price` y `distance` en mismo SL/GSLO request | Mutuamente excluyentes — especificar solo uno |
| Cuenta MT4 | NO modificar `clientExtensions` ni `tradeClientExtensions` |
| `marginCloseoutPercent >= 1.0` | Sistema crea Market Orders automáticos para cerrar posiciones |
| `units = 0` en TradeClose parcial | Resultado indefinido — usar `"ALL"` para cierre completo |
| `InstrumentsCandlesFactory` + `from`+`to`+`count` | `count` es tamaño de batch, no límite total |
| PricingStream con instrumento no tradeable | `tradeable=false` en tick; `closeoutBid/closeoutAsk` disponibles |
| PricingStream: max 4 ticks/segundo por instrumento | Períodos de movimiento rápido → no todos los precios se transmiten |
| PricingStream: ventanas de 250ms no sincronizadas | Distintos clientes pueden recibir precios diferentes en simultáneo |
| `count` sin `from`/`to` en velas | Retorna las `count` velas más recientes |
| `from` y `to` y `count` juntos en velas | `count` se ignora — el rango temporal determina las velas |
| `complete=false` en última vela | Vela en curso — no usar para señales de trading |
| OrderReplace devuelve HTTP 201 | No 200 — verificar `orderCreateTransaction.id` para nuevo ID |
| Stream heartbeat | Cada 5 segundos — si no llega en >10s → reconectar |
| `TradeSpecifier` con `@` | Prefijo `@` para buscar por `clientTradeID`, sin `@` es `TradeID` numérico |

### Variables de Estado para Monitoreo de Riesgo

```python
# Umbral de alerta progresiva:
# marginCloseoutPercent >= 0.5  → ADVERTENCIA
# marginCloseoutPercent >= 0.8  → ALERTA
# marginCloseoutPercent >= 1.0  → CRÍTICO (closeout activo)

# Capital disponible para nuevas posiciones:
# marginAvailable = capital disponible
# withdrawalLimit = límite máximo de retiro

# Cálculo de posición máxima:
# max_units = marginAvailable / (precio_actual * marginRate_instrumento)
```

---

## [SÍNTESIS DE EVIDENCIA] — Resumen Maestro de Endpoints

| Módulo | HTTP | Endpoint | Clase Python | Resp. |
|--------|------|---------|--------------|-------|
| Account | GET | `/v3/accounts` | `AccountList()` | 200 |
| Account | GET | `/v3/accounts/{id}` | `AccountDetails(accountID)` | 200 |
| Account | GET | `/v3/accounts/{id}/summary` | `AccountSummary(accountID)` | 200 |
| Account | GET | `/v3/accounts/{id}/instruments` | `AccountInstruments(accountID, params)` | 200 |
| Account | PATCH | `/v3/accounts/{id}/configuration` | `AccountConfiguration(accountID, data)` | 200 |
| Account | GET | `/v3/accounts/{id}/changes` | `AccountChanges(accountID, params)` | 200 |
| Order | POST | `/v3/accounts/{id}/orders` | `OrderCreate(accountID, data)` | **201** |
| Order | GET | `/v3/accounts/{id}/orders` | `OrderList(accountID, params)` | 200 |
| Order | GET | `/v3/accounts/{id}/pendingOrders` | `OrdersPending(accountID)` | 200 |
| Order | GET | `/v3/accounts/{id}/orders/{oid}` | `OrderDetails(accountID, orderID)` | 200 |
| Order | PUT | `/v3/accounts/{id}/orders/{oid}` | `OrderReplace(accountID, orderID, data)` | **201** |
| Order | PUT | `/v3/accounts/{id}/orders/{oid}/cancel` | `OrderCancel(accountID, orderID)` | 200 |
| Order | PUT | `/v3/accounts/{id}/orders/{oid}/clientExtensions` | `OrderClientExtensions(accountID, orderID, data)` | 200 |
| Trade | GET | `/v3/accounts/{id}/trades` | `TradesList(accountID, params)` | 200 |
| Trade | GET | `/v3/accounts/{id}/openTrades` | `OpenTrades(accountID)` | 200 |
| Trade | GET | `/v3/accounts/{id}/trades/{tid}` | `TradeDetails(accountID, tradeID)` | 200 |
| Trade | PUT | `/v3/accounts/{id}/trades/{tid}/close` | `TradeClose(accountID, tradeID, data)` | 200 |
| Trade | PUT | `/v3/accounts/{id}/trades/{tid}/clientExtensions` | `TradeClientExtensions(accountID, tradeID, data)` | 200 |
| Trade | PUT | `/v3/accounts/{id}/trades/{tid}/orders` | `TradeCRCDO(accountID, tradeID, data)` | 200 |
| Position | GET | `/v3/accounts/{id}/positions` | `PositionList(accountID)` | 200 |
| Position | GET | `/v3/accounts/{id}/openPositions` | `OpenPositions(accountID)` | 200 |
| Position | GET | `/v3/accounts/{id}/positions/{instr}` | `PositionDetails(accountID, instrument)` | 200 |
| Position | PUT | `/v3/accounts/{id}/positions/{instr}/close` | `PositionClose(accountID, instrument, data)` | 200 |
| Pricing | GET | `/v3/accounts/{id}/candles/latest` | `PricingInfo(accountID, params)` con `candleSpecifications` | 200 |
| Pricing | GET | `/v3/accounts/{id}/pricing` | `PricingInfo(accountID, params)` | 200 |
| Pricing | GET | `/v3/accounts/{id}/pricing/stream` **[STREAM]** | `PricingStream(accountID, params)` | 200 |
| Instrument | GET | `/v3/instruments/{instr}/candles` | `InstrumentsCandles(instrument, params)` | 200 |
| Instrument | GET | `/v3/instruments/{instr}/orderBook` | `InstrumentsOrderBook(instrument, params)` | 200 |
| Instrument | GET | `/v3/instruments/{instr}/positionBook` | `InstrumentsPositionBook(instrument, params)` | 200 |
| Transaction | GET | `/v3/accounts/{id}/transactions` | `TransactionList(accountID, params)` | 200 |
| Transaction | GET | `/v3/accounts/{id}/transactions/{tid}` | `TransactionDetails(accountID, transactionID)` | 200 |
| Transaction | GET | `/v3/accounts/{id}/transactions/idrange` | `TransactionIDRange(accountID, params)` | 200 |
| Transaction | GET | `/v3/accounts/{id}/transactions/sinceid` | `TransactionsSinceID(accountID, params)` | 200 |
| Transaction | GET | `/v3/accounts/{id}/transactions/stream` **[STREAM]** | `TransactionsStream(accountID)` | 200 |

> **STREAM endpoints:** Usar URL de streaming. Iterar con `for item in r`. Detener con `r.terminate("msg")`. Levanta `StreamTerminated` al detener. Heartbeat cada 5 segundos.

---

## [SÍNTESIS DE EVIDENCIA] — Template de Agente Base

```python
"""
Template base para agente de trading OANDA REST-V20
"""
import logging
from oandapyV20 import API
from oandapyV20.exceptions import V20Error, StreamTerminated
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.instruments as instruments
from oandapyV20.contrib.requests import (
    MarketOrderRequest, LimitOrderRequest, StopOrderRequest,
    TakeProfitDetails, StopLossDetails, TrailingStopLossDetails,
    TradeCloseRequest, PositionCloseRequest
)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Configuración
ACCESS_TOKEN = "your_token"
ACCOUNT_ID = "001-001-xxxxxxx-001"
ENVIRONMENT = "practice"  # "practice" | "live"

api = API(access_token=ACCESS_TOKEN, environment=ENVIRONMENT,
          request_params={"timeout": 10})


def get_account_state():
    """Retorna dict con estado actual del account."""
    r = accounts.AccountSummary(ACCOUNT_ID)
    rv = api.request(r)
    acc = rv["account"]
    return {
        "balance": float(acc["balance"]),
        "nav": float(acc["NAV"]),
        "unrealized_pl": float(acc["unrealizedPL"]),
        "margin_used": float(acc["marginUsed"]),
        "margin_available": float(acc["marginAvailable"]),
        "margin_closeout_pct": float(acc["marginCloseoutPercent"]),
        "open_trades": acc["openTradeCount"],
        "open_positions": acc["openPositionCount"],
    }


def open_market_order(instrument, units, tp_price=None, sl_price=None):
    """
    Abre Market Order. units > 0 = LONG, units < 0 = SHORT.
    Retorna tradeID si exitoso, None si falla.
    """
    kwargs = {"instrument": instrument, "units": units}
    if tp_price:
        kwargs["takeProfitOnFill"] = TakeProfitDetails(price=tp_price).data
    if sl_price:
        kwargs["stopLossOnFill"] = StopLossDetails(price=sl_price).data

    mo = MarketOrderRequest(**kwargs)
    r = orders.OrderCreate(ACCOUNT_ID, data=mo.data)
    try:
        rv = api.request(r)
        if "orderFillTransaction" in rv:
            trade_id = rv["orderFillTransaction"]["tradeOpened"]["tradeID"]
            fill_price = rv["orderFillTransaction"]["price"]
            logger.info(f"Trade abierto: {trade_id} @ {fill_price}")
            return trade_id
        else:
            logger.warning("Orden no se ejecutó inmediatamente")
            return None
    except V20Error as e:
        logger.error(f"Error abriendo orden: {e.code} — {e.msg}")
        return None


def close_trade(trade_id, units="ALL"):
    """Cierra trade (total o parcial). Retorna P&L realizado o None."""
    r = trades.TradeClose(ACCOUNT_ID, tradeID=str(trade_id),
                           data=TradeCloseRequest(units=units).data)
    try:
        rv = api.request(r)
        pl = rv["orderFillTransaction"]["pl"]
        logger.info(f"Trade {trade_id} cerrado. PnL: {pl}")
        return float(pl)
    except V20Error as e:
        logger.error(f"Error cerrando trade {trade_id}: {e.code} — {e.msg}")
        return None


def get_current_price(instrument):
    """Retorna (bid, ask, mid) actual para el instrumento."""
    r = pricing.PricingInfo(ACCOUNT_ID, params={"instruments": instrument})
    rv = api.request(r)
    price_data = rv["prices"][0]
    if not price_data.get("tradeable", False):
        return None, None, None
    bid = float(price_data["bids"][0]["price"])
    ask = float(price_data["asks"][0]["price"])
    mid = (bid + ask) / 2
    return bid, ask, mid


def get_candles(instrument, granularity="M5", count=100, price="M"):
    """Retorna lista de velas completas."""
    r = instruments.InstrumentsCandles(instrument, params={
        "count": count, "granularity": granularity, "price": price
    })
    rv = api.request(r)
    return [c for c in rv["candles"] if c["complete"]]


if __name__ == "__main__":
    state = get_account_state()
    logger.info(f"Account state: NAV={state['nav']} | "
                f"Margin closeout: {state['margin_closeout_pct']*100:.1f}%")

    bid, ask, mid = get_current_price("EUR_USD")
    if mid:
        logger.info(f"EUR_USD: bid={bid} ask={ask} mid={mid:.5f}")

    candles = get_candles("EUR_USD", granularity="H1", count=5)
    logger.info(f"Últimas 5 velas H1 EUR_USD:")
    for c in candles:
        logger.info(f"  {c['time']}: O={c['mid']['o']} H={c['mid']['h']} "
                    f"L={c['mid']['l']} C={c['mid']['c']}")
```
