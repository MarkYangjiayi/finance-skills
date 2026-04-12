# Indicator Interpretation Reference

Historical calibration, theoretical basis, and empirical track record for every indicator the skill uses. Read this when interpreting flagged extremes in Stage 5 — it prevents overreading noise and under-reading genuine signal.

The organizing question for every indicator below: **"If this reading has shown up historically, what has tended to happen next, and how strong is the evidence?"**

---

## Evidence tier system

Indicators are labeled **A / B / C** based on the strength of empirical support:

- **A — Robust across multiple studies, reproducible, survived out-of-sample testing.** Use these as the spine of any analysis.
- **B — Supporting evidence exists but with caveats (in-sample bias, regime-dependent, or only works at extremes).** Use as corroborating evidence.
- **C — Widely watched but with weak or contested empirical support.** Report if asked, but do not build theses on these alone.

---

## Tier 1 — Core daily indicators

### High-yield credit spread — BAMLH0A0HYM2 (FRED)
**Evidence: A**

**What it captures**: The yield differential between US high-yield corporate bonds and comparable Treasuries. Paid by the weakest borrowers, so it's extraordinarily sensitive to perceptions of default risk and to liquidity conditions in credit markets.

**Theoretical basis**: Credit investors are institutional, focused on downside, and react fast to fundamental deterioration. HY spreads therefore tend to lead equity sentiment by days to a couple of weeks. Gilchrist & Zakrajšek's "Excess Bond Premium" literature formalised this — credit spread innovations predict equity returns after controlling for default expectations.

**Historical calibration**:
- Long-run median: ~4.5-5.5%
- "Calm" regime: <3.5% — complacency zone
- "Normal" regime: 3.5-5%
- "Stressed" regime: 5-8%
- "Panic" regime: >8% (GFC peak ~22%, COVID peak ~11%, 2011 Euro crisis ~9%)

**What extreme readings have meant**:
- Spreads troughing near 3% (2007, Jan 2020, 2021, late 2024) preceded volatility spikes within 6-12 months in most cases but NOT all (2017-18 stayed low for over a year).
- Spreads above 8% have been excellent buy signals for equities over 12-month horizons (2009, 2011, 2016, 2020 all recovered).
- The **rate of change** matters more than the level. A 100bp widening in 2 weeks has historically been more predictive than an absolute level.

**Notable episodes**:
- 2008: Widened from 4% (June) to 22% (Dec) — led equity market bottom by ~3 months.
- 2020 COVID: Widened from 3.3% (Feb) to 10.9% (Mar 23) — bottomed within a week of equity low.
- 2023 SVB crisis: Widened only modestly (~100bp), suggesting the stress was contained — correct call in hindsight.

**Do not overread**: HY spreads have compressed structurally since the late 1990s because of QE and compressed Treasury curve, so "below 4%" is not as meaningful now as it was in the 1990s.

---

### Investment grade credit spread — BAMLC0A0CM (FRED)
**Evidence: A**

**What it captures**: IG corporate spread. Less volatile than HY but more representative of broad corporate funding costs.

**Historical calibration**:
- Long-run median: ~1.3%
- Calm: <0.9%
- Normal: 0.9-1.5%
- Stressed: 1.5-2.5%
- Panic: >2.5% (GFC peak ~6%, COVID peak ~3.7%)

**Usage**: Best used as a ratio with HY spread. The HY-IG differential (HY minus IG) is the "quality spread" — widening quality spreads signal that the weakest credits are cracking while strong credits are still fine, which historically has been an early warning.

---

### Yield curve (10Y-2Y) — T10Y2Y (FRED)
**Evidence: A (for recessions) / B (for sentiment timing)**

**What it captures**: Slope of the Treasury yield curve. Traditional recession predictor.

**Historical calibration**:
- Positive and rising: normal expansion
- Flat (<0.25%): late cycle
- Inverted (<0): has preceded every recession since 1970 (with ~12-24 month lead)

**Caveats**:
- The curve **un-inverts** before recessions actually start — the steepening is the immediate pre-recession signal, not the inversion itself.
- Has produced false signals (1966, mid-1998).
- 2022-23 saw the deepest and longest inversion on record yet recession was delayed or absent — the relationship may be breaking down in the QE era.

**In this skill**: Treat inversion as negative sentiment but **don't overweight it for short-horizon questions**. The lead time is measured in quarters.

---

### Chicago Fed NFCI — NFCI (FRED)
**Evidence: A**

**What it captures**: Weighted average of 105 financial activity measures spanning money markets, debt/equity markets, banking system health, and shadow banking. Designed to capture financial conditions relative to their historical average.

**Historical calibration**:
- Below 0: Looser than average (positive for risk)
- Above 0: Tighter than average (negative for risk)
- Above +0.5: Stress (GFC peaked ~4.8, COVID ~1.9)
- Below -0.5: Very loose (typically late-cycle easy conditions)

**Why it works**: It's a real-time composite of things that actually matter for risk markets — not a survey, not a price-based average. The variables include dozens of spreads and volatility measures, pre-weighted by their relevance.

**In this skill**: Treat as a key Tier 1 input. Unlike sentiment surveys, NFCI captures actual financial activity, not opinion.

---

### St. Louis Fed Financial Stress Index v4 — STLFSI4 (FRED)
**Evidence: A**

**What it captures**: A 18-component stress index using SOFR-based inputs (successor to STLFSI2 after LIBOR discontinuation). Mean-zero by construction.

**Usage**: Complements NFCI. When NFCI and STLFSI4 disagree, usually NFCI is more authoritative (broader component set), but divergences can be informative.

---

### VIX level — VIXCLS (FRED) or ^VIX (yfinance)
**Evidence: A**

**What it captures**: 30-day implied volatility of S&P 500 options, computed from a strip of out-of-the-money puts and calls. The market's dollar-weighted forecast of realised vol over the next month.

**Historical calibration**:
- Long-run average: ~19-20
- Ultra-calm: <13 (often precedes bigger moves — NOT a buy signal)
- Normal: 13-20
- Elevated: 20-30
- Stressed: 30-40
- Panic: >40 (GFC peak 89, COVID peak 82, 2018 vol spike 50)

**Critical caveats**:
- VIX is **not a pure sentiment signal**. It's a compensation for insurance. In calm regimes, the supply of vol sellers drives VIX lower even if no one is particularly complacent.
- The famous "VIX below 12 = complacency" rule has been wrong for extended periods (most of 2017, most of 2024).
- **VIX extremes at the high end are more reliable than at the low end**. Spikes above 40 have always been contrarian buy signals over 3-6 month horizons in the post-1990 data. Low VIX readings are a much weaker sell signal.

---

### VIX term structure (VIX3M/VIX ratio) — yfinance
**Evidence: A (for the backwardation signal specifically)**

**What it captures**: Ratio of 3-month expected vol to 1-month expected vol. Captures the shape of the volatility futures curve.

**Historical behavior**:
- Ratio > 1.0 (contango): ~80% of days. This is the "normal" state — traders demand a premium for insuring against longer horizons.
- Ratio < 1.0 (backwardation): ~15-20% of days. Near-term fear exceeds long-term fear.
- Ratio < 0.90: Acute stress. Historically clustered at market bottoms.

**Empirical support**:
- Backwardation has **preceded positive 3-month S&P 500 returns ~75% of the time** in post-2000 data (various practitioner backtests, though publication-bias concerns apply).
- This is one of the empirically strongest contrarian signals in the entire sentiment universe.

**In this skill**: Report the ratio explicitly. Flag ratio < 0.95 as a contrarian buy signal. Flag ratio > 1.15 as a complacency warning (weaker signal).

---

### CBOE SKEW — ^SKEW (yfinance)
**Evidence: B**

**What it captures**: The implied volatility of far out-of-the-money S&P 500 puts relative to at-the-money puts. Essentially, how much more expensive disaster insurance is than ordinary insurance.

**Historical calibration**:
- Range: roughly 100-170
- Long-run mean: ~120
- "Normal": 115-135
- "Crowded tail hedging": >145
- "Extreme": >155

**Counterintuitive empirical finding**: Very high SKEW readings have been followed by **calm** markets more often than crashes. When everyone is buying OTM puts, the tail hedges are already in place — the population is defensively positioned, and subsequent crashes tend to emerge from *complacent* rather than paranoid markets. This is the core insight in Christopher Cole's work at Artemis.

**In this skill**: Report SKEW and its percentile rank. Do NOT call high SKEW bearish reflexively. If SKEW is high and VIX is low, note the divergence — this has historically been an ambiguous regime.

---

## Tier 2 — Cross-asset risk appetite

### Gold / Copper ratio — GC=F / HG=F (yfinance)
**Evidence: B**

**What it captures**: Risk-off commodity (gold) divided by risk-on growth commodity (copper). Rising ratio = defensive positioning.

**Historical behavior**:
- Ratio spikes at every major growth scare since 1990 (1998 LTCM, 2008, 2011 Euro crisis, 2015-16 manufacturing recession, 2020 COVID).
- A rising ratio over 2-3 months has a decent track record of preceding slower growth.
- Parnes (2024, *North American Journal of Economics and Finance*) confirmed statistical information content for predicting Treasury yields.

**Recent complications**:
- Central bank gold buying since 2022 has pushed gold higher independent of risk sentiment.
- Copper demand has a "green premium" from EV / electrification.
- The ratio's traditional relationship may be partially broken — treat as a Tier 2 input, not Tier 1.

### USD/JPY — USDJPY.FOREX (EODHD)
**Evidence: B, diminishing**

**What it captures**: The JPY was historically a funding currency for carry trades. Carry unwinds (risk-off) drive JPY stronger, so USD/JPY falls.

**Caveat**: Post-2022 BoJ policy normalization has diminished JPY's safe-haven properties. The T. Rowe Price 2025 safe-haven analysis notes JPY now behaves less reliably as a risk-off proxy than in the 2000s-2010s.

**Usage**: Report the level and its 3-month direction, but weight it lightly.

### Crypto Fear & Greed Index (alternative.me)
**Evidence: B**

**What it captures**: Proprietary composite of Bitcoin volatility, momentum, social media, surveys, dominance, and Google trends. Updated daily.

**Usage**: Useful as a broad risk-appetite cross-check. Crypto has correlated 0.5-0.8 with high-beta tech since 2020. Extreme Fear (<20) readings have historically aligned with broader risk-off episodes; Extreme Greed (>80) with euphoric tops.

**Historical**: Hit 3-5 at major crypto bottoms (Nov 2022, Jun 2022). Hit 95+ in Q4 2021 top.

---

## Institutional positioning — COT reports

### Leveraged money positioning in E-mini S&P 500 (CFTC TFF)
**Evidence: B-A, depending on market**

**What it captures**: Net positioning of hedge funds and CTAs in S&P 500 futures. They are trend-followers, so extreme positioning typically marks trend exhaustion.

**Historical empirical record**:
- **Wang (2001, 2003)** found commercial (hedger) positioning in commodity futures works as a contrarian signal over multi-week horizons. Evidence was weaker for non-commercials (large specs).
- **Bessembinder (1992)** established the underlying hedging pressure theory.
- **De Roon, Nijman & Veld (2000)** confirmed hedging pressure effects across 20 markets.
- **Sanders, Irwin & Merrin (2009)** found much weaker results — positions primarily respond to prices rather than predict them.

**The contradiction matters**: Evidence is strongest in commodity futures where commercial hedgers have genuine fundamental information. In equity index futures, commercials are typically index arbitrageurs and portfolio hedgers, so the classic "commercials are contrarians" logic is weaker.

**In this skill**:
- For equity indices: Use TFF. Focus on **leveraged money** (lev_money_positions_long/short) as the trend-following group. Extreme positioning on either side flags exhaustion risk.
- For commodities: Use Disaggregated report. Focus on **managed money** (similar concept) vs **producer/merchant** (commercials).
- Compute COT index: `100 × (current_net - min_net_3y) / (max_net_3y - min_net_3y)`. Flag ≥80 or ≤20.

---

### Commercial hedger positioning in gold, oil, grains (CFTC Disaggregated)
**Evidence: A for commodities**

Much stronger empirical record than for equity index futures. Commercial hedgers in commodities have genuine information about supply/demand. When they reach extreme net long positions (in gold, historically preceded rallies) or extreme net short positions (preceded tops), the signal has empirical support.

**Notable historical episodes**:
- Gold 2016: Commercial net short reached record extreme at summer 2016 top → gold sold off.
- Gold 2018: Commercial net long reached max since 2001 in fall 2018 → gold rallied to new all-time highs.
- Oil 2014: Commercials built historic long position during crash → marked the eventual bottom ~2 months later.

---

## 13F hedge fund holdings (SEC EDGAR via edgartools)

**Evidence: B-A for cross-sectional, C for market timing**

**What it captures**: Quarterly snapshot of long equity positions for institutional managers with >$100M in qualifying assets.

**Empirical record**:
- **Goldman Sachs Hedge Fund Trend Monitor** has documented that the 20 most concentrated stocks among hedge funds outperform the S&P 500 in ~59% of quarters since 2001 with average quarterly excess return ~1.4%. Statistically significant cross-sectionally.
- But: **by the time 13F data is public, it's 45+ days stale**. The alpha is in the information before filing, not after.

**Useful applications**:
- Identifying which stocks/sectors the hedge fund cohort rotated into or out of (aggregate positioning changes).
- Cross-checking a user's specific holdings against where "smart money" sits.
- NOT useful for aggregate market timing — the cohort is always mostly long by definition.

**Caveats to state in every report**:
1. 45-day reporting delay
2. Long-only view — misses shorts and derivatives
3. US equities only
4. Does not capture intra-quarter trading

---

## NLP news sentiment (EODHD)

**Evidence: B**

**What it captures**: Aggregated sentiment scoring of news articles for specific tickers, using NLP models. Returns a 0-1 normalized score.

**Academic basis**:
- **Tetlock (2007)**: Media pessimism predicts downward price pressure followed by reversion.
- **Loughran-McDonald (2011)**: Domain-specific finance dictionary dramatically outperforms general sentiment tools.

**In this skill**:
- Use as a Tier 2 input for single-stock or sector questions.
- Watch for the `count` field — if daily article count is under ~10, the score is noisy; suppress it.
- Multi-day smoothed averages are more reliable than single-day readings.
- The score is a ready-made composite. Don't try to second-guess it unless you have a specific reason.

---

## Indicators explicitly NOT used, and why

These show up in the research literature and you should acknowledge them when asked, but they are NOT in the composite because they are unavailable via free APIs:

| Indicator | Why not used | What to say if asked |
|---|---|---|
| **AAII Sentiment Survey** | Paid membership, no free API. | "AAII data requires a paid membership. As a substitute we use NFCI + news sentiment, which capture retail sentiment indirectly." |
| **CBOE Put/Call Ratio** | CBOE publishes but no reliable free API. | "Put/call ratio data is unavailable via free APIs. VIX term structure and SKEW cover similar options-market information." |
| **Gamma Exposure / GEX** | Requires full options chain (paid). | "GEX requires options chain data which is behind paywalls. The closest free substitute is VIX term structure + SKEW." |
| **Investors Intelligence** | Subscription only. | "Proprietary, not accessible." |
| **Citi Panic/Euphoria** | Bank-client only. Also, Advisor Perspectives documented that Citi retrospectively adjusted the thresholds, so evidence is questionable even if you had access. | "Proprietary, and the historical track record is contested." |
| **BofA Bull & Bear** | Bank-client only. | "Proprietary, not accessible." |
| **CNN Fear & Greed Index** | No official API; unofficial scrapers are unreliable. | "We build our own composite from primary sources instead." |
| **Social media sentiment (Reddit, X)** | APIs have been progressively locked down post-2023. | "Free social sentiment feeds were deprecated. Per-ticker EODHD news sentiment is the closest substitute." |

---

## Cross-indicator conflicts and how to handle them

The research is emphatic that **conflicts ARE signal** — never smooth them over. Common conflict patterns:

### VIX low but SKEW high
Tail risk is being priced in even though headline vol is calm. Historically ambiguous — has preceded both calm periods (defensive positioning works) and crashes (tail fears were correct). **Report the divergence and let the user decide.**

### HY spreads tight but leveraged money net short
Credit sees no stress but hedge funds are positioned for a decline. Usually credit wins this contest — credit investors have better fundamental information. **Weight credit higher.**

### 13F shows hedge funds piling into a sector while news sentiment on the sector is negative
Classic "smart money buying the dip" setup IF the 13F data isn't too stale. Remember 13F is 45+ days lagged — the hedge funds may have already sold.

### Composite says "Neutral" but multiple individual indicators are flagged at extremes
This is the most important case. A neutral average can mask genuinely bifurcated markets. **Always read the flags even when the composite is boring.** The research explicitly warns that composites can wash out the most actionable signal.

### Yield curve inverted but credit spreads tight
Rates market sees recession coming but credit market sees no immediate stress. Historically this is the "long-lead recession warning" regime — recession eventually arrives but not for 6-18 months. Equities often continue rallying in the interim.
