#!/usr/bin/env python3
"""
detect_anomalies.py — apply thresholds to a price snapshot and decide flags.

Reads JSON from stdin (the output of fetch_prices.py) and a thresholds JSON
from --thresholds, writes JSON to stdout with a 'flags' list of human-readable
reasons why this ticker deserves attention today. Empty list = quiet.

Usage:
  cat price.json | python detect_anomalies.py --thresholds '{"price_move_pct":3.0,"volume_multiple":2.0}'
"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thresholds", required=True, help="JSON string of threshold overrides")
    args = ap.parse_args()

    try:
        data = json.load(sys.stdin)
    except Exception as e:
        print(json.dumps({"error": f"bad stdin: {e}"}))
        return

    th = {
        "price_move_pct": 3.0,
        "volume_multiple": 2.0,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "window_move_pct": 7.0,  # used for catch-up mode
    }
    try:
        th.update(json.loads(args.thresholds))
    except Exception:
        pass

    flags = []
    if "error" in data:
        print(json.dumps({"ticker": data.get("ticker"), "flags": [], "error": data["error"]}))
        return

    pct_1d = data.get("pct_change_1d") or 0
    pct_w = data.get("pct_change_window") or 0
    vol_m = data.get("volume_vs_20d_avg")
    rsi_v = data.get("rsi_14")
    pos_52 = data.get("pos_52w")

    if abs(pct_1d) >= th["price_move_pct"]:
        flags.append(f"price move {pct_1d:+.1f}% on last session")
    if abs(pct_w) >= th["window_move_pct"] and abs(pct_w) > abs(pct_1d):
        flags.append(f"cumulative {pct_w:+.1f}% over window")
    if vol_m and vol_m >= th["volume_multiple"]:
        flags.append(f"volume {vol_m:.1f}× 20d avg")
    if rsi_v is not None:
        if rsi_v >= th["rsi_overbought"]:
            flags.append(f"RSI overbought ({rsi_v:.0f})")
        elif rsi_v <= th["rsi_oversold"]:
            flags.append(f"RSI oversold ({rsi_v:.0f})")
    if pos_52 is not None:
        if pos_52 >= 0.98:
            flags.append("at/near 52w high")
        elif pos_52 <= 0.02:
            flags.append("at/near 52w low")

    out = dict(data)
    out["flags"] = flags
    out["is_quiet"] = len(flags) == 0
    print(json.dumps(out))


if __name__ == "__main__":
    main()
