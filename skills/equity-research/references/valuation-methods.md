# Valuation Methods Reference

## Table of Contents
1. [Comparable Company Analysis (Comps)](#1-comparable-company-analysis)
2. [Discounted Cash Flow (DCF)](#2-discounted-cash-flow)
3. [Dividend Discount Model (DDM)](#3-dividend-discount-model)
4. [Sum-of-the-Parts (SOTP)](#4-sum-of-the-parts)
5. [Sector-Specific Valuation Notes](#5-sector-specific-notes)
6. [Synthesis: Building a Fair Value Range](#6-synthesis)

---

## 1. Comparable Company Analysis

### When to Use
Always. Comps is the primary valuation cross-check for every analysis.

### Step-by-Step Procedure

**Step 1: Identify the peer group (5-15 companies)**

```
→ get_fundamentals_data(ticker, sections=["General","Highlights","Valuation"], include_financials=false)
```
Extract: GicSubIndustry, MarketCapitalization, OperatingMarginTTM, QuarterlyRevenueGrowthYOY.

Use `stock_screener` to find peers:
```
→ stock_screener(filters=[
    ["market_capitalization", ">", target_mcap * 0.25],
    ["market_capitalization", "<", target_mcap * 4],
    ["sector", "=", target_gics_sector],
    ["exchange", "=", "US"]
  ], limit=30, sort="market_capitalization.desc")
```

Refine by: same GICS sub-industry first, then broaden to industry/group if <5 peers. Filter for similar growth profile (±10pp revenue growth) and margin profile.

**Step 2: Pull multiples for each peer**

For each peer, use `get_fundamentals_data` with `sections=["Highlights","Valuation"]`:

| Multiple | Source Fields | When to Use |
|----------|-------------|-------------|
| P/E (trailing) | `Valuation.TrailingPE` | Most stocks (20 of 25 GICS groups) |
| P/E (forward) | `Valuation.ForwardPE` | Preferred when earnings are growing |
| EV/EBITDA | `Valuation.EnterpriseValueEbitda` | Capital-intensive, telecom, energy, industrials |
| EV/Revenue | `Valuation.EnterpriseValueRevenue` | High-growth unprofitable companies (SaaS, biotech) |
| P/B | `Valuation.PriceBookMRQ` | Banks, insurance, REITs |
| PEG | `Highlights.PEGRatio` | Growth-adjusted P/E comparison |
| P/S | `Valuation.PriceSalesTTM` | Retailers, early-stage tech |

**Step 3: Compute peer statistics**

From the peer set, compute: median, mean, 25th percentile, 75th percentile for each relevant multiple.

**Step 4: Apply to target**

```
Implied share price = Target's financial metric × Peer median multiple
```

For P/E: `Implied Price = EPS_TTM × Peer_Median_PE`
For EV/EBITDA: `Implied EV = EBITDA × Peer_Median_EV_EBITDA → Implied Equity = EV - Net Debt → Price = Equity / Shares`
For forward P/E: `Implied Price = EPSEstimateNextYear × Peer_Median_ForwardPE`

**Step 5: Present as a range**
Use 25th-75th percentile multiples to generate a valuation range, not just point estimate.

### Batch Optimization
For large peer sets, use `get_bulk_fundamentals` instead of individual calls:
```
→ get_bulk_fundamentals(exchange="US", symbols="AAPL,MSFT,GOOG,META,AMZN")
```
Returns Highlights + Valuation for all tickers in one call (100 API credits).

---

## 2. Discounted Cash Flow

### When to Use
Non-financial companies with predictable cash flows. NOT for banks (use DDM or excess return model), insurance, or pre-revenue companies.

### Step-by-Step Procedure

**Step 1: Gather historical financials (last 3-5 years)**

```
→ get_fundamentals_data(ticker, include_financials=true)
```

Extract from Income_Statement (quarterly, last 12-20 quarters):
- totalRevenue, grossProfit, operatingIncome, ebitda, netIncome
- depreciationAndAmortization, incomeTaxExpense, incomeBeforeTax

Extract from Cash_Flow:
- totalCashFromOperatingActivities, capitalExpenditures, freeCashFlow
- changeInWorkingCapital, stockBasedCompensation

Extract from Balance_Sheet (latest quarter):
- shortLongTermDebtTotal (or longTermDebt + shortTermDebt)
- cashAndShortTermInvestments
- totalStockholderEquity

**Step 2: Compute historical metrics**

```
Revenue Growth Rate (3Y CAGR) = (Revenue_latest / Revenue_3y_ago)^(1/3) - 1
Operating Margin = operatingIncome / totalRevenue
Effective Tax Rate = incomeTaxExpense / incomeBeforeTax
CapEx/Revenue = capitalExpenditures / totalRevenue
FCF Margin = freeCashFlow / totalRevenue
D&A/Revenue = depreciationAndAmortization / totalRevenue
NWC/Revenue = changeInWorkingCapital / ΔRevenue
```

**Step 3: Build WACC**

```
→ get_ust_yield_rates(year=current_year)  # latest 10Y rate
```
Extract the most recent 10Y tenor rate as risk-free rate (Rf).

From fundamentals:
```
Beta = Technicals.Beta (or compute via get_technical_indicators function=beta, code2=SPY.US)
Market Cap (E) = Highlights.MarketCapitalization
Total Debt (D) = Balance_Sheet.shortLongTermDebtTotal
Tax Rate (t) = effective tax rate from Step 2
Cost of Equity (Ke) = Rf + Beta × 5.5%  (5.5% = default ERP)
Cost of Debt (Kd) = interestExpense / avgDebt (from Income_Statement / Balance_Sheet)
  If interestExpense is null or 0: use Rf + 1.5% as approximation
WACC = (E/(E+D)) × Ke + (D/(E+D)) × Kd × (1-t)
```

**Step 4: Project free cash flows (5 years)**

Base case projections using analyst estimates + historical trends:
```
Year 1 Revenue = RevenueTTM × (1 + analyst_implied_growth)
  analyst_implied_growth ≈ EPSEstimateNextYear/DilutedEpsTTM - 1 (approximate)
  or use historical revenue CAGR if estimate not available
Years 2-5: Taper growth toward terminal rate (2-3%)
```

For each projected year:
```
EBIT = Revenue × projected_operating_margin
NOPAT = EBIT × (1 - Tax Rate)
D&A = Revenue × (D&A/Revenue ratio, from historical)
CapEx = Revenue × (CapEx/Revenue ratio)
ΔNWC = ΔRevenue × (NWC/Revenue ratio)
UFCF = NOPAT + D&A - CapEx - ΔNWC
```

**Step 5: Terminal value**

Use **Exit Multiple method** (preferred for reliability):
```
Terminal Value = Year_5_EBITDA × Terminal_EV_EBITDA_Multiple
  Terminal multiple = peer median EV/EBITDA (from comps analysis)
```

Or **Gordon Growth method**:
```
Terminal Value = Year_5_FCF × (1 + g) / (WACC - g)
  where g = 2.0-2.5% (long-term nominal GDP growth)
  CRITICAL: g must be < WACC, and the difference should be > 2%
```

**Step 6: Discount and derive share price**

```
PV of projected FCFs = Σ UFCF_t / (1 + WACC)^t
PV of Terminal Value = TV / (1 + WACC)^5
Enterprise Value = PV(FCFs) + PV(TV)
Equity Value = EV - Net Debt
  Net Debt = Total Debt - Cash (from Balance_Sheet)
Implied Share Price = Equity Value / Diluted Shares Outstanding
  Shares from outstandingShares section (latest quarterly)
```

**Step 7: Sensitivity table**

ALWAYS present a sensitivity table varying:
- WACC: base ± 1% in 0.5% increments (5 columns)
- Terminal growth (or exit multiple): base ± 1% in 0.5% increments (5 rows)

Format as a clean grid showing implied share price at each intersection.

---

## 3. Dividend Discount Model

### When to Use
- Dividend yield > 2% AND stable/growing payout history
- Banks, utilities, REITs, mature consumer staples, telecoms, insurance
- Companies where FCF is hard to define (banks: debt is an operating asset)

### Step-by-Step Procedure

**Step 1: Gather dividend data**

```
→ get_fundamentals_data(ticker, sections=["Highlights","SplitsDividends"], include_financials=false)
→ get_upcoming_dividends(symbol=ticker, date_from="2020-01-01")
```

Extract: DividendShare, ForwardAnnualDividendRate, PayoutRatio, dividend history.

**Step 2: Compute dividend growth rate**

From historical dividends, compute:
```
DPS CAGR (5Y) = (DPS_latest / DPS_5y_ago)^(1/5) - 1
DPS CAGR (3Y) = (DPS_latest / DPS_3y_ago)^(1/3) - 1
Sustainable growth = ROE × (1 - PayoutRatio)
```

Use the lower of historical CAGR and sustainable growth.

**Step 3: Cost of Equity**
Same CAPM calculation as DCF Step 3.

**Step 4: Apply appropriate DDM variant**

**Gordon Growth (single-stage)** — for stable, mature dividend payers:
```
Intrinsic Value = DPS_forward / (Ke - g)
  where g = sustainable dividend growth rate
  CRITICAL: Ke - g must be > 1.5%, otherwise model breaks
```

**Two-stage DDM** — for companies with above-average near-term growth:
```
Stage 1 (Years 1-5): DPS growing at g1 (higher rate)
Stage 2 (Year 6+): DPS growing at g2 (terminal rate, 2-3%)

Value = Σ [DPS_0 × (1+g1)^t / (1+Ke)^t] for t=1..5
      + [DPS_5 × (1+g2) / (Ke - g2)] / (1+Ke)^5
```

**Step 5: Payout sustainability check**
```
Payout Ratio < 75% for non-REITs → Sustainable
Payout Ratio < 90% for REITs/utilities → Sustainable (higher is normal)
Payout Ratio > 100% → Dividend at risk, flag in analysis
FCF Payout = DividendsPaid / FreeCashFlow → should be < 80%
```

---

## 4. Sum-of-the-Parts

### When to Use
Companies with 2+ distinct business segments operating in different industries (e.g., Alphabet: Search/YouTube + Cloud + Waymo; Amazon: Retail + AWS + Ads; Berkshire Hathaway).

### Step-by-Step Procedure

**Step 1: Extract segment data from SEC filings**

Read `references/edgar-segments.md` for the full edgartools extraction procedure.

Quick pattern:
```bash
python3 << 'EOF'
import os
from edgar import Company, set_identity
set_identity(os.environ.get("EDGAR_IDENTITY", "Research Agent user@example.com"))
company = Company("TICKER")
tenk = company.get_filings(form="10-K")[0].obj()
facts = tenk.financials.xb.facts.to_dataframe()
# Filter for segment revenue
seg_rev = facts[
    (facts['concept'] == 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax') &
    (facts['dim_us-gaap_StatementBusinessSegmentsAxis'].notna())
]
# Filter for segment operating income
seg_oi = facts[
    (facts['concept'] == 'us-gaap:OperatingIncomeLoss') &
    (facts['dim_us-gaap_StatementBusinessSegmentsAxis'].notna())
]
EOF
```

**Step 2: Value each segment separately**

For each segment:
1. Identify pure-play comps (companies operating primarily in that segment's industry)
2. Screen using `stock_screener` with appropriate sector/industry filters
3. Pull peer multiples using `get_fundamentals_data` or `get_bulk_fundamentals`
4. Apply the most appropriate multiple:
   - Growth segments: EV/Revenue
   - Profitable segments: EV/EBITDA
   - Stable/mature: P/E or EV/EBIT

```
Segment Value = Segment Revenue (or EBITDA) × Peer Median Multiple
```

**Step 3: Sum and adjust**

```
Total Enterprise Value = Σ Segment Values
Less: Corporate overhead (if not allocated to segments)
  Overhead = Total Operating Expenses - Σ Segment Operating Expenses
  Value corporate overhead as a negative: -Overhead × peer overhead multiple (8-10×)
Less: Net Debt (from consolidated balance sheet)
Add: Cash & investments (from consolidated balance sheet)
Add: Value of equity investments (if material, from 10-K)
Equity Value = Total EV - Net Debt + Cash + Investments
Implied Price = Equity Value / Shares Outstanding
```

**Step 4: Conglomerate discount assessment**
```
Implied conglomerate discount = 1 - (Current Market Cap / SOTP Equity Value)
Typical range: 10-30%
If discount > 30%: potential catalyst for activist involvement or spinoff
If discount < 10%: market already values segments efficiently
```

---

## 5. Sector-Specific Notes

### Banks & Financials
- **DO NOT use DCF or EV/EBITDA** — debt is an operating asset, not a financing choice
- **Use**: P/E, P/B (book value is meaningful), P/TBV (tangible book), DDM
- **Use Praams bank endpoints** for specialized financials:
  ```
  → get_mp_praams_bank_income_statement_by_ticker(ticker)  # NII, fee income, provisions
  → get_mp_praams_bank_balance_sheet_by_ticker(ticker)     # loans, deposits, IEA
  ```
- Key metrics: NIM (net interest margin), efficiency ratio, NPL ratio, CET1 ratio, ROE, ROTCE

### REITs
- **Use**: P/FFO, P/AFFO (not P/E — depreciation is meaningless for real estate)
- FFO = Net Income + D&A - Gains on property sales (compute from financials)
- AFFO = FFO - maintenance capex - straight-line rent adjustments
- Key metrics: dividend yield, payout ratio (as % of FFO), NAV discount/premium

### Utilities
- **Use**: P/E, DDM, EV/EBITDA
- Regulatory framework determines earnings power — check allowed ROE
- Key metrics: regulated vs merchant revenue mix, rate base growth, dividend yield

### Biotech / Pre-Revenue
- **Use**: EV/Revenue (if any), pipeline value (risk-adjusted NPV), comparable deal values
- Standard DCF is unreliable — too dependent on binary clinical outcomes
- Key: cash runway (cash / quarterly burn rate), pipeline stage, addressable market

### SaaS / High-Growth Tech
- **Use**: EV/Revenue (NTM), EV/Gross Profit, Rule of 40 (growth + margin)
- Forward multiples preferred over trailing (growth changes quickly)
- Key metrics: ARR growth, net dollar retention, gross margin, FCF margin

---

## 6. Synthesis: Building a Fair Value Range

After running applicable methods, synthesize as follows:

1. **Weight by reliability**: Comps (40%), DCF (35%), DDM (25%) — adjust per situation
2. **Compute weighted average** of implied prices from each method
3. **Set the range**: Use ±1 standard deviation of the method outputs, or the 25th-75th percentile if >3 methods
4. **Compare to current price**: Calculate upside/downside as % from current market price
5. **Assign a rating**:
   - **Buy**: >15% upside to fair value midpoint
   - **Hold**: -10% to +15%
   - **Sell**: >10% downside to fair value midpoint
6. **State conviction**: High (3+ methods agree within 10%), Medium (methods agree within 20%), Low (wide dispersion)
