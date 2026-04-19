#!/usr/bin/env python3
"""
utils.py — shared helpers for loading watchlist, merging thresholds, and
managing state. Meant to be imported OR called via CLI.

CLI modes:
  python utils.py load-watchlist <path>
  python utils.py get-window <state-path>      # prints {"start":..., "end":..., "first_run":...}
  python utils.py update-state <state-path> <report-path>
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


DEFAULT_THRESHOLDS = {
    "price_move_pct": 3.0,
    "volume_multiple": 2.0,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "window_move_pct": 7.0,
    "sentiment_delta": 0.3,
}


def load_watchlist(path):
    if yaml is None:
        raise RuntimeError("pyyaml not installed")
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    # Normalize into a list of clusters, each with name/thesis/thresholds/tickers
    clusters = []
    if "clusters" in data:
        order = data.get("cluster_order") or sorted(data["clusters"].keys())
        for name in order:
            if name not in data["clusters"]:
                continue
            c = data["clusters"][name]
            clusters.append({
                "name": name,
                "thesis": c.get("thesis", ""),
                "thresholds": {**DEFAULT_THRESHOLDS, **(c.get("thresholds") or {})},
                "tickers": c.get("tickers", []),
            })
    if "uncategorized" in data:
        clusters.append({
            "name": "uncategorized",
            "thesis": "Names without a specific theme",
            "thresholds": DEFAULT_THRESHOLDS.copy(),
            "tickers": data["uncategorized"].get("tickers", []),
        })
    # Flat-list fallback
    if not clusters and "tickers" in data:
        clusters.append({
            "name": "all",
            "thesis": "Flat watchlist — no clusters defined",
            "thresholds": DEFAULT_THRESHOLDS.copy(),
            "tickers": data["tickers"],
        })
    return clusters


def get_window(state_path):
    now = datetime.now(timezone.utc)
    p = Path(state_path)
    if not p.exists():
        start = now - timedelta(days=7)
        return {"start": start.date().isoformat(), "end": now.date().isoformat(), "first_run": True}
    try:
        state = json.loads(p.read_text())
        last = datetime.fromisoformat(state["last_run_utc"].replace("Z", "+00:00"))
        days = max(1, (now - last).days)
        start = now - timedelta(days=days)
        return {"start": start.date().isoformat(), "end": now.date().isoformat(), "first_run": False}
    except Exception:
        start = now - timedelta(days=7)
        return {"start": start.date().isoformat(), "end": now.date().isoformat(), "first_run": True}


def update_state(state_path, report_path):
    now = datetime.now(timezone.utc)
    state = {
        "last_run_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "last_report_path": str(report_path),
    }
    Path(state_path).write_text(json.dumps(state, indent=2))
    return state


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: utils.py <load-watchlist|get-window|update-state> ...")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "load-watchlist":
        print(json.dumps(load_watchlist(sys.argv[2]), indent=2))
    elif cmd == "get-window":
        print(json.dumps(get_window(sys.argv[2])))
    elif cmd == "update-state":
        print(json.dumps(update_state(sys.argv[2], sys.argv[3])))
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)
