---
name: equity-research
description: "Professional equity research and stock analysis for US markets. Use this skill whenever the user asks to analyze a stock, value a company, run a DCF, do comparable company analysis, screen for stocks, build a financial model, perform sum-of-the-parts valuation, check analyst estimates, compute WACC, evaluate dividends, assess factors/momentum/quality, review insider activity, analyze earnings, or do any form of equity due diligence. Also trigger when the user mentions tickers with intent to evaluate (e.g. 'what do you think of AAPL', 'is MSFT overvalued', 'deep dive on GOOG'). Covers: DCF, comps, DDM, SOTP, 3-statement modeling, factor screening, sentiment/news analysis, macro context, ESG, risk scoring, and earnings analysis. Data sources: EODHD MCP (primary), FRED API (macro), edgartools (SEC EDGAR segments/filings)."
---

# Equity Research Agent Skill

## Overview

This skill enables professional-grade equity research on US-listed stocks using three data sources:

| Source | Access Method | Coverage |
|--------|--------------|----------|
| **EODHD** | MCP tools (direct) | Financials, prices, estimates, screener, technicals, news, sentiment, treasury rates, ESG, options, insider data |
| **FRED** | HTTP API via bash (`curl`) | Macro indicators, yield curves, credit spreads, VIX |
| **SEC EDGAR** | `edgartools` Python package via bash | Segment revenue/EBITDA, 10-K/10-Q full text, XBRL facts |

## Ticker Format

EODHD requires `SYMBOL.EXCHANGE` format. For US stocks: `AAPL.US`, `GOOG.US`, `JPM.US`.
Use `get_stocks_from_search` to resolve ambiguous tickers.

## Routing: Which Reference to Read

Based on the user's request, read the appropriate reference file BEFORE proceeding:

| User Intent | Reference File |
|-------------|---------------|
| Value a stock, DCF, what's it worth, intrinsic value, price target | `references/valuation-methods.md` |
| Compare to peers, comps, relative valuation, multiples, overvalued/undervalued | `references/valuation-methods.md` |
| Dividend analysis, DDM, yield, payout sustainability | `references/valuation-methods.md` |
| Sum-of-the-parts, conglomerate, segment breakdown | `references/valuation-methods.md` + `references/edgar-segments.md` |
| Screen stocks, find stocks matching criteria, factor screening, momentum, quality | `references/factor-screening.md` |
| Full equity research report, deep dive, due diligence | Read ALL reference files; follow the **Full Research Report** workflow below |
| Macro context, interest rates, WACC inputs, economic outlook | `references/data-sources.md` §Macro |
| Earnings analysis, estimates, revisions, surprises | `references/data-sources.md` §Earnings |
| News, sentiment, insider activity | `references/data-sources.md` §Sentiment and §Insider |
| ESG scoring | `references/data-sources.md` §ESG |

## Full Research Report Workflow

When the user asks for a comprehensive analysis ("deep dive on X", "full research report on X", "analyze X for me"):

### Step 1: Company Overview & Context
```
→ get_fundamentals_data(ticker, sections=["General","Highlights","Valuation","SharesStats","Technicals","SplitsDividends","AnalystRatings"], include_financials=false)
```
Extract: name, sector, GICS classification, market cap, description, key officers, employee count.

### Step 2: Financial Model (3-Statement)
```
→ get_fundamentals_data(ticker, include_financials=true)
```
From Financials.Income_Statement (quarterly), extract last 8 quarters:
- Revenue, gross profit, operating income, EBITDA, net income
- Compute margins: gross margin, operating margin, net margin
- Compute growth: QoQ and YoY for revenue and EPS

From Financials.Balance_Sheet:
- Total assets, debt (short + long), cash, equity, net debt
- Compute: debt/equity, net debt/EBITDA, current ratio

From Financials.Cash_Flow:
- CFO, capex, FCF, dividends paid, buybacks, SBC
- Compute: FCF yield, FCF margin, capex/revenue

### Step 3: Valuation
Read `references/valuation-methods.md` and apply:
1. **Comps** (always) — screen peers via GICS, apply median multiples
2. **DCF** (for non-financials) — project FCF, compute WACC, discount
3. **DDM** (if dividend payer with >2% yield and stable payout)
4. **SOTP** (if conglomerate with 2+ distinct segments) — use edgartools
   - Before running: verify via `python3 -c "import edgar"`. If ImportError, run `pip install edgartools --break-system-packages` first.

Synthesize a **fair value range** from the methods used.

### Step 4: Growth & Catalysts
```
→ get_earnings_trends(symbols=ticker)
→ get_company_news(ticker=ticker, limit=20)
→ get_sentiment_data(symbols=ticker)
```
- EPS revision direction (up/down over 30/90 days)
- Upcoming earnings date and consensus
- Recent news themes and sentiment trend
- Key catalysts (product launches, regulatory, M&A)

### Step 5: Risk Assessment
```
→ get_mp_praams_risk_scoring_by_ticker(ticker)
→ get_insider_transactions(symbol=ticker, limit=20)
```
- Praams risk scores (volatility, stress-test, liquidity, solvency)
- Insider buying/selling pattern
- Short interest (from Technicals section)
- Key risk factors from news

### Step 6: Macro Context
Read `references/data-sources.md` §Macro section and fetch:
```
→ get_ust_yield_rates(year=2026)  # use the current calendar year; update annually
→ get_economic_events(country="US", limit=10)  # upcoming events
```
FRED (via bash): 10Y yield, 2Y yield, credit spreads, VIX.

### Step 7: Synthesize & Present
Combine all sections into a structured report:
1. **Investment Thesis** (2-3 sentences: bull case, bear case, conclusion)
2. **Rating**: Buy / Hold / Sell with conviction level
3. **Fair Value Range**: $X - $Y (current price: $Z, upside/downside: %)
4. **Financial Summary Table**: Key metrics (revenue, EPS, margins, growth, valuation multiples)
5. **Valuation Detail**: Method-by-method breakdown
6. **Growth Drivers & Catalysts**
7. **Risk Factors**
8. **Macro Context**

## Key Computation Formulas

### WACC
```
Risk-free rate = 10Y UST yield (from get_ust_yield_rates)
Equity Risk Premium = 5.5% (default, adjustable)
Cost of Equity = Rf + Beta × ERP
Cost of Debt = Interest Expense / Average Total Debt × (1 - Tax Rate)
Tax Rate = Income Tax Expense / Income Before Tax (from financials)
WACC = (E/V) × Ke + (D/V) × Kd
  where E = Market Cap, D = Total Debt, V = E + D
```

### Free Cash Flow
```
UFCF = EBIT × (1 - Tax Rate) + D&A - CapEx - ΔWorking Capital
  Available directly: freeCashFlow from Cash_Flow section
  Or compute from: totalCashFromOperatingActivities - capitalExpenditures
```

### Enterprise Value
```
EV = Market Cap + Total Debt - Cash & Short-term Investments
  Available directly: EnterpriseValue from Valuation section
  Or compute from: MarketCapitalization + shortLongTermDebtTotal - cashAndShortTermInvestments
```

## FRED API Access Pattern

```bash
# Template for FRED API calls (requires FRED_API_KEY env variable)
curl -s "https://api.stlouisfed.org/fred/series/observations?series_id=SERIES_ID&api_key=${FRED_API_KEY}&file_type=json&sort_order=desc&limit=N"
```

Key series IDs:
| Series | ID | Use |
|--------|-----|-----|
| 10Y Treasury | DGS10 | Risk-free rate |
| 2Y Treasury | DGS2 | Yield curve |
| 10Y-2Y Spread | T10Y2Y | Recession signal |
| Fed Funds Rate | FEDFUNDS | Policy rate |
| CPI (Urban) | CPIAUCSL | Inflation |
| HY OAS Spread | BAMLH0A0HYM2 | Credit stress / cost of debt proxy |
| VIX | VIXCLS | Market fear gauge |
| US GDP | GDP | Growth context |
| Unemployment | UNRATE | Labor market |

If FRED_API_KEY is not set, fall back to EODHD equivalents:
- `get_ust_yield_rates` for treasury yields
- `get_macro_indicator(country="USA")` for GDP, CPI, unemployment
- `get_economic_events` for event calendar

## Error Handling

- If `get_fundamentals_data` returns empty financials: the ticker may be an ETF, index, or delisted. Check `General.Type`.
- If edgartools fails: fall back to consolidated-only analysis; inform user that segment data is unavailable.
- If FRED API key is missing: use EODHD treasury and macro endpoints as substitutes.
- For banks/financials: use Praams bank endpoints (`get_mp_praams_bank_income_statement_by_ticker`, `get_mp_praams_bank_balance_sheet_by_ticker`) instead of standard fundamentals for NII, provisions, interest-earning assets.

## Output Formatting

- Present financial data in clean tables with proper formatting ($B, %, x for multiples)
- Always show the source methodology and key assumptions
- For DCF: include sensitivity table (WACC × terminal growth)
- For comps: show the peer set with individual multiples, not just medians
- Round valuation outputs to nearest $0.50 for large caps, $0.25 for mid/small caps

## Reference Files

- `references/valuation-methods.md` — DCF, Comps, DDM, SOTP step-by-step procedures and sector-specific notes
- `references/data-sources.md` — Complete EODHD MCP endpoint reference, FRED API patterns, ticker format rules
- `references/edgar-segments.md` — edgartools XBRL segment extraction for SOTP; install instructions and error handling
- `references/factor-screening.md` — Stock screener patterns, Piotroski F-Score, momentum, quality, multi-factor ranking
