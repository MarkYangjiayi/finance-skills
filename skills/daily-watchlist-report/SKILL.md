---
name: daily-watchlist-report
description: Generate a daily triage report for a personal stock watchlist of 50-100 tickers, grouped by investment theme/cluster (e.g. "AI infra", "DRAM", "Clean energy"). Use this skill whenever the user asks for their "daily report", "watchlist report", "morning brief", "what happened to my stocks", "any news on my watchlist", "catch me up on my portfolio", or similar phrasing — even if they don't explicitly say "use the skill". Pulls price/volume moves, news, SEC 8-K filings, upcoming earnings, and sentiment from EODHD, Yahoo Finance RSS, and SEC EDGAR. Always runs cluster-level subagents in parallel so it stays fast with large watchlists. Produces a dated markdown report saved to the skill's `reports/` folder.
---

# Daily Watchlist Report

This skill produces a concise morning triage report for the user's personal stock watchlist. The goal is **surface what needs attention today, skip everything else** — not deep analysis of every ticker.

## Core principles

1. **Triage over analysis.** The report's job is "which names deserve the user's eyes today", not "here is a full write-up of all 80 tickers". Silence on a ticker means "nothing worth flagging", not "we forgot it".
2. **Cluster-first, not ticker-first.** The user thinks in investment themes (AI infra, DRAM, space, clean energy). The report is organized that way, with each cluster framed against its thesis.
3. **Parallel by cluster.** With 50-100 tickers, always spawn one subagent per cluster to fetch + analyze in parallel. Never serialize.
4. **Catch-up aware.** If the user skipped a few days, the report covers everything since the last run — not just yesterday. State lives in `state.json`.

## Inputs the skill expects

### `watchlist.yaml`
Two supported shapes:

**Flat list (starter shape — used when the user is new to the skill):**
```yaml
tickers: [NVDA, AVGO, MU, VRT, TSM, ASML, ...]
```

**Clustered (target shape — what the user should evolve toward):**
```yaml
clusters:
  ai_infra:
    thesis: "Hyperscaler capex cycle; watching demand signals and supply constraints"
    thresholds:
      price_move_pct: 3.0
      volume_multiple: 2.0
    tickers: [NVDA, AVGO, VRT, SMCI, DELL]
  dram:
    thesis: "Memory pricing recovery, HBM demand from AI accelerators"
    tickers: [MU, 000660.KS]  # per-cluster thresholds optional, falls back to global
  space:
    thesis: "Launch cadence + defense budgets"
    tickers: [RKLB, ASTS, LMT]
# Optional: ungrouped names
uncategorized:
  tickers: [BRK-B, COST]
```

A ticker may appear in multiple clusters — that's fine, report it under each.

**If the watchlist is still flat**, offer to help the user cluster it (see `references/clustering_guide.md`) before running, but don't block — the skill can run on a flat list too, it just won't have themed sections.

### `state.json`
```json
{
  "last_run_utc": "2026-04-13T06:00:00Z",
  "last_report_path": "reports/2026-04-13.md"
}
```
First run: file missing → default to a 7-day lookback.

### EODHD ticker format
EODHD uses `SYMBOL.EXCHANGE` (e.g. `AAPL.US`, `ASML.AS`, `000660.KS`). If the watchlist has bare symbols, assume `.US`. Non-US names must be fully qualified in the YAML.

## Workflow

### Step 1: Load inputs and check state
- Read `watchlist.yaml` from the skill directory.
- Read `state.json`; if missing, set `lookback_days = 7` and note this is a first run. Otherwise `lookback_days = max(1, days_since(last_run_utc))`.
- Compute `start_date = today - lookback_days` and `end_date = today`.

### Step 2: Fan out one subagent per cluster (CRITICAL — do this in parallel)
For each cluster (including `uncategorized` if present), spawn a subagent **in the same turn** with this task:

> You are analyzing the `<cluster_name>` cluster for a daily watchlist report.
> Thesis: `<cluster thesis>`
> Tickers: `<list>`
> Window: `<start_date>` to `<end_date>`
> Thresholds: `<merged cluster + global>`
>
> For each ticker, do the following (use the helper scripts — don't reinvent):
> 1. `python3 scripts/fetch_prices.py <ticker> --start <start> --end <end>` — gets price, % move, volume vs 20d avg, 52-week position, RSI.
> 2. `python3 scripts/fetch_news_yahoo.py <ticker> --since <start>` — headlines from Yahoo Finance RSS via feedparser.
> 3. Call the EODHD MCP tool `eodhd-mcp:get_company_news` with `ticker`, `start_date`, `end_date`, `limit=20` — primary news source with sentiment.
> 4. Call `eodhd-mcp:get_sentiment_data` with `symbols=<ticker>` for the window — aggregate sentiment score.
> 5. `python3 scripts/fetch_sec_filings.py <ticker> --since <start>` — 8-K material events via `edgartools` (US tickers only; skip for foreign).
> 6. Check `eodhd-mcp:get_upcoming_earnings` for any earnings in the next 7 days.
> 7. Pipe `fetch_prices.py` output into `python3 scripts/detect_anomalies.py --thresholds '<json>'` to decide what's flagged.
>
> Write your cluster section to `/tmp/watchlist_report/<cluster_name>.md` using the template in `references/report_template.md`. Frame flagged items **against the thesis** — why does this matter for *this* thesis, not just generically. If nothing is flagged, write a one-line "No material developments." section. Return a short JSON summary: `{"cluster": "...", "flagged_count": N, "top_items": [...], "section_path": "..."}`.

Spawning all cluster subagents in a single turn is how parallelism actually happens — don't loop.

### Step 3: Build the top summary
Once all subagents return, the main agent:
1. Reads each cluster's section file.
2. Writes a "What matters today" lead section (3-7 bullets) picking the highest-signal items across clusters. Prioritize: earnings surprises, 8-K filings, >1.5σ price moves with volume confirmation, and news with strong sentiment deltas.
3. Adds a macro header: call `eodhd-mcp:get_ust_yield_rates` for the 10Y, and note DXY/VIX level if available. One line, not a dissertation.
4. Stitches sections in a stable order (alphabetical by cluster name, or a user-defined order if present in `watchlist.yaml` as `cluster_order`).

### Step 4: Save and update state
- Save final report to `reports/YYYY-MM-DD.md` (use UTC date). If a report for today already exists, append `-run2`, `-run3`, etc.
- Update `state.json` with the new `last_run_utc` and `last_report_path`.
- Present the report path to the user and show the "What matters today" section inline so they see the headline without opening the file.

## Report structure

Always follow this template (also in `references/report_template.md`):

```markdown
# Watchlist Report — <YYYY-MM-DD>
*Window: <start> → <end> · <N> tickers across <M> clusters*

## Macro snapshot
- 10Y: X.XX% (Δ)
- DXY: ... · VIX: ...

## What matters today
- **[Cluster] Ticker**: one-line why-it-matters, framed against the thesis.
- ...

## Upcoming catalysts (next 7 days)
- Earnings: TICKER (date), ...
- Ex-div: ...

---

## <Cluster 1 name>
*Thesis: ...*

### Flagged
- **TICKER** — +X.X% on Nx volume. [news headline] ([source]). Why it matters: ...
### Quiet
TICKER, TICKER, TICKER (no material developments)

## <Cluster 2 name>
...
```

## Clustering a flat watchlist

If the user's `watchlist.yaml` is still a flat list and they ask you to cluster it, read `references/clustering_guide.md`. The short version: propose clusters based on the business driver (what macro/secular force moves the stock), not the GICS sector. Always let the user approve/edit before writing.

## Thresholds

Default global thresholds (overridable per cluster in YAML):
- `price_move_pct`: 3.0 (flag any |%move| > this)
- `volume_multiple`: 2.0 (flag if volume > N× 20d average)
- `rsi_overbought`: 70
- `rsi_oversold`: 30
- `sentiment_delta`: 0.3 (flag if daily sentiment shifts by this much)

See `references/thresholds.md` for the rationale and how to tune.

## What this skill does NOT do
- **No buy/sell recommendations.** The report flags things to look at. The user decides.
- **No backtesting or historical reconstruction.** It's a forward-looking triage tool.
- **No portfolio weighting or position sizing.** Purely a watchlist monitor.

## Scripts — execute for data collection

Execute scripts with `python3 scripts/<name>.py` (use `python3`, not `python` — macOS system Python is only exposed as `python3`).

- **`scripts/fetch_prices.py`** — Pulls EOD price history, computes % move, volume vs 20d avg, RSI(14), 52-week position, and SMA cross via EODHD REST API. Usage: `python3 scripts/fetch_prices.py NVDA.US --start 2026-04-12 --end 2026-04-19`. Requires `EODHD_API_TOKEN` env var.
- **`scripts/fetch_news_yahoo.py`** — Fetches headlines from Yahoo Finance RSS for a ticker. Usage: `python3 scripts/fetch_news_yahoo.py NVDA --since 2026-04-12`. Falls back gracefully for non-US tickers.
- **`scripts/fetch_sec_filings.py`** — Pulls recent 8-K filings via `edgartools`. US tickers only; non-US tickers are skipped. Usage: `python3 scripts/fetch_sec_filings.py NVDA --since 2026-04-12`.
- **`scripts/detect_anomalies.py`** — Reads price JSON from stdin, applies threshold rules, and returns a `flags` list. Usage: `python3 scripts/fetch_prices.py NVDA.US --start ... --end ... | python3 scripts/detect_anomalies.py --thresholds '{"price_move_pct":3.0}'`.
- **`scripts/utils.py`** — Shared helpers: parse `watchlist.yaml`, compute the lookback window from `state.json`, and update state after a run. Usage: `python3 scripts/utils.py load-watchlist watchlist.yaml` or `python3 scripts/utils.py get-window state.json`.

### Prerequisites

- `EODHD_API_TOKEN` environment variable — required by `fetch_prices.py` (EODHD REST API key)
- EODHD MCP server connected — required for MCP tool calls (`eodhd-mcp:get_company_news`, `eodhd-mcp:get_sentiment_data`, etc.)
- Python packages:
  ```bash
  python3 -m pip install feedparser pyyaml requests "edgartools>=2,<3"
  ```
- `edgartools` is only needed for SEC 8-K fetching; skip if you don't need SEC filings. Pin to `<3` — edgartools 3.x+ has a pyarrow compatibility regression on macOS system Python 3.9.
