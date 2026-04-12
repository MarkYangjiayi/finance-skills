# Earnings Analysis & Signals Reference

Read this file when performing Phase 5 (Signals & Sentiment) or when the user asks specifically about earnings quality, management credibility, or consensus analysis.

## Earnings Surprise Analysis Framework

### Data Source

**EODHD Earnings History** — returned inside `get_fundamentals_data` under `Earnings.History`. Each entry has:
- `reportDate`: when the company reported
- `epsActual`: actual EPS
- `epsEstimate`: consensus estimate at report time
- `epsDifference`: actual minus estimate
- `surprisePercent`: percentage beat/miss

### Beat/Miss Pattern Classification

Analyze the last 8-12 quarters and classify the pattern:

| Pattern | Description | Signal |
|---------|-------------|--------|
| **Consistent beater** | Beats 80%+ of quarters by small amounts (1-5%) | Management sandbagging guidance; likely conservative |
| **Volatile surprises** | Alternates beats and misses or has large swings | Poor visibility or volatile business; harder to model |
| **Deteriorating** | Beat magnitude shrinking or switching from beats to misses | Fundamentals weakening; may precede guidance cut |
| **Accelerating** | Beat magnitude growing over time | Business inflecting positively; momentum signal |
| **Miss and lower** | Recent miss followed by guidance reduction | Potential structural issue; highest risk pattern |

### Consensus Estimates Analysis

From `eodhd-mcp:get_earnings_trends`:
- `earningsEstimateAvg`, `earningsEstimateHigh`, `earningsEstimateLow` — current quarter and next quarter
- `revenueEstimateAvg`, `revenueEstimateHigh`, `revenueEstimateLow`
- `earningsEstimateNumberOfAnalysts` — coverage breadth
- `earningsEstimateGrowth` — consensus growth rate

Key metrics to derive:
- **Estimate dispersion** = (High - Low) / Average — wider dispersion means more uncertainty
- **Revision direction** = compare current estimates to 30/60/90 day prior (if available in trend data)
- **Coverage trend** = declining analyst count may indicate reduced interest or MiFID II attrition

### The "Beat and Raise" Framework

This is the standard classification sell-side analysts use:

| Current Quarter | Forward Guidance | Market Reaction Pattern |
|----------------|-----------------|------------------------|
| Beat | Raise | Most bullish — execution + confidence. Typically strong positive reaction. |
| Beat | Maintain | Moderately positive — good execution, cautious outlook. |
| Beat | Lower | Negative despite beat — the guidance cut signals forward problems. |
| Miss | Raise | Rare and confusing — typically due to one-time items; investigate what was missed and what drove the raise. |
| Miss | Maintain | Moderately negative — stumble but not structural. |
| Miss | Lower | Most bearish — execution failure + deteriorating outlook. Typically sharp selloff. |

### Management Credibility Scoring

Track management's guidance accuracy over time:

```
For each quarter:
  Guidance_Accuracy = (Actual_Result - Midpoint_of_Guidance) / Midpoint_of_Guidance

Over 4-8 quarters:
  Average_Accuracy = mean of quarterly accuracy scores
  Accuracy_Consistency = standard deviation of quarterly accuracy scores
```

| Profile | Avg Accuracy | Std Dev | Assessment |
|---------|-------------|---------|-----------|
| Conservative sandbagging | +2% to +5% | Low (<2%) | Reliable; build model 2-3% above guidance |
| Straight shooter | -1% to +1% | Low (<2%) | Trustworthy guidance; model near midpoint |
| Promotional | +5% to +10% | Medium | May be gaming expectations; verify with cash flow |
| Unreliable | Variable | High (>5%) | Discount guidance; rely more on own model |
| Consistently miss | Negative | Any | Credibility problem; weight own analysis heavily |

---

## Insider Transaction Analysis

### Data Source

`eodhd-mcp:get_insider_transactions` returns SEC Form 4 filings with:
- `transactionDate`: when the trade occurred
- `transactionCode`: "P" (Purchase), "S" (Sale), "A" (Award/Grant), "M" (Option Exercise)
- `transactionShares`: number of shares
- `transactionPrice`: price per share
- `ownerName`: who traded
- `ownerRelationship`: CEO, CFO, Director, 10% Owner, etc.

### Signal Hierarchy (from strongest to weakest)

1. **CEO/CFO open-market purchase ("P")** — strongest bullish signal. Executives putting their own money at risk means they believe the stock is undervalued. Weight > $500K purchases most heavily.

2. **Cluster buying** — multiple different insiders buying in the same 2-week window. Even stronger than a single large purchase because it suggests broad insider confidence.

3. **Director purchases** — board members have less day-to-day visibility than executives but still possess material non-public awareness of company health.

4. **Insider selling** — much weaker signal. Most insider selling is routine (pre-planned 10b5-1 sales, diversification, tax obligations on vesting shares). Only investigate selling if:
   - It's a sudden deviation from the insider's historical pattern
   - Multiple executives sell large amounts in the same window
   - Selling occurs shortly before earnings or a major announcement
   - The insider has no 10b5-1 plan on file

5. **Option exercises followed by immediate sale ("M" + "S" same day)** — weakest signal, typically routine. Ignore unless the volume is extraordinary.

### Timing Analysis

- **Pre-earnings purchases** (within blackout window) — should not happen; if they do, may indicate the insider expects good results (or is violating trading policies)
- **Post-earnings purchases** (within 3 days of release) — the insider has seen the numbers and is buying; strong signal
- **Post-guidance-cut purchases** — extremely bullish; insider believes the market overreacted to bad news

### Quantitative Flags

```
Insider_Buy_Signal = Sum of insider purchase $ in last 90 days
Insider_Sell_Signal = Sum of insider sale $ in last 90 days (exclude 10b5-1 if identifiable)
Net_Insider_Activity = Buy_Signal - Sell_Signal
```

Compare to the company's market cap for context. $5M in insider buying means very different things for a $500M company vs a $500B company.

---

## News Sentiment Analysis

### Data Sources

1. **`eodhd-mcp:get_sentiment_data`** — returns daily sentiment scores per ticker
   - `count`: number of articles analyzed
   - `sentiment`: aggregate sentiment score
   - Useful for tracking sentiment trend over 30/60/90 days

2. **`eodhd-mcp:get_company_news`** — returns individual news articles
   - `title`, `content`: article text
   - `date`: publication date
   - `sentiment`: per-article sentiment data
   - Use to identify specific catalysts or concerns driving sentiment

3. **`eodhd-mcp:get_news_word_weights`** — returns weighted keywords from news
   - Reveals the dominant narrative themes (e.g., "restructuring", "growth", "investigation")
   - Track keyword shifts over time to detect narrative changes

### Sentiment Trend Analysis

Pull 90 days of sentiment data and compute:
- 30-day moving average of sentiment
- Direction of trend (improving/deteriorating/stable)
- Any sharp spikes (positive or negative) — cross-reference with news articles on those dates

### Narrative Theme Detection

From word weights, identify:
- **Bullish themes**: "growth", "expansion", "innovation", "beat", "upgrade", "dividend"
- **Bearish themes**: "investigation", "recall", "lawsuit", "downgrade", "restructuring", "layoffs"
- **Neutral operational**: "earnings", "revenue", "quarter", "guidance"

Track theme shifts between periods — a company's news narrative transitioning from "growth" to "restructuring" keywords is a leading indicator.

---

## Combining Signals: The Weight of Evidence Framework

Each signal provides a piece of the mosaic. Weight them as follows when forming an overall assessment:

| Signal Category | Weight | Rationale |
|----------------|--------|-----------|
| Forensic quality (M-Score, Sloan, CFO/NI) | Highest | These are fact-based, computed from audited data |
| Working capital trends (DSO/DIO/DPO) | High | Leading indicators of earnings problems |
| Insider purchases (not sales) | High | Skin-in-the-game with legal liability for mis-timing |
| Earnings surprise pattern | Medium | Historical pattern, not guaranteed to continue |
| Consensus estimate revisions | Medium | Reflects aggregated analyst views, but analysts herd |
| News sentiment | Low-Medium | Noisy, but extreme readings matter |
| Insider selling | Low | Too many benign explanations |

### Red Flag Escalation

If 2+ of these appear simultaneously, flag as requiring deeper investigation:
1. M-Score above -1.78
2. Sloan ratio above 15%
3. CFO/NI below 0.7x for 2+ years
4. DSO growing 10%+ faster than revenue
5. Insider cluster selling by C-suite
6. Declining analyst coverage (suggests banks dropping coverage due to concerns)
7. Auditor change, especially from Big 4 to non-Big 4
8. CFO departure (the person who signs off on the numbers is leaving)

When 3+ red flags co-occur, the probability of a material negative event (restatement, guidance cut, fraud revelation) is historically elevated. Use edgartools to pull the 10-K risk factors and compare to prior year — new risk factor language is itself a signal.
