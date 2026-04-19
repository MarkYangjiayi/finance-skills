#!/usr/bin/env python3
"""
fetch_prices.py — pull price + volume + simple technicals for one ticker.

Uses the EODHD REST API directly (via requests) rather than the MCP tools, so
this can be called from a subagent shell without needing tool access. The
subagent can also call the MCP tools directly if preferred; this script is a
convenience for bulk/parallel invocation.

Output: JSON to stdout with:
  {
    "ticker": "NVDA.US",
    "last_close": 950.12,
    "last_date": "2026-04-11",
    "pct_change_1d": 2.3,
    "pct_change_window": 5.1,
    "volume": 42000000,
    "volume_vs_20d_avg": 1.8,
    "rsi_14": 64.2,
    "pos_52w": 0.92,            # 0-1 where in the 52w range
    "above_sma_50": true,
    "above_sma_200": true
  }

Requires EODHD_API_TOKEN env var. If not set, prints an error JSON and exits 0
(so the caller can still assemble a report).
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta

try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests not installed"}))
    sys.exit(0)


def normalize_ticker(t: str) -> str:
    return t if "." in t else f"{t}.US"


def fetch_eod(ticker: str, start: str, end: str, token: str):
    url = f"https://eodhd.com/api/eod/{ticker}"
    params = {"from": start, "to": end, "api_token": token, "fmt": "json"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_52w(ticker: str, token: str):
    end = date.today()
    start = end - timedelta(days=400)
    return fetch_eod(ticker, start.isoformat(), end.isoformat(), token)


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()

    token = os.environ.get("EODHD_API_TOKEN")
    if not token:
        print(json.dumps({
            "ticker": args.ticker,
            "error": "EODHD_API_TOKEN not set in environment"
        }))
        return

    ticker = normalize_ticker(args.ticker)

    try:
        bars_52w = fetch_52w(ticker, token)
    except Exception as e:
        print(json.dumps({"ticker": ticker, "error": f"fetch failed: {e}"}))
        return

    if not bars_52w:
        print(json.dumps({"ticker": ticker, "error": "no data"}))
        return

    closes = [b["close"] for b in bars_52w]
    volumes = [b["volume"] for b in bars_52w]
    dates = [b["date"] for b in bars_52w]

    last_close = closes[-1]
    last_date = dates[-1]
    prev_close = closes[-2] if len(closes) >= 2 else last_close
    pct_1d = round((last_close / prev_close - 1) * 100, 2) if prev_close else 0.0

    # Window move: from first bar on/after args.start.
    # If args.start is a weekend/holiday and no bar meets the condition, fall back
    # to the closest bar before args.start rather than silently using index 0
    # (which would be the oldest bar in the 52w dataset and produce a misleading move).
    window_start_idx = None
    for i, d in enumerate(dates):
        if d >= args.start:
            window_start_idx = i
            break
    if window_start_idx is None:
        # All bars are before args.start — use the most recent bar as baseline (0% window move)
        window_start_idx = len(closes) - 1
    window_start_close = closes[window_start_idx]
    pct_window = round((last_close / window_start_close - 1) * 100, 2) if window_start_close else 0.0

    vol_20d_avg = sum(volumes[-21:-1]) / 20 if len(volumes) >= 21 else None
    vol_mult = round(volumes[-1] / vol_20d_avg, 2) if vol_20d_avg else None

    hi_52w = max(closes[-252:])
    lo_52w = min(closes[-252:])
    pos_52w = round((last_close - lo_52w) / (hi_52w - lo_52w), 2) if hi_52w != lo_52w else 0.5

    sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    sma_200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None

    out = {
        "ticker": ticker,
        "last_close": last_close,
        "last_date": last_date,
        "pct_change_1d": pct_1d,
        "pct_change_window": pct_window,
        "volume": volumes[-1],
        "volume_vs_20d_avg": vol_mult,
        "rsi_14": rsi(closes),
        "pos_52w": pos_52w,
        "above_sma_50": (last_close > sma_50) if sma_50 else None,
        "above_sma_200": (last_close > sma_200) if sma_200 else None,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
