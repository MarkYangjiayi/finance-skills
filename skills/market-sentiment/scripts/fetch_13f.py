#!/usr/bin/env python3
"""
fetch_13f.py — Pull recent 13F-HR filings via edgartools (SEC EDGAR) for a
default basket of well-known hedge funds / asset managers.

For each fund, grabs the two most recent 13F-HR filings and produces:
  - A summary of the latest holdings (top N by value)
  - The net change in positions vs the prior quarter (additions, reductions,
    new positions, exits, and weight changes)

This script emits JSON. It is deliberately slow (~5-10 seconds per fund) because
each filing requires an SEC EDGAR fetch, and SEC asks clients to self-throttle.
Reduce the --funds list if you want speed.

IMPORTANT CAVEATS to always state in reports using this data:
  1. 13F filings are due 45 days after quarter-end, so the data is always
     1-3 months stale.
  2. Long equity positions ONLY — no shorts, no derivatives, no fixed income.
  3. US-listed equities only.
  4. $100M AUM minimum — does not cover smaller funds.

Usage:
    python fetch_13f.py                                  # default fund list
    python fetch_13f.py --funds 0001067983,0001350694    # Berkshire + Bridgewater
    python fetch_13f.py --top 15                         # show top 15 holdings per fund
    python fetch_13f.py --list-funds                     # show default basket
"""

import argparse
import json
import sys
from collections import defaultdict

try:
    from edgar import set_identity, Company
except ImportError:
    print(json.dumps({"error": "edgartools not installed. Run: pip install edgartools --break-system-packages --quiet"}))
    sys.exit(1)


# Default basket of "smart money" funds. These are all 13F filers with distinct
# investing styles — a mix of concentrated value (Berkshire), global macro
# (Bridgewater), pure quant (RenTec, Two Sigma), multi-strat (Citadel, Millennium,
# Point72), growth (Tiger Global), and value (Baupost).
DEFAULT_FUNDS = {
    "0001067983": "Berkshire Hathaway",
    "0001350694": "Bridgewater Associates",
    "0001037389": "Renaissance Technologies",
    "0001423053": "Citadel Advisors",
    "0001273087": "Millennium Management",
    "0001603466": "Point72 Asset Management",
    "0001009207": "D.E. Shaw",
    "0001179392": "Two Sigma",
    "0001167483": "Tiger Global",
    "0001061165": "Baupost Group",
}


def holdings_to_dict(info_table):
    """Convert the infotable DataFrame to a {cusip: {...}} dict, aggregating
    duplicate rows for the same security (13Fs often list a single issuer
    across multiple sub-accounts with different investment discretion codes).

    edgartools DataFrame columns:
      - Issuer (str), Class (str), Cusip (str), Ticker (str)
      - Value (int64) — IN ACTUAL US DOLLARS (post-2022 SEC rule change; older filings
        were in thousands, but edgartools normalizes to dollars)
      - SharesPrnAmount (int64) — Number of shares (when Type='Shares')
      - Type (str) — 'Shares' or 'Principal' (bonds)
      - PutCall (str) — 'Put', 'Call', or blank (blank means direct long equity)
    """
    out = {}
    for _, row in info_table.iterrows():
        cusip = str(row.get("Cusip", "")).strip()
        if not cusip:
            continue
        # Skip derivative rows (puts/calls) — we only want direct long equity for this skill
        put_call = str(row.get("PutCall", "") or "").strip()
        if put_call in ("Put", "Call"):
            continue

        ticker = str(row.get("Ticker", "") or "").strip()
        issuer = str(row.get("Issuer", "") or "").strip()
        try:
            value = int(row.get("Value", 0) or 0)
        except (ValueError, TypeError):
            value = 0
        try:
            shares = int(row.get("SharesPrnAmount", 0) or 0)
        except (ValueError, TypeError):
            shares = 0

        if cusip in out:
            out[cusip]["value"] += value
            out[cusip]["shares"] += shares
        else:
            out[cusip] = {
                "cusip": cusip,
                "ticker": ticker,
                "issuer": issuer,
                "value": value,
                "shares": shares,
            }
    return out


def diff_holdings(latest, prior):
    """Compute position-level changes between two periods.

    Returns dict of: additions, reductions, new_positions, exits, unchanged.
    Each is a list of holding dicts with 'change_value' / 'change_shares' populated.
    """
    additions = []
    reductions = []
    new_positions = []
    exits = []
    unchanged = []

    prior_cusips = set(prior.keys())
    latest_cusips = set(latest.keys())

    for cusip in latest_cusips - prior_cusips:
        h = dict(latest[cusip])
        h["change_value"] = h["value"]
        h["change_shares"] = h["shares"]
        new_positions.append(h)

    for cusip in prior_cusips - latest_cusips:
        h = dict(prior[cusip])
        h["change_value"] = -h["value"]
        h["change_shares"] = -h["shares"]
        exits.append(h)

    for cusip in latest_cusips & prior_cusips:
        h_l = latest[cusip]
        h_p = prior[cusip]
        dv = h_l["value"] - h_p["value"]
        ds = h_l["shares"] - h_p["shares"]
        h = dict(h_l)
        h["change_value"] = dv
        h["change_shares"] = ds
        if ds > 0:
            additions.append(h)
        elif ds < 0:
            reductions.append(h)
        else:
            unchanged.append(h)

    return {
        "new_positions": new_positions,
        "exits": exits,
        "additions": additions,
        "reductions": reductions,
        "unchanged": unchanged,
    }


def analyze_fund(cik: str, name: str, top_n: int = 10):
    """Analyze one fund. Returns summary dict or {'error': ...}."""
    try:
        company = Company(cik)
    except Exception as e:
        return {"cik": cik, "name": name, "error": f"Company lookup failed: {e}"}

    try:
        filings = company.get_filings(form="13F-HR").head(2)
        filing_list = list(filings)
        if not filing_list:
            return {"cik": cik, "name": name, "error": "No 13F-HR filings found"}
    except Exception as e:
        return {"cik": cik, "name": name, "error": f"Filing fetch failed: {e}"}

    try:
        latest_filing = filing_list[0]
        latest_obj = latest_filing.obj()
        latest_holdings = holdings_to_dict(latest_obj.infotable)
    except Exception as e:
        return {"cik": cik, "name": name, "error": f"Latest infotable parse failed: {e}"}

    latest_total = sum(h["value"] for h in latest_holdings.values())
    latest_positions = len(latest_holdings)

    # Sort top holdings by value
    top_holdings = sorted(latest_holdings.values(), key=lambda h: -h["value"])[:top_n]
    for h in top_holdings:
        h["weight_pct"] = round(100 * h["value"] / latest_total, 2) if latest_total else 0.0

    result = {
        "cik": cik,
        "name": name,
        "latest_filing_date": str(latest_filing.filing_date),
        "latest_total_value_usd": latest_total,
        "latest_position_count": latest_positions,
        "top_holdings": top_holdings,
    }

    # If we have a prior filing, compute the diff
    if len(filing_list) > 1:
        try:
            prior_filing = filing_list[1]
            prior_obj = prior_filing.obj()
            prior_holdings = holdings_to_dict(prior_obj.infotable)
            diffs = diff_holdings(latest_holdings, prior_holdings)

            # Sort each change bucket
            diffs["new_positions"].sort(key=lambda h: -h["change_value"])
            diffs["exits"].sort(key=lambda h: -abs(h["change_value"]))
            diffs["additions"].sort(key=lambda h: -h["change_value"])
            diffs["reductions"].sort(key=lambda h: -abs(h["change_value"]))

            result["prior_filing_date"] = str(prior_filing.filing_date)
            result["qoq_changes"] = {
                "n_new_positions": len(diffs["new_positions"]),
                "n_exits": len(diffs["exits"]),
                "n_additions": len(diffs["additions"]),
                "n_reductions": len(diffs["reductions"]),
                "n_unchanged": len(diffs["unchanged"]),
                "top_new_positions": diffs["new_positions"][:5],
                "top_exits": diffs["exits"][:5],
                "top_additions": diffs["additions"][:5],
                "top_reductions": diffs["reductions"][:5],
            }
        except Exception as e:
            result["qoq_changes_error"] = str(e)

    return result


def aggregate_cohort(fund_results):
    """Across all funds, tally which tickers saw the most net buying vs selling."""
    net_buying = defaultdict(lambda: {"ticker": "", "issuer": "", "n_funds_adding": 0, "n_funds_reducing": 0, "net_change_value": 0})

    for f in fund_results:
        if "qoq_changes" not in f:
            continue
        for h in f["qoq_changes"].get("top_new_positions", []) + f["qoq_changes"].get("top_additions", []):
            key = h.get("ticker") or h.get("cusip")
            net_buying[key]["ticker"] = h.get("ticker", "")
            net_buying[key]["issuer"] = h.get("issuer", "")
            net_buying[key]["n_funds_adding"] += 1
            net_buying[key]["net_change_value"] += h.get("change_value", 0)
        for h in f["qoq_changes"].get("top_exits", []) + f["qoq_changes"].get("top_reductions", []):
            key = h.get("ticker") or h.get("cusip")
            net_buying[key]["ticker"] = h.get("ticker", "")
            net_buying[key]["issuer"] = h.get("issuer", "")
            net_buying[key]["n_funds_reducing"] += 1
            net_buying[key]["net_change_value"] += h.get("change_value", 0)

    ranked = sorted(net_buying.values(), key=lambda x: -x["net_change_value"])
    return {
        "top_cohort_buys": ranked[:10],
        "top_cohort_sells": ranked[-10:][::-1],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--funds", default=None, help="Comma-separated CIKs (overrides default basket)")
    p.add_argument("--top", type=int, default=10, help="Top N holdings per fund (default 10)")
    p.add_argument("--list-funds", action="store_true", help="Print default basket and exit")
    args = p.parse_args()

    if args.list_funds:
        for cik, name in DEFAULT_FUNDS.items():
            print(f"  {cik}  {name}")
        return

    # edgartools requires an identity header (SEC courtesy requirement)
    set_identity("Market Sentiment Skill research@example.com")

    if args.funds:
        fund_ciks = [c.strip() for c in args.funds.split(",") if c.strip()]
        fund_names = {c: DEFAULT_FUNDS.get(c, f"CIK {c}") for c in fund_ciks}
    else:
        fund_names = DEFAULT_FUNDS
        fund_ciks = list(DEFAULT_FUNDS.keys())

    results = []
    for cik in fund_ciks:
        name = fund_names.get(cik, f"CIK {cik}")
        print(f"[fetching] {name} ({cik})...", file=sys.stderr)
        result = analyze_fund(cik, name, top_n=args.top)
        results.append(result)

    cohort = aggregate_cohort(results)

    out = {
        "caveats": [
            "13F filings are 45+ days stale (due 45 days after quarter-end)",
            "Long US equity positions only — no shorts, no derivatives, no foreign",
            "Only managers with $100M+ in 13F-eligible assets",
        ],
        "funds_analyzed": len(results),
        "cohort_summary": cohort,
        "funds": results,
    }
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
