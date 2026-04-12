#!/usr/bin/env python3
"""
fetch_yfinance_vol.py — Pull VIX term structure, SKEW, and safe-haven commodities from yfinance.

Outputs JSON with the latest values AND 3-year percentile ranks for each, ready to feed
into compute_composite.py.

Usage:
    python fetch_yfinance_vol.py                 # default bundle
    python fetch_yfinance_vol.py --tickers ^VIX,^SKEW,GC=F

Default bundle:
    ^VIX     — 30d implied vol
    ^VIX9D   — 9d implied vol (short end of term structure)
    ^VIX3M   — 3-month implied vol (long end of term structure)
    ^SKEW    — CBOE SKEW index (tail risk pricing)
    GC=F     — Gold futures continuous
    HG=F     — Copper futures continuous
    ^TNX     — 10Y Treasury yield
    ^GVZ     — Gold VIX (vol of gold)

Also computes two composite ratios the skill cares about:
    vix3m_vix_ratio — >1 is contango (normal), <1 is backwardation (stress)
    gold_copper_ratio — higher = more risk-off positioning
"""

import argparse
import json
import sys
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    print(json.dumps({"error": "yfinance not installed. Run: pip install yfinance --break-system-packages --quiet"}))
    sys.exit(1)


DEFAULT_TICKERS = ["^VIX", "^VIX9D", "^VIX3M", "^SKEW", "GC=F", "HG=F", "^TNX", "^GVZ"]


def pct_rank(series, value):
    """Return the percentile rank of `value` within `series` (0-100)."""
    if series is None or len(series) == 0:
        return None
    import numpy as np
    arr = np.asarray(series, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return None
    return round(100.0 * (arr <= value).sum() / len(arr), 1)


def fetch_one(ticker, period="3y"):
    """Fetch and summarize one ticker. Returns a dict or an error dict."""
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist is None or len(hist) == 0:
            return {"error": f"empty history for {ticker}"}
        closes = hist["Close"].dropna()
        if len(closes) == 0:
            return {"error": f"no close data for {ticker}"}
        latest = float(closes.iloc[-1])
        latest_date = closes.index[-1].strftime("%Y-%m-%d")
        import numpy as np
        values = closes.values
        mean = float(np.mean(values))
        std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        z = (latest - mean) / std if std > 0 else 0.0
        return {
            "ticker": ticker,
            "latest_value": round(latest, 4),
            "latest_date": latest_date,
            "n_obs": len(values),
            "mean_3y": round(mean, 4),
            "std_3y": round(std, 4),
            "z_score": round(z, 3),
            "percentile_3y": pct_rank(values, latest),
            "min_3y": round(float(np.min(values)), 4),
            "max_3y": round(float(np.max(values)), 4),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def compute_derived(results):
    """Compute derived ratios from the raw results."""
    derived = {}

    # VIX term structure: VIX3M / VIX
    if "^VIX3M" in results and "^VIX" in results:
        v3m = results["^VIX3M"].get("latest_value")
        v1m = results["^VIX"].get("latest_value")
        if v3m and v1m and v1m > 0:
            ratio = v3m / v1m
            derived["vix3m_vix_ratio"] = {
                "latest_value": round(ratio, 4),
                "interpretation": (
                    "BACKWARDATION — acute near-term fear > long-term" if ratio < 1.0
                    else "CONTANGO — normal shape, long-term fear > near-term"
                ),
                "contrarian_signal": (
                    "BUY SIGNAL (strong) — backwardation historically preceded positive 3m returns ~75% of time"
                    if ratio < 0.95 else
                    "Complacency warning (weak)" if ratio > 1.15 else
                    "No extreme"
                ),
            }

    # Gold / Copper ratio
    if "GC=F" in results and "HG=F" in results:
        gc = results["GC=F"].get("latest_value")
        hg = results["HG=F"].get("latest_value")
        if gc and hg and hg > 0:
            ratio = gc / hg
            derived["gold_copper_ratio"] = {
                "latest_value": round(ratio, 2),
                "interpretation": (
                    "Higher ratios reflect safe-haven demand / weaker growth expectations. "
                    "Current range of ~600-900 is structurally higher than pre-2022 due to "
                    "central bank gold buying and copper's electrification premium."
                ),
            }

    return derived


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tickers", default=",".join(DEFAULT_TICKERS),
                   help="Comma-separated list of yfinance tickers")
    p.add_argument("--period", default="3y", help="Lookback period (default 3y)")
    args = p.parse_args()

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    results = {}
    for t in tickers:
        results[t] = fetch_one(t, args.period)

    derived = compute_derived(results)

    out = {
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "period": args.period,
        "tickers": results,
        "derived": derived,
    }
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
