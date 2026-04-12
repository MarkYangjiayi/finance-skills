# Forensic Accounting Formulas Reference

Read this file when computing forensic quality metrics in Phase 2. All formulas use two consecutive annual periods: current year (t) and prior year (t-1).

## Beneish M-Score: Complete 8-Variable Model

The M-Score detects earnings manipulation. Developed by Professor Messod Beneish (Indiana University, 1999). Each variable captures a different dimension of financial distortion.

### The Formula

```
M = -4.84 + 0.920×DSRI + 0.528×GMI + 0.404×AQI + 0.892×SGI
    + 0.115×DEPI - 0.172×SGAI + 4.679×TATA - 0.327×LVGI
```

### Variable Definitions

**1. DSRI — Days Sales in Receivables Index**
```
DSRI = (Receivables_t / Revenue_t) / (Receivables_{t-1} / Revenue_{t-1})
```
Measures whether receivables are growing disproportionately to revenue. DSRI > 1.0 means receivables grew faster than sales — a classic channel stuffing or aggressive revenue recognition signal.

EODHD fields: `netReceivables` (Balance Sheet), `totalRevenue` (Income Statement)

**2. GMI — Gross Margin Index**
```
GMI = Gross_Margin_{t-1} / Gross_Margin_t
where Gross_Margin = (Revenue - COGS) / Revenue
```
GMI > 1.0 means margins are deteriorating. Companies with deteriorating margins face pressure to manipulate earnings.

EODHD fields: `totalRevenue`, `costOfRevenue` (Income Statement)

**3. AQI — Asset Quality Index**
```
AQI = [1 - (Current_Assets_t + PP&E_t + Securities_t) / Total_Assets_t]
    / [1 - (Current_Assets_{t-1} + PP&E_{t-1} + Securities_{t-1}) / Total_Assets_{t-1}]
```
Measures the proportion of "soft" or intangible assets. AQI > 1.0 means a growing share of assets are non-physical — potentially indicating cost capitalization (what WorldCom did with $3.8B in operating expenses).

EODHD fields: `totalCurrentAssets`, `propertyPlantEquipment`, `shortTermInvestments`, `totalAssets` (Balance Sheet)

Note: If `securities` / `shortTermInvestments` is not available, use 0 or omit from numerator. The key insight is tracking the ratio of hard assets to total assets.

**4. SGI — Sales Growth Index**
```
SGI = Revenue_t / Revenue_{t-1}
```
High growth companies face more pressure to maintain growth and have more opportunity to manipulate. Not a manipulation indicator on its own, but amplifies other signals.

**5. DEPI — Depreciation Index**
```
DEPI = Depreciation_Rate_{t-1} / Depreciation_Rate_t
where Depreciation_Rate = Depreciation / (Depreciation + PP&E)
```
DEPI > 1.0 means the depreciation rate is slowing, suggesting the company is revising useful life estimates upward to reduce expenses and inflate earnings.

EODHD fields: `depreciation` (Cash Flow or Income Statement), `propertyPlantEquipment` (Balance Sheet)

**6. SGAI — SGA Expense Index**
```
SGAI = (SGA_t / Revenue_t) / (SGA_{t-1} / Revenue_{t-1})
```
Measures selling/general/administrative cost efficiency. SGAI > 1.0 means SGA is growing faster than revenue, suggesting declining efficiency. The negative coefficient (-0.172) means higher SGAI actually reduces the M-Score — the logic is that companies cutting SGA disproportionately (SGAI < 1.0) may be doing so to artificially inflate earnings.

EODHD fields: `sellingGeneralAdministrative` (Income Statement)

**7. TATA — Total Accruals to Total Assets** (Most important variable — coefficient 4.679)
```
TATA = (Net_Income_t - CFO_t) / Total_Assets_t
```
This is the single strongest manipulation signal. A large positive TATA means reported earnings far exceed cash earnings — the gap is filled by accounting accruals. This is the variable that flagged Enron.

EODHD fields: `netIncome` (Income Statement), `totalCashFromOperatingActivities` (Cash Flow), `totalAssets` (Balance Sheet)

**8. LVGI — Leverage Index**
```
LVGI = Leverage_t / Leverage_{t-1}
where Leverage = Total_Debt / Total_Assets
```
Rising leverage increases the pressure to meet debt covenants, creating incentive to manipulate.

EODHD fields: `shortTermDebt`, `longTermDebt`, `totalAssets` (Balance Sheet)

### Interpretation

| M-Score Range | Assessment | Action |
|---------------|-----------|--------|
| Below -2.22 | Low manipulation risk | Standard analysis |
| -2.22 to -1.78 | Grey zone | Investigate TATA and DSRI specifically |
| Above -1.78 | High manipulation probability | Deep forensic dive; investigate footnotes via edgartools |

When M-Score flags high risk, report which sub-indices are the primary drivers:
- High TATA → earnings not backed by cash
- High DSRI → receivables outpacing revenue
- High AQI → rising soft/intangible assets
- High DEPI → slowing depreciation rates

### Historical Accuracy

The model correctly identified 76% of known manipulators while incorrectly flagging 17.5% of non-manipulators. It flagged Enron as a likely manipulator in 1998 — three years before the collapse.

---

## Sloan Accruals Ratio

Richard Sloan's 1996 research showed that companies with high accruals systematically underperform.

### Formula

```
Sloan_Ratio = (Net_Income - CFO) / Average_Total_Assets
where Average_Total_Assets = (Total_Assets_t + Total_Assets_{t-1}) / 2
```

### Interpretation

| Range | Assessment |
|-------|-----------|
| -10% to +10% | Normal — earnings largely backed by cash |
| +10% to +15% | Caution — elevated accruals, investigate |
| Above +15% | Red flag — earnings heavily reliant on accruals |
| Below -10% | Cash earnings significantly exceed reported — usually positive |

### Notes
- Compute for each of the last 3-5 years to identify trend
- A company consistently in the +5% to +15% range is concerning even if never above +15%
- Combine with TATA from M-Score for a robust accruals assessment

---

## CFO-to-Net-Income Quality Ratio

### Formula

```
Quality_Ratio = CFO / Net_Income
```

### Interpretation

| Range | Assessment |
|-------|-----------|
| > 1.2x | High quality — strong cash backing, typical for asset-light businesses |
| 1.0x to 1.2x | Good quality — cash roughly matches reported earnings |
| 0.7x to 1.0x | Moderate concern — some earnings not converting to cash |
| < 0.7x | Serious concern — significant portion of earnings are non-cash |
| < 0.5x for 2+ years | Major red flag — investigate immediately |

### Caveats
- For high-growth companies investing heavily in working capital, a ratio below 1.0 may be normal temporarily
- Negative net income makes the ratio meaningless — switch to absolute CFO assessment
- Seasonal businesses may show volatile quarterly ratios but stable annual ones

---

## Channel Stuffing Detection

### Signals to Check

1. **DSO vs Revenue growth divergence**
   ```
   DSO_Growth = (DSO_t - DSO_{t-1}) / DSO_{t-1}
   Revenue_Growth = (Revenue_t - Revenue_{t-1}) / Revenue_{t-1}
   Gap = DSO_Growth - Revenue_Growth
   ```
   Gap > 5 percentage points = warning signal

2. **Quarter-end revenue concentration**
   Check if the final month of each quarter accounts for >40% of quarterly revenue (requires monthly data if available, otherwise compare Q4 to full-year)

3. **Receivables turnover deceleration**
   ```
   AR_Turnover = Revenue / Average_Receivables
   ```
   Declining AR turnover for 2+ consecutive quarters while revenue grows = red flag

4. **Allowance for doubtful accounts**
   If available via edgartools, check if the bad debt reserve as % of gross receivables is declining while receivables grow — suggests under-reserving

---

## Cookie-Jar Reserve Detection

### What to Look For

1. **Reserve-to-sales ratio volatility**
   - Pull warranty reserves, bad debt reserves, restructuring reserves from balance sheet notes (via edgartools)
   - Compute reserve/revenue ratio each period
   - Erratic patterns (big build-up → big release) suggest earnings smoothing

2. **Suspiciously smooth earnings**
   - Compute earnings volatility (std dev of YoY earnings growth)
   - Compare to revenue volatility
   - If revenue is volatile but earnings are smooth, reserves may be absorbing the variance

3. **Restructuring charge persistence**
   - If restructuring charges appear in 3+ consecutive years, they are effectively recurring costs being excluded from "adjusted" earnings
   - Track cumulative "non-recurring" items over 5 years as % of cumulative GAAP earnings

---

## Altman Z-Score (supplementary solvency check)

While not a manipulation detector, the Z-Score provides solvency context. For manufacturing companies:

```
Z = 1.2×(WC/TA) + 1.4×(RE/TA) + 3.3×(EBIT/TA) + 0.6×(MVE/TL) + 1.0×(Sales/TA)

where:
  WC = Working Capital (Current Assets - Current Liabilities)
  TA = Total Assets
  RE = Retained Earnings
  EBIT = Earnings Before Interest and Taxes
  MVE = Market Value of Equity (from EODHD Highlights.MarketCapitalization)
  TL = Total Liabilities
```

| Z-Score | Assessment |
|---------|-----------|
| > 2.99 | Safe zone |
| 1.81 to 2.99 | Grey zone |
| < 1.81 | Distress zone |

For non-manufacturing / service firms, use the revised Z''-Score model which drops the Sales/TA term and adjusts coefficients.
