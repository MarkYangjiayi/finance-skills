# Valuation Methods Reference

Read this file when performing Phase 4 (Returns Analysis & Valuation). All formulas reference data available from EODHD fundamentals, FRED API, and edgartools.

## DuPont Decomposition

### 3-Factor Model

```
ROE = Net_Profit_Margin × Asset_Turnover × Equity_Multiplier

where:
  Net_Profit_Margin = Net_Income / Revenue
  Asset_Turnover = Revenue / Average_Total_Assets
  Equity_Multiplier = Average_Total_Assets / Average_Stockholders_Equity
```

EODHD fields:
- `netIncome`, `totalRevenue` (Income Statement)
- `totalAssets`, `totalStockholderEquity` (Balance Sheet)

### 5-Factor Model (extended)

```
ROE = Tax_Burden × Interest_Burden × Operating_Margin × Asset_Turnover × Equity_Multiplier

where:
  Tax_Burden = Net_Income / Pretax_Income
  Interest_Burden = Pretax_Income / EBIT
  Operating_Margin = EBIT / Revenue
  Asset_Turnover = Revenue / Average_Total_Assets
  Equity_Multiplier = Average_Total_Assets / Average_Stockholders_Equity
```

Additional EODHD fields: `incomeBeforeTax`, `operatingIncome` (as EBIT proxy)

### Interpretation

Compute each factor for 3-5 years and identify the primary ROE driver:
- **Margin-driven ROE** = high-quality, sustainable (software companies, luxury brands)
- **Turnover-driven ROE** = operationally efficient, moderate quality (retailers, industrials)
- **Leverage-driven ROE** = fragile, vulnerable to rate increases (financials, leveraged companies)

Flag any case where ROE is high primarily because of leverage — this masks underlying business quality.

---

## ROIC (Return on Invested Capital)

### Formula

```
NOPAT = EBIT × (1 - Effective_Tax_Rate)
Invested_Capital = Total_Equity + Total_Debt - Excess_Cash

ROIC = NOPAT / Average_Invested_Capital
```

Where:
- Effective_Tax_Rate = Income_Tax_Expense / Pretax_Income (from EODHD Income Statement)
- Total_Debt = Short_Term_Debt + Long_Term_Debt (from Balance Sheet)
- Excess_Cash = Cash - max(0, Current_Liabilities - Current_Assets_ex_Cash) — conservative estimate; simpler proxy: just use total Cash

### Incremental ROIC

```
Incremental_ROIC = (NOPAT_t - NOPAT_{t-1}) / (Invested_Capital_t - Invested_Capital_{t-1})
```

This shows the return on each new dollar of investment. Declining incremental ROIC while absolute ROIC remains high suggests the company is running out of attractive reinvestment opportunities.

### ROIC vs WACC Spread

```
Value_Spread = ROIC - WACC
```
- Positive spread = creating economic value
- Negative spread = destroying economic value
- Narrowing positive spread = competitive advantages eroding

---

## WACC Calculation

### Cost of Equity (CAPM)

```
Ke = Rf + Beta × ERP

where:
  Rf = 10-Year Treasury Yield (FRED series: DGS10)
  Beta = from EODHD Highlights or compute from historical returns regression
  ERP = Equity Risk Premium ≈ 5.0% (Damodaran's estimate for US market)
```

**FRED API call for risk-free rate:**
```
GET https://api.stlouisfed.org/fred/series/observations
  ?series_id=DGS10
  &api_key=YOUR_KEY
  &sort_order=desc
  &limit=1
  &file_type=json
```

### Cost of Debt

```
Kd = Interest_Expense / Average_Total_Debt
```
Or use the yield on the company's publicly traded bonds if available. For investment-grade, use FRED BAA/AAA spreads as a sanity check.

### WACC Assembly

```
WACC = (E/V) × Ke + (D/V) × Kd × (1 - Tax_Rate)

where:
  E = Market Cap (EODHD Highlights.MarketCapitalization)
  D = Total Debt (Balance Sheet: shortTermDebt + longTermDebt)
  V = E + D
  Tax_Rate = Effective tax rate from Income Statement
```

Important: Use market-value weights, not book value. Book-value weights is one of the most common errors in amateur DCF models.

---

## DCF Valuation (Unlevered FCF to Firm)

### Step 1: Calculate Historical FCF

```
UFCF = EBIT × (1-t) + Depreciation - Capex - Change_in_Working_Capital

or simplified:
UFCF = CFO - Capex + Interest_Expense × (1-t)
```

Compute for 3-5 historical years to establish the base growth rate.

### Step 2: Project FCF

Use a 2-stage approach:
- **Stage 1 (5 years)**: Project revenue growth decaying from current rate toward long-term rate. Apply target margin assumptions. Derive FCF from projected financials.
- **Stage 2 (terminal)**: Assume stable growth forever.

Revenue growth decay formula:
```
Growth_Year_N = Current_Growth - (Current_Growth - Terminal_Growth) × (N / Stage_1_Years)
```

### Step 3: Terminal Value

**Gordon Growth Model:**
```
TV = FCF_Final × (1 + g) / (WACC - g)
where g = long-term growth rate (2-3% for mature companies, should not exceed nominal GDP growth)
```

**Exit Multiple Method:**
```
TV = EBITDA_Final × EV/EBITDA_Exit_Multiple
```

Best practice: compute both and cross-check. Calculate the implied perpetuity growth from the exit multiple and the implied exit multiple from the perpetuity growth. They should be consistent.

### Step 4: Discount and Derive Equity Value

```
Enterprise_Value = Sum of [FCF_t / (1+WACC)^t] + TV / (1+WACC)^n
Equity_Value = Enterprise_Value - Net_Debt + Cash
Intrinsic_Value_Per_Share = Equity_Value / Diluted_Shares_Outstanding
```

### Step 5: Sensitivity Table

Always present a sensitivity table varying WACC (±1% in 0.5% steps) and terminal growth rate (1% to 4% in 0.5% steps). This shows the range of fair values and highlights which assumptions matter most.

---

## Reverse DCF

Instead of projecting forward, start from the current stock price and back-solve for implied assumptions.

### Method

```
Current_Market_Cap + Net_Debt = Enterprise_Value
```

Then solve for the FCF growth rate (g_implied) that makes:
```
Sum of [FCF_0 × (1+g_implied)^t / (1+WACC)^t] + TV / (1+WACC)^n = Enterprise_Value
```

This requires iterative solving (goal seek or Newton's method). A simpler approximation for a perpetuity:
```
g_implied = WACC - (FCF_current / Enterprise_Value)
```

### Interpretation

- Implied growth < historical growth = market is skeptical, potentially undervalued
- Implied growth > 15% for 10+ years = very aggressive pricing, limited margin of safety
- Compare implied growth to industry growth rate and the company's reinvestment rate × ROIC

---

## Comparable Multiples Valuation

### Key Multiples (all from EODHD Valuation section)

| Multiple | Best for | Watch out for |
|----------|---------|---------------|
| P/E (trailing and forward) | Profitable companies | Distorted by one-time items; use normalized earnings |
| EV/EBITDA | Capital-intensive businesses, M&A | Doesn't capture capex or working capital needs |
| EV/Revenue (P/S) | High-growth, pre-profit companies | Wide range; must pair with margin trajectory |
| P/B | Financials, asset-heavy | Irrelevant for asset-light tech |
| P/FCF | All (gold standard) | FCF can be volatile year-to-year |
| EV/EBIT | Better than EV/EBITDA for capex-heavy | EBIT can be negative |

### Valuation via Multiples

```
Implied_EV = Peer_Median_EV/EBITDA × Company_EBITDA
Implied_Equity = Implied_EV - Net_Debt
Implied_Price = Implied_Equity / Shares_Outstanding
```

Always check whether the company deserves a premium or discount vs peers based on:
- Growth rate differential
- Margin differential
- ROIC differential
- Risk profile (leverage, geographic, customer concentration)

### Historical Multiple Analysis

Pull historical price data from `get_historical_stock_prices` and pair with historical earnings from fundamentals. Compute trailing P/E for each quarter over 5 years. Current multiple vs own historical average reveals mean-reversion potential.

---

## Bull/Base/Bear Scenario Framework

For each scenario, project revenue, margins, and multiples:

| Scenario | Probability | Revenue Growth | Margin | Multiple |
|----------|-------------|---------------|--------|----------|
| Bull | 20-25% | Upside case | Expansion | Re-rate higher |
| Base | 50-60% | Consensus-ish | Stable | Current multiple |
| Bear | 20-25% | Downside case | Compression | De-rate lower |

```
Expected_Value = P(Bull) × Bull_Price + P(Base) × Base_Price + P(Bear) × Bear_Price
Upside/Downside = (Bull_Price - Current) / (Current - Bear_Price)
```

Target asymmetry: look for 3:1 or better upside-to-downside ratios.

---

## FRED API Series Reference

| Series ID | Description | Use in Valuation |
|-----------|-------------|-----------------|
| DGS10 | 10-Year Treasury Constant Maturity Rate | Risk-free rate for WACC |
| DGS2 | 2-Year Treasury Rate | Yield curve analysis |
| DFF | Federal Funds Effective Rate | Monetary policy context |
| BAMLC0A0CM | ICE BofA US Corporate Index OAS | Credit spread context |
| BAA | Moody's BAA Corporate Bond Yield | Cost of debt benchmark |
| AAA | Moody's AAA Corporate Bond Yield | Cost of debt benchmark |
| CPIAUCSL | CPI (All Urban Consumers) | Real vs nominal adjustment |
| GDP | Nominal GDP | Terminal growth rate cap |
| GDPC1 | Real GDP | Real growth rate reference |

**FRED API pattern:**
```
https://api.stlouisfed.org/fred/series/observations?series_id={SERIES_ID}&api_key={KEY}&sort_order=desc&limit=1&file_type=json
```
