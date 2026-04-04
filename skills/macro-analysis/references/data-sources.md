# Data Sources Reference

Exact tool calls and API endpoints for each macro indicator.

## Table of Contents
1. [EODHD MCP Tools](#eodhd-mcp-tools)
2. [FRED API Endpoints](#fred-api-endpoints)
3. [Ticker Mapping Table](#ticker-mapping-table)
4. [Data Freshness & Update Schedules](#data-freshness)

---

## EODHD MCP Tools

### 1. US Treasury Yield Curve

**Tool:** `get_ust_yield_rates`
**Parameters:** `year` = current year (e.g., 2026), `limit` = 200
**Returns:** Array of `{date, tenor, rate}` objects.
**Tenors available:** 1M, 1.5M, 2M, 3M, 4M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y

**Extraction logic:**
```
For the most recent date in the response:
  - rate_3M = tenor "3M"
  - rate_2Y = tenor "2Y"
  - rate_10Y = tenor "10Y"
  - spread_10Y_2Y = rate_10Y - rate_2Y  (in basis points × 100)
  - spread_10Y_3M = rate_10Y - rate_3M
```

### 2. US Treasury Real Yield Rates (TIPS)

**Tool:** `get_ust_real_yield_rates`
**Parameters:** `year` = current year, `limit` = 100
**Returns:** Array of `{date, tenor, rate}`. Tenors: 5Y, 7Y, 10Y, 20Y, 30Y
**Extract:** Most recent 10Y real yield rate.

### 3. Cross-Asset Prices (Historical)

**Tool:** `get_historical_stock_prices`
**Parameters:** `ticker`, `start_date` = 90 days ago, `period` = "d", `fmt` = "json"

Fetch the following tickers:

| Asset | Ticker | Notes |
|-------|--------|-------|
| Gold | `GLD.US` | SPDR Gold ETF; alternative `GC.COMM` |
| Copper | `CPER.US` | United States Copper ETF; alternative `HG.COMM` |
| WTI Oil | `CL.COMM` | Crude Oil WTI futures; alternative `USO.US` |
| USD proxy | `UUP.US` | Invesco DB USD Index Bull Fund |
| AUD/JPY | `AUDJPY.FOREX` | Direct forex cross rate |
| S&P 500 | `GSPC.INDX` | S&P 500 index |
| VIX | `VIX.INDX` | CBOE Volatility Index |

**Copper/Gold Ratio calculation:**
```
For each overlapping date:
  ratio = CPER_close / GLD_close
Calculate 20-day and 60-day simple moving averages of ratio.
If 20d MA > 60d MA → Rising (Risk-On)
If 20d MA < 60d MA → Falling (Risk-Off)
```

**AUD/JPY trend:**
```
Compare current AUD/JPY to 20-day moving average.
Above → Risk-On; Below → Risk-Off
```

**USD (UUP) trend:**
```
Compare current UUP to 20-day moving average.
Above (strengthening) → Risk-Off; Below (weakening) → Risk-On
```

### 4. Economic Events Calendar

**Tool:** `get_economic_events`
**Parameters:**
- `country` = "US"
- `start_date` = 60 days ago
- `end_date` = today
- `limit` = 100

**What to look for:**
- Events containing "ISM" or "PMI" in the name → extract `actual` value
- Events containing "CPI" → extract `actual` value and YoY comparison
- Events containing "Fed" and "Rate" → extract rate decision
- Events containing "Initial Jobless Claims" → as backup if FRED unavailable

### 5. VIX Live Price

**Tool:** `get_live_price_data`
**Parameters:** `ticker` = "VIX.INDX"
**Returns:** Current/delayed VIX level.

---

## FRED API Endpoints

Base URL: `https://api.stlouisfed.org/fred/series/observations`

Common parameters for all calls:
```
api_key={FRED_API_KEY}
file_type=json
sort_order=desc
limit=60
```

### Series Reference

| Indicator | Series ID | Frequency | Description |
|-----------|-----------|-----------|-------------|
| HY OAS | `BAMLH0A0HYM2` | Daily | ICE BofA US HY Option-Adjusted Spread |
| IG OAS | `BAMLC0A0CM` | Daily | ICE BofA US Corporate Master OAS |
| NFCI | `NFCI` | Weekly | Chicago Fed National Financial Conditions Index |
| M2 (weekly) | `WM2NS` | Weekly | M2 Money Stock, Not Seasonally Adjusted |
| M2 (monthly) | `M2SL` | Monthly | M2 Money Stock, Seasonally Adjusted |
| Initial Claims | `ICSA` | Weekly | Initial Claims, Seasonally Adjusted |
| LEI | `USSLIND` | Monthly | Conference Board Leading Economic Index |
| Fed Funds Rate | `DFF` | Daily | Effective Federal Funds Rate |
| CPI YoY | `CPIAUCSL` | Monthly | CPI for All Urban Consumers (use for YoY calc) |

### Example FRED curl calls

```bash
# HY credit spread
curl -s "https://api.stlouisfed.org/fred/series/observations?series_id=BAMLH0A0HYM2&api_key=${FRED_API_KEY}&file_type=json&sort_order=desc&limit=5"

# NFCI
curl -s "https://api.stlouisfed.org/fred/series/observations?series_id=NFCI&api_key=${FRED_API_KEY}&file_type=json&sort_order=desc&limit=10"

# M2 for YoY growth (need 14 months of monthly data)
curl -s "https://api.stlouisfed.org/fred/series/observations?series_id=M2SL&api_key=${FRED_API_KEY}&file_type=json&sort_order=desc&limit=14"
```

### FRED Response Format

```json
{
  "observations": [
    {
      "date": "2026-03-27",
      "value": "3.42"
    }
  ]
}
```

Note: `value` is always a string. Parse to float. Value of `"."` means data not available.

---

## Ticker Mapping Table

Quick reference for all tickers used in the analysis:

| Purpose | Primary Ticker | Fallback Ticker | Source |
|---------|---------------|-----------------|--------|
| 10Y Yield | via get_ust_yield_rates | — | EODHD UST API |
| 2Y Yield | via get_ust_yield_rates | — | EODHD UST API |
| 3M Yield | via get_ust_yield_rates | — | EODHD UST API |
| 10Y Real Yield | via get_ust_real_yield_rates | — | EODHD UST API |
| Gold | `GLD.US` | `GC.COMM` | EODHD EOD |
| Copper | `CPER.US` | `HG.COMM` | EODHD EOD |
| WTI Oil | `CL.COMM` | `USO.US` | EODHD EOD |
| USD Index | `UUP.US` | `DX-Y.NYB` | EODHD EOD |
| AUD/JPY | `AUDJPY.FOREX` | — | EODHD EOD |
| S&P 500 | `GSPC.INDX` | `SPY.US` | EODHD EOD |
| VIX | `VIX.INDX` | — | EODHD EOD/Live |
| HY Spread | `BAMLH0A0HYM2` | HYG.US vs TLT.US ratio | FRED / EODHD |
| IG Spread | `BAMLC0A0CM` | LQD.US vs TLT.US ratio | FRED / EODHD |
| NFCI | `NFCI` | — | FRED only |
| M2 | `M2SL` / `WM2NS` | — | FRED only |
| Initial Claims | `ICSA` | econ events calendar | FRED / EODHD |
| LEI | `USSLIND` | — | FRED only |
| Fed Funds | `DFF` | interest_rate macro indicator | FRED / EODHD |

---

## Data Freshness

| Data Type | Update Frequency | Typical Lag |
|-----------|-----------------|-------------|
| UST yield rates | Daily | T+0 (same day) |
| UST real yield rates | Daily | T+0 |
| EOD stock/ETF/forex prices | Daily | T+0 after market close |
| FRED HY/IG OAS | Daily | T+1 |
| FRED NFCI | Weekly (Wednesday) | ~3 days |
| FRED M2 | Weekly/Monthly | 1-2 weeks |
| FRED Initial Claims | Weekly (Thursday) | T+0 |
| FRED LEI | Monthly | ~3 weeks after month end |
| EODHD Economic Events | As published | Real-time |
