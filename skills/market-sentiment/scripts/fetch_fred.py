#!/usr/bin/env python3
"""
fetch_fred.py — Pull FRED time series and compute 3-year z-scores / percentiles
in the same shape as fetch_yfinance_vol.py output, ready for compute_composite.py.

The FRED API key is read from the FRED_API_KEY environment variable. Get a
free key at https://fred.stlouisfed.org/docs/api/api_key.html and export it:
    export FRED_API_KEY=your_key_here

Usage:
    python fetch_fred.py                        # default bundle (Tier 1 + some Tier 2)
    python fetch_fred.py --series BAMLH0A0HYM2  # single series
    python fetch_fred.py --series BAMLH0A0HYM2,VIXCLS,NFCI  # multiple series

Default bundle:
    BAMLH0A0HYM2  — HY credit spread
    BAMLC0A0CM    — IG credit spread
    BAMLH0A3HYC   — CCC tier spread (distress)
    T10Y2Y        — 10Y-2Y yield curve
    T10Y3M        — 10Y-3M yield curve
    NFCI          — Chicago Fed NFCI (weekly)
    STLFSI4       — St Louis Fed Financial Stress Index (weekly)
    VIXCLS        — VIX (redundant w/ yfinance ^VIX but useful if yfinance blocked)
    DGS10         — 10Y yield
    DGS2          — 2Y yield
    SOFR          — Secured Overnight Financing Rate
    UMCSENT       — Michigan Consumer Sentiment (monthly)
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime

import os
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
if not FRED_API_KEY:
    raise EnvironmentError("FRED_API_KEY environment variable is not set. "
                           "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html")
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

DEFAULT_SERIES = [
    "BAMLH0A0HYM2",
    "BAMLC0A0CM",
    "BAMLH0A3HYC",
    "T10Y2Y",
    "T10Y3M",
    "NFCI",
    "STLFSI4",
    "VIXCLS",
    "DGS10",
    "DGS2",
    "SOFR",
    "UMCSENT",
]

# Human-readable descriptions for the report
SERIES_LABELS = {
    "BAMLH0A0HYM2": "ICE BofA US High Yield OAS",
    "BAMLC0A0CM": "ICE BofA US IG Corporate OAS",
    "BAMLH0A3HYC": "ICE BofA CCC & Lower HY OAS",
    "BAMLH0A1HYBB": "ICE BofA BB HY OAS",
    "T10Y2Y": "10Y-2Y Yield Curve",
    "T10Y3M": "10Y-3M Yield Curve",
    "NFCI": "Chicago Fed Financial Conditions Index",
    "STLFSI4": "St Louis Fed Financial Stress Index v4",
    "VIXCLS": "CBOE Volatility Index",
    "DGS10": "10-Year Treasury Constant Maturity",
    "DGS2": "2-Year Treasury Constant Maturity",
    "SOFR": "Secured Overnight Financing Rate",
    "UMCSENT": "Michigan Consumer Sentiment",
    "DFF": "Effective Federal Funds Rate",
    "ICSA": "Initial Jobless Claims",
}


def fetch_series(series_id: str, limit: int = 800):
    """Fetch observations for one series. Returns list of (date, float_value) tuples."""
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": str(limit),
    }
    url = f"{FRED_BASE}?{urllib.parse.urlencode(params)}"
    # Note: FRED's edge (Akamai) silently stalls response bodies for some
    # custom User-Agent strings, causing read timeouts. Using a curl-style UA
    # or the urllib default works reliably. Do NOT set "market-sentiment-skill/1.0".
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "observations" not in data:
        raise ValueError(f"FRED error for {series_id}: {data.get('error_message','unknown')}")
    return [(o["date"], float(o["value"])) for o in data["observations"] if o["value"] != "."]


def summarize(series_id: str, obs):
    """Compute latest value, 3y z-score, percentile rank."""
    if not obs:
        return {"series_id": series_id, "error": "no observations"}
    import numpy as np
    # obs is descending by date (most recent first); reverse for analysis
    obs_sorted = sorted(obs, key=lambda x: x[0])
    values = np.array([v for _, v in obs_sorted], dtype=float)
    latest_date = obs_sorted[-1][0]
    latest_value = float(values[-1])

    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    z = (latest_value - mean) / std if std > 0 else 0.0
    pct = round(100.0 * (values <= latest_value).sum() / len(values), 1)

    return {
        "series_id": series_id,
        "label": SERIES_LABELS.get(series_id, series_id),
        "latest_value": round(latest_value, 4),
        "latest_date": latest_date,
        "n_obs": len(values),
        "mean_3y": round(mean, 4),
        "std_3y": round(std, 4),
        "z_score": round(z, 3),
        "percentile_3y": pct,
        "min_3y": round(float(np.min(values)), 4),
        "max_3y": round(float(np.max(values)), 4),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--series", default=",".join(DEFAULT_SERIES),
                   help="Comma-separated FRED series IDs")
    p.add_argument("--limit", type=int, default=800,
                   help="Max observations per series (800 = ~3y daily or ~15y weekly)")
    args = p.parse_args()

    series_ids = [s.strip() for s in args.series.split(",") if s.strip()]
    results = {}
    for sid in series_ids:
        try:
            obs = fetch_series(sid, args.limit)
            results[sid] = summarize(sid, obs)
        except Exception as e:
            results[sid] = {"series_id": sid, "error": str(e)}

    out = {
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "FRED (St. Louis Fed)",
        "series": results,
    }
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
