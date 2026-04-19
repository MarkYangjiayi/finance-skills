#!/usr/bin/env python3
"""
fetch_news_yahoo.py — Yahoo Finance RSS news for a ticker.

Yahoo exposes a per-ticker RSS feed:
    https://feeds.finance.yahoo.com/rss/2.0/headline?s=<TICKER>&region=US&lang=en-US

Note: Yahoo's RSS uses the bare US symbol (no .US suffix). For non-US tickers,
we strip the exchange suffix and try — Yahoo sometimes returns results for the
underlying symbol, sometimes not. Skip gracefully if empty.

Output: JSON list of {title, link, published, summary} filtered to items since --since.
"""
import argparse
import json
import sys
from datetime import datetime

try:
    import feedparser
except ImportError:
    print(json.dumps({"error": "feedparser not installed"}))
    sys.exit(0)


def yahoo_symbol(ticker: str) -> str:
    # Strip EODHD-style exchange suffix for Yahoo
    if "." in ticker:
        base, ex = ticker.rsplit(".", 1)
        if ex.upper() == "US":
            return base
        # Non-US: Yahoo uses its own suffixes; best effort pass-through
        # (e.g. ASML.AS → AS.AS doesn't work; user should rely on EODHD news for non-US)
        return ticker
    return ticker


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--since", required=True, help="YYYY-MM-DD lower bound")
    ap.add_argument("--limit", type=int, default=15)
    args = ap.parse_args()

    sym = yahoo_symbol(args.ticker)
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&region=US&lang=en-US"

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(json.dumps({"ticker": args.ticker, "error": f"feed parse failed: {e}", "items": []}))
        return

    since = datetime.strptime(args.since, "%Y-%m-%d")
    items = []
    for entry in feed.entries:
        pub = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub = datetime(*entry.published_parsed[:6])
        if pub and pub < since:
            continue
        items.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": pub.isoformat() if pub else entry.get("published", ""),
            "summary": entry.get("summary", "")[:500],
        })
        if len(items) >= args.limit:
            break

    print(json.dumps({"ticker": args.ticker, "yahoo_symbol": sym, "items": items}))


if __name__ == "__main__":
    main()
