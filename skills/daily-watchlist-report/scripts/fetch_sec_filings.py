#!/usr/bin/env python3
"""
fetch_sec_filings.py — recent 8-K material events for a US ticker.

Uses edgartools. 8-K is the form for "material events between periodic filings"
— things like acquisitions, resignations, earnings pre-announcements, etc.
These often move stocks before news wires catch up.

For non-US tickers (anything with a non-.US suffix), this script returns an
empty list — foreign issuers file 6-K or 20-F, which we can add later if useful.

Output: JSON list of {form, filed_date, accession_no, items, url}
"""
import argparse
import json
import sys
from datetime import datetime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--since", required=True)
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()

    # Non-US ticker → skip
    if "." in args.ticker and not args.ticker.upper().endswith(".US"):
        print(json.dumps({"ticker": args.ticker, "filings": [], "note": "non-US, skipped"}))
        return

    bare = args.ticker.split(".")[0]

    try:
        from edgar import Company, set_identity
    except ImportError:
        print(json.dumps({
            "ticker": args.ticker,
            "error": "edgartools not installed (pip install edgartools)",
            "filings": [],
        }))
        return

    # SEC requires a user-agent identity. Use a reasonable default; user can override
    # by setting EDGAR_IDENTITY env var.
    import os
    set_identity(os.environ.get("EDGAR_IDENTITY", "watchlist-report user@example.com"))

    try:
        co = Company(bare)
        filings = co.get_filings(form="8-K")
    except Exception as e:
        print(json.dumps({"ticker": args.ticker, "error": f"edgar fetch failed: {e}", "filings": []}))
        return

    since = datetime.strptime(args.since, "%Y-%m-%d").date()
    out = []
    checked = 0
    # Use pandas conversion to avoid edgartools' buggy __getitem__ / __iter__
    try:
        df = filings.to_pandas()
    except Exception as e:
        print(json.dumps({"ticker": args.ticker, "error": f"filings.to_pandas() failed: {e}", "filings": []}))
        return

    for _, row in df.iterrows():
        if checked >= args.limit * 3:
            break
        checked += 1
        try:
            filed_raw = row.get("filing_date") or row.get("filingDate") or row.get("date")
            if filed_raw is None:
                continue
            filed = filed_raw if hasattr(filed_raw, "date") else datetime.strptime(str(filed_raw)[:10], "%Y-%m-%d").date()
            if hasattr(filed, "date"):
                filed = filed.date()
            if filed < since:
                continue
            out.append({
                "form": str(row.get("form", "8-K")),
                "filed_date": filed.isoformat(),
                "accession_no": str(row.get("accession_no", row.get("accessionNo", ""))),
                "url": str(row.get("homepage_url", row.get("filing_url", ""))),
            })
            if len(out) >= args.limit:
                break
        except Exception:
            continue

    print(json.dumps({"ticker": args.ticker, "filings": out}))


if __name__ == "__main__":
    main()
