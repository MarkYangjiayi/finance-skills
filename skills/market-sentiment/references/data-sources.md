# Data Sources Reference

Complete mapping of every indicator in this skill to its API endpoint, authentication method, tool call syntax, and tested example. All calls here have been verified working.

## Table of contents

1. [FRED (St. Louis Fed)](#fred)
2. [EODHD (via MCP)](#eodhd)
3. [yfinance (free, no key)](#yfinance)
4. [CFTC Socrata API (free, no key)](#cftc-socrata)
5. [edgartools / SEC EDGAR (free, no key)](#edgar)
6. [alternative.me Crypto Fear & Greed (free, no key)](#altme)
7. [Data freshness / release calendar](#freshness)

---

## 1. FRED <a name="fred"></a>

**Authentication**: Set `FRED_API_KEY` environment variable. Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html
```
https://api.stlouisfed.org/fred/series/observations?series_id={ID}&api_key=$FRED_API_KEY&file_type=json&sort_order=desc&limit={N}
```

**Tool**: Plain `curl` via `bash_tool`, OR the `fetch_fred` helper function (see below).

### Tier 1 indicators on FRED

| Series ID | Description | Frequency | Notes |
|---|---|---|---|
| `BAMLH0A0HYM2` | ICE BofA US High Yield Index Option-Adjusted Spread | Daily | The primary credit stress indicator. Historical range ~3-20%. Spikes above 8% = stress. |
| `BAMLC0A0CM` | ICE BofA US Corporate (Investment Grade) Index OAS | Daily | IG spread. Normal range 0.9-1.5%. >2% = concern. |
| `BAMLH0A3HYC` | ICE BofA CCC & Lower HY OAS | Daily | Distress tier. Most sensitive to credit cycle inflection. |
| `BAMLH0A1HYBB` | ICE BofA BB US High Yield OAS | Daily | Crossover credit. |
| `T10Y2Y` | 10-Year minus 2-Year Treasury | Daily | Classic yield curve. Inverted = recession signal. |
| `T10Y3M` | 10-Year minus 3-Month Treasury | Daily | NY Fed's preferred recession indicator. |
| `DGS10` | 10-Year Treasury Constant Maturity | Daily | Raw 10Y yield. |
| `DGS2` | 2-Year Treasury Constant Maturity | Daily | Raw 2Y yield. |
| `NFCI` | Chicago Fed National Financial Conditions Index | Weekly (Wed) | Composite of 100+ indicators. >0 = tighter than average. |
| `STLFSI4` | St. Louis Fed Financial Stress Index v4 | Weekly | Post-LIBOR replacement. Interpretation: 0 = average stress. |
| `VIXCLS` | CBOE Volatility Index | Daily | FRED's VIX. Identical to yfinance `^VIX`. |
| `SOFR` | Secured Overnight Financing Rate | Daily | Replaces LIBOR. |
| `UMCSENT` | University of Michigan Consumer Sentiment | Monthly | Baker-Wurgler uses this. Released ~15th and end of month. |
| `DFF` | Effective Federal Funds Rate | Daily | Policy rate context. |
| `WM2NS` | M2 Money Stock | Weekly | Liquidity context. |
| `ICSA` | Initial Jobless Claims | Weekly | Macro context for risk regime. |
| `BOGZ1FL663067003Q` | Margin Debt (Z.1 Flow of Funds) | Quarterly | **Very lagged.** Use cautiously. |

### Tested working example
```bash
curl -s "https://api.stlouisfed.org/fred/series/observations?series_id=BAMLH0A0HYM2&api_key=$FRED_API_KEY&file_type=json&sort_order=desc&limit=760" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['observations']),'observations; latest:',d['observations'][0])"
```
`limit=760` gives roughly 3 years of daily data (250 trading days × 3).

### Python helper pattern
```python
import urllib.request, json
def fetch_fred(series_id, limit=760):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={os.environ['FRED_API_KEY']}&file_type=json&sort_order=desc&limit={limit}"
    with urllib.request.urlopen(url) as r:
        obs = json.load(r)["observations"]
    # Parse numeric, skip "."
    return [(o["date"], float(o["value"])) for o in obs if o["value"] != "."]
```

---

## 2. EODHD <a name="eodhd"></a>

**Authentication**: Configured in the MCP server already. Use MCP tools directly.

### Price data
Tool: `eodhd-mcp:get_historical_stock_prices`

Confirmed working tickers:
| Ticker | What | Notes |
|---|---|---|
| `VIX.INDX` | VIX index | Identical to FRED VIXCLS, use either |
| `GSPC.INDX` | S&P 500 | |
| `SPY.US` | SPY ETF | |
| `QQQ.US` | QQQ ETF | |
| `GLD.US` | Gold ETF (tracks gold price) | Use this OR yfinance GC=F |
| `CPER.US` | Copper ETF | Use this OR yfinance HG=F |
| `UUP.US` | USD Index ETF (DXY proxy) | |
| `HYG.US` | High yield bond ETF | Proxy for HY credit risk |
| `TLT.US` | Long-term Treasury ETF | |
| `USDJPY.FOREX` | USD/JPY | Safe-haven proxy (yen strength = risk-off) |
| `USDCHF.FOREX` | USD/CHF | Safe-haven proxy (franc strength = risk-off) |
| `EURUSD.FOREX` | EUR/USD | |

Example call:
```python
eodhd-mcp:get_historical_stock_prices(
    ticker="VIX.INDX",
    start_date="2023-04-01",
    order="d"
)
```

### News sentiment (per ticker)
Tool: `eodhd-mcp:get_sentiment_data`

Returns daily aggregated NLP sentiment scores for one or more tickers. The `normalized` field is a 0-1 score (0.5 = neutral). The `count` field is the article count that day — low counts mean the score is noisy.

Example:
```python
eodhd-mcp:get_sentiment_data(
    symbols="SPY.US,QQQ.US",
    start_date="2026-03-01",
    end_date="2026-04-03"
)
```

**Interpretation**: The score is a ready-made NLP sentiment aggregate. Do NOT treat it as a pure contrarian signal — it reflects news *tone*, which can be leading, lagging, or coincident depending on the regime. Use it as one Tier 2 input among others.

### News word weights
Tool: `eodhd-mcp:get_news_word_weights`

Returns the top keywords weighted by frequency × sentiment in the news stream for a ticker. Useful for explaining *why* sentiment is shifting.

### Company news (raw articles)
Tool: `eodhd-mcp:get_company_news`

Use sparingly — it's raw articles, not aggregated. Only pull if the user specifically asks "what's driving sentiment on X".

### What EODHD does NOT give you on this plan
- **Options EOD data** (tested, returns 403 Forbidden). No put/call ratios or GEX from EODHD.
- **Technical indicators endpoint** — returns empty for most calls. Compute indicators manually from the prices.

---

## 3. yfinance <a name="yfinance"></a>

**Authentication**: None. Free. No key.

**Install**: `pip install yfinance --break-system-packages --quiet` (already done in the Claude execution environment usually, but check).

**Critical tickers**:

| Ticker | What | Why |
|---|---|---|
| `^VIX` | VIX 30-day implied vol | Same as FRED VIXCLS |
| `^VIX9D` | VIX 9-day | **Short end of term structure** |
| `^VIX3M` | VIX 3-month | **Long end of term structure** |
| `^SKEW` | CBOE SKEW index | **Tail risk pricing — only free source** |
| `^OVX` | Oil VIX | Asset-specific vol |
| `^GVZ` | Gold VIX | Asset-specific vol |
| `GC=F` | Gold futures continuous | Safe-haven proxy |
| `HG=F` | Copper futures continuous | Growth/risk proxy |
| `CL=F` | Crude oil futures | |
| `^TNX` | 10-Year Treasury yield | (Redundant with FRED DGS10) |
| `ZN=F` | 10Y Treasury note futures | |
| `DX-Y.NYB` | Dollar index | Try this if `DX=F` fails |

### VIX term structure — the single most important Stage 2 indicator

```python
import yfinance as yf
vix = yf.Ticker("^VIX").history(period="3y")["Close"]
vix3m = yf.Ticker("^VIX3M").history(period="3y")["Close"]
# Term structure ratio
ratio = vix3m / vix
# ratio > 1.0 = contango (normal, fear is priced in near-term)
# ratio < 1.0 = backwardation (acute stress, near-term fear > long-term)
```

**Backwardation happens <20% of the time** and has historically been a contrarian buy signal. This is one of the empirically best signals in the entire sentiment universe.

### SKEW interpretation
- SKEW range: roughly 100 (no tail risk pricing) to 170 (extreme tail risk pricing).
- Historical mean ~120. Values above 145 indicate crowded tail hedging.
- Counterintuitively, very high SKEW has sometimes preceded *calm* markets — crashes often come from unhedged complacency (low SKEW) rather than paranoid hedging.

### Tested working script

See `scripts/fetch_yfinance_vol.py` for a complete wrapper that returns a JSON blob ready for the composite scorer.

---

## 4. CFTC Socrata API <a name="cftc-socrata"></a>

**Authentication**: None. Free. No key. Rate limit applies but is generous for research use.

**Base URL**: `https://publicreporting.cftc.gov/resource/`

### The four main COT report datasets

| Dataset ID | Report | Coverage |
|---|---|---|
| `6dca-aqww` | **Legacy report** | All reportable futures markets, commercial vs non-commercial breakdown |
| `gpe5-46if` | **TFF (Traders in Financial Futures)** | Financial futures only (S&P, Treasuries, FX, etc.) with 4-category breakdown: Dealer / Asset Manager / Leveraged Money / Other |
| `72hh-3qpr` | **Disaggregated** | Commodity futures with Producer/Merchant / Swap Dealer / Managed Money / Other breakdown |
| `jun7-fc8e` | Supplemental | Selected agricultural markets |

### Which dataset to use

- **Equity index futures (S&P, Nasdaq, Russell, Dow)** → TFF (`gpe5-46if`). Use `contract_market_name="E-MINI S&P 500"`.
- **Treasury futures** → TFF (`gpe5-46if`). E.g., `contract_market_name="UST 10Y NOTE"`.
- **FX futures (JPY, EUR, GBP, etc.)** → TFF (`gpe5-46if`).
- **Gold, silver, copper, oil, natgas** → Disaggregated (`72hh-3qpr`).
- **Agriculturals (corn, wheat, soy)** → Disaggregated (`72hh-3qpr`).
- **Anything not covered above** → Legacy (`6dca-aqww`).

### Tested working call (TFF for E-mini S&P 500)

```bash
curl -s "https://publicreporting.cftc.gov/resource/gpe5-46if.json?\$limit=1&contract_market_name=E-MINI%20S%26P%20500&\$order=report_date_as_yyyy_mm_dd%20DESC"
```

Returns dealer_positions_long_all, dealer_positions_short_all, asset_mgr_positions_long, asset_mgr_positions_short, lev_money_positions_long, lev_money_positions_short, and change_* fields for week-over-week delta.

### Key field names (TFF)

- `report_date_as_yyyy_mm_dd` — Tuesday of the reporting week
- `dealer_positions_long_all` / `dealer_positions_short_all` — Swap dealer positioning (typically hedgers)
- `asset_mgr_positions_long` / `asset_mgr_positions_short` — Asset managers (typically long-biased, slow-moving)
- `lev_money_positions_long` / `lev_money_positions_short` — **Hedge funds / CTAs** (typically trend-following; this is the group that matters most for contrarian signals at extremes)
- `other_rept_positions_long` / `other_rept_positions_short` — Other reportables
- `change_in_lev_money_long` etc. — WoW deltas

### Key field names (Legacy)

- `noncomm_positions_long_all` / `noncomm_positions_short_all` — Large speculators (hedge funds + CTAs aggregated)
- `comm_positions_long_all` / `comm_positions_short_all` — Commercial hedgers
- `nonrept_positions_long_all` / `nonrept_positions_short_all` — Small speculators
- `open_interest_all` — Total open interest

### Computing the COT Index

Common practitioner formula — the "COT Index" over a rolling window:
```
COT Index = 100 × (current_net - min_net_3y) / (max_net_3y - min_net_3y)
```
where `net = longs - shorts` for the trader group of interest. Readings ≥80 or ≤20 flag extremes.

### The skill's helper script

`scripts/fetch_cot.py` wraps all of this. It handles URL encoding, dataset selection by market name, percentile rank calculation, and returns clean JSON.

### Data freshness

- Reports cover positions as of **Tuesday** of each week
- Released **Friday at 3:30 PM ET**
- So by Monday morning, you have Tuesday-of-previous-week data (5 days stale)
- Government shutdowns delay publication; check for gaps

### Common market name strings

The `fetch_cot.py` script has aliases for all of these, so you can use short names:

| Alias | Report | Full CFTC market name |
|---|---|---|
| `ES` / `SPX` / `SP500` | tff | `E-MINI S&P 500` |
| `NQ` / `NDX` | tff | `E-MINI NASDAQ-100` |
| `RTY` | tff | `E-MINI RUSSELL 2000` |
| `VIX` | tff | `VIX FUTURES` |
| `UST10Y` | tff | `UST 10Y NOTE` |
| `UST2Y` | tff | `UST 2Y NOTE` |
| `UST30Y` | tff | `UST BOND` |
| `JPY` | tff | `JAPANESE YEN` |
| `EUR` | tff | `EURO FX` |
| `GBP` | tff | `BRITISH POUND` |
| `CHF` | tff | `SWISS FRANC` |
| `AUD` | tff | `AUSTRALIAN DOLLAR` |
| `BTC` | tff | `BITCOIN` |
| `GOLD` | disagg | `GOLD - COMMODITY EXCHANGE INC.` |
| `SILVER` | disagg | `SILVER - COMMODITY EXCHANGE INC.` |
| `COPPER` | disagg | `COPPER- #1 - COMMODITY EXCHANGE INC.` |
| `PLATINUM` | disagg | `PLATINUM - NEW YORK MERCANTILE EXCHANGE` |
| `CRUDE` / `WTI` | disagg | `WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE` |
| `NATGAS` | disagg | `NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE` |
| `CORN` | disagg | `CORN - CHICAGO BOARD OF TRADE` |
| `WHEAT` | disagg | `WHEAT-SRW - CHICAGO BOARD OF TRADE` |
| `SOY` | disagg | `SOYBEANS - CHICAGO BOARD OF TRADE` |

**Important**: CFTC market names are EXACT strings — spacing, punctuation, and the trailing "- EXCHANGE NAME" part all matter. If you need to query a market not in the alias list, run `python scripts/fetch_cot.py --list-aliases` to see what's available, or query the API with a `$where` LIKE pattern to discover the exact name.

**Notable historical naming quirks**:
- Copper is `"COPPER- #1 - COMMODITY EXCHANGE INC."` — the `#1` denotes the primary contract and the hyphen-space is literal.
- The main WTI crude contract with hedge-fund activity is `WTI-PHYSICAL`, not the sidecar `WTI FINANCIAL CRUDE OIL`.
- Natural gas uses the abbreviation `NAT GAS NYME`, not the fully-spelled `NATURAL GAS`.

---

## 5. edgartools / SEC EDGAR <a name="edgar"></a>

**Authentication**: None, but you must set an identity string (any email works, it's a courtesy header SEC requires).

**Install**: `pip install edgartools --break-system-packages --quiet`

### Use cases for this skill

- Pull latest 13F-HR filings for major hedge funds
- Extract holdings and compute aggregate positioning changes
- Track which stocks are gaining/losing hedge fund sponsorship

### Minimum working example

```python
from edgar import set_identity, Company
set_identity("Market Sentiment Analysis research@example.com")

# Berkshire Hathaway CIK
brk = Company("0001067983")
latest = brk.get_filings(form="13F-HR").latest()
print(f"Filing date: {latest.filing_date}")

holdings = latest.obj().infotable  # pandas DataFrame
print(f"Holdings: {len(holdings)}")
print(holdings[['Issuer','Ticker','Value','Shares']].head())
```

### Useful CIKs for "smart money" tracking

| Fund | CIK | Notes |
|---|---|---|
| Berkshire Hathaway | 0001067983 | Buffett — long-only, slow-moving |
| Bridgewater Associates | 0001350694 | Ray Dalio's fund — global macro |
| Renaissance Technologies | 0001037389 | Jim Simons' quant fund |
| Citadel Advisors | 0001423053 | Ken Griffin multi-strat |
| Millennium Management | 0001273087 | Izzy Englander multi-strat |
| Point72 Asset Management | 0001603466 | Steve Cohen |
| D.E. Shaw | 0001009207 | |
| Two Sigma | 0001179392 | Quant |
| Tiger Global | 0001167483 | Growth equity |
| Baupost Group | 0001061165 | Seth Klarman — value |

### Critical caveats

1. **45-day reporting delay.** 13F filings are due 45 days after quarter-end. A filing seen today is reporting on positions from ~3 months ago. STATE THIS IN EVERY REPORT.
2. **Long positions only.** No shorts, no options (though options show up as underlying exposure in some cases).
3. **US equity only.** No foreign holdings, no private positions, no bonds.
4. **$100M threshold**. Only managers with >$100M in 13F-eligible assets file.

### The skill's helper script

`scripts/fetch_13f.py` handles the CIK list, batch extraction, and produces an aggregate view of which sectors/stocks the hedge fund cohort is moving into or out of.

---

## 6. Crypto Fear & Greed Index <a name="altme"></a>

**Authentication**: None. Free. No key.

**Endpoint**: `https://api.alternative.me/fng/?limit=30`

### Tested working call

```bash
curl -s "https://api.alternative.me/fng/?limit=30"
```

Returns a list of daily values, each 0-100, with `value_classification` labels: "Extreme Fear" (0-25), "Fear" (26-45), "Neutral" (46-54), "Greed" (55-75), "Extreme Greed" (76-100).

### How to use it

- **Not** a pure equity signal. It's a crypto risk-appetite proxy.
- **Useful** as a Tier 2 cross-asset indicator because crypto sentiment now moves with broader risk appetite (high correlation with NDX and high-beta tech since 2020).
- Include it whenever the user asks about risk-on/risk-off regimes or sentiment broadly. Exclude it if the user is specifically asking about commodity or rates sentiment.

### Python helper

```python
import urllib.request, json
def fetch_crypto_fng(limit=30):
    url = f"https://api.alternative.me/fng/?limit={limit}"
    with urllib.request.urlopen(url) as r:
        return json.load(r)["data"]
```

---

## 7. Data freshness / release calendar <a name="freshness"></a>

| Indicator | Release cadence | Typical lag | Notes |
|---|---|---|---|
| FRED credit spreads | Daily | T-1 | Updates ~mid-morning ET |
| FRED yields | Daily | T-1 | |
| FRED VIX | Daily | T-1 | |
| NFCI | Weekly (Wed) | ~3 days | Covers prior Friday |
| STLFSI4 | Weekly (Thu) | ~3 days | |
| UMCSENT | Monthly | ~15 days | Preliminary mid-month, final end-month |
| EODHD prices | Daily | T-1 | |
| EODHD sentiment | Daily | T-0 to T-1 | |
| yfinance VIX/SKEW | Daily | T-1 | |
| CFTC COT reports | **Weekly (Fri 3:30pm ET)** | **~3 days** | Covers Tuesday of release week |
| SEC 13F-HR | **Quarterly** | **~45 days** | Due 45 days after quarter-end |
| Crypto F&G | Daily | T-0 | Updates around midnight UTC |

## Quick reference: "I need to show X, what do I call?"

| User asks about... | Call this |
|---|---|
| "Credit spreads" | FRED BAMLH0A0HYM2, BAMLC0A0CM |
| "Yield curve" | FRED T10Y2Y, T10Y3M |
| "VIX / volatility" | FRED VIXCLS + yfinance ^VIX3M ^VIX9D ^SKEW |
| "Fear and greed" | Composite of all Tier 1 + Tier 2, mapped to regime label |
| "COT report" | `scripts/fetch_cot.py` with the right market name |
| "Hedge fund positioning" | `scripts/fetch_13f.py` (with 45-day lag caveat) |
| "Safe haven demand" | yfinance GC=F + EODHD USDJPY.FOREX |
| "News sentiment on [ticker]" | `eodhd-mcp:get_sentiment_data` |
| "Crypto sentiment" | alternative.me fng API |
| "Consumer sentiment" | FRED UMCSENT |
| "Financial conditions" | FRED NFCI, STLFSI4 |
| "Risk on or risk off" | Gold/copper ratio + VIX + HY spreads |
