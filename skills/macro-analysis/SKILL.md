---
name: macro-analysis
description: >
  Macro-economic regime analysis and cross-asset signal dashboard for equity investing.
  Use this skill whenever the user asks about the current macro environment, economic cycle phase,
  yield curve status, credit spreads, cross-asset signals, risk-on/risk-off assessment,
  Investment Clock positioning, recession probability, or any question connecting macroeconomic
  indicators to stock market outlook. Also trigger when the user mentions terms like
  "macro dashboard", "yield curve", "credit spread", "PMI", "NFCI", "M2", "financial conditions",
  "Investment Clock", "macro regime", "recession signal", "term spread", "copper gold ratio",
  or asks "what does the macro picture look like" / "should I be risk-on or risk-off".
  This skill combines EODHD MCP tools with FRED API data to produce a structured macro assessment.
---

# Macro Economic Analysis Skill

## Purpose

This skill enables Claude to perform a systematic macroeconomic regime assessment by:
1. Fetching real-time data from EODHD MCP and FRED API
2. Computing derived indicators (yield curve spreads, copper/gold ratio, etc.)
3. Classifying the current Investment Clock quadrant
4. Producing a cross-asset risk signal scorecard
5. Delivering an actionable macro briefing with key thresholds and warnings

## When to Use

Trigger this skill for any question about macroeconomic conditions and their investment implications.
Typical user queries include:
- "What's the current macro regime?"
- "Show me the yield curve and credit spread status"
- "Are we in a risk-on or risk-off environment?"
- "What phase of the Investment Clock are we in?"
- "Give me a macro dashboard update"
- "What are recession signals saying right now?"
- "How do macro indicators look for equities?"

Do NOT trigger for questions about individual stock fundamentals, earnings analysis,
or portfolio construction that don't require macro context.

## Workflow

Follow these steps IN ORDER. Each step builds on the previous one.

### Step 1: Gather Data

Fetch data in parallel where possible. Read `references/data-sources.md` for the exact
tool calls and FRED API endpoints to use for each indicator.

**From EODHD MCP (use MCP tools directly):**
- US Treasury yield curve: `get_ust_yield_rates` → extract 3M, 2Y, 10Y tenors
- US Treasury real yields: `get_ust_real_yield_rates` → extract 10Y real yield
- Cross-asset prices via `get_historical_stock_prices` (last 60 trading days):
  - Gold: `GC.COMM` or `GLD.US`
  - Copper: `HG.COMM` or `CPER.US`
  - Oil (WTI): `CL.COMM` or `USO.US`
  - USD Index: `UUP.US` (dollar bull ETF as DXY proxy)
  - AUD/JPY: `AUDJPY.FOREX`
  - S&P 500: `GSPC.INDX`
  - VIX: `VIX.INDX`
- Economic events calendar: `get_economic_events` with country=US for recent PMI/ISM readings

**From FRED API (use bash curl or web_fetch):**
The user's FRED API key should be provided in conversation or stored in environment.
If no API key is available, skip FRED indicators and note the gap.

- HY credit spread (OAS): series `BAMLH0A0HYM2`
- IG credit spread (OAS): series `BAMLC0A0CM`
- Chicago Fed NFCI: series `NFCI`
- M2 money supply: series `WM2NS` (weekly) or `M2SL` (monthly)
- Initial jobless claims: series `ICSA`
- Conference Board LEI: series `USSLIND`
- Fed Funds Rate: series `DFF`

FRED API call format:
```
https://api.stlouisfed.org/fred/series/observations?series_id={SERIES_ID}&api_key={KEY}&file_type=json&sort_order=desc&limit=60
```

### Step 2: Compute Derived Indicators

Calculate these from raw data:

| Indicator | Formula | Source |
|-----------|---------|--------|
| 10Y-2Y spread | 10Y yield − 2Y yield | EODHD yield rates |
| 10Y-3M spread | 10Y yield − 3M yield | EODHD yield rates |
| Copper/Gold ratio | Copper price / Gold price (indexed) | EODHD historical prices |
| Copper/Gold ratio trend | 20-day vs 60-day moving average of ratio | Computed |
| M2 YoY growth rate | (current M2 / M2 12 months ago) − 1 | FRED M2 |
| VIX term structure | Compare VIX spot to VIX3M if available, or note current level | EODHD |

### Step 3: Classify Macro Regime (Investment Clock)

Use the Investment Clock framework to classify the current phase:

**Inputs needed:**
- Growth signal: ISM PMI level and direction (from economic events or FRED)
- Inflation signal: Most recent CPI YoY reading direction (from economic events)

**Classification rules:**
- **Reflation** (low growth + low inflation): PMI < 50 and declining, CPI trending down
  → Bonds outperform. Favor: financials, consumer staples, healthcare
- **Recovery** (high growth + low inflation): PMI > 50 and rising, CPI still moderate
  → Equities outperform. Favor: tech, consumer discretionary, materials
- **Overheat** (high growth + high inflation): PMI > 50, CPI rising above 3%
  → Commodities outperform. Favor: energy, industrials, materials
- **Stagflation** (low growth + high inflation): PMI < 50 or declining, CPI sticky above 3%
  → Cash outperforms. Favor: utilities, healthcare, consumer staples

If data is insufficient for confident classification, state "Transitional / uncertain"
and explain which signals conflict.

### Step 4: Cross-Asset Signal Scorecard

Rate each signal as 🟢 Risk-On, 🟡 Neutral, or 🔴 Risk-Off:

| Signal | Risk-On | Neutral | Risk-Off |
|--------|---------|---------|----------|
| Yield curve (10Y-2Y) | > +50bp steepening | 0 to +50bp | Inverted (< 0) |
| HY credit spread | < 350bp | 350-500bp | > 500bp |
| Copper/Gold ratio | Rising (20d > 60d MA) | Flat | Falling (20d < 60d MA) |
| USD (UUP) | Weakening trend | Flat | Strengthening trend |
| AUD/JPY | Rising | Flat | Falling |
| VIX | < 16 | 16-25 | > 25 |
| NFCI | < -0.5 (loose) | -0.5 to 0 | > 0 (tight) |
| Fed Funds direction | Cutting | Holding | Hiking |

**Composite score**: Count 🟢 minus 🔴.
- Score ≥ +4: Strong Risk-On
- +1 to +3: Mild Risk-On
- -1 to +1: Neutral / Mixed
- -2 to -3: Mild Risk-Off
- ≤ -4: Strong Risk-Off

### Step 5: Key Threshold Alerts

Flag any of these critical conditions:
- ⚠️ Yield curve inverted (10Y-3M < 0) for 3+ months → elevated recession risk
- ⚠️ HY OAS > 500bp → credit stress regime
- ⚠️ VIX > 30 → acute fear
- ⚠️ NFCI > 0 → financial conditions tightening beyond average
- ⚠️ M2 YoY growth negative → liquidity contraction
- ⚠️ Initial claims 4-week average rising > 10% from trough → labor market deterioration

### Step 6: Output Format

Present the analysis as a structured briefing:

```
## 📊 Macro Regime Assessment — [Date]

### Current Phase: [Reflation / Recovery / Overheat / Stagflation / Transitional]
[1-2 sentence summary of why this classification]

### Key Indicators
| Indicator | Current Value | Signal | Threshold/Context |
|-----------|--------------|--------|-------------------|
| 10Y-2Y spread | +XXbp | 🟢/🟡/🔴 | ... |
| 10Y-3M spread | +XXbp | 🟢/🟡/🔴 | ... |
| HY OAS | XXXbp | 🟢/🟡/🔴 | <350 / 350-500 / >500 |
| ... | ... | ... | ... |

### Cross-Asset Scorecard
Composite: X/8 signals Risk-On → [Strong Risk-On / Mild Risk-On / Neutral / ...]

### ⚠️ Threshold Alerts
[List any active alerts, or "No critical thresholds breached"]

### Investment Clock Implications
[2-3 sentences on sector/asset allocation implications based on current phase]

### Data Gaps & Caveats
[Note any indicators that couldn't be fetched and how that affects confidence]
```

## Important Notes

- Always state the date of the data being analyzed
- All macro analysis is informational — never present as investment advice
- If FRED API key is not available, the analysis can still run with EODHD data alone,
  but note that credit spreads, NFCI, and M2 will be missing (reduces confidence)
- For PMI/ISM, prefer the most recent `get_economic_events` reading over stale annual data
- The copper/gold ratio interpretation has weakened since 2023 due to structural factors
  (central bank gold buying, green transition copper demand) — caveat this in output
- VIX term structure backwardation (near-term VIX > longer-term) is a stronger fear signal
  than VIX level alone

## Reference Files

- `references/data-sources.md` — Detailed API call examples and ticker mappings
- `references/indicator-thresholds.md` — Historical context for each threshold
