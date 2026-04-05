# SEC EDGAR Segment Data Extraction (edgartools)

## Overview
`edgartools` provides structured access to SEC XBRL filings, enabling extraction of segment-level revenue and operating income that EODHD does not provide. This is critical for Sum-of-the-Parts (SOTP) valuation.

## Prerequisites
```bash
pip install edgartools --break-system-packages
```

## Core Extraction Pattern

### Step 1: Load Company and Latest 10-K

```python
import os
from edgar import Company, set_identity
import pandas as pd

# SEC EDGAR fair-use policy requires a real name + email. Set EDGAR_IDENTITY env var,
# or ask the user for their name/email before running.
set_identity(os.environ.get("EDGAR_IDENTITY", "Research Agent user@example.com"))

company = Company("TICKER")  # e.g., "GOOG", "AMZN", "BRK-A"
filings = company.get_filings(form="10-K")
tenk = filings[0].obj()  # latest 10-K

# Access XBRL data
facts = tenk.financials.xb.facts.to_dataframe()
```

### Step 2: Extract Segment Revenue

```python
# Revenue by business segment
seg_rev = facts[
    (facts['concept'] == 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax') &
    (facts['is_dimensioned'] == True) &
    (facts['dim_us-gaap_StatementBusinessSegmentsAxis'].notna())
].copy()

# Deduplicate (facts may appear in multiple disclosure roles)
seg_rev = seg_rev.drop_duplicates(subset=['label', 'period_end', 'numeric_value'])

# Clean output
for period in sorted(seg_rev['period_end'].unique()):
    period_data = seg_rev[seg_rev['period_end'] == period]
    print(f"\n--- FY {period} ---")
    for _, row in period_data.sort_values('numeric_value', ascending=False).iterrows():
        rev_b = row['numeric_value'] / 1e9
        segment = row['dim_us-gaap_StatementBusinessSegmentsAxis']
        print(f"  {row['label']:45s}  ${rev_b:>8.1f}B  [{segment}]")
```

### Step 3: Extract Segment Operating Income

```python
seg_oi = facts[
    (facts['concept'] == 'us-gaap:OperatingIncomeLoss') &
    (facts['is_dimensioned'] == True) &
    (facts['dim_us-gaap_StatementBusinessSegmentsAxis'].notna())
].copy()

seg_oi = seg_oi.drop_duplicates(subset=['dim_us-gaap_StatementBusinessSegmentsAxis', 'period_end', 'numeric_value'])
```

### Step 4: Extract Revenue by Product/Service (Sub-Segment)

Some companies report sub-segment detail (e.g., Alphabet: Google Search, YouTube, Network within Google Services):

```python
product_rev = facts[
    (facts['concept'] == 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax') &
    (facts['is_dimensioned'] == True) &
    (facts['dim_srt_ProductOrServiceAxis'].notna())
].copy()

product_rev = product_rev.drop_duplicates(subset=['label', 'period_end', 'numeric_value'])
```

### Step 5: Extract Geographic Revenue

```python
geo_rev = facts[
    (facts['concept'] == 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax') &
    (facts['is_dimensioned'] == True) &
    (facts['dim_srt_StatementGeographicalAxis'].notna())
].copy()
```

## Key XBRL Dimension Columns

| Column | What It Contains | Use Case |
|--------|-----------------|----------|
| `dim_us-gaap_StatementBusinessSegmentsAxis` | Reportable segment | Segment revenue/OI |
| `dim_srt_ProductOrServiceAxis` | Product/service line | Sub-segment revenue |
| `dim_srt_StatementGeographicalAxis` | Geographic region | Geographic breakdown |
| `dim_srt_ConsolidationItemsAxis` | Elimination/corp entries | Inter-segment adjustments |

## Alternative Revenue Concepts

Not all companies use the same XBRL revenue concept. If the primary concept returns empty, try:

```python
# Alternative revenue concepts
revenue_concepts = [
    'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',  # ASC 606 (most common)
    'us-gaap:Revenues',                                              # Legacy
    'us-gaap:SalesRevenueNet',                                       # Legacy
    'us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax',   # Gross revenue
]

for concept in revenue_concepts:
    seg = facts[
        (facts['concept'] == concept) &
        (facts['dim_us-gaap_StatementBusinessSegmentsAxis'].notna())
    ]
    if len(seg) > 0:
        print(f"Found {len(seg)} segment revenue facts using {concept}")
        break
```

## Alternative Operating Income Concepts

```python
oi_concepts = [
    'us-gaap:OperatingIncomeLoss',
    'us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
    'us-gaap:GrossProfit',  # If OI not reported by segment
]
```

## Handling Different Company Types

### Conglomerates (Alphabet, Amazon, Meta)
Typically have clean segment reporting via `StatementBusinessSegmentsAxis`.
- Alphabet: Google Services, Google Cloud, Other Bets
- Amazon: North America, International, AWS
- Meta: Family of Apps, Reality Labs

### Financials / Banks
May use different segment axes. Check:
```python
# Find all dimension columns that have data
dim_cols = [c for c in facts.columns if c.startswith('dim_') and facts[c].notna().any()]
print("Available dimensions:", dim_cols)
```

### Companies Without XBRL Segments
Some smaller companies don't tag segment data in XBRL. Fallback options:
1. Use `tenk.management_discussion` to read the MD&A section (unstructured text)
2. Use `tenk.notes` to access financial statement notes
3. Parse `tenk.business` for business description

```python
# Access 10-K text sections
mda = tenk.management_discussion  # MD&A text
notes = tenk.notes                # Financial notes
business = tenk.business          # Business description
```

## Accessing Financial Statements Directly

edgartools also provides parsed financial statements:

```python
# Consolidated income statement (3 years)
income = tenk.income_statement
print(income)

# Consolidated balance sheet
balance = tenk.balance_sheet
print(balance)

# Cash flow statement
cashflow = tenk.cash_flow_statement
print(cashflow)
```

These are formatted tables with multi-year comparisons, useful for quick cross-checks against EODHD data.

## Complete SOTP Extraction Script

```python
import os
from edgar import Company, set_identity
import pandas as pd
import json

set_identity(os.environ.get("EDGAR_IDENTITY", "Research Agent user@example.com"))

def extract_segments(ticker):
    """Extract segment revenue and operating income for SOTP valuation."""
    company = Company(ticker)
    tenk = company.get_filings(form="10-K")[0].obj()
    facts = tenk.financials.xb.facts.to_dataframe()
    
    result = {"ticker": ticker, "filing_date": str(tenk.filing_date), "segments": {}}
    
    # Revenue by segment
    seg_rev = facts[
        (facts['concept'] == 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax') &
        (facts['dim_us-gaap_StatementBusinessSegmentsAxis'].notna())
    ].drop_duplicates(subset=['label', 'period_end', 'numeric_value'])
    
    # Operating income by segment
    seg_oi = facts[
        (facts['concept'] == 'us-gaap:OperatingIncomeLoss') &
        (facts['dim_us-gaap_StatementBusinessSegmentsAxis'].notna())
    ].drop_duplicates(subset=['dim_us-gaap_StatementBusinessSegmentsAxis', 'period_end', 'numeric_value'])
    
    # Get latest period
    latest_period = seg_rev['period_end'].max()
    
    for _, row in seg_rev[seg_rev['period_end'] == latest_period].iterrows():
        seg_name = row['label']
        seg_axis = row['dim_us-gaap_StatementBusinessSegmentsAxis']
        
        # Match OI for same segment
        oi_match = seg_oi[
            (seg_oi['dim_us-gaap_StatementBusinessSegmentsAxis'] == seg_axis) &
            (seg_oi['period_end'] == latest_period)
        ]
        oi_val = oi_match['numeric_value'].iloc[0] if len(oi_match) > 0 else None
        
        result["segments"][seg_name] = {
            "revenue": row['numeric_value'],
            "operating_income": oi_val,
            "segment_axis_member": seg_axis,
            "period": str(latest_period)
        }
    
    return result

# Usage
segments = extract_segments("GOOG")
print(json.dumps(segments, indent=2, default=str))
```

## Error Handling

```python
try:
    company = Company(ticker)
    filings = company.get_filings(form="10-K")
    if len(filings) == 0:
        print(f"No 10-K filings found for {ticker}")
        # Fallback: try 10-K/A (amended)
        filings = company.get_filings(form="10-K/A")
    
    tenk = filings[0].obj()
    facts = tenk.financials.xb.facts.to_dataframe()
    
except Exception as e:
    print(f"edgartools error for {ticker}: {e}")
    print("Falling back to consolidated-only analysis (no segment data)")
    # Agent proceeds with EODHD consolidated financials only
```

## Rate Limiting
SEC EDGAR limits to 10 requests per second. edgartools handles this automatically via built-in rate limiting. For batch operations across many tickers, add small delays:

```python
import time
for ticker in ticker_list:
    result = extract_segments(ticker)
    time.sleep(0.5)  # extra safety margin
```
