#!/usr/bin/env python3
"""
fetch_cot.py — Pull CFTC Commitments of Traders data via the free Socrata API.

Three dataset types:
- legacy  (6dca-aqww): Commercial vs Non-commercial, all futures markets
- tff     (gpe5-46if): Traders in Financial Futures — S&P, Treasuries, FX. Use for equity indices.
- disagg  (72hh-3qpr): Disaggregated — Producer/Merchant / Swap Dealer / Managed Money. Use for commodities.

Usage:
    python fetch_cot.py --market "E-MINI S&P 500" --report tff
    python fetch_cot.py --market "GOLD" --report disagg
    python fetch_cot.py --market "CRUDE OIL, LIGHT SWEET-NYMEX" --report disagg

Outputs JSON with: latest_report, historical series of net positioning, COT index (0-100 percentile rank).
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request

DATASETS = {
    "legacy": {
        "id": "6dca-aqww",
        "market_field": "market_and_exchange_names",
        "long_fields": {
            "noncomm": "noncomm_positions_long_all",
            "comm": "comm_positions_long_all",
            "nonrept": "nonrept_positions_long_all",
        },
        "short_fields": {
            "noncomm": "noncomm_positions_short_all",
            "comm": "comm_positions_short_all",
            "nonrept": "nonrept_positions_short_all",
        },
        "focus_group": "noncomm",  # large speculators
    },
    "tff": {
        "id": "gpe5-46if",
        "market_field": "contract_market_name",
        "long_fields": {
            "dealer": "dealer_positions_long_all",
            "asset_mgr": "asset_mgr_positions_long",
            "lev_money": "lev_money_positions_long",
            "other_rept": "other_rept_positions_long",
        },
        "short_fields": {
            "dealer": "dealer_positions_short_all",
            "asset_mgr": "asset_mgr_positions_short",
            "lev_money": "lev_money_positions_short",
            "other_rept": "other_rept_positions_short",
        },
        "focus_group": "lev_money",  # hedge funds — trend followers, contrarian at extremes
    },
    "disagg": {
        "id": "72hh-3qpy",
        "market_field": "market_and_exchange_names",
        "long_fields": {
            "prod_merc": "prod_merc_positions_long",
            "swap": "swap_positions_long_all",
            "m_money": "m_money_positions_long_all",
            "other_rept": "other_rept_positions_long",
        },
        "short_fields": {
            "prod_merc": "prod_merc_positions_short",
            "swap": "swap_positions_short_all",
            "m_money": "m_money_positions_short_all",
            "other_rept": "other_rept_positions_short",
        },
        "focus_group": "m_money",  # managed money — same as lev_money in TFF
    },
}

# Convenience aliases — short names → exact CFTC market string
# Saves the caller from having to remember exact punctuation and exchange suffixes.
# Use --market with either the short alias or the full string.
MARKET_ALIASES = {
    # Equity indices (TFF)
    "ES": ("E-MINI S&P 500", "tff"),
    "SPX": ("E-MINI S&P 500", "tff"),
    "SP500": ("E-MINI S&P 500", "tff"),
    "NQ": ("E-MINI NASDAQ-100", "tff"),
    "NDX": ("E-MINI NASDAQ-100", "tff"),
    "RTY": ("E-MINI RUSSELL 2000", "tff"),
    "VIX": ("VIX FUTURES", "tff"),
    # Rates (TFF)
    "UST10Y": ("UST 10Y NOTE", "tff"),
    "UST2Y": ("UST 2Y NOTE", "tff"),
    "UST30Y": ("UST BOND", "tff"),
    # FX (TFF)
    "JPY": ("JAPANESE YEN", "tff"),
    "EUR": ("EURO FX", "tff"),
    "GBP": ("BRITISH POUND", "tff"),
    "CHF": ("SWISS FRANC", "tff"),
    "AUD": ("AUSTRALIAN DOLLAR", "tff"),
    "BTC": ("BITCOIN", "tff"),
    # Metals (Disagg)
    "GOLD": ("GOLD - COMMODITY EXCHANGE INC.", "disagg"),
    "SILVER": ("SILVER - COMMODITY EXCHANGE INC.", "disagg"),
    "COPPER": ("COPPER- #1 - COMMODITY EXCHANGE INC.", "disagg"),
    "PLATINUM": ("PLATINUM - NEW YORK MERCANTILE EXCHANGE", "disagg"),
    # Energy (Disagg)
    "CRUDE": ("WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE", "disagg"),
    "WTI": ("WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE", "disagg"),
    "NATGAS": ("NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE", "disagg"),
    # Grains (Disagg)
    "CORN": ("CORN - CHICAGO BOARD OF TRADE", "disagg"),
    "WHEAT": ("WHEAT-SRW - CHICAGO BOARD OF TRADE", "disagg"),
    "SOY": ("SOYBEANS - CHICAGO BOARD OF TRADE", "disagg"),
}


def fetch_series(report_type: str, market: str, limit: int = 160):
    """Fetch `limit` weekly reports for the given market. 160 weeks = ~3 years."""
    ds = DATASETS[report_type]
    market_field = ds["market_field"]

    # Socrata SoQL: filter by market, order descending by date, limit
    params = {
        "$limit": str(limit),
        "$order": "report_date_as_yyyy_mm_dd DESC",
        market_field: market,
    }
    qs = urllib.parse.urlencode(params)
    url = f"https://publicreporting.cftc.gov/resource/{ds['id']}.json?{qs}"

    req = urllib.request.Request(url, headers={"User-Agent": "market-sentiment-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def compute_net_positions(rows, report_type: str):
    """For each row, compute net positioning for every trader group."""
    ds = DATASETS[report_type]
    out = []
    for row in rows:
        record = {"date": row.get("report_date_as_yyyy_mm_dd", "")[:10]}
        for group in ds["long_fields"]:
            long_val = _to_int(row.get(ds["long_fields"][group]))
            short_val = _to_int(row.get(ds["short_fields"][group]))
            record[f"{group}_long"] = long_val
            record[f"{group}_short"] = short_val
            record[f"{group}_net"] = long_val - short_val
        record["open_interest"] = _to_int(row.get("open_interest_all"))
        out.append(record)
    return out


def _to_int(v):
    if v is None:
        return 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def compute_cot_index(series, group: str):
    """COT Index formula: 100 * (current_net - min_net) / (max_net - min_net)
    over the entire series (typically 3 years)."""
    nets = [r[f"{group}_net"] for r in series]
    if not nets:
        return None
    current = nets[0]  # series is DESC, so index 0 is latest
    lo, hi = min(nets), max(nets)
    if hi == lo:
        return 50.0
    return round(100 * (current - lo) / (hi - lo), 1)


def summarize_latest(series, report_type: str):
    """Build a plain-English summary of the latest week."""
    if not series:
        return {"error": "no data"}
    ds = DATASETS[report_type]
    latest = series[0]
    prev = series[1] if len(series) > 1 else None

    summary = {
        "latest_date": latest["date"],
        "previous_date": prev["date"] if prev else None,
        "groups": {},
    }
    for group in ds["long_fields"]:
        g = {
            "long": latest[f"{group}_long"],
            "short": latest[f"{group}_short"],
            "net": latest[f"{group}_net"],
            "cot_index_3y": compute_cot_index(series, group),
        }
        if prev:
            g["net_change_wow"] = latest[f"{group}_net"] - prev[f"{group}_net"]
        summary["groups"][group] = g

    # Flag extremes on the focus group.
    # COT Index is a percentile rank of the current net position within the 3y range,
    # NOT an absolute long/short classification. A high index means "nearer to 3y max net"
    # which could still be net short in absolute terms if the group is structurally short.
    focus = ds["focus_group"]
    cot_idx = summary["groups"][focus]["cot_index_3y"]
    focus_net = summary["groups"][focus]["net"]
    if cot_idx is not None:
        net_desc = f"net {'long' if focus_net >= 0 else 'short'} {abs(focus_net):,}"
        if cot_idx >= 80:
            summary["flag"] = (
                f"{focus} COT index = {cot_idx}/100 (3y percentile of net) — "
                f"near 3y HIGH of net positioning ({net_desc}). Contrarian bearish signal if "
                f"this group is trend-following (lev_money, m_money, noncomm)."
            )
        elif cot_idx <= 20:
            summary["flag"] = (
                f"{focus} COT index = {cot_idx}/100 (3y percentile of net) — "
                f"near 3y LOW of net positioning ({net_desc}). Contrarian bullish signal if "
                f"this group is trend-following (lev_money, m_money, noncomm)."
            )
        else:
            summary["flag"] = f"{focus} COT index = {cot_idx}/100 (3y percentile) — no extreme ({net_desc})"
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--market", required=True,
                   help="CFTC market name OR short alias. Aliases: " + ", ".join(sorted(MARKET_ALIASES.keys())))
    p.add_argument("--report", choices=["legacy", "tff", "disagg"], default=None,
                   help="Report type. If using an alias, inferred automatically. Otherwise defaults to tff.")
    p.add_argument("--limit", type=int, default=160, help="Number of weekly reports to fetch (default 160 = ~3 years)")
    p.add_argument("--raw", action="store_true", help="Also emit the raw weekly series")
    p.add_argument("--list-aliases", action="store_true", help="Print all aliases and exit")
    args = p.parse_args()

    if args.list_aliases:
        for k, (name, rpt) in sorted(MARKET_ALIASES.items()):
            print(f"  {k:10s} → {rpt:6s} {name}")
        return

    # Resolve alias if provided
    market_key = args.market.upper()
    if market_key in MARKET_ALIASES:
        market, inferred_report = MARKET_ALIASES[market_key]
        report_type = args.report or inferred_report
    else:
        market = args.market
        report_type = args.report or "tff"

    try:
        rows = fetch_series(report_type, market, args.limit)
    except urllib.error.HTTPError as e:
        print(json.dumps({
            "error": f"HTTP {e.code}: {e.reason}",
            "market_tried": market,
            "report_tried": report_type,
            "hint": "Check that --market matches the exact CFTC string, or use --list-aliases to see shortcuts",
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e), "market_tried": market}))
        sys.exit(1)

    if not rows:
        print(json.dumps({
            "error": "No data returned",
            "market_tried": market,
            "report_tried": report_type,
            "hint": f"No records found. The market name may be wrong. Try --list-aliases.",
        }))
        sys.exit(1)

    series = compute_net_positions(rows, report_type)
    summary = summarize_latest(series, report_type)

    out = {
        "report_type": report_type,
        "market": market,
        "n_weeks": len(series),
        "summary": summary,
    }
    if args.raw:
        out["series"] = series

    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
