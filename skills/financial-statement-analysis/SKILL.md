---
name: financial-statement-analysis
description: >
  Equity-research-grade financial statement analysis. Trigger whenever the user asks to analyze a company's financials,
  earnings, 10-K, 10-Q, balance sheet, income statement, cash flow, or any filing. Also trigger for: earnings quality,
  Beneish M-Score, Sloan accruals, margin analysis, working capital, DuPont, ROIC, DCF valuation, channel stuffing,
  GAAP vs non-GAAP, or "is this company's numbers trustworthy." Trigger even for just a ticker + "analyze it."
  Covers: EODHD MCP + FRED + edgartools data fetching, forensic ratios, DSO/DIO/DPO/CCC, margin decomposition,
  valuation (DCF, multiples, reverse DCF), earnings surprises, insider signals, and sentiment. Use for any depth
  from quick health check to full deep dive.
---

# Financial Statement Analysis Skill

This skill turns raw financial data into equity-research-grade analysis. It mirrors the workflow used by professional sell-side and buy-side analysts: extract data, compute forensic quality metrics, assess working capital health, decompose margins and returns, check consensus and surprises, scan for red flags, and integrate into valuation.

## Data Sources

| Source | What it provides | How to access |
|--------|-----------------|---------------|
| **EODHD MCP** | Financial statements (IS/BS/CF quarterly+annual), valuation multiples, earnings history/trends, insider transactions, sentiment, news, historical prices, market cap | `eodhd-mcp:get_fundamentals_data`, `get_earnings_trends`, `get_insider_transactions`, `get_sentiment_data`, `get_company_news`, `get_historical_stock_prices`, `get_historical_market_cap` |
| **FRED API** | Risk-free rates (DGS10, DGS2), credit spreads (BAA, AAA), GDP growth, CPI, Fed Funds Rate | HTTP calls to `https://api.stlouisfed.org/fred/series/observations` |
| **edgartools** | Raw SEC filings (10-K, 10-Q, 8-K), XBRL data, footnotes, MD&A, risk factors, segment detail | Python: `from edgar import Company; Company(ticker).get_filings(form="10-K")` |

## Workflow Phases

Run these phases in order. The user may request only specific phases — adapt accordingly. For a quick analysis, Phase 1-2 is sufficient. For a full deep dive, run all five.

### Phase 1: Data Extraction & Overview

**Goal**: Pull all financial data and build a snapshot of the company.

1. **Fetch EODHD fundamentals** — call `eodhd-mcp:get_fundamentals_data` with the ticker (format: `TICKER.US` for US stocks). This returns:
   - `General` → sector, industry, employees, description
   - `Highlights` → market cap, P/E, EPS, margins, ROE/ROA, revenue TTM, dividend yield
   - `Valuation` → trailing/forward P/E, P/S, P/B, EV/Revenue, EV/EBITDA
   - `SharesStats` → shares outstanding, float, insider %, institutional %, short interest
   - `Financials` → Income_Statement, Balance_Sheet, Cash_Flow (quarterly + yearly)
   - `Earnings` → History (actual vs estimate per quarter), Trend, Annual

2. **Parse financial statements** — extract the last 3-5 years annual and 8 quarters of data from `Financials`. Key line items to extract:

   Income Statement: `totalRevenue`, `costOfRevenue`, `grossProfit`, `operatingIncome`, `netIncome`, `ebitda`, `researchDevelopment`, `sellingGeneralAdministrative`, `interestExpense`, `incomeBeforeTax`, `incomeTaxExpense`

   Balance Sheet: `totalCurrentAssets`, `cash`, `netReceivables`, `inventory`, `totalAssets`, `propertyPlantEquipment`, `goodWill`, `intangibleAssets`, `totalCurrentLiabilities`, `accountsPayable`, `shortTermDebt`, `longTermDebt`, `totalStockholderEquity`, `totalLiab`

   Cash Flow: `totalCashFromOperatingActivities`, `capitalExpenditures`, `totalCashflowsFromInvestingActivities`, `totalCashFromFinancingActivities`, `changeInCash`, `depreciation`, `stockBasedCompensation`, `changeToNetincome`, `changeToOperatingActivities`

3. **Compute quick-look metrics** from Highlights:
   - Revenue growth (QoQ, YoY)
   - Gross/operating/net margins and their trend direction
   - EPS growth trajectory
   - Dividend yield and payout ratio

4. **Present the snapshot** — a concise company overview before deeper analysis.

### Phase 2: Forensic Quality Analysis

**Goal**: Determine if reported earnings are trustworthy. This is the highest-value phase.

Run the Python script at `scripts/forensic_ratios.py` or compute these manually:

#### Beneish M-Score (earnings manipulation detector)

Read `references/forensic-formulas.md` for the full 8-variable formula and interpretation guide.

The M-Score uses two consecutive periods of financial data. Extract from EODHD fundamentals:
- Revenue (current and prior year)
- Receivables, COGS, Current Assets, Total Assets, PP&E, Depreciation, SGA, Long-term Debt, Net Income, CFO

**Interpretation**: M-Score > -1.78 → high probability of earnings manipulation. Flag and explain which sub-indices are driving it (DSRI = receivables growing faster than revenue, TATA = large gap between earnings and cash, AQI = rising soft assets, etc.).

#### Sloan Accruals Ratio

Formula: `(Net Income - CFO) / Average Total Assets`

- Safe zone: -10% to +10%
- Caution zone: +10% to +15%
- Red flag: above +15%

High accruals mean earnings are driven by accounting entries rather than cash — historically associated with poor future stock performance.

#### CFO/NI Quality Ratio

Formula: `Cash from Operations / Net Income`

- Healthy: persistently above 1.0x (cash earnings exceed reported earnings)
- Warning: below 1.0x for 2+ consecutive years
- Red flag: below 0.5x or trending sharply downward

#### Channel Stuffing Flags

Compare DSO growth rate vs revenue growth rate. If DSO is growing significantly faster than revenue (>5 percentage points), it may indicate the company is shipping product to distributors to inflate sales. Also check for hockey-stick quarterly revenue patterns (disproportionate % of annual revenue in Q4).

#### Non-GAAP Quality Check

If edgartools is available, pull the 8-K press release (exhibit 99.1) and compare GAAP net income to the company's non-GAAP adjusted figures. Track the cumulative gap over 5 years — if non-GAAP adjustments exceed 20% of cumulative GAAP earnings, the adjusted numbers are likely misleading.

### Phase 3: Working Capital & Balance Sheet Deep Dive

**Goal**: Assess operational efficiency and hidden risks.

Run `scripts/working_capital_analysis.py` or compute manually.

#### Core Working Capital Metrics

| Metric | Formula | What it reveals |
|--------|---------|-----------------|
| DSO | (Avg Receivables / Revenue) × 365 | Collection speed; rising = potential bad debts or stuffing |
| DIO | (Avg Inventory / COGS) × 365 | Inventory efficiency; rising = demand weakness or obsolescence |
| DPO | (Avg Payables / COGS) × 365 | Payment leverage; falling = weakening supplier position |
| CCC | DSO + DIO - DPO | Full cash cycle; lengthening precedes cash problems by 1-2 quarters |

Compute for each of the last 8 quarters. Present as a time-series trend and flag any metric moving >5 days YoY.

#### Debt & Leverage Analysis

From EODHD Balance Sheet:
- Net Debt = Total Debt - Cash
- Net Debt / EBITDA ratio (healthy: <3x for most industries)
- Interest Coverage = EBIT / Interest Expense (healthy: >3x)
- Fixed vs floating rate mix (check edgartools footnotes if available)

#### Capital Allocation Assessment

- Maintenance Capex estimate ≈ Depreciation expense
- Growth Capex = Total Capex - Maintenance Capex
- FCF = CFO - Total Capex
- FCF Yield = FCF / Market Cap
- SBC as % of Revenue and as % of FCF (critical for tech companies)
- Buyback effectiveness: compare shares outstanding trend vs buyback spending

### Phase 4: Returns Analysis & Valuation

**Goal**: Measure economic value creation and estimate intrinsic value.

Read `references/valuation-methods.md` for detailed formulas.

#### DuPont Decomposition (ROE breakdown)

3-factor: `ROE = (NI/Sales) × (Sales/Assets) × (Assets/Equity)`
- Net Margin × Asset Turnover × Equity Multiplier
- Shows whether ROE is driven by profitability, efficiency, or leverage

5-factor extends to: Tax Burden × Interest Burden × Operating Margin × Asset Turnover × Equity Multiplier

#### ROIC (Return on Invested Capital)

```
NOPAT = EBIT × (1 - Tax Rate)
Invested Capital = Total Equity + Total Debt - Cash
ROIC = NOPAT / Invested Capital
```

Compare ROIC to WACC. ROIC > WACC = economic value creation. Track the trend.

**Incremental ROIC** = Change in NOPAT / Change in Invested Capital — shows returns on new investments.

#### DCF Valuation (simplified)

1. Fetch risk-free rate from FRED (series: DGS10)
2. Get beta from EODHD fundamentals → `Highlights`
3. Estimate cost of equity: `Rf + Beta × ERP` (use ERP ≈ 5%)
4. WACC = (E/V × Ke) + (D/V × Kd × (1-t))
5. Project FCF for 5 years using historical growth rate, decaying toward GDP growth
6. Terminal Value = Final Year FCF × (1+g) / (WACC-g), where g = 2-3%
7. Discount everything back, subtract net debt, divide by shares

#### Reverse DCF

Start with current market cap → back-solve for implied FCF growth rate. If the implied rate seems unrealistic (e.g., >20% for 10 years for a mature company), the stock may be overvalued.

#### Comparable Multiples

From EODHD `Valuation` section: compare P/E, EV/EBITDA, P/S, P/B to:
- The company's own 5-year historical average (use `get_historical_stock_prices` + fundamentals time series)
- Industry peers (user must provide or you can use same sector/industry from `General`)

### Phase 5: Signals & Sentiment

**Goal**: Check behavioral and market signals around the filing.

#### Earnings Surprise Analysis

From EODHD `Earnings.History`:
- Plot last 8-12 quarters of actual vs estimate
- Calculate beat/miss pattern and magnitude
- Identify whether company consistently beats (sandbagging) or shows volatile surprises

From `get_earnings_trends`:
- Current consensus estimates for next quarter and fiscal year
- Number of analysts, estimate range (high/low/mean)
- Revision trend (upward/downward over last 30/90 days)

#### Insider Transactions

Call `eodhd-mcp:get_insider_transactions` filtered by the company's ticker.
- Focus on open-market purchases (transaction code "P") — these are the highest signal
- Cluster selling is less informative (could be pre-planned 10b5-1), but large unplanned sales near earnings are notable
- Compare insider activity timing to the filing date

#### News Sentiment

Call `eodhd-mcp:get_sentiment_data` for the ticker.
- Track sentiment trend over the last 30/60/90 days
- Use `get_company_news` for recent headlines
- Use `get_news_word_weights` to identify dominant narrative themes

## Output Structure

Present the analysis in this order (adapt depth to what the user requested):

1. **Company Snapshot** — one paragraph: what the company does, sector, size, key metrics
2. **Earnings Quality Verdict** — Beneish M-Score, Sloan ratio, CFO/NI, with plain-English interpretation and risk level (Green/Yellow/Red)
3. **Working Capital Health** — DSO/DIO/DPO/CCC trends with flags
4. **Profitability & Returns** — margin trends, DuPont breakdown, ROIC vs WACC
5. **Valuation** — current multiples vs history, simplified DCF range, reverse DCF implied growth
6. **Signals** — earnings surprise pattern, insider activity, sentiment
7. **Key Risks & Red Flags** — anything that emerged from the analysis
8. **Bottom Line** — synthesis: what does this all mean together

## Important Notes

- EODHD tickers use format `SYMBOL.EXCHANGE` (e.g., `AAPL.US`, `TSLA.US`, `MSFT.US`). For non-US, use the appropriate exchange code (e.g., `.LSE`, `.AS`, `.PA`).
- EODHD fundamentals costs 10 API calls per request — cache the response and extract all needed data from one call.
- FRED API requires an API key passed as `&api_key=YOUR_KEY` — the user should have this configured.
- edgartools is a Python library (`pip install edgartools`). Use it for SEC filing text analysis. It requires setting a user-agent identity.
- For banks, use Praams bank-specific endpoints (`get_mp_praams_bank_balance_sheet_by_ticker`, `get_mp_praams_bank_income_statement_by_ticker`) instead of standard fundamentals — bank financials have fundamentally different structures.
- All forensic ratios require at least 2 periods of data. If only 1 period is available, note this limitation.
- Never provide investment advice. Present the analysis as factual information; remind the user that this is analytical output, not a buy/sell recommendation.
