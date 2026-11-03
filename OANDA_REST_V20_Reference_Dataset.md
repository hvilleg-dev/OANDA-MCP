# OANDA REST-V20 API — Dataset de Referencia para Agentes Programadores

> **Fuente:** oandapyV20 REST-V20 API Documentation v0.6.3 + developer.oanda.com live definitions  
> **Entornos:** `practice` → `https://api-fxpractice.oanda.com` | `live` → `https://api-fxtrade.oanda.com`  
> **Autenticación:** Bearer Token en header `Authorization: Bearer {access_token}`

---

## [NÚCLEO ONTOLÓGICO] — Primitivos y Tipos Base

### Glosario Técnico de Tipos Primitivos

| Tipo | Formato | Ejemplo |
|------|---------|---------|
| `AccountID` | `"{siteID}-{divisionID}-{userID}-{accountNumber}"` | `001-011-5838423-001` |
| `TransactionID` | Integer string positivo | `"2304"` |
| `OrderID` | Integer string positivo (derivado de TransactionID) | `"1523"` |
| `TradeID` | Integer string positivo (derivado de TransactionID que abrió el trade) | `"1523"` |
| `InstrumentName` | `"{base}_{quote}"` (ISO 4217) | `"EUR_USD"`, `"DE30_EUR"` |
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
| `RequestID` | String | identificador de request HTTP |

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

### Instrumento — Schema Completo

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

> **Cálculo pip:** $\text{pip\_decimal\_position} = 10^{\text{pipLocation}}$  
> Si `pipLocation = -4` → pip = $10^{-4} = 0.0001$

#### `InstrumentCommission`
```json
{
  "commission": "(DecimalNumber)",
  "unitsTraded": "(DecimalNumber)",
  "minimumCommission": "(DecimalNumber)"
}
```

#### `InstrumentFinancing`
```json
{
  "longRate": "(DecimalNumber)",
  "shortRate": "(DecimalNumber)",
  "financingDaysOfWeek": "(Array[FinancingDayOfWeek])"
}
```
- `longRate` / `shortRate`: fracción decimal (5% → `0.05`)

#### `GuaranteedStopLossOrderLevelRestriction`
```json
{
  "volume": "(DecimalNumber)",
  "priceRange": "(DecimalNumber)"
}
```

#### Conversión de Moneda

**`HomeConversionFactors`**
```json
{
  "gainQuoteHome": { "factor": "(DecimalNumber)" },
  "lossQuoteHome": { "factor": "(DecimalNumber)" },
  "gainBaseHome":  { "factor": "(DecimalNumber)" },
  "lossBaseHome":  { "factor": "(DecimalNumber)" }
}
```

$$\text{amount\_home} = \text{amount\_foreign} \times \text{factor}$$

---

## [NÚCLEO ONTOLÓGICO] — Account Definitions

### Axiomas de Account

> `NAV = balance + unrealizedPL`  
> `marginCloseoutPercent ≥ 1.0` → estado de **margin closeout**  
> `marginCallPercent ≥ 1.0` → estado de **margin call**

### Account (Schema Completo)

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

### AccountSummary
Schema idéntico al `Account` pero sin arrays `trades`, `positions`, `orders`.

### AccountChangesState (estado dinámico)
Subset de campos de Account más:
```json
{
  "orders": "(Array[DynamicOrderState])",
  "trades": "(Array[CalculatedTradeState])",
  "positions": "(Array[CalculatedPositionState])"
}
```

### AccountChanges
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

### Enums de Account

#### `GuaranteedStopLossOrderMode`
| Valor | Comportamiento |
|-------|---------------|
| `DISABLED` | No se permite crear GSLO |
| `ALLOWED` | GSLO opcional para trades abiertos |
| `REQUIRED` | GSLO obligatorio para todos los trades abiertos |

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

---

## [NÚCLEO ONTOLÓGICO] — Order Definitions

### Axiomas de Órdenes

> **MARKET**: se ejecuta inmediatamente al precio de mercado vigente  
> **LIMIT**: se ejecuta solo si precio ≤ threshold (long) o ≥ threshold (short)  
> **STOP**: se ejecuta solo si precio ≥ threshold (long) o ≤ threshold (short) — dirección opuesta a LIMIT  
> **TAKE_PROFIT / STOP_LOSS / TRAILING_STOP_LOSS**: no abren posiciones nuevas; solo cierran trades existentes  
> **`units > 0`** → orden LONG; **`units < 0`** → orden SHORT

### Tipos de Órdenes (`OrderType`)

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

### `CancellableOrderType`
Solo pueden cancelarse: `LIMIT`, `STOP`, `MARKET_IF_TOUCHED`, `TAKE_PROFIT`, `STOP_LOSS`, `GUARANTEED_STOP_LOSS`, `TRAILING_STOP_LOSS`

### `OrderState`

| Valor | Condición |
|-------|-----------|
| `PENDING` | Orden en espera de ejecución |
| `FILLED` | Orden ejecutada completamente |
| `TRIGGERED` | Orden activada (MIT orders) |
| `CANCELLED` | Orden cancelada |

### `TimeInForce`

| Valor | Descripción | Aplica a |
|-------|-------------|----------|
| `GTC` | Good unTil Cancelled | LIMIT, STOP, MIT, TP, SL, TSL |
| `GTD` | Good unTil Date (requiere `gtdTime`) | LIMIT, STOP, MIT, TP, SL, TSL |
| `GFD` | Good For Day (cancela 5pm NY) | LIMIT, STOP, MIT, TP, SL, TSL |
| `FOK` | Fill Or Kill (inmediato o cancela) | MARKET (default) |
| `IOC` | Immediately partial fill Or Cancel | MARKET |

### `OrderPositionFill`

| Valor | Comportamiento al llenar |
|-------|------------------------|
| `OPEN_ONLY` | Solo abre o extiende posición existente |
| `REDUCE_FIRST` | Primero reduce posición existente, luego abre nueva |
| `REDUCE_ONLY` | Solo reduce posición existente |
| `DEFAULT` | `REDUCE_FIRST` para cuentas sin hedging; `OPEN_ONLY` para cuentas con hedging |

### `OrderTriggerCondition`

| Valor | Comparación de precio |
|-------|----------------------|
| `DEFAULT` | Ask para órdenes long; Bid para órdenes short |
| `INVERSE` | Bid para órdenes long; Ask para órdenes short |
| `BID` | Siempre compara con Bid |
| `ASK` | Siempre compara con Ask |
| `MID` | Siempre compara con Midpoint |

> **Restricción GSLO:** `triggerCondition` solo acepta `DEFAULT` o el lado "natural" del DEFAULT. Long GSLO: `DEFAULT` o `BID`. Short GSLO: `DEFAULT` o `ASK`.

---

## [LÓGICA PROCEDIMENTAL] — Schemas de Órdenes (Objects)

### Order (Base)
```json
{
  "id": "(OrderID)",
  "createTime": "(DateTime)",
  "state": "(OrderState)",
  "clientExtensions": "(ClientExtensions)"
}
```

### MarketOrder
```json
{
  "id": "(OrderID)", "createTime": "(DateTime)", "state": "(OrderState)",
  "clientExtensions": "(ClientExtensions)",
  "type": "MARKET",
  "instrument": "(InstrumentName)",
  "units": "(DecimalNumber)",
  "timeInForce": "(TimeInForce: FOK|IOC)",
  "priceBound": "(PriceValue)",
  "positionFill": "(OrderPositionFill)",
  "tradeClose": "(MarketOrderTradeClose)",
  "longPositionCloseout": "(MarketOrderPositionCloseout)",
  "shortPositionCloseout": "(MarketOrderPositionCloseout)",
  "marginCloseout": "(MarketOrderMarginCloseout)",
  "delayedTradeClose": "(MarketOrderDelayedTradeClose)",
  "takeProfitOnFill": "(TakeProfitDetails)",
  "stopLossOnFill": "(StopLossDetails)",
  "guaranteedStopLossOnFill": "(GuaranteedStopLossDetails)",
  "trailingStopLossOnFill": "(TrailingStopLossDetails)",
  "tradeClientExtensions": "(ClientExtensions)",
  "fillingTransactionID": "(TransactionID)",
  "filledTime": "(DateTime)",
  "tradeOpenedID": "(TradeID)",
  "tradeReducedID": "(TradeID)",
  "tradeClosedIDs": "(Array[TradeID])",
  "cancellingTransactionID": "(TransactionID)",
  "cancelledTime": "(DateTime)"
}
```

### LimitOrder
```json
{
  "id": "(OrderID)", "createTime": "(DateTime)", "state": "(OrderState)",
  "clientExtensions": "(ClientExtensions)",
  "type": "LIMIT",
  "instrument": "(InstrumentName)",
  "units": "(DecimalNumber)",
  "price": "(PriceValue)",
  "timeInForce": "(TimeInForce: GTC|GTD|GFD)",
  "gtdTime": "(DateTime)",
  "positionFill": "(OrderPositionFill)",
  "triggerCondition": "(OrderTriggerCondition)",
  "takeProfitOnFill": "(TakeProfitDetails)",
  "stopLossOnFill": "(StopLossDetails)",
  "guaranteedStopLossOnFill": "(GuaranteedStopLossDetails)",
  "trailingStopLossOnFill": "(TrailingStopLossDetails)",
  "tradeClientExtensions": "(ClientExtensions)",
  "fillingTransactionID": "(TransactionID)", "filledTime": "(DateTime)",
  "tradeOpenedID": "(TradeID)", "tradeReducedID": "(TradeID)",
  "tradeClosedIDs": "(Array[TradeID])",
  "cancellingTransactionID": "(TransactionID)", "cancelledTime": "(DateTime)",
  "replacesOrderID": "(OrderID)", "replacedByOrderID": "(OrderID)"
}
```

### StopOrder
```json
{
  "type": "STOP",
  "instrument": "(InstrumentName)",
  "units": "(DecimalNumber)",
  "price": "(PriceValue)",
  "priceBound": "(PriceValue)",
  "timeInForce": "(TimeInForce: GTC|GTD|GFD)",
  "gtdTime": "(DateTime)",
  "positionFill": "(OrderPositionFill)",
  "triggerCondition": "(OrderTriggerCondition)",
  "takeProfitOnFill": "(TakeProfitDetails)",
  "stopLossOnFill": "(StopLossDetails)",
  "guaranteedStopLossOnFill": "(GuaranteedStopLossDetails)",
  "trailingStopLossOnFill": "(TrailingStopLossDetails)",
  "tradeClientExtensions": "(ClientExtensions)",
  "replacesOrderID": "(OrderID)", "replacedByOrderID": "(OrderID)"
}
```
> Si mercado hace gap cruzando `price` Y `priceBound` → orden **cancelada** en lugar de ejecutarse.

### MarketIfTouchedOrder (MIT)
```json
{
  "type": "MARKET_IF_TOUCHED",
  "instrument": "(InstrumentName)",
  "units": "(DecimalNumber)",
  "price": "(PriceValue)",
  "priceBound": "(PriceValue)",
  "timeInForce": "(TimeInForce: GTC|GTD|GFD)",
  "gtdTime": "(DateTime)",
  "positionFill": "(OrderPositionFill)",
  "triggerCondition": "(OrderTriggerCondition)",
  "initialMarketPrice": "(PriceValue)",
  "takeProfitOnFill": "(TakeProfitDetails)",
  "stopLossOnFill": "(StopLossDetails)",
  "guaranteedStopLossOnFill": "(GuaranteedStopLossDetails)",
  "trailingStopLossOnFill": "(TrailingStopLossDetails)",
  "tradeClientExtensions": "(ClientExtensions)",
  "replacesOrderID": "(OrderID)", "replacedByOrderID": "(OrderID)"
}
```
> Comportamiento: si `price > initialMarketPrice` → actúa como STOP; si `price < initialMarketPrice` → actúa como LIMIT.

### TakeProfitOrder
```json
{
  "type": "TAKE_PROFIT",
  "tradeID": "(TradeID)",
  "clientTradeID": "(ClientID)",
  "price": "(PriceValue)",
  "timeInForce": "(TimeInForce: GTC|GTD|GFD)",
  "gtdTime": "(DateTime)",
  "triggerCondition": "(OrderTriggerCondition)",
  "replacesOrderID": "(OrderID)", "replacedByOrderID": "(OrderID)"
}
```

### StopLossOrder
```json
{
  "type": "STOP_LOSS",
  "tradeID": "(TradeID)",
  "clientTradeID": "(ClientID)",
  "price": "(PriceValue)",
  "distance": "(DecimalNumber)",
  "timeInForce": "(TimeInForce: GTC|GTD|GFD)",
  "gtdTime": "(DateTime)",
  "triggerCondition": "(OrderTriggerCondition)",
  "replacesOrderID": "(OrderID)", "replacedByOrderID": "(OrderID)"
}
```
> `price` y `distance` son mutuamente excluyentes. Si Trade es short: distancia desde Bid. Si Trade es long: distancia desde Ask.

### GuaranteedStopLossOrder (GSLO)
```json
{
  "type": "GUARANTEED_STOP_LOSS",
  "tradeID": "(TradeID)",
  "clientTradeID": "(ClientID)",
  "price": "(PriceValue)",
  "distance": "(DecimalNumber)",
  "timeInForce": "(TimeInForce: GTC|GTD|GFD)",
  "gtdTime": "(DateTime)",
  "triggerCondition": "(OrderTriggerCondition)",
  "guaranteedExecutionPremium": "(DecimalNumber)",
  "replacesOrderID": "(OrderID)", "replacedByOrderID": "(OrderID)"
}
```
> `guaranteedExecutionPremium`: cobro en price units por cada unidad del trade. Sin slippage garantizado.

### TrailingStopLossOrder
```json
{
  "type": "TRAILING_STOP_LOSS",
  "tradeID": "(TradeID)",
  "clientTradeID": "(ClientID)",
  "distance": "(DecimalNumber)",
  "timeInForce": "(TimeInForce: GTC|GTD|GFD)",
  "gtdTime": "(DateTime)",
  "triggerCondition": "(OrderTriggerCondition)",
  "trailingStopValue": "(PriceValue)"
}
```
> `trailingStopValue` sigue al precio ganador manteniendo distancia `distance`. Si precio toca `trailingStopValue` → trade se cierra.

### FixedPriceOrder
```json
{
  "type": "FIXED_PRICE",
  "instrument": "(InstrumentName)",
  "units": "(DecimalNumber)",
  "price": "(PriceValue)",
  "positionFill": "(OrderPositionFill)",
  "tradeState": "(string)",
  "takeProfitOnFill": "(TakeProfitDetails)",
  "stopLossOnFill": "(StopLossDetails)",
  "guaranteedStopLossOnFill": "(GuaranteedStopLossDetails)",
  "trailingStopLossOnFill": "(TrailingStopLossDetails)",
  "tradeClientExtensions": "(ClientExtensions)"
}
```

### DynamicOrderState (solo TrailingStopLoss)
```json
{
  "id": "(OrderID)",
  "trailingStopValue": "(PriceValue)",
  "triggerDistance": "(PriceValue)",
  "isTriggerDistanceExact": "(boolean)"
}
```

### UnitsAvailable
```json
{
  "default":     { "long": "(DecimalNumber)", "short": "(DecimalNumber)" },
  "reduceFirst": { "long": "(DecimalNumber)", "short": "(DecimalNumber)" },
  "reduceOnly":  { "long": "(DecimalNumber)", "short": "(DecimalNumber)" },
  "openOnly":    { "long": "(DecimalNumber)", "short": "(DecimalNumber)" }
}
```

---

## [LÓGICA PROCEDIMENTAL] — Order Requests (creación)

### MarketOrderRequest
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

### LimitOrderRequest
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

### StopOrderRequest
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

### MarketIfTouchedOrderRequest
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

### TakeProfitOrderRequest
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

### StopLossOrderRequest
```json
{
  "order": {
    "type": "STOP_LOSS",
    "tradeID": "(TradeID, required)",
    "clientTradeID": "(ClientID)",
    "price": "(PriceValue, required — OR use distance)",
    "distance": "(DecimalNumber — OR use price)",
    "timeInForce": "(GTC|GTD|GFD, default=GTC)",
    "gtdTime": "(DateTime)",
    "triggerCondition": "(OrderTriggerCondition, default=DEFAULT)",
    "clientExtensions": "(ClientExtensions)"
  }
}
```

### GuaranteedStopLossOrderRequest
```json
{
  "order": {
    "type": "GUARANTEED_STOP_LOSS",
    "tradeID": "(TradeID, required)",
    "clientTradeID": "(ClientID)",
    "price": "(PriceValue, required — OR use distance)",
    "distance": "(DecimalNumber — OR use price)",
    "timeInForce": "(GTC|GTD|GFD, default=GTC)",
    "gtdTime": "(DateTime)",
    "triggerCondition": "(OrderTriggerCondition, default=DEFAULT)",
    "clientExtensions": "(ClientExtensions)"
  }
}
```

### TrailingStopLossOrderRequest
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

---

## [LÓGICA PROCEDIMENTAL] — Trade Definitions

### Trade (Schema Completo)
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

### TradeSummary
Schema idéntico a `Trade` pero en lugar de objetos de órdenes completos, contiene IDs:
```json
{
  "takeProfitOrderID": "(OrderID)",
  "stopLossOrderID": "(OrderID)",
  "guaranteedStopLossOrderID": "(OrderID)",
  "trailingStopLossOrderID": "(OrderID)"
}
```

### CalculatedTradeState
```json
{
  "id": "(TradeID)",
  "unrealizedPL": "(AccountUnits)",
  "marginUsed": "(AccountUnits)"
}
```

### TradeState
| Valor | Condición |
|-------|-----------|
| `OPEN` | Trade activo, `currentUnits > 0` |
| `CLOSED` | Trade completamente cerrado, `currentUnits = 0` |
| `CLOSE_WHEN_TRADEABLE` | Se cerrará cuando el instrumento vuelva a ser tradeable |

### TradePL
| Valor | Condición |
|-------|-----------|
| `POSITIVE` | `unrealizedPL > 0` o `realizedPL > 0` |
| `NEGATIVE` | `unrealizedPL < 0` o `realizedPL < 0` |
| `ZERO` | `unrealizedPL = 0` o `realizedPL = 0` |

---

## [LÓGICA PROCEDIMENTAL] — Position Definitions

### Position
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

### PositionSide
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
> `averagePrice` = VWAP (Volume-Weighted Average Price) de los trades abiertos en esa dirección.

$$\text{averagePrice} = \frac{\sum_{i} (\text{price}_i \times |\text{units}_i|)}{\sum_{i} |\text{units}_i|}$$

### CalculatedPositionState
```json
{
  "instrument": "(InstrumentName)",
  "netUnrealizedPL": "(AccountUnits)",
  "longUnrealizedPL": "(AccountUnits)",
  "shortUnrealizedPL": "(AccountUnits)",
  "marginUsed": "(AccountUnits)"
}
```

---

## [LÓGICA PROCEDIMENTAL] — Pricing Definitions

### ClientPrice
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

### PriceBucket
```json
{
  "price": "(PriceValue)",
  "liquidity": "(integer or decimal)"
}
```

### PricingHeartbeat
```json
{
  "type": "HEARTBEAT",
  "time": "(DateTime)"
}
```

### QuoteHomeConversionFactors (deprecated)
```json
{
  "positiveUnits": "(DecimalNumber)",
  "negativeUnits": "(DecimalNumber)"
}
```

### HomeConversions
```json
{
  "currency": "(Currency)",
  "accountGain": "(DecimalNumber)",
  "accountLoss": "(DecimalNumber)",
  "positionValue": "(DecimalNumber)"
}
```

### `PriceStatus`
| Valor | Estado |
|-------|--------|
| `tradeable` | Precio ejecutable |
| `non-tradeable` | Precio no ejecutable |
| `invalid` | Instrumento inválido o sin precio |

### CandleSpecification (string format)
```
"{InstrumentName}:{CandlestickGranularity}:{PricingComponent}"
```
Ejemplo: `"EUR_USD:S10:BM"` → EUR_USD, 10 segundos, Bid+Mid

### `PricingComponent` (string combinable)
| Char | Tipo de Vela |
|------|-------------|
| `M` | Midpoint (mid) |
| `B` | Bid |
| `A` | Ask |

### `CandlestickGranularity` (completo)
| Valor | Período |
|-------|---------|
| `S5` | 5 segundos |
| `S10` | 10 segundos |
| `S15` | 15 segundos |
| `S30` | 30 segundos |
| `M1` | 1 minuto |
| `M2` | 2 minutos |
| `M4` | 4 minutos |
| `M5` | 5 minutos |
| `M10` | 10 minutos |
| `M15` | 15 minutos |
| `M30` | 30 minutos |
| `H1` | 1 hora |
| `H2` | 2 horas |
| `H3` | 3 horas |
| `H4` | 4 horas |
| `H6` | 6 horas |
| `H8` | 8 horas |
| `H12` | 12 horas |
| `D` | 1 día (alineado diario) |
| `W` | 1 semana (alineado semanal) |
| `M` | 1 mes |

---

## [LÓGICA PROCEDIMENTAL] — Transaction Definitions

### Transaction (Base)
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

### MarketOrderTransaction (Schema Key)
Extiende `Transaction` con:
```json
{
  "type": "MARKET_ORDER",
  "instrument": "(InstrumentName)",
  "units": "(DecimalNumber)",
  "timeInForce": "(FOK|IOC)",
  "priceBound": "(PriceValue)",
  "positionFill": "(OrderPositionFill)",
  "tradeClose": "(MarketOrderTradeClose)",
  "longPositionCloseout": "(MarketOrderPositionCloseout)",
  "shortPositionCloseout": "(MarketOrderPositionCloseout)",
  "marginCloseout": "(MarketOrderMarginCloseout)",
  "delayedTradeClose": "(MarketOrderDelayedTradeClose)",
  "reason": "(MarketOrderReason)",
  "clientExtensions": "(ClientExtensions)",
  "takeProfitOnFill": "(TakeProfitDetails)",
  "stopLossOnFill": "(StopLossDetails)",
  "trailingStopLossOnFill": "(TrailingStopLossDetails)",
  "guaranteedStopLossOnFill": "(GuaranteedStopLossDetails)",
  "tradeClientExtensions": "(ClientExtensions)"
}
```

### LimitOrderTransaction (Schema Key)
Extiende `Transaction` con:
```json
{
  "type": "LIMIT_ORDER",
  "instrument": "(InstrumentName)",
  "units": "(DecimalNumber)",
  "price": "(PriceValue)",
  "timeInForce": "(TimeInForce)",
  "gtdTime": "(DateTime)",
  "positionFill": "(OrderPositionFill)",
  "triggerCondition": "(OrderTriggerCondition)",
  "reason": "(LimitOrderReason)",
  "clientExtensions": "(ClientExtensions)",
  "takeProfitOnFill": "(TakeProfitDetails)",
  "stopLossOnFill": "(StopLossDetails)",
  "trailingStopLossOnFill": "(TrailingStopLossDetails)",
  "guaranteedStopLossOnFill": "(GuaranteedStopLossDetails)",
  "tradeClientExtensions": "(ClientExtensions)",
  "replacesOrderID": "(OrderID)",
  "cancellingTransactionID": "(TransactionID)"
}
```

### OrderFillTransaction
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

### OrderCancelTransaction
```json
{
  "type": "ORDER_CANCEL",
  "orderID": "(OrderID)",
  "clientOrderID": "(ClientID)",
  "reason": "(OrderCancelReason)",
  "replacedByOrderID": "(OrderID)"
}
```

### ClientConfigureTransaction
```json
{
  "type": "CLIENT_CONFIGURE",
  "alias": "(string)",
  "marginRate": "(DecimalNumber)"
}
```

### TransferFundsTransaction
```json
{
  "type": "TRANSFER_FUNDS",
  "amount": "(AccountUnits)",
  "fundingReason": "(FundingReason)",
  "comment": "(string)",
  "accountBalance": "(AccountUnits)"
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

### `LimitOrderReason` / `StopOrderReason` / `MarketIfTouchedOrderReason`
| Valor | Origen |
|-------|--------|
| `CLIENT_ORDER` | Orden del cliente |
| `REPLACEMENT` | Reemplaza otra orden |

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

### `OrderCancelReason` (parcial — causas comunes)
| Valor | Causa |
|-------|-------|
| `CLIENT_REQUEST` | Cancelación manual |
| `CLIENT_REQUEST_REPLACED` | Reemplazada por otra orden |
| `TIME_IN_FORCE_EXPIRED` | TIF expirado |
| `LINKED_TRADE_CLOSED` | Trade vinculado se cerró |
| `MARKET_HALTED` | Mercado detenido |
| `INSUFFICIENT_MARGIN` | Margen insuficiente |
| `INSUFFICIENT_LIQUIDITY` | Liquidez insuficiente |
| `BOUNDS_VIOLATION` | Precio fuera de límites (Stop con priceBound) |
| `LOSING_TAKE_PROFIT` | Take profit resultaría en pérdida |

### `FundingReason`
| Valor | Descripción |
|-------|-------------|
| `CLIENT_FUNDING` | Fondos del cliente |
| `ACCOUNT_TRANSFER` | Transferencia entre cuentas |
| `DIVISION_MIGRATION` | Migración de división |
| `SITE_MIGRATION` | Migración de sitio |
| `ADJUSTMENT` | Ajuste |

### `TransactionRejectReason` (errores de validación comunes)
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

## [LÓGICA PROCEDIMENTAL] — oandapyV20 Python SDK

### Instalación

```bash
pip install oandapyV20
# o desde source:
pip install git+https://github.com/hootnot/oanda-api-v20.git
```

### Cliente API

```python
from oandapyV20 import API

# Inicialización
api = API(
    access_token="your_token_here",
    environment="practice",   # "practice" | "live"
    headers=None,             # dict opcional de headers adicionales
    request_params={"timeout": 10}  # parámetros requests (timeout, etc.)
)

# Ejecución de request
rv = api.request(endpoint_instance)
# rv es dict con respuesta JSON
# endpoint_instance.response también contiene la respuesta
```

### Excepciones

```python
from oandapyV20.exceptions import V20Error

try:
    rv = api.request(r)
except V20Error as e:
    print(e.code)   # HTTP status code (>= 400)
    print(e.msg)    # mensaje de error
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

```python
import oandapyV20.endpoints.accounts as accounts

# GET /v3/accounts
r = accounts.AccountList()

# GET /v3/accounts/{accountID}
r = accounts.AccountDetails(accountID)

# GET /v3/accounts/{accountID}/summary
r = accounts.AccountSummary(accountID)

# GET /v3/accounts/{accountID}/instruments
r = accounts.AccountInstruments(accountID, params={"instruments": "EUR_USD,DE30_EUR"})

# PATCH /v3/accounts/{accountID}/configuration
r = accounts.AccountConfiguration(accountID, data={"marginRate": "0.05"})

# GET /v3/accounts/{accountID}/changes
r = accounts.AccountChanges(accountID, params={"sinceTransactionID": "2308"})
```

**Patrón de uso:**
```python
rv = api.request(r)
print(r.response)  # equivalente a rv
```

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Orders

```python
import oandapyV20.endpoints.orders as orders

# POST /v3/accounts/{accountID}/orders — HTTP 201 esperado
r = orders.OrderCreate(accountID, data={
    "order": {
        "type": "MARKET",
        "instrument": "EUR_USD",
        "units": "10000",
        "timeInForce": "FOK",
        "positionFill": "DEFAULT"
    }
})

# GET /v3/accounts/{accountID}/orders
r = orders.OrderList(accountID, params={"state": "PENDING"})

# GET /v3/accounts/{accountID}/pendingOrders
r = orders.OrdersPending(accountID)

# GET /v3/accounts/{accountID}/orders/{orderID}
r = orders.OrderDetails(accountID, orderID="2304")

# PUT /v3/accounts/{accountID}/orders/{orderID} — HTTP 201
r = orders.OrderReplace(accountID, orderID="2304", data={
    "order": {"type": "LIMIT", "instrument": "EUR_USD", "units": "-500000", "price": "1.25000"}
})

# PUT /v3/accounts/{accountID}/orders/{orderID}/cancel
r = orders.OrderCancel(accountID, orderID="2304")

# PUT /v3/accounts/{accountID}/orders/{orderID}/clientExtensions
r = orders.OrderClientExtensions(accountID, orderID="2304", data={
    "clientExtensions": {"comment": "myComment", "id": "myID"}
})
```

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Trades

```python
import oandapyV20.endpoints.trades as trades

# GET /v3/accounts/{accountID}/trades
r = trades.TradesList(accountID, params={"instrument": "EUR_USD", "state": "OPEN"})

# GET /v3/accounts/{accountID}/openTrades
r = trades.OpenTrades(accountID)

# GET /v3/accounts/{accountID}/trades/{tradeID}
r = trades.TradeDetails(accountID, tradeID="1030")

# PUT /v3/accounts/{accountID}/trades/{tradeID}/close
# Cierre total:
r = trades.TradeClose(accountID, tradeID="1030")
# Cierre parcial:
r = trades.TradeClose(accountID, tradeID="1030", data={"units": "5"})

# PUT /v3/accounts/{accountID}/trades/{tradeID}/clientExtensions
r = trades.TradeClientExtensions(accountID, tradeID="1030", data={
    "clientExtensions": {"id": "myID2315", "comment": "myComment"}
})

# PUT /v3/accounts/{accountID}/trades/{tradeID}/orders
# Crear/Reemplazar/Cancelar órdenes dependientes (TakeProfit + StopLoss)
r = trades.TradeCRCDO(accountID, tradeID="1030", data={
    "takeProfit": {"timeInForce": "GTC", "price": "1.10"},
    "stopLoss": {"timeInForce": "GTC", "price": "1.05"}
})
```

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Positions

```python
import oandapyV20.endpoints.positions as positions

# GET /v3/accounts/{accountID}/positions
r = positions.PositionList(accountID)

# GET /v3/accounts/{accountID}/openPositions
r = positions.OpenPositions(accountID)

# GET /v3/accounts/{accountID}/positions/{instrument}
r = positions.PositionDetails(accountID, instrument="EUR_USD")

# PUT /v3/accounts/{accountID}/positions/{instrument}/close
# Cierre total long:
r = positions.PositionClose(accountID, instrument="EUR_USD",
                             data={"longUnits": "ALL"})
# Cierre parcial short:
r = positions.PositionClose(accountID, instrument="EUR_USD",
                             data={"shortUnits": "100"})
# Cierre ambas direcciones:
r = positions.PositionClose(accountID, instrument="EUR_USD",
                             data={"longUnits": "ALL", "shortUnits": "ALL"})
```

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Pricing

```python
import oandapyV20.endpoints.pricing as pricing

# GET /v3/accounts/{accountID}/pricing
r = pricing.PricingInfo(accountID, params={"instruments": "EUR_USD,EUR_JPY"})

# GET /v3/accounts/{accountID}/pricing/stream (STREAMING)
r = pricing.PricingStream(accountID, params={"instruments": "EUR_USD,EUR_JPY"})
rv = api.request(r)
maxrecs = 100
for tick in r:
    # tick es dict con type="PRICE" o type="HEARTBEAT"
    if tick.get("type") == "PRICE":
        process(tick)
    maxrecs -= 1
    if maxrecs == 0:
        r.terminate("limit reached")
```

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Instruments

```python
import oandapyV20.endpoints.instruments as instruments

# GET /v3/instruments/{instrument}/candles
r = instruments.InstrumentsCandles(
    instrument="EUR_USD",
    params={"count": 5, "granularity": "M5"}
)

# GET /v3/instruments/{instrument}/orderBook
r = instruments.InstrumentsOrderBook(instrument="EUR_USD")

# GET /v3/instruments/{instrument}/positionBook
r = instruments.InstrumentsPositionBook(instrument="EUR_USD")
```

#### Parámetros de Velas
```python
params = {
    "count": 5,                          # número de velas (default 500, max depende de granularidad)
    "granularity": "M5",                 # CandlestickGranularity
    "price": "MBA",                      # PricingComponent: M=mid, B=bid, A=ask (combinable)
    "from": "2017-01-01T00:00:00Z",      # DateTime inicio
    "to": "2017-12-31T23:59:59Z",        # DateTime fin
    "smooth": False,                      # suavizado de velas
    "includeFirst": True,                 # incluir primera vela del rango
    "dailyAlignment": 17,                # hora de alineación diaria (0-23)
    "alignmentTimezone": "America/New_York",
    "weeklyAlignment": "Friday"          # WeeklyAlignment
}
```

#### Schema de respuesta de vela
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

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: Transactions

```python
import oandapyV20.endpoints.transactions as transactions

# GET /v3/accounts/{accountID}/transactions
r = transactions.TransactionList(accountID, params={"pageSize": 200})

# GET /v3/accounts/{accountID}/transactions/{transactionID}
r = transactions.TransactionDetails(accountID, transactionID="2304")

# GET /v3/accounts/{accountID}/transactions/idrange
r = transactions.TransactionIDRange(accountID, params={"from": "2304", "to": "2306"})

# GET /v3/accounts/{accountID}/transactions/sinceid
r = transactions.TransactionsSinceID(accountID, params={"id": "2306"})

# GET /v3/accounts/{accountID}/transactions/stream (STREAMING)
r = transactions.TransactionsStream(accountID)
rv = api.request(r)
for T in r:
    # T es dict con type="TRANSACTION" o type="HEARTBEAT"
    process(T)
```

---

## [LÓGICA PROCEDIMENTAL] — Endpoints: ForexLabs

```python
import oandapyV20.endpoints.forexlabs as labs

# GET labs/v1/signal/autochartist
r = labs.Autochartist(params={"instrument": "EUR_JPY"})

# GET labs/v1/calendar
r = labs.Calendar(params={"instrument": "EUR_USD", "period": 86400})

# GET labs/v1/commitments_of_traders
r = labs.CommitmentsOfTraders(params={"instrument": "EUR_USD"})

# GET labs/v1/historical_position_ratios
r = labs.HistoricalPositionRatios(params={"instrument": "EUR_USD", "period": 86400})

# GET labs/v1/orderbook_data
r = labs.OrderbookData(params={"instrument": "EUR_USD", "period": 3600})

# GET labs/v1/spreads
r = labs.Spreads(params={"instrument": "EUR_USD", "period": 57600})
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
```

### MarketOrderRequest

```python
mo = MarketOrderRequest(
    instrument="EUR_USD",
    units=10000,            # positivo=LONG, negativo=SHORT
    priceBound=None,        # PriceValue opcional
    positionFill="DEFAULT",
    timeInForce="FOK",
    clientExtensions=None,
    takeProfitOnFill=None,
    stopLossOnFill=None,
    trailingStopLossOnFill=None,
    tradeClientExtensions=None
)
r = orders.OrderCreate(accountID, data=mo.data)
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
# lo.data contiene el JSON listo para OrderCreate
```

### StopOrderRequest

```python
so = StopOrderRequest(
    instrument="EUR_USD",
    units=10000,
    price=1.07,
    priceBound=None,
    positionFill="DEFAULT",
    timeInForce="GTC",
    gtdTime=None,
    stopLossOnFill=None,
    takeProfitOnFill=None,
    trailingStopLossOnFill=None,
    tradeClientExtensions=None,
    clientExtensions=None
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
    timeInForce="GTC",
    gtdTime=None,
    stopLossOnFill=None,
    takeProfitOnFill=None,
    trailingStopLossOnFill=None,
    tradeClientExtensions=None,
    clientExtensions=None
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
```

### StopLossOrderRequest

```python
sl = StopLossOrderRequest(
    tradeID="1234",
    price=1.07,
    clientTradeID=None,
    timeInForce="GTC",
    gtdTime=None,
    clientExtensions=None
)
```

### TrailingStopLossOrderRequest

```python
tsl = TrailingStopLossOrderRequest(
    tradeID="1234",
    distance=20,            # price units de distancia
    clientTradeID=None,
    timeInForce="GTC",
    gtdTime=None,
    clientExtensions=None
)
```

### TradeCloseRequest

```python
tc = TradeCloseRequest(units="ALL")      # cierre total
tc = TradeCloseRequest(units=5000)       # cierre parcial
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
# Especificación inline al crear una orden (se ejecuta si la orden se llena)
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

client = API(access_token="...")
instrument, granularity = "EUR_USD", "M15"
params = {
    "from": "2017-01-01T00:00:00Z",
    "granularity": granularity,
    "count": 2500,    # velas por request batch
}

with open("/tmp/EUR_USD.M15.json", "w") as OUT:
    for r in InstrumentsCandlesFactory(instrument=instrument, params=params):
        client.request(r)
        OUT.write(json.dumps(r.response.get("candles"), indent=2))
```

> **Lógica interna:** calcula automáticamente el número total de velas entre `from` y `to` (o `now`), genera múltiples requests consecutivos de `count` velas cada uno. Fuerza `includeFirst=True` para evitar gaps de 1 registro entre batches.

---

## [LÓGICA PROCEDIMENTAL] — contrib.generic

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

---

## [LÓGICA PROCEDIMENTAL] — Tipos del SDK (oandapyV20.types)

```python
from oandapyV20.types import (
    AccountID, AccountUnits, ClientComment, ClientID, ClientTag,
    DateTime, OrderID, OrderIdentifier, OrderSpecifier, PriceValue,
    TradeID, Units
)

# Siempre retornan string representation; validan el valor de entrada
pv = PriceValue(1.23456)        # → pv.value = "1.23456"
pv = PriceValue("1.23456")     # → pv.value = "1.23456"

oid = OrderID(1234)             # → oid.value = "1234"
tid = TradeID(1234)             # → tid.value = "1234"
u   = Units(10000)              # → u.value = "10000"

# DateTime acepta: RFC3339 string, dict de partes, o datetime.datetime
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

---

## [LÓGICA PROCEDIMENTAL] — Definitions (oandapyV20.definitions)

```python
# Acceso a definiciones con descripción textual
import oandapyV20.definitions.orders as deforders
import oandapyV20.definitions.accounts as defaccounts
import oandapyV20.definitions.instruments as definstruments
import oandapyV20.definitions.pricing as defpricing
import oandapyV20.definitions.trades as deftrades
import oandapyV20.definitions.transactions as deftransactions

# Obtener valor constante
deforders.OrderType.MARKET          # → "MARKET"
deforders.TimeInForce.GTC           # → "GTC"
deforders.OrderState.CANCELLED      # → "CANCELLED"

# Obtener descripción de un valor
c = deforders.OrderType()
c[c.MARKET]                         # → "A Market Order"

# Listar todas las claves
deforders.OrderPositionFill().definitions.keys()

# CandlestickGranularity
definstruments.CandlestickGranularity.H4      # → "H4"
c = definstruments.CandlestickGranularity()
c[c.H4]                                        # → "4 hour candlesticks, day alignment"
```

---

## [SÍNTESIS DE EVIDENCIA] — Flujos Operativos Completos

### Flujo 1: Abrir Posición LONG con TP y SL

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
    print(f"Trade abierto: {trade_id}")
except V20Error as e:
    print(f"Error {e.code}: {e.msg}")
```

### Flujo 2: Listar Trades Abiertos y Cerrar Parcialmente

```python
import oandapyV20.endpoints.trades as trades
from oandapyV20.contrib.requests import TradeCloseRequest

# Listar trades abiertos
r = trades.OpenTrades(accountID)
rv = api.request(r)
trade_ids = [t["id"] for t in rv["trades"]]

# Cerrar 5 unidades del primer trade
r = trades.TradeClose(accountID, tradeID=trade_ids[0],
                       data=TradeCloseRequest(units=5).data)
rv = api.request(r)
print(f"P&L realizado: {rv['orderFillTransaction']['pl']}")
```

### Flujo 3: Cerrar Posición Completa

```python
import oandapyV20.endpoints.positions as positions
from oandapyV20.contrib.requests import PositionCloseRequest

r = positions.PositionClose(
    accountID,
    instrument="EUR_USD",
    data=PositionCloseRequest(longUnits="ALL").data
)
rv = api.request(r)
```

### Flujo 4: Monitoreo de Precio en Tiempo Real

```python
import oandapyV20.endpoints.pricing as pricing
from oandapyV20.exceptions import StreamTerminated

r = pricing.PricingStream(accountID, params={"instruments": "EUR_USD"})
api.request(r)

maxrecs = 50
try:
    for tick in r:
        if tick.get("type") == "PRICE" and tick.get("tradeable"):
            bid = tick["bids"][0]["price"]
            ask = tick["asks"][0]["price"]
            mid = (float(bid) + float(ask)) / 2
            print(f"EUR_USD: bid={bid} ask={ask} mid={mid:.5f}")
        maxrecs -= 1
        if maxrecs == 0:
            r.terminate("limit reached")
except StreamTerminated as e:
    print(f"Stream terminado: {e}")
```

### Flujo 5: Consultar Estado de Account y Calcular Leverage

```python
import oandapyV20.endpoints.accounts as accounts

r = accounts.AccountSummary(accountID)
rv = api.request(r)
acc = rv["account"]

balance = float(acc["balance"])
nav = float(acc["NAV"])
margin_used = float(acc["marginUsed"])
margin_closeout_pct = float(acc["marginCloseoutPercent"])

# Leverage efectivo aproximado
leverage = margin_used / nav if nav > 0 else 0

# Estado de riesgo
if margin_closeout_pct >= 1.0:
    print("ALERTA: Margin Closeout activo")
elif margin_closeout_pct >= 0.5:
    print("ADVERTENCIA: Margin Closeout al 50%")
```

### Flujo 6: Reemplazar Limit Order

```python
import oandapyV20.endpoints.orders as orders

# Crear orden original
lo = LimitOrderRequest(instrument="EUR_USD", units=-100, price=1.20)
r = orders.OrderCreate(accountID, data=lo.data)
rv = api.request(r)
order_id = rv["orderCreateTransaction"]["id"]

# Reemplazar con nuevo precio
r = orders.OrderReplace(
    accountID,
    orderID=order_id,
    data={"order": {"type": "LIMIT", "instrument": "EUR_USD",
                    "units": "-500000", "price": "1.25000"}}
)
rv = api.request(r)
new_order_id = rv["orderCreateTransaction"]["id"]
cancelled_order_id = rv["orderCancelTransaction"]["orderID"]
```

### Flujo 7: Descarga Histórico de Velas en Lote

```python
from oandapyV20.contrib.factories import InstrumentsCandlesFactory
import json

params = {
    "from": "2020-01-01T00:00:00Z",
    "to": "2020-12-31T23:59:59Z",
    "granularity": "H1",
    "count": 5000,
    "price": "MBA"
}

all_candles = []
for r in InstrumentsCandlesFactory(instrument="EUR_USD", params=params):
    api.request(r)
    all_candles.extend(r.response.get("candles", []))

print(f"Total velas descargadas: {len(all_candles)}")
```

---

## [SÍNTESIS DE EVIDENCIA] — Casos Borde (Edge Cases)

### Restricciones Críticas

| Condición | Restricción / Comportamiento |
|-----------|------------------------------|
| `timeInForce=FOK` + `units` no disponibles | Orden cancelada inmediatamente |
| Market Order con `priceBound` | Si precio de mercado supera `priceBound` → cancelada |
| Stop Order: mercado hace gap cruzando `price` Y `priceBound` | Orden cancelada (no ejecutada) |
| `GSLO triggerCondition` inválido | Solo acepta `DEFAULT` o lado natural; cualquier otro valor → REJECT |
| `price` y `distance` en misma SL/GSLO Request | Mutuamente excluyentes; especificar solo uno |
| Cuenta MT4 | NO modificar `clientExtensions` ni `tradeClientExtensions` |
| `marginCloseoutPercent >= 1.0` | Sistema crea Market Orders automáticos para cerrar posiciones |
| `units = 0` en TradeClose parcial | Resultado indefinido; usar `"ALL"` para cierre completo |
| InstrumentsCandlesFactory + `from`+`to`+`count` | `count` se usa como tamaño de batch, no como límite total |
| PricingStream con instrumento no tradeable | Tick con `tradeable=false`; `closeoutBid/closeoutAsk` disponibles para margin closeout |

### Errores Comunes y Diagnóstico

```python
# V20Error con código 400 → parámetros inválidos (revisar TransactionRejectReason)
# V20Error con código 401 → token inválido o expirado
# V20Error con código 404 → accountID, orderID, tradeID inexistente
# V20Error con código 422 → regla de negocio violada (ej: precio de SL > precio de entry para long)

# Patrón de diagnóstico
try:
    rv = api.request(r)
except V20Error as e:
    if e.code == 400:
        import json
        err_data = json.loads(e.msg)
        print(f"Razón de rechazo: {err_data.get('errorMessage')}")
    elif e.code == 404:
        print("Recurso no encontrado")
    elif e.code >= 500:
        print("Error del servidor OANDA — reintentar con backoff")
```

### Variables de Estado Clave para Monitoreo

```python
# Variables que indican riesgo de closeout inminente:
# marginCloseoutPercent >= 0.8 → zona de alerta
# marginCloseoutPercent >= 1.0 → closeout activo

# Variables para cálculo de margen libre:
# marginAvailable = capital disponible para nuevas posiciones
# withdrawalLimit = límite máximo de retiro

# Fórmulas de margen:
# margin_requerido = notional_value * marginRate
# notional_value = units * price_actual
# leverage = 1 / marginRate
```

---

## [SÍNTESIS DE EVIDENCIA] — Resumen de Endpoints por Módulo

| Módulo | Endpoint | HTTP | Clase Python |
|--------|---------|------|-------------|
| Account | `GET /v3/accounts` | 200 | `AccountList()` |
| Account | `GET /v3/accounts/{id}` | 200 | `AccountDetails(accountID)` |
| Account | `GET /v3/accounts/{id}/summary` | 200 | `AccountSummary(accountID)` |
| Account | `GET /v3/accounts/{id}/instruments` | 200 | `AccountInstruments(accountID)` |
| Account | `PATCH /v3/accounts/{id}/configuration` | 200 | `AccountConfiguration(accountID, data)` |
| Account | `GET /v3/accounts/{id}/changes` | 200 | `AccountChanges(accountID, params)` |
| Order | `POST /v3/accounts/{id}/orders` | **201** | `OrderCreate(accountID, data)` |
| Order | `GET /v3/accounts/{id}/orders` | 200 | `OrderList(accountID, params)` |
| Order | `GET /v3/accounts/{id}/pendingOrders` | 200 | `OrdersPending(accountID)` |
| Order | `GET /v3/accounts/{id}/orders/{oid}` | 200 | `OrderDetails(accountID, orderID)` |
| Order | `PUT /v3/accounts/{id}/orders/{oid}` | **201** | `OrderReplace(accountID, orderID, data)` |
| Order | `PUT /v3/accounts/{id}/orders/{oid}/cancel` | 200 | `OrderCancel(accountID, orderID)` |
| Order | `PUT /v3/accounts/{id}/orders/{oid}/clientExtensions` | 200 | `OrderClientExtensions(accountID, orderID, data)` |
| Trade | `GET /v3/accounts/{id}/trades` | 200 | `TradesList(accountID, params)` |
| Trade | `GET /v3/accounts/{id}/openTrades` | 200 | `OpenTrades(accountID)` |
| Trade | `GET /v3/accounts/{id}/trades/{tid}` | 200 | `TradeDetails(accountID, tradeID)` |
| Trade | `PUT /v3/accounts/{id}/trades/{tid}/close` | 200 | `TradeClose(accountID, tradeID, data)` |
| Trade | `PUT /v3/accounts/{id}/trades/{tid}/clientExtensions` | 200 | `TradeClientExtensions(accountID, tradeID, data)` |
| Trade | `PUT /v3/accounts/{id}/trades/{tid}/orders` | 200 | `TradeCRCDO(accountID, tradeID, data)` |
| Position | `GET /v3/accounts/{id}/positions` | 200 | `PositionList(accountID)` |
| Position | `GET /v3/accounts/{id}/openPositions` | 200 | `OpenPositions(accountID)` |
| Position | `GET /v3/accounts/{id}/positions/{instr}` | 200 | `PositionDetails(accountID, instrument)` |
| Position | `PUT /v3/accounts/{id}/positions/{instr}/close` | 200 | `PositionClose(accountID, instrument, data)` |
| Pricing | `GET /v3/accounts/{id}/pricing` | 200 | `PricingInfo(accountID, params)` |
| Pricing | `GET /v3/accounts/{id}/pricing/stream` | 200 | `PricingStream(accountID, params)` [STREAM] |
| Instrument | `GET /v3/instruments/{instr}/candles` | 200 | `InstrumentsCandles(instrument, params)` |
| Instrument | `GET /v3/instruments/{instr}/orderBook` | 200 | `InstrumentsOrderBook(instrument, params)` |
| Instrument | `GET /v3/instruments/{instr}/positionBook` | 200 | `InstrumentsPositionBook(instrument, params)` |
| Transaction | `GET /v3/accounts/{id}/transactions` | 200 | `TransactionList(accountID, params)` |
| Transaction | `GET /v3/accounts/{id}/transactions/{tid}` | 200 | `TransactionDetails(accountID, transactionID)` |
| Transaction | `GET /v3/accounts/{id}/transactions/idrange` | 200 | `TransactionIDRange(accountID, params)` |
| Transaction | `GET /v3/accounts/{id}/transactions/sinceid` | 200 | `TransactionsSinceID(accountID, params)` |
| Transaction | `GET /v3/accounts/{id}/transactions/stream` | 200 | `TransactionsStream(accountID)` [STREAM] |
| ForexLabs | `GET labs/v1/signal/autochartist` | 200 | `Autochartist(params)` |
| ForexLabs | `GET labs/v1/calendar` | 200 | `Calendar(params)` |
| ForexLabs | `GET labs/v1/commitments_of_traders` | 200 | `CommitmentsOfTraders(params)` |
| ForexLabs | `GET labs/v1/historical_position_ratios` | 200 | `HistoricalPositionRatios(params)` |
| ForexLabs | `GET labs/v1/orderbook_data` | 200 | `OrderbookData(params)` |
| ForexLabs | `GET labs/v1/spreads` | 200 | `Spreads(params)` |

> **STREAM endpoints**: retornan un generador. Iterar con `for item in r`. Detener con `r.terminate("msg")`. Levanta `StreamTerminated` al detener.

---

## [SÍNTESIS DE EVIDENCIA] — Respuestas Típicas de Referencia

### OrderCreate (MARKET) — Respuesta exitosa (HTTP 201)
```json
{
  "orderCreateTransaction": {
    "type": "MARKET_ORDER",
    "id": "2503",
    "batchID": "2503",
    "timeInForce": "FOK",
    "instrument": "EUR_USD",
    "units": "10000",
    "positionFill": "DEFAULT",
    "reason": "CLIENT_ORDER",
    "time": "2016-11-11T19:59:43.253587917Z",
    "accountID": "101-004-1435156-001",
    "userID": 1435156
  },
  "orderFillTransaction": {
    "type": "ORDER_FILL",
    "id": "2504",
    "orderID": "2503",
    "batchID": "2503",
    "instrument": "EUR_USD",
    "units": "10000",
    "price": "1.08463",
    "pl": "0.0000",
    "financing": "0.0000",
    "accountBalance": "97864.8813",
    "reason": "MARKET_ORDER",
    "tradeOpened": { "tradeID": "2504", "units": "10000" },
    "time": "2016-11-11T19:59:43.253587917Z"
  },
  "relatedTransactionIDs": ["2503", "2504"],
  "lastTransactionID": "2504"
}
```

### TradeClose (parcial) — Respuesta exitosa
```json
{
  "orderCreateTransaction": {
    "type": "MARKET_ORDER",
    "id": "1041",
    "instrument": "DE30_EUR",
    "units": "5",
    "timeInForce": "FOK",
    "reason": "TRADE_CLOSE"
  },
  "orderFillTransaction": {
    "type": "ORDER_FILL",
    "id": "1042",
    "price": "10131.6",
    "pl": "14.0000",
    "financing": "-0.1519",
    "accountBalance": "44876.2548",
    "tradeReduced": {
      "tradeID": "1030",
      "units": "5",
      "realizedPL": "14.0000",
      "financing": "-0.1519"
    }
  },
  "relatedTransactionIDs": ["1041", "1042"],
  "lastTransactionID": "1042"
}
```

### PricingInfo — Respuesta
```json
{
  "prices": [
    {
      "instrument": "EUR_USD",
      "tradeable": true,
      "time": "2016-10-05T05:28:16.729643492Z",
      "bids": [
        {"price": "1.12157", "liquidity": 10000000},
        {"price": "1.12155", "liquidity": 10000000}
      ],
      "asks": [
        {"price": "1.12170", "liquidity": 10000000},
        {"price": "1.12172", "liquidity": 10000000}
      ],
      "closeoutBid": "1.12153",
      "closeoutAsk": "1.12174"
    }
  ]
}
```

### TransactionList — Respuesta (paginada)
```json
{
  "count": 2124,
  "from": "2016-06-24T21:03:50.914647476Z",
  "to": "2016-10-05T06:54:14.025946546Z",
  "pageSize": 100,
  "lastTransactionID": "2124",
  "pages": [
    "https://api-fxpractice.oanda.com/v3/accounts/.../transactions/idrange?from=1&to=100",
    "..."
  ]
}
```
