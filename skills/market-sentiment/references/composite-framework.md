# Composite Scoring Framework

How to aggregate multiple sentiment indicators into a single score, based on the research literature and adapted for the data sources this skill has access to.

Read this at Stage 4 of the workflow when you're computing the composite, and especially if the user asks "why did you weight it that way?" or "what does the composite actually mean?"

---

## The core idea

No single sentiment indicator reliably times markets. The research is unambiguous on this — in-sample fit is often decent (R² of 3-15%), but out-of-sample predictive power is much weaker for nearly every individual measure. What does work better:

1. **Composite indices beat individual indicators** in direct empirical comparisons (Baker-Wurgler 2006 and replications).
2. **The construction method matters**. PLS (partial least squares) beats PCA (Huang, Jiang, Tu, Zhou 2015). Both beat naive averaging, but only slightly.
3. **Even composites don't reliably predict aggregate market direction.** Their strongest empirical support is cross-sectional — sentiment affects which stocks outperform, not whether the market rises or falls.

Given these findings, this skill uses a **conservative weighted z-score approach** rather than pretending we can do sophisticated PLS with such a small and heterogeneous indicator set. The goal is *honest aggregation* — show the user where the mood sits, not predict tomorrow's move.

---

## The three-step process

### Step 1: Compute trailing z-scores

For each indicator, compute:
```
z_i = (current_value - mean_3y) / std_3y
```
Using the **trailing 3-year window** (roughly 750 trading days). Three years is long enough to span a cycle fragment but short enough to avoid regime-dependence (HY spreads in 2005 are not comparable to HY spreads in 2024 after QE).

**Why not use longer history?** Because financial regimes shift. The 1990s VIX distribution was fundamentally different from the 2020s VIX distribution, so standardising against 30 years of VIX history gives you a reading anchored to a world that no longer exists.

**Why not use shorter history?** Because sub-year windows don't give enough extreme observations. You can't know what a real "extreme" looks like from 6 months of data.

### Step 2: Sign-align every indicator

This is where most amateur composites go wrong. Different indicators have opposite semantics:
- High VIX = fear
- High HY spread = fear
- High 10Y-2Y spread = optimism (normal curve)
- High gold/copper ratio = fear
- High news sentiment score = optimism
- High NFCI = tighter conditions = fear

You need to flip signs so that **after alignment, a positive z-score consistently means "greedy / complacent / risk-on" and a negative z-score consistently means "fearful / stressed / risk-off"**.

The full sign-alignment table:

| Indicator | Raw interpretation | Sign flip? | Aligned z meaning |
|---|---|---|---|
| HY credit spread | High = fear | **FLIP** | +z = complacent |
| IG credit spread | High = fear | **FLIP** | +z = complacent |
| HY-IG differential | High = quality fear | **FLIP** | +z = complacent |
| 10Y-2Y yield curve | High = normal, low/inverted = recession fear | No flip | +z = bullish |
| 10Y-3M yield curve | Same | No flip | +z = bullish |
| NFCI | High = tight | **FLIP** | +z = loose conditions (bullish) |
| STLFSI4 | High = stress | **FLIP** | +z = calm (bullish) |
| VIX level | High = fear | **FLIP** | +z = complacent |
| VIX3M/VIX ratio | High = contango = normal, low = backwardation = fear | No flip | +z = normal term structure (bullish) |
| VIX9D/VIX ratio | Same logic | No flip | +z = normal |
| CBOE SKEW | High = tail hedging = *some* fear (but see interpretation.md) | **FLIP** (with caveat) | +z = low tail fear |
| Gold/copper ratio | High = risk-off | **FLIP** | +z = risk-on |
| USD/JPY level | High (yen weak) = risk-on carry | No flip | +z = risk-on |
| SPY price (trend vs 200dma) | Above 200dma = risk-on | No flip | +z = risk-on |
| HY bond ETF (HYG) return vs Treasury (TLT) | HYG outperforming = risk-on | No flip | +z = risk-on |
| EODHD news sentiment | High normalized = bullish | No flip | +z = bullish |
| Crypto F&G | High = greed | No flip | +z = greed |
| Leveraged money net long in ES (COT) | Extreme positive = crowded long (contrarian bearish) | **FLIP** (contrarian) | +z = contrarian bearish position |
| Commercial net long in GC (COT) | Extreme positive = hedgers are long (contrarian bullish) | No flip | +z = contrarian bullish position |

**Handling COT data specifically**: This is the trickiest part. COT positioning is a *contrarian* indicator at extremes, which means the sign convention depends on which group you're looking at. The rule to remember:

- **Leveraged money / non-commercials / managed money** are trend followers. Their extremes mark exhaustion. So when they are maximally long, that's a **bearish** signal (align as NEGATIVE).
- **Commercial hedgers / producers** tend to be contrarians / mean-reverters. When they're maximally long, that's a **bullish** signal (align as POSITIVE).

This is the single place in the framework where the "high = bullish" intuition breaks down, so handle COT explicitly rather than treating it like a normal price series.

### Step 3: Weighted aggregation

Once every indicator is sign-aligned, bucket them by tier and compute weighted averages.

**Tier 1** (strongest evidence, always included — weight 2.0 each):
- HY credit spread
- IG credit spread (or HY-IG differential — pick one to avoid double-counting)
- 10Y-2Y curve
- NFCI
- VIX level
- VIX3M/VIX ratio (backwardation signal)
- SKEW (optional; weight 1.0 due to ambiguous interpretation)

**Tier 2** (supporting evidence — weight 1.0 each):
- Gold/copper ratio
- USD/JPY
- Crypto F&G
- EODHD news sentiment (aggregate across SPY and QQQ if broad-market)
- COT leveraged money net position (as contrarian)
- SPY vs 200-day MA

**Composite formula**:
```
composite_z = (Σ(w_i × z_aligned_i)) / (Σ w_i)
```

### Step 4: Map to regime labels

| Composite z | Label | Historical meaning |
|---|---|---|
| `> +2.0` | **EXTREME GREED** | Contrarian sell zone. Rare (<5% of days). |
| `+1.0 to +2.0` | Greed | Above-average complacency. |
| `-1.0 to +1.0` | Neutral | Normal range — most days. |
| `-2.0 to -1.0` | Fear | Above-average stress. |
| `< -2.0` | **EXTREME FEAR** | Contrarian buy zone. Rare (<5% of days). |

**The labels are descriptive, not prescriptive**. An "Extreme Greed" reading does NOT mean "the market will crash tomorrow". It means the current mood is in the top ~5% of its 3-year distribution. Historically, these readings have coincided with subsequent underperformance on average, but with enormous variance.

---

## Alternative approaches (mentioned for completeness, not used by default)

If a user asks "why not use PCA / PLS?" — here's the honest answer.

### PCA (Principal Component Analysis)
Extracts the first principal component from a set of indicators. This is what Baker-Wurgler (2006) did. Advantage: captures the latent "true sentiment" factor. Disadvantages: (a) the first PC can be dominated by one or two high-variance indicators, (b) PC loadings are not interpretable, (c) requires a long enough historical window to stabilise, (d) the PC can flip sign between rolling windows.

**This skill doesn't use PCA because**: with only ~12-15 indicators on inconsistent frequencies (daily vs weekly) and different start dates, PCA would be dominated by whichever indicators have the most variance, and the first PC's stability is questionable.

### PLS (Partial Least Squares)
Huang, Jiang, Tu, Zhou (2015) showed PLS outperforms PCA by maximising covariance between indicators and the target (future returns). Advantage: directly optimises for predictive power. Disadvantages: (a) requires labeled training data (you need to define "future returns" for some horizon), (b) look-ahead bias if not done carefully, (c) results depend heavily on the chosen prediction horizon, (d) overfitting risk with small samples.

**This skill doesn't use PLS because**: it would require backtesting infrastructure the skill doesn't have, and the honest answer is we don't know what "the right" prediction horizon is — 1 month, 3 month, and 12 month PLS give very different weights.

### Factor rotation / dynamic weighting
Some practitioner frameworks (SentimenTrader's composite, etc.) use time-varying weights based on recent indicator performance. Advantage: adapts to regime. Disadvantage: classic data-mining trap — you end up overweighting whichever indicator worked recently.

**This skill doesn't use it because**: it's methodologically opaque and hard to explain honestly.

---

## Handling missing data

Not every indicator is available every day. NFCI is weekly. Consumer sentiment is monthly. Sometimes an API call fails. Here's how to handle it:

1. **Forward-fill weekly/monthly data** up to the current date. The last observation is still the current reading.
2. **If a Tier 1 indicator fails entirely**, proceed with a reduced Tier 1 set and note the omission in the "What the evidence does NOT tell you" section.
3. **If Tier 2 indicators fail**, just omit them. Tier 2 is supporting evidence.
4. **Never fabricate a substitute**. If HY spreads are unavailable, do not use HYG ETF price as a proxy without explicitly labeling it as a proxy.

---

## Edge cases

### "The composite says Neutral but HY spread is at the 95th percentile"

This is the single most important case in the framework. A neutral composite can mask extreme bifurcation. **Always surface the extreme flags separately from the composite**. The composite is one number; the flags are the actionable data. A report that only shows the composite has failed.

### "All Tier 1 indicators say fear but news sentiment says greed"

Note the divergence explicitly. News sentiment tends to be backward-looking — it reports what has already happened. Tier 1 financial indicators tend to be more forward-looking. When they disagree, weight Tier 1.

### "Composite is -1.5 (fear) but the market has been rallying for 2 weeks"

Possible explanations:
- The rally is a dead-cat bounce in a stressed regime (credit still wide, VIX still elevated).
- The indicators are lagging the price action (sentiment usually follows price with 1-2 week lag).
- The rally is correct and the indicators are about to normalise downward.

Report all three possibilities. Don't pick one.

### "User asks about a specific stock and the composite is neutral"

For single-stock analysis, the broad-market composite is not the right tool. Lean on:
- EODHD per-ticker news sentiment
- Per-ticker news word weights
- (If institutional) 13F ownership trends for that specific stock
- Sector-relative positioning

Note that the broad-market composite is neutral but also flag whether the user's stock is in a sector with specific stress signals.

---

## What a good composite output looks like

A well-formed composite output tells the user:

1. **The number** and the regime label
2. **The top 2-3 contributors** (which aligned z-scores were most extreme in either direction)
3. **The top 2-3 flagged indicators** (which individual readings are in the top/bottom 10%)
4. **The confidence level** — if most indicators agree with the composite, confidence is high; if they disagree, confidence is low

Example of a good summary line:
> "Composite: +1.4 (Greed). Driven primarily by compressed HY spreads (93rd percentile) and low VIX (25th percentile). Flagged individual extremes: SKEW at 96th percentile (tail hedging very elevated — note divergence from low VIX), gold/copper ratio at 89th percentile (risk-off commodity signal). Signal confidence: MODERATE — Tier 1 broadly agrees on complacency but tail hedging and safe-haven flows are running hotter, suggesting the complacency is not universal."

Example of a BAD summary line:
> "Composite: +1.4. The market is in greed territory and a pullback is likely."

The bad version is (a) overconfident, (b) ignores the actual research finding that composite extremes have weak point-forecasting power, and (c) hides the internal conflicts.
