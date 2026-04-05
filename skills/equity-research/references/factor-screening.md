# Factor Screening & Quantitative Analysis Reference

## Table of Contents
1. [Stock Screener](#1-stock-screener)
2. [Factor Construction](#2-factor-construction)
3. [Piotroski F-Score](#3-piotroski-f-score)
4. [Momentum Strategies](#4-momentum-strategies)
5. [Quality Screening](#5-quality-screening)
6. [Multi-Factor Ranking](#6-multi-factor-ranking)

---

## 1. Stock Screener

### Basic Screening
```
→ stock_screener(
    filters=[
      ["market_capitalization", ">", 10000000000],    # >$10B
      ["exchange", "=", "US"],
      ["sector", "=", "Technology"],
      ["pe_ratio", "<", 25]
    ],
    sort="market_capitalization.desc",
    limit=50
  )
```

### Available Filter Fields
| Field | Type | Example |
|-------|------|---------|
| `market_capitalization` | numeric | `[">", 1000000000]` |
| `pe_ratio` | numeric | `["<", 30]` |
| `dividend_yield` | numeric | `[">", 0.02]` |
| `beta` | numeric | `["<", 1.5]` |
| `sector` | string | `["=", "Technology"]` |
| `industry` | string | `["=", "Software"]` |
| `exchange` | string | `["=", "US"]` |
| `earnings_share` | numeric | EPS |
| `revenue` | numeric | Total revenue |
| `wall_street_target_price` | numeric | Consensus target |

### Pre-Built Signals
```
→ stock_screener(signals="new_high", exchange="US", limit=20)
```

Available signals: `new_high`, `new_low`, `most_traded`, `most_active`, `overbought`, `oversold`, `bookvalue_neg`, `wallstreet_hi`, `wallstreet_lo`

### Screening Patterns for Common Strategies

**Value stocks**:
```
filters=[
  ["market_capitalization", ">", 2000000000],
  ["pe_ratio", "<", 15],
  ["pe_ratio", ">", 0],
  ["dividend_yield", ">", 0.02],
  ["exchange", "=", "US"]
]
```

**Growth stocks**:
```
filters=[
  ["market_capitalization", ">", 5000000000],
  ["earnings_share", ">", 0],
  ["exchange", "=", "US"]
]
# Then post-filter using get_fundamentals_data for:
# QuarterlyRevenueGrowthYOY > 0.20 AND QuarterlyEarningsGrowthYOY > 0.20
```

**Dividend aristocrats (screening proxy)**:
```
filters=[
  ["dividend_yield", ">", 0.015],
  ["dividend_yield", "<", 0.08],
  ["market_capitalization", ">", 10000000000],
  ["exchange", "=", "US"]
]
# Then validate with get_upcoming_dividends for consistent dividend history
```

---

## 2. Factor Construction

For each factor, the agent computes scores from EODHD data, then ranks the universe.

### Value Factors

| Factor | Formula | Data Source |
|--------|---------|-------------|
| **Earnings Yield (E/P)** | 1 / TrailingPE | Valuation.TrailingPE |
| **Book-to-Market (B/M)** | BookValue × SharesOutstanding / MarketCap | Highlights.BookValue, .MarketCapitalization |
| **FCF Yield** | FreeCashFlow / MarketCap | Cash_Flow.freeCashFlow, Highlights.MarketCapitalization |
| **EV/EBITDA (inverted)** | 1 / EnterpriseValueEbitda | Valuation.EnterpriseValueEbitda |
| **Dividend Yield** | ForwardAnnualDividendYield | SplitsDividends.ForwardAnnualDividendYield |

### Growth Factors

| Factor | Formula | Data Source |
|--------|---------|-------------|
| **Revenue Growth** | QuarterlyRevenueGrowthYOY | Highlights.QuarterlyRevenueGrowthYOY |
| **EPS Growth** | QuarterlyEarningsGrowthYOY | Highlights.QuarterlyEarningsGrowthYOY |
| **EPS Revision** | Change in EPSEstimate over time | get_earnings_trends (track over multiple snapshots) |
| **Sustainable Growth** | ROE × (1 - PayoutRatio) | Highlights.ReturnOnEquityTTM, SplitsDividends.PayoutRatio |

### Profitability / Quality Factors

| Factor | Formula | Data Source |
|--------|---------|-------------|
| **ROE** | ReturnOnEquityTTM | Highlights.ReturnOnEquityTTM |
| **ROA** | ReturnOnAssetsTTM | Highlights.ReturnOnAssetsTTM |
| **Gross Margin** | GrossProfit / Revenue | Income_Statement.grossProfit / .totalRevenue |
| **Operating Margin** | OperatingMarginTTM | Highlights.OperatingMarginTTM |
| **Net Margin** | ProfitMargin | Highlights.ProfitMargin |
| **Asset Turnover** | Revenue / Total Assets | Income_Statement.totalRevenue / Balance_Sheet.totalAssets |

### Risk / Volatility Factors

| Factor | Formula | Data Source |
|--------|---------|-------------|
| **Beta** | Direct | Technicals.Beta or get_technical_indicators(function="beta") |
| **Historical Volatility** | Std dev of daily returns | get_technical_indicators(function="volatility") |
| **Short Interest** | ShortPercent | Technicals.ShortPercent |

### Size Factor

| Factor | Formula | Data Source |
|--------|---------|-------------|
| **Market Cap** | Direct | Highlights.MarketCapitalization |
| **Log Market Cap** | ln(MarketCap) | Computed |

---

## 3. Piotroski F-Score

A 9-point composite score measuring financial strength. Each test = 1 point (pass) or 0 (fail).

### Data Needed
Fetch the last 2 years of quarterly financials:
```
→ get_fundamentals_data(ticker, include_financials=true, from_date="2024-01-01")
```

### Scoring Rules

**Profitability (4 points)**:
1. **ROA > 0**: netIncome_TTM / totalAssets_avg > 0 → 1 point
2. **Operating Cash Flow > 0**: totalCashFromOperatingActivities_TTM > 0 → 1 point
3. **ΔROA > 0**: ROA_current_year > ROA_prior_year → 1 point
4. **Accruals**: CFO > Net Income (cash earnings > accrual earnings) → 1 point

**Leverage/Liquidity (3 points)**:
5. **ΔLeverage < 0**: (longTermDebt/totalAssets) decreased YoY → 1 point
6. **ΔCurrent Ratio > 0**: (totalCurrentAssets/totalCurrentLiabilities) increased → 1 point
7. **No Dilution**: shares outstanding did not increase YoY → 1 point

**Operating Efficiency (2 points)**:
8. **ΔGross Margin > 0**: gross margin increased YoY → 1 point
9. **ΔAsset Turnover > 0**: (revenue/totalAssets) increased YoY → 1 point

### Interpretation
- **8-9**: Strong — historically outperform market by 7.5% annually
- **5-7**: Neutral
- **0-4**: Weak — historically underperform, potential short candidates

### Implementation Pattern
```python
# Pseudo-code for agent computation
# Requires last 8 quarterly financials to compute TTM and YoY
scores = {}
scores['roa_positive'] = 1 if net_income_ttm / avg_total_assets > 0 else 0
scores['cfo_positive'] = 1 if cfo_ttm > 0 else 0
scores['roa_improving'] = 1 if roa_current > roa_prior else 0
scores['accruals'] = 1 if cfo_ttm > net_income_ttm else 0
scores['leverage_down'] = 1 if leverage_current < leverage_prior else 0
scores['liquidity_up'] = 1 if current_ratio_now > current_ratio_prior else 0
scores['no_dilution'] = 1 if shares_now <= shares_prior else 0
scores['margin_up'] = 1 if gross_margin_now > gross_margin_prior else 0
scores['turnover_up'] = 1 if asset_turnover_now > asset_turnover_prior else 0
f_score = sum(scores.values())
```

---

## 4. Momentum Strategies

### Price Momentum (12-1 Month)
The classic Jegadeesh-Titman momentum signal: return from T-12 to T-1 months (skip the most recent month to avoid short-term reversal).

```
→ get_historical_stock_prices(ticker, period="m", start_date="13_months_ago")
```

```
Momentum_12_1 = Price_1_month_ago / Price_13_months_ago - 1
```

### Short-Term Reversal (1 Month)
```
Reversal_1M = -1 × (Price_now / Price_1_month_ago - 1)
```
Negative of last month's return (losers tend to bounce, winners tend to fade in the very short term).

### Earnings Momentum
```
→ get_earnings_trends(symbols=ticker)
```
Track EPS estimate changes:
- **EPS Revision %** = (Current Estimate - Estimate_90d_ago) / |Estimate_90d_ago|
- Positive revisions: bullish momentum signal
- Negative revisions: bearish momentum signal

### RSI-Based Momentum/Mean Reversion
```
→ get_technical_indicators(function="rsi", ticker="AAPL.US", period=14)
```
- RSI > 70: Overbought (potential mean reversion short)
- RSI < 30: Oversold (potential mean reversion long)
- RSI 40-60 with rising trend: Momentum confirmation

---

## 5. Quality Screening

### Composite Quality Score
Build a quality composite by z-scoring and averaging:

1. **Profitability**: ROE, ROA, Gross Margin, Operating Margin
2. **Stability**: Earnings volatility (std dev of quarterly EPS growth)
3. **Growth consistency**: Revenue growth consistency over 4+ quarters
4. **Balance sheet strength**: Debt/Equity ratio (lower = better), current ratio
5. **Cash conversion**: FCF / Net Income > 0.8 indicates high-quality earnings

### GARP (Growth at a Reasonable Price)
```
PEG Ratio = Highlights.PEGRatio
Target: PEG between 0.5 and 1.5
  PEG < 1.0: Growth is underpriced
  PEG 1.0-1.5: Fairly priced growth
  PEG > 2.0: Growth is overpriced
```

Screen:
```
→ stock_screener(filters=[
    ["market_capitalization", ">", 5000000000],
    ["exchange", "=", "US"],
    ["earnings_share", ">", 0]
  ], limit=100)
```
Then filter for PEGRatio < 1.5 AND QuarterlyRevenueGrowthYOY > 0.10 from fundamentals.

---

## 6. Multi-Factor Ranking

### Universe Construction
Start with a filtered universe:
```
→ stock_screener(filters=[
    ["market_capitalization", ">", 2000000000],
    ["exchange", "=", "US"]
  ], limit=100)
```

### Z-Score Ranking Method
For each factor:
1. Compute the factor value for all stocks in the universe
2. Z-score = (value - mean) / standard_deviation
3. For factors where lower is better (P/E, volatility), multiply z-score by -1
4. Composite score = weighted average of z-scores

### Suggested Factor Weights

**Balanced multi-factor**:
| Factor | Weight |
|--------|--------|
| Value (E/P) | 20% |
| Momentum (12-1m) | 20% |
| Quality (ROE) | 20% |
| Growth (Revenue YoY) | 20% |
| Low Volatility | 10% |
| F-Score | 10% |

**Value-tilted**:
| Factor | Weight |
|--------|--------|
| Value (FCF Yield) | 30% |
| Value (E/P) | 20% |
| Quality (F-Score) | 25% |
| Momentum | 15% |
| Low Volatility | 10% |

**Growth-tilted**:
| Factor | Weight |
|--------|--------|
| Growth (Rev YoY) | 25% |
| Momentum (12-1m) | 25% |
| EPS Revision | 20% |
| Quality (Margin) | 20% |
| Value (PEG) | 10% |

### Output Format
Present as a ranked table:
```
| Rank | Ticker | Name | Composite Score | Value | Momentum | Quality | Growth |
|------|--------|------|-----------------|-------|----------|---------|--------|
| 1    | XYZ    | ...  | 2.15            | 1.8   | 2.5      | 1.9     | 2.4    |
| 2    | ...    |      |                 |       |          |         |        |
```

Show top 10-20 stocks. Highlight any stocks with extreme single-factor scores (>2 or <-2 z-scores) as they may represent concentrated bets.
