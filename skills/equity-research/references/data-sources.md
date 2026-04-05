# Data Sources Reference

## Table of Contents
1. [Company Fundamentals](#1-company-fundamentals)
2. [Price & Technical Data](#2-price--technical-data)
3. [Earnings & Analyst Estimates](#3-earnings--analyst-estimates)
4. [Sentiment & News](#4-sentiment--news)
5. [Insider & Institutional](#5-insider--institutional)
6. [Macro & Rates](#6-macro--rates)
7. [ESG](#7-esg)
8. [Risk Scoring (Praams)](#8-risk-scoring-praams)
9. [Bank-Specific Financials](#9-bank-specific-financials)
10. [Corporate Events Calendar](#10-corporate-events-calendar)
11. [Options](#11-options)
12. [Index Data](#12-index-data)
13. [FRED API Patterns](#13-fred-api-patterns)

---

## 1. Company Fundamentals

**Primary endpoint**: `get_fundamentals_data(ticker, ...)`

### Sections Parameter Options
Use `sections` to limit response size and API cost:

```
sections=["General"]              → Company info, GICS, officers, description
sections=["Highlights"]           → Market cap, P/E, EPS, margins, ROE/ROA, growth
sections=["Valuation"]            → Trailing/Forward PE, P/S, P/B, EV, EV/EBITDA, EV/Revenue
sections=["SharesStats"]          → Shares outstanding, float, insider %, institutional %
sections=["Technicals"]           → Beta, 52wk high/low, 50/200 day MA, short interest
sections=["SplitsDividends"]      → Dividend rate, yield, payout ratio, ex-date, split history
sections=["AnalystRatings"]       → Consensus rating (1-5), target price, buy/hold/sell counts
sections=["outstandingShares"]    → Quarterly + annual share count time series
sections=["ESGScores"]            → E/S/G scores (legacy, use Investverte instead)
sections=["Earnings"]             → Historical EPS actual vs estimate (last 4Q + 4Y)
```

### Financials (3-Statement Model)
Set `include_financials=true` to get full financial statements.
Use `from_date` and `to_date` (YYYY-MM-DD) to limit the date range.

**Income Statement fields** (quarterly + yearly):
`totalRevenue`, `costOfRevenue`, `grossProfit`, `researchDevelopment`, `sellingGeneralAdministrative`, `sellingAndMarketingExpenses`, `operatingIncome`, `ebit`, `ebitda`, `depreciationAndAmortization`, `incomeBeforeTax`, `incomeTaxExpense`, `netIncome`, `interestExpense`, `totalOtherIncomeExpenseNet`

**Balance Sheet fields**:
`totalAssets`, `totalCurrentAssets`, `cash`, `cashAndShortTermInvestments`, `shortTermInvestments`, `netReceivables`, `inventory`, `totalCurrentLiabilities`, `accountsPayable`, `shortTermDebt`, `longTermDebt`, `shortLongTermDebtTotal`, `totalStockholderEquity`, `retainedEarnings`, `propertyPlantEquipment`, `longTermInvestments`, `netWorkingCapital`, `netInvestedCapital`, `commonStockSharesOutstanding`

**Cash Flow fields**:
`totalCashFromOperatingActivities`, `capitalExpenditures`, `freeCashFlow`, `totalCashflowsFromInvestingActivities`, `totalCashFromFinancingActivities`, `dividendsPaid`, `salePurchaseOfStock`, `netBorrowings`, `stockBasedCompensation`, `depreciation`, `changeInWorkingCapital`

Each period includes `date`, `filing_date`, `currency_symbol`.

### Batch Access
```
→ get_bulk_fundamentals(exchange="US", symbols="AAPL,MSFT,GOOG")
```
Returns Highlights + Valuation + Technicals for all specified symbols. Cost: 100 API calls. Max 500 symbols per call.

---

## 2. Price & Technical Data

### Historical Prices
```
→ get_historical_stock_prices(ticker="AAPL.US", period="d", start_date="2024-01-01")
```
Returns: date, open, high, low, close, adjusted_close, volume.
Periods: `d` (daily), `w` (weekly), `m` (monthly).

### Intraday Prices
```
→ get_intraday_historical_data(ticker="AAPL.US", interval="5m", from_timestamp="2025-01-01")
```
Intervals: `1m` (120 days max), `5m` (600 days), `1h` (7200 days).

### Live/Delayed Price
```
→ get_live_price_data(ticker="AAPL.US")
```
Returns: current price, change, change_p, volume, timestamp.
Can request multiple: `additional_symbols=["MSFT.US","GOOG.US"]` (max ~15-20).

### Technical Indicators
```
→ get_technical_indicators(function="FUNCTION", ticker="AAPL.US", period=N, ...)
```

Available functions:
| Function | Description | Key Params |
|----------|-------------|------------|
| `sma` | Simple Moving Average | `period` (default 50) |
| `ema` | Exponential Moving Average | `period` |
| `wma` | Weighted Moving Average | `period` |
| `macd` | MACD | `fast_period`, `slow_period`, `signal_period` |
| `rsi` | Relative Strength Index | `period` (default 14) |
| `stochastic` | Stochastic Oscillator | `fast_kperiod`, `slow_kperiod`, `slow_dperiod` |
| `stochrsi` | Stochastic RSI | `fast_kperiod`, `slow_dperiod`, `period` |
| `adx` | Average Directional Index | `period` (default 14) |
| `atr` | Average True Range | `period` |
| `bbands` | Bollinger Bands | `period` |
| `cci` | Commodity Channel Index | `period` |
| `sar` | Parabolic SAR | `acceleration` |
| `beta` | Beta vs benchmark | `period`, `code2` (e.g., `SPY.US`) |
| `volatility` | Historical volatility | `period` |
| `avgvol` | Average Volume | `period` |

Use `start_date`/`end_date` to filter. Each call costs 5 API credits.

### Historical Market Cap
```
→ get_historical_market_cap(ticker="AAPL.US", start_date="2024-01-01")
```
Weekly data points. US stocks only, from 2020. Costs 10 API calls.

---

## 3. Earnings & Analyst Estimates

### Consensus Estimates
From `get_fundamentals_data` → Highlights section:
- `EPSEstimateCurrentQuarter`, `EPSEstimateCurrentYear`, `EPSEstimateNextYear`, `EPSEstimateNextQuarter`
- `WallStreetTargetPrice` (consensus price target)

From → AnalystRatings section:
- `Rating` (1.0 = Strong Buy, 5.0 = Strong Sell)
- `StrongBuy`, `Buy`, `Hold`, `Sell`, `StrongSell` (analyst count distribution)

### Earnings Trends (Revision Tracking)
```
→ get_earnings_trends(symbols="AAPL.US")
```
Returns EPS trends including revisions over 7/30/60/90 days. Use to gauge estimate momentum.

### Earnings Calendar & Surprises
```
→ get_upcoming_earnings(symbols="AAPL.US")
```
Returns: report_date, eps_estimate, eps_actual, revenue_estimate, revenue_actual, surprise.

Historical surprises from `get_fundamentals_data` → Earnings section (set `sections=["Earnings"]`).

### NOTE: Revenue Estimates
EODHD provides EPS estimates but NOT revenue consensus estimates. To approximate revenue growth:
- Use `EPSEstimateNextYear / DilutedEpsTTM - 1` as an EPS growth proxy
- Apply historical margin relationship to back into implied revenue
- Or use the `get_upcoming_earnings` endpoint which does include `revenue_estimate` for upcoming quarters

---

## 4. Sentiment & News

### Company News
```
→ get_company_news(ticker="AAPL.US", limit=50, start_date="2025-01-01")
```
Returns: title, date, content, link, symbols mentioned. Max 1000 per request.
Can also filter by topic: `tag="technology"` (without ticker for broad searches).

### Sentiment Scores
```
→ get_sentiment_data(symbols="AAPL.US", start_date="2025-01-01")
```
Returns daily sentiment aggregates per ticker. Useful for trend analysis.

### News Word Weights
```
→ get_news_word_weights(ticker="AAPL.US", limit=50)
```
Returns TF-IDF weighted keywords from recent news about the ticker. Good for identifying themes (e.g., "tariff", "AI", "layoffs").

### NLP Analysis Approach
Since earnings call transcripts are not available in EODHD, use Claude's native NLP on:
1. `get_company_news` content → extract themes, sentiment, key events
2. `get_news_word_weights` → identify dominant narrative shifts
3. `get_sentiment_data` → track sentiment trend over time

---

## 5. Insider & Institutional

### Insider Transactions (SEC Form 4)
```
→ get_insider_transactions(symbol="AAPL.US", limit=50)
```
Returns: date, reporterName, transactionType (P=Purchase, S=Sale), transactionAmount, transactionPrice, ownerType.

Interpretation framework:
- **Cluster buying** (3+ insiders buying within 30 days): Strong bullish signal
- **CEO/CFO buying**: Strongest signal (they know the most)
- **Routine selling** (scheduled 10b5-1 plans): Ignore
- **Unusual large sales** (outside 10b5-1): Worth flagging

### Ownership Data
From `get_fundamentals_data` → SharesStats:
- `PercentInsiders` — insider ownership %
- `PercentInstitutions` — institutional ownership %
- `SharesShort`, `ShortRatio`, `ShortPercent` (from Technicals section)

### Institutional Holdings (13F)
NOT available in EODHD. For 13F data, use edgartools:
```python
from edgar import Company, set_identity
set_identity("Research Agent research@example.com")
# Look up institutional holders via SEC 13F filings
# This is supplementary and may not be needed for standard analysis
```

---

## 6. Macro & Rates

### Treasury Yield Curve (EODHD)
```
→ get_ust_yield_rates(year=2026)
```
Returns full yield curve: 1M, 1.5M, 2M, 3M, 4M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y.
Use the latest 10Y rate as risk-free rate for WACC.

### Treasury Bill Rates
```
→ get_ust_bill_rates(year=2026)
```
Tenors: 4WK, 8WK, 13WK, 17WK, 26WK, 52WK. For short-end rate analysis.

### Real Yields (TIPS)
```
→ get_ust_real_yield_rates(year=2026)
```
Tenors: 5Y, 7Y, 10Y, 20Y, 30Y. Inflation-adjusted yields.

### Macro Indicators
```
→ get_macro_indicator(country="USA", indicator="INDICATOR_CODE")
```

Key indicators:
| Indicator | Code |
|-----------|------|
| GDP (current USD) | `gdp_current_usd` |
| GDP growth (annual %) | `gdp_growth_annual` |
| Inflation (CPI, annual %) | `inflation_consumer_prices_annual` |
| Unemployment (%) | `unemployment_total` |
| Real interest rate | `real_interest_rate` |
| Current account (% of GDP) | `current_account_balance` |

### Economic Events Calendar
```
→ get_economic_events(country="US", start_date="2026-04-01", limit=20)
```
Returns upcoming events: FOMC, CPI, NFP, PMI, etc. with actual/estimate/previous values.

### FRED API (Supplementary)
See §13 below for FRED API patterns. Key series not covered by EODHD:
- `BAMLH0A0HYM2` — ICE BofA HY OAS (credit spread, useful for cost of debt)
- `VIXCLS` — VIX (implied volatility)
- `T10Y2Y` — 10Y-2Y spread (yield curve inversion)

---

## 7. ESG

### Investverte ESG (Recommended)
> **Ticker format**: Investverte endpoints use the bare symbol WITHOUT exchange suffix (e.g., `"AAPL"` not `"AAPL.US"`).
```
→ get_mp_investverte_esg_view_company(symbol="AAPL", year=2024)
```
Returns: `e` (environment), `s` (social), `g` (governance), `esg` (composite). Annual data.

### ESG Sector Benchmarks
```
→ get_mp_investverte_esg_list_sectors()  → list of sectors
→ get_mp_investverte_esg_view_sector(sector="Technology")  → sector averages
```

### Legacy ESGScores
Available in `get_fundamentals_data` → ESGScores, but data is from 2019 and marked "early Beta". Use Investverte instead.

---

## 8. Risk Scoring (Praams)

> **Ticker format**: Praams endpoints use the bare symbol WITHOUT exchange suffix (e.g., `"AAPL"` not `"AAPL.US"`). Same applies to all `get_mp_praams_*` and `get_mp_praams_bank_*` endpoints.

```
→ get_mp_praams_risk_scoring_by_ticker(ticker="AAPL")
```

Returns comprehensive multi-factor scoring including:
- **Return factors**: valuation score, performance, profitability, growth, momentum, dividend metrics
- **Risk factors**: volatility assessment, stress-test results, liquidity score, solvency, country risk
- **Analyst view**: consensus and price target metrics
- **PRAAMS Ratio**: composite risk/return score

Cost: 10 API calls per request.

### Full PDF Report
```
→ get_mp_praams_report_equity_by_ticker(ticker="AAPL", email="user@example.com")
```
Generates downloadable PDF with full multi-factor analysis.

---

## 9. Bank-Specific Financials

For banks (JPM, BAC, C, WFC, GS, MS, etc.), standard Income_Statement lacks key banking metrics. Use Praams bank endpoints:

### Bank Income Statement
```
→ get_mp_praams_bank_income_statement_by_ticker(ticker="JPM")
```
Returns: net interest income, net fee & commission income, core revenue, RIBPT, provisioning, non-recurring income.

### Bank Balance Sheet
```
→ get_mp_praams_bank_balance_sheet_by_ticker(ticker="JPM")
```
Returns: gross loans, loan provisions, net loans, deposits, interest-earning assets, interest-bearing liabilities, securities REPO, total equity.

### Key Bank Metrics to Compute
```
NIM = Net Interest Income / Average Interest-Earning Assets
Efficiency Ratio = Non-Interest Expense / Total Revenue
PPNR = Pre-Provision Net Revenue
Loan Loss Rate = Provisions / Average Loans
```

---

## 10. Corporate Events Calendar

| Event | Endpoint | Key Params |
|-------|----------|------------|
| Earnings dates | `get_upcoming_earnings` | `symbols` or `start_date`/`end_date` |
| Dividends | `get_upcoming_dividends` | `symbol`, `date_from`/`date_to` |
| Stock splits | `get_upcoming_splits` | `from_date`/`to_date` |
| IPOs | `get_upcoming_ipos` | `from_date`/`to_date` |
| Economic events | `get_economic_events` | `country`, `start_date`/`end_date` |

---

## 11. Options

### Options Chain
```
→ get_us_options_contracts(underlying_symbol="AAPL", type="call", exp_date_from="2026-04-01", exp_date_to="2026-06-30")
```
Returns: contract symbol, underlying, type, strike, expiry, last price, bid, ask, volume, OI.

### Options EOD Data
```
→ get_us_options_eod(...)  # Use tool_search to load if needed
```

### Note: Derived Metrics
Implied volatility, Greeks, put-call ratios are NOT pre-computed. Agent must compute from raw chain data if needed (typically out of scope for standard equity research).

---

## 12. Index Data

### Index Components
```
→ mp_index_components(symbol="GSPC.INDX")  # S&P 500
```
Returns current constituents with weights. Available for major indices.

### Index List
Use `get_stocks_from_search(query="S&P", type="index")` to find index codes.

---

## 13. FRED API Patterns

### Access via bash
```bash
FRED_KEY="${FRED_API_KEY}"
# Get latest N observations of a series
curl -s "https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key=${FRED_KEY}&file_type=json&sort_order=desc&limit=5" | python3 -c "
import json,sys
data = json.load(sys.stdin)
for obs in data.get('observations',[]):
    print(f\"{obs['date']}: {obs['value']}\")
"
```

### Key FRED Series for Equity Research

| Purpose | Series ID | Description |
|---------|-----------|-------------|
| Risk-free rate | `DGS10` | 10Y Treasury yield |
| Short rate | `DGS2` | 2Y Treasury yield |
| Curve slope | `T10Y2Y` | 10Y minus 2Y |
| Policy rate | `FEDFUNDS` | Federal funds rate |
| Credit spread | `BAMLH0A0HYM2` | ICE BofA US HY OAS |
| IG spread | `BAMLC0A4CBBB` | BBB corporate OAS |
| Volatility | `VIXCLS` | CBOE VIX |
| Inflation | `CPIAUCSL` | CPI-U (seasonally adjusted) |
| Breakeven | `T10YIE` | 10Y breakeven inflation |
| GDP | `GDP` | Nominal GDP |
| Real GDP | `GDPC1` | Real GDP |
| Unemployment | `UNRATE` | Unemployment rate |
| ISM Manufacturing | `MANEMP` | Manufacturing employment |

### FRED Fallback
If `FRED_API_KEY` is not available, use EODHD substitutes:
- `get_ust_yield_rates` → replaces DGS10, DGS2
- `get_ust_real_yield_rates` → replaces TIPS/breakeven
- `get_macro_indicator(country="USA")` → replaces GDP, CPI, unemployment
- No direct substitute for: HY OAS, VIX, breakeven inflation (inform user)
