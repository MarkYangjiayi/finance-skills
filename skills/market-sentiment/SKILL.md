---
name: market-sentiment
description: Systematic multi-source analysis of market sentiment and positioning to gauge risk appetite, identify contrarian signals, and assess where markets sit between fear and greed. Pulls live data from FRED (credit spreads, financial conditions), EODHD (prices, news sentiment), yfinance (VIX term structure, SKEW), CFTC COT reports (institutional futures positioning), SEC 13F filings (hedge fund holdings), and the Crypto Fear & Greed Index, then computes z-score composites and flags extreme readings. Use this skill whenever the user asks about market sentiment, investor positioning, risk-on/risk-off regimes, hedge fund positioning, COT reports, fear & greed, market tops or bottoms, contrarian signals, "where are we in the cycle", credit stress, volatility term structure, or any variation of "what is the market telling us right now" — even if they don't use these exact words.
---

# Market Sentiment & Positioning Analysis

This skill operationalizes the research framework on market sentiment indicators — pulling real data for the indicators that have survived empirical scrutiny (VIX term structure, credit spreads, COT positioning, composite z-scores à la Baker-Wurgler/Huang) and flagging where the evidence is weaker (put/call ratios, single-survey measures, folklore indicators).

## When to use this skill

Trigger this skill for any question about the **current state** of market sentiment, positioning, or risk appetite. Typical phrasings:

- "What is market sentiment right now?"
- "Are we at a top / bottom?"
- "Risk-on or risk-off?"
- "What's hedge fund positioning?"
- "COT report for [asset]"
- "Credit spreads flashing warnings?"
- "Fear and greed?"
- "Is the market overbought?"
- "What do contrarian indicators say?"
- "Where are the smart money and dumb money?"

Do NOT use this skill for: backward-looking return analysis, fundamental valuation of specific stocks, macro forecasting (use a dedicated macro skill), or pure chart/technical analysis.

## Core philosophy

The skill applies three principles from the research:

1. **Composites beat individuals.** No single indicator reliably times markets. Build a weighted z-score across diverse sources.
2. **Extremes matter, middles don't.** Most sentiment indicators only produce signal at percentile extremes (roughly top/bottom 10-15% of their own history). Report these as "flagged" separately from the composite.
3. **Respect the evidence hierarchy.** Volatility term structure, credit spreads, and commercial hedger positioning have the strongest empirical support. Surveys and retail flows are weaker. Flag which tier each data point came from.

## The workflow

Follow these six stages in order. Do not skip Stage 1 — scoping dictates which data you pull.

### Stage 1 — Scope the question

Before calling any API, identify:

- **Time horizon**: Is the user asking about "right now" (today's snapshot), "this week", or a multi-month trend? This determines whether you pull just the latest observation or a trailing series.
- **Asset focus**: Broad US equity (default), a specific asset class (gold, bonds, currencies, crypto), or a single stock?
- **Depth**: A quick read ("what's the mood?") or a full dashboard?

If the user asked about a specific stock or sector, you'll pull per-ticker news sentiment (EODHD) in addition to the broad-market indicators. If they asked about futures/commodities, you'll prioritize CFTC COT data for that specific market. If they asked about crypto risk appetite, add the Crypto Fear & Greed Index.

**Do not ask clarifying questions unless the request is truly ambiguous.** Pick the most plausible interpretation, state the assumption inline, and proceed. Default to a US-broad-equity snapshot if no asset is specified.

### Stage 2 — Pull Tier 1 core indicators (always)

These seven indicators form the backbone of every analysis. They have the strongest empirical support and are available daily. Always pull all seven.

Read **`references/data-sources.md`** for exact tool calls, series IDs, and ticker symbols. The short version:

| Indicator | Source | Identifier |
|---|---|---|
| High-yield credit spread | FRED | `BAMLH0A0HYM2` |
| Investment-grade spread | FRED | `BAMLC0A0CM` |
| Yield curve (10Y-2Y) | FRED | `T10Y2Y` |
| Financial conditions (NFCI) | FRED | `NFCI` |
| VIX level | FRED | `VIXCLS` |
| VIX term structure | yfinance script | `^VIX`, `^VIX3M` |
| CBOE SKEW | yfinance script | `^SKEW` |

Pull roughly **3 years of daily history** for each so you can compute percentile ranks. Z-score the latest value against its own 3-year distribution.

### Stage 3 — Pull Tier 2 context indicators (scope-dependent)

Based on Stage 1 scoping, add the relevant Tier 2 indicators:

**Always add (cross-asset risk appetite):**
- Gold vs Copper futures (risk-off vs growth proxy) — yfinance `GC=F` and `HG=F`
- USD/JPY (carry / safe-haven) — EODHD `USDJPY.FOREX`
- Crypto Fear & Greed — alternative.me API

**Add if asset is equity or broad market:**
- CFTC TFF report for E-mini S&P 500 — leveraged money and asset manager net positioning (run `scripts/fetch_cot.py`)
- EODHD aggregate news sentiment for SPY and QQQ

**Add if asset is a specific commodity or futures market:**
- CFTC Legacy or Disaggregated COT report for that specific contract (run `scripts/fetch_cot.py` with the correct market code)

**Add if asked about institutional positioning or "smart money":**
- 13F holdings trends for a basket of ~5 major hedge funds (run `scripts/fetch_13f.py`)
- Note: 13F data has a 45-day reporting delay. State this explicitly.

**Add if asked about a specific stock:**
- EODHD per-ticker news sentiment (last 30 days)
- EODHD news word weights (to identify tone drivers)

### Stage 4 — Compute the composite score

Run **`scripts/compute_composite.py`** with the collected data, OR compute inline if the dataset is small. The scoring method:

1. For each indicator, compute the **current value's z-score** vs its own trailing 3-year distribution.
2. **Sign-align** so that positive z-scores always mean "greedy / risk-on / complacent" and negative means "fearful / risk-off / stressed". Some indicators need inversion:
   - Invert VIX, credit spreads, SKEW (high = fear, so flip sign)
   - Do NOT invert yield curve (positive slope = normal, inverted = warning — treat as negative sentiment)
   - Do NOT invert gold/copper ratio (high ratio = risk-off, so flip sign)
3. Average the aligned z-scores within each Tier, then average Tier 1 and Tier 2 with **Tier 1 weighted 2x** (stronger evidence base).
4. Map the composite to a regime label:
   - `> +2.0`: **Extreme Greed** (contrarian sell zone)
   - `+1.0 to +2.0`: Greed
   - `-1.0 to +1.0`: Neutral
   - `-2.0 to -1.0`: Fear
   - `< -2.0`: **Extreme Fear** (contrarian buy zone)

See **`references/composite-framework.md`** for the full weighting rationale, edge cases, and alternative aggregation methods (PLS, PCA) if the user asks why you used simple weighting.

### Stage 5 — Flag contrarian extremes

Separately from the composite, flag any individual indicator whose current reading is in the **top 10% or bottom 10% of its 3-year distribution**. These are the actionable data points. The composite tells you the average mood; the flags tell you where the actual tension sits.

For each flagged indicator:
- State the current value and its percentile rank
- Note whether historical extremes at this level preceded notable moves (use **`references/indicator-interpretation.md`** for calibration context)
- Explicitly label each flag as "confirming" or "contrarian"

### Stage 6 — Generate the report

ALWAYS use this exact template. Do not improvise section ordering — the structure is designed so a busy user can stop reading after the Headline and still get the main answer.

```markdown
# Market sentiment snapshot — [date]

## Headline
**Composite regime: [LABEL] (z = X.XX)**
[One-sentence plain-English summary of what the composite says and what's driving it.]

## Tier 1 core indicators
| Indicator | Current | 3Y percentile | Aligned z | Signal |
|---|---|---|---|---|
| HY credit spread | X.XX% | XX | ±X.XX | [colour] |
| IG spread | ... | ... | ... | ... |
| 10Y-2Y curve | ... | ... | ... | ... |
| NFCI | ... | ... | ... | ... |
| VIX | ... | ... | ... | ... |
| VIX3M/VIX ratio | ... | ... | ... | ... |
| SKEW | ... | ... | ... | ... |

**Tier 1 average z: ±X.XX**

## Tier 2 context indicators
[Same table format, only the indicators you pulled in Stage 3]

**Tier 2 average z: ±X.XX**

## Contrarian flags
[List each indicator at an extreme percentile, one per line, with a one-sentence interpretation. If nothing is flagged, say "No individual indicator is at a 3-year extreme."]

## Positioning detail
[Only if COT or 13F data was pulled. Summarise the positioning in plain English — who is long, who is short, where does positioning sit vs its own history.]

## What the evidence does NOT tell you
[Always include this section. Name the gaps explicitly: AAII survey unavailable, put/call ratio unavailable, GEX unavailable, etc. This manages user expectations and prevents them from thinking your composite is the whole picture.]

## Bottom line
[Two or three sentences. Repeat the regime, state the one or two signals the user should actually act on (if any), and note the main caveat.]
```

## Critical execution rules

1. **Verify, don't guess.** Every number in your report must come from a live API call made in this session. Do not fabricate historical values or percentiles from memory. If a data pull fails, say so — do not invent a plausible-looking value.

2. **Cite your sources inline.** Every table row should implicitly be backed by a tool call visible in the session. If the user asks "where did X come from", you should be able to point to the exact call.

3. **State data freshness.** FRED data is T-1 typically, COT data is released Friday afternoons for Tuesday-of-same-week positions, 13F data is 45 days stale. Always state which date each observation is from.

4. **Never claim predictive power the research does not support.** The research explicitly documents that (a) composite indices do NOT reliably time aggregate market tops/bottoms, (b) sentiment works better cross-sectionally than aggregately, and (c) out-of-sample R² for most of these indicators is low. Do not write things like "the composite is signalling a top". Write "the composite sits in the [X] regime, which has historically coincided with [Y]" — and only if you can actually support that claim.

5. **Handle conflicting signals explicitly.** When Tier 1 and Tier 2 disagree, say so. When individual flags contradict the composite, say so. Conflicts ARE the signal — don't paper over them.

6. **Be concise in the final report.** The markdown template is deliberately compact. Do not add narrative paragraphs between sections. Users want the dashboard, not a thinkpiece.

## Reference files — read when needed

- **`references/data-sources.md`** — Complete mapping of every indicator to its API call, with tested examples and troubleshooting. **Read this at Stage 2 before making any data calls.**
- **`references/indicator-interpretation.md`** — Historical calibration for each indicator: what readings have meant historically, notable episodes, empirical evidence base. **Read this at Stage 5 when interpreting flagged extremes.**
- **`references/composite-framework.md`** — Full methodology for z-score aggregation, sign alignment table, alternative approaches (PCA, PLS), and an explanation of why certain weights are used. **Read this at Stage 4 if a user asks methodology questions or if you need to handle an edge case.**

## Scripts — execute for specialised data

- **`scripts/fetch_cot.py`** — Pulls CFTC COT reports (Legacy + TFF) via the free Socrata API. Usage: `python scripts/fetch_cot.py --market "E-MINI S&P 500" --report tff` or `--report legacy`. Returns the latest report plus a percentile rank for the current positioning.
- **`scripts/fetch_13f.py`** — Uses `edgartools` to pull recent 13F holdings for a list of well-known hedge funds and compute aggregate positioning changes. Usage: `python scripts/fetch_13f.py` (uses a default fund list) or `python scripts/fetch_13f.py --funds 0001067983,0001350694`.
- **`scripts/fetch_yfinance_vol.py`** — Pulls VIX, VIX9D, VIX3M, SKEW, GC=F, HG=F, ^TNX via yfinance in one shot, returning the latest values and 3-year percentile ranks.
- **`scripts/compute_composite.py`** — Takes a JSON blob of indicators and produces sign-aligned z-scores, tier averages, and the composite score. Usage: pipe the indicator JSON via stdin or pass `--input indicators.json`.

Execute scripts with `python3 scripts/<name>.py` (use `python3`, not `python` — macOS system Python is only exposed as `python3`). They are self-contained and handle their own API authentication.

### Prerequisites

- `FRED_API_KEY` environment variable (free key at https://fred.stlouisfed.org/docs/api/api_key.html)
- Python packages: `yfinance` is auto-installed on first run of `fetch_yfinance_vol.py`. `edgartools` must be installed manually if you use `fetch_13f.py`:
  ```
  python3 -m pip install --break-system-packages edgartools
  ```
- All other scripts rely only on the standard library + `numpy` (preinstalled on most systems).

## What this skill does NOT do

Be explicit about these limits in every report's "What the evidence does NOT tell you" section:

- **No AAII survey data.** AAII requires a paid membership and has no free API.
- **No CBOE put/call ratio.** CBOE publishes it on their website but there is no reliable free programmatic source.
- **No gamma exposure (GEX) or dealer positioning.** This requires a full options chain, which is behind a paywall on all accessible APIs.
- **No Investors Intelligence, Citi Panic/Euphoria, or BofA Bull & Bear.** These are proprietary / subscription-only.
- **No real-time intraday data.** Everything here is end-of-day or slower.
- **No social media sentiment.** StockTwits / Reddit / X sentiment APIs have been progressively locked down.

These are **not** gaps in the skill — they are gaps in what is accessible without paid vendor relationships. The skill is honest about this.
