#!/usr/bin/env python3
"""
compute_composite.py — Aggregate sentiment indicators into a tier-weighted
composite z-score, apply sign alignment, and flag individual extremes.

Reads JSON outputs from fetch_fred.py, fetch_yfinance_vol.py, fetch_cot.py
and produces a single unified dashboard view.

Usage:
    # Feed individual fetcher outputs as separate files
    python compute_composite.py \\
        --fred /tmp/fred.json \\
        --yf /tmp/yf.json \\
        --cot /tmp/cot_spx.json

    # Or read a combined JSON from stdin
    cat combined.json | python compute_composite.py --stdin

    # Or run the entire pipeline end-to-end (calls the other fetchers)
    python compute_composite.py --run-all --cot-market SPX

Output: A JSON report with tier breakdowns, aligned z-scores, composite score,
regime label, and the list of flagged indicators at 3y extremes.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# ==============================================================================
# Sign alignment table
# After alignment, POSITIVE z = greedy/complacent/risk-on, NEGATIVE = fearful/risk-off.
#
# Format: {source_key: {indicator_key: (tier, weight, flip_sign, display_label)}}
# - tier: 1 (strongest evidence) or 2 (supporting)
# - weight: multiplier applied within the tier average
# - flip_sign: True if we need to flip raw z (high = fear)
# - display_label: human-readable name
# ==============================================================================

FRED_MAPPING = {
    "BAMLH0A0HYM2": (1, 2.0, True,  "HY credit spread"),
    "BAMLC0A0CM":   (1, 1.0, True,  "IG credit spread"),
    "BAMLH0A3HYC":  (1, 1.0, True,  "CCC credit spread (distress tier)"),
    "T10Y2Y":       (1, 1.0, False, "10Y-2Y yield curve"),
    "NFCI":         (1, 2.0, True,  "Chicago Fed NFCI"),
    "STLFSI4":      (1, 1.0, True,  "St Louis Fed Stress Index"),
    "VIXCLS":       (1, 1.0, True,  "VIX (FRED)"),  # redundant w/ ^VIX; weight 1
    "UMCSENT":      (2, 1.0, False, "Michigan Consumer Sentiment"),
}

YFINANCE_MAPPING = {
    "^VIX":     (1, 2.0, True,  "VIX (yfinance)"),
    "^VIX3M":   (1, 1.0, True,  "VIX3M (3-month implied vol)"),
    "^SKEW":    (1, 1.0, True,  "CBOE SKEW (tail risk pricing)"),
    "GC=F":     (2, 1.0, True,  "Gold futures (safe haven)"),
    "HG=F":     (2, 1.0, False, "Copper futures (growth proxy)"),
    "^TNX":     (2, 0.5, False, "10Y Treasury yield"),  # weak signal, light weight
}

# Derived indicators from yfinance script
YFINANCE_DERIVED_MAPPING = {
    # For the VIX term structure ratio: we don't z-score it, we score based on
    # hardcoded thresholds matching the research (backwardation = contrarian buy)
    "vix3m_vix_ratio": (1, 2.0, "VIX3M/VIX term structure ratio"),
}


def _deep_get(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d


def _classify_percentile(pct):
    """Return 'extreme_high', 'high', 'normal', 'low', or 'extreme_low'."""
    if pct is None:
        return "unknown"
    if pct >= 90:
        return "extreme_high"
    if pct >= 75:
        return "high"
    if pct <= 10:
        return "extreme_low"
    if pct <= 25:
        return "low"
    return "normal"


def extract_fred_indicators(fred_json):
    """Pull indicators from fetch_fred.py output. Returns list of dicts."""
    out = []
    series_dict = fred_json.get("series", {})
    for sid, mapping in FRED_MAPPING.items():
        s = series_dict.get(sid)
        if not s or "error" in s:
            continue
        tier, weight, flip, label = mapping
        raw_z = s.get("z_score", 0.0)
        aligned_z = -raw_z if flip else raw_z
        out.append({
            "source": "FRED",
            "id": sid,
            "label": label,
            "tier": tier,
            "weight": weight,
            "latest_value": s.get("latest_value"),
            "latest_date": s.get("latest_date"),
            "percentile_3y": s.get("percentile_3y"),
            "raw_z": raw_z,
            "aligned_z": round(aligned_z, 3),
            "flipped": flip,
            "classification": _classify_percentile(s.get("percentile_3y")),
        })
    return out


def extract_yfinance_indicators(yf_json):
    """Pull indicators from fetch_yfinance_vol.py output."""
    out = []
    tickers = yf_json.get("tickers", {})
    for tid, mapping in YFINANCE_MAPPING.items():
        s = tickers.get(tid)
        if not s or "error" in s:
            continue
        tier, weight, flip, label = mapping
        raw_z = s.get("z_score", 0.0)
        aligned_z = -raw_z if flip else raw_z
        out.append({
            "source": "yfinance",
            "id": tid,
            "label": label,
            "tier": tier,
            "weight": weight,
            "latest_value": s.get("latest_value"),
            "latest_date": s.get("latest_date"),
            "percentile_3y": s.get("percentile_3y"),
            "raw_z": raw_z,
            "aligned_z": round(aligned_z, 3),
            "flipped": flip,
            "classification": _classify_percentile(s.get("percentile_3y")),
        })

    # Special handling for the VIX term structure ratio.
    # Translate the ratio into a synthetic z-score using empirical thresholds:
    # ratio > 1.15 = very strong contango = complacent = z=+1.0
    # ratio in 1.05-1.15 = contango = z=+0.3
    # ratio in 0.95-1.05 = flat = z=0
    # ratio in 0.90-0.95 = mild backwardation = z=-1.0
    # ratio < 0.90 = deep backwardation = z=-2.0
    derived = yf_json.get("derived", {})
    ts = derived.get("vix3m_vix_ratio")
    if ts and ts.get("latest_value") is not None:
        r = ts["latest_value"]
        if r >= 1.15:
            synthetic_z, pct_proxy = 1.0, 85
        elif r >= 1.05:
            synthetic_z, pct_proxy = 0.3, 65
        elif r >= 0.95:
            synthetic_z, pct_proxy = 0.0, 50
        elif r >= 0.90:
            synthetic_z, pct_proxy = -1.0, 15
        else:
            synthetic_z, pct_proxy = -2.0, 3
        tier, weight, label = YFINANCE_DERIVED_MAPPING["vix3m_vix_ratio"]
        out.append({
            "source": "yfinance_derived",
            "id": "vix3m_vix_ratio",
            "label": label,
            "tier": tier,
            "weight": weight,
            "latest_value": r,
            "latest_date": None,
            "percentile_3y": pct_proxy,
            "raw_z": synthetic_z,
            "aligned_z": synthetic_z,
            "flipped": False,
            "classification": _classify_percentile(pct_proxy),
            "note": "synthetic z from empirical term-structure thresholds",
        })
    return out


def extract_cot_indicator(cot_json):
    """Convert a COT report (from fetch_cot.py) into a single contrarian indicator.

    The COT index is 0-100 (percentile of net positioning in 3y). For trend-following
    groups (lev_money, m_money, noncomm), extreme positioning is a contrarian signal:
    - COT index 80-100 = crowded long = contrarian bearish = aligned z NEGATIVE
    - COT index 0-20 = washed out = contrarian bullish = aligned z POSITIVE

    We convert the 0-100 percentile to a z-score via the inverse normal CDF
    (approximately linear in the 20-80 range for this purpose, but extremes get
    amplified).
    """
    summary = cot_json.get("summary", {})
    groups = summary.get("groups", {})
    market = cot_json.get("market", "unknown")

    # Which group to use as the contrarian signal
    focus_group_by_report = {
        "tff": "lev_money",
        "disagg": "m_money",
        "legacy": "noncomm",
    }
    report_type = cot_json.get("report_type", "tff")
    focus = focus_group_by_report.get(report_type, "lev_money")
    g = groups.get(focus)
    if not g or g.get("cot_index_3y") is None:
        return None

    cot_idx = g["cot_index_3y"]  # 0-100
    net = g.get("net", 0)

    # Convert percentile to a symmetric z-score:
    # 50 → 0, 95 → +1.645, 5 → -1.645 (roughly standard normal inverse)
    # Simple linear approximation: z_pct = (pct - 50) / 25
    # (So pct=100 → z=+2, pct=0 → z=-2)
    z_pct = (cot_idx - 50.0) / 25.0
    # FLIP sign because crowded long (high pct) is contrarian bearish
    aligned_z = -z_pct

    return {
        "source": "CFTC COT",
        "id": f"cot_{focus}_{market[:20]}",
        "label": f"COT {focus} positioning in {market}",
        "tier": 2,
        "weight": 1.5,  # COT is tier 2 but deserves a higher weight than other tier 2s
        "latest_value": cot_idx,
        "latest_date": summary.get("latest_date"),
        "percentile_3y": cot_idx,  # already a percentile
        "raw_z": round(z_pct, 3),
        "aligned_z": round(aligned_z, 3),
        "flipped": True,
        "classification": _classify_percentile(cot_idx),
        "note": f"Net {'long' if net >= 0 else 'short'} {abs(net):,} contracts. COT index is contrarian at extremes.",
    }


def compute_composite(indicators):
    """Aggregate all indicators into a tier-weighted composite score."""
    tier_1 = [i for i in indicators if i["tier"] == 1]
    tier_2 = [i for i in indicators if i["tier"] == 2]

    def weighted_avg(items):
        if not items:
            return None
        total_w = sum(i["weight"] for i in items)
        if total_w == 0:
            return None
        return sum(i["aligned_z"] * i["weight"] for i in items) / total_w

    t1_z = weighted_avg(tier_1)
    t2_z = weighted_avg(tier_2)

    # Tier 1 gets 2x weight vs Tier 2 in the composite
    if t1_z is not None and t2_z is not None:
        composite = (t1_z * 2 + t2_z * 1) / 3
    elif t1_z is not None:
        composite = t1_z
    elif t2_z is not None:
        composite = t2_z
    else:
        composite = None

    # Regime label
    def label_for(z):
        if z is None:
            return "UNKNOWN"
        if z > 2.0:
            return "EXTREME GREED"
        if z > 1.0:
            return "Greed"
        if z > -1.0:
            return "Neutral"
        if z > -2.0:
            return "Fear"
        return "EXTREME FEAR"

    return {
        "tier_1_z": round(t1_z, 3) if t1_z is not None else None,
        "tier_2_z": round(t2_z, 3) if t2_z is not None else None,
        "composite_z": round(composite, 3) if composite is not None else None,
        "regime": label_for(composite),
        "n_tier_1_indicators": len(tier_1),
        "n_tier_2_indicators": len(tier_2),
    }


def find_extreme_flags(indicators):
    """Return the list of indicators at 3y extremes (top/bottom 10%)."""
    flags = []
    for i in indicators:
        if i["classification"] in ("extreme_high", "extreme_low"):
            flags.append({
                "source": i["source"],
                "label": i["label"],
                "percentile_3y": i["percentile_3y"],
                "latest_value": i["latest_value"],
                "aligned_z": i["aligned_z"],
                "classification": i["classification"],
                "interpretation": _interpret_flag(i),
            })
    flags.sort(key=lambda f: abs(f["aligned_z"]), reverse=True)
    return flags


def _interpret_flag(indicator):
    """Short plain-English interpretation of why an indicator is flagged."""
    cls = indicator["classification"]
    label = indicator["label"]
    pct = indicator["percentile_3y"]
    direction = "near 3y HIGH" if cls == "extreme_high" else "near 3y LOW"
    aligned_sign = "+" if indicator["aligned_z"] >= 0 else "-"
    mood = "complacency/greed" if indicator["aligned_z"] > 0 else "stress/fear"
    return f"{label} at {pct}th percentile — {direction}. Aligned z {aligned_sign}{abs(indicator['aligned_z']):.1f} → contributes to {mood}."


def detect_conflicts(indicators, composite):
    """Identify cross-indicator conflicts worth surfacing."""
    conflicts = []
    labels_by_id = {i["id"]: i for i in indicators}

    # VIX vs SKEW divergence
    vix = labels_by_id.get("^VIX") or labels_by_id.get("VIXCLS")
    skew = labels_by_id.get("^SKEW")
    if vix and skew:
        if vix["percentile_3y"] and skew["percentile_3y"]:
            if vix["percentile_3y"] < 35 and skew["percentile_3y"] > 70:
                conflicts.append(
                    f"VIX low ({vix['percentile_3y']}th pct) but SKEW elevated ({skew['percentile_3y']}th pct): "
                    f"tail risk being priced in despite calm headline vol. Historically ambiguous."
                )
            elif vix["percentile_3y"] > 70 and skew["percentile_3y"] < 35:
                conflicts.append(
                    f"VIX elevated ({vix['percentile_3y']}th pct) but SKEW low ({skew['percentile_3y']}th pct): "
                    f"front-month stress without tail hedging demand — often a late-cycle bounce setup."
                )

    # Credit vs yield curve divergence
    hy = labels_by_id.get("BAMLH0A0HYM2")
    curve = labels_by_id.get("T10Y2Y")
    if hy and curve:
        if hy["percentile_3y"] is not None and curve["percentile_3y"] is not None:
            if hy["percentile_3y"] < 30 and curve["percentile_3y"] < 20:
                conflicts.append(
                    f"HY spreads tight (credit sees no stress) but yield curve flat/inverted (rates market sees recession). "
                    f"Classic long-lead warning: recession eventually arrives but equities can continue rallying 6-18 months."
                )

    # CCC quality spread vs IG/HY divergence
    ccc = labels_by_id.get("BAMLH0A3HYC")
    ig = labels_by_id.get("BAMLC0A0CM")
    if ccc and ig and hy:
        if (ccc["percentile_3y"] or 0) > 70 and (hy["percentile_3y"] or 100) < 40:
            conflicts.append(
                f"CCC (distress) spreads elevated ({ccc['percentile_3y']}th pct) while broad HY tight "
                f"({hy['percentile_3y']}th pct): quality divergence inside credit — weakest borrowers cracking first."
            )

    # Gold AND Copper both near highs (unusual)
    gold = labels_by_id.get("GC=F")
    copper = labels_by_id.get("HG=F")
    if gold and copper:
        if (gold["percentile_3y"] or 0) > 85 and (copper["percentile_3y"] or 0) > 85:
            conflicts.append(
                f"Gold AND copper both near 3y highs ({gold['percentile_3y']}th / {copper['percentile_3y']}th pct): "
                f"unusual. Safe-haven and growth metals rarely rally together. Likely reflects structural "
                f"factors (central bank gold buying, electrification copper demand) rather than a pure risk signal."
            )

    # Composite is neutral but multiple flags exist
    if composite.get("composite_z") is not None:
        if -0.5 < composite["composite_z"] < 0.5:
            n_flags = sum(1 for i in indicators if i["classification"] in ("extreme_high", "extreme_low"))
            if n_flags >= 3:
                conflicts.append(
                    f"Composite is neutral ({composite['composite_z']:+.2f}) but {n_flags} individual indicators "
                    f"are at 3y extremes. Bifurcated market — the average is masking genuine tension. "
                    f"Read the flags, not the composite."
                )

    return conflicts


def run_all_pipeline(cot_market: str):
    """Run all three fetchers and assemble a combined dict."""
    script_dir = Path(__file__).parent
    combined = {}

    # FRED
    try:
        out = subprocess.run(
            [sys.executable, str(script_dir / "fetch_fred.py")],
            capture_output=True, text=True, timeout=90,
        )
        if out.returncode == 0:
            combined["fred"] = json.loads(out.stdout)
        else:
            combined["fred_error"] = out.stderr
    except Exception as e:
        combined["fred_error"] = str(e)

    # yfinance
    try:
        out = subprocess.run(
            [sys.executable, str(script_dir / "fetch_yfinance_vol.py")],
            capture_output=True, text=True, timeout=120,
        )
        if out.returncode == 0:
            combined["yf"] = json.loads(out.stdout)
        else:
            combined["yf_error"] = out.stderr
    except Exception as e:
        combined["yf_error"] = str(e)

    # COT
    try:
        out = subprocess.run(
            [sys.executable, str(script_dir / "fetch_cot.py"), "--market", cot_market],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode == 0:
            combined["cot"] = json.loads(out.stdout)
        else:
            combined["cot_error"] = out.stderr
    except Exception as e:
        combined["cot_error"] = str(e)

    return combined


def build_report(combined):
    """Main pipeline: combined dict → indicators → composite → report."""
    indicators = []
    if "fred" in combined:
        indicators.extend(extract_fred_indicators(combined["fred"]))
    if "yf" in combined:
        indicators.extend(extract_yfinance_indicators(combined["yf"]))
    if "cot" in combined:
        cot_ind = extract_cot_indicator(combined["cot"])
        if cot_ind:
            indicators.append(cot_ind)

    composite = compute_composite(indicators)
    flags = find_extreme_flags(indicators)
    conflicts = detect_conflicts(indicators, composite)

    # Find top drivers (most extreme aligned z-scores)
    sorted_by_impact = sorted(
        indicators,
        key=lambda i: abs(i["aligned_z"]) * i["weight"],
        reverse=True,
    )
    top_drivers = [
        {
            "label": i["label"],
            "tier": i["tier"],
            "aligned_z": i["aligned_z"],
            "percentile_3y": i["percentile_3y"],
            "contribution": round(i["aligned_z"] * i["weight"], 3),
        }
        for i in sorted_by_impact[:5]
    ]

    return {
        "composite": composite,
        "top_drivers": top_drivers,
        "flagged_extremes": flags,
        "conflicts": conflicts,
        "all_indicators": indicators,
        "data_gaps": [
            k.replace("_error", "") for k in combined if k.endswith("_error")
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fred", help="Path to fetch_fred.py JSON output")
    p.add_argument("--yf", help="Path to fetch_yfinance_vol.py JSON output")
    p.add_argument("--cot", help="Path to fetch_cot.py JSON output")
    p.add_argument("--stdin", action="store_true", help="Read combined JSON from stdin")
    p.add_argument("--run-all", action="store_true", help="Run all fetchers in sequence")
    p.add_argument("--cot-market", default="SPX", help="Market alias for --run-all COT fetch (default SPX)")
    args = p.parse_args()

    if args.run_all:
        combined = run_all_pipeline(args.cot_market)
    elif args.stdin:
        combined = json.loads(sys.stdin.read())
    else:
        combined = {}
        if args.fred:
            combined["fred"] = json.loads(Path(args.fred).read_text())
        if args.yf:
            combined["yf"] = json.loads(Path(args.yf).read_text())
        if args.cot:
            combined["cot"] = json.loads(Path(args.cot).read_text())

    if not combined:
        print(json.dumps({"error": "No input. Use --run-all or provide --fred/--yf/--cot files or --stdin"}))
        sys.exit(1)

    report = build_report(combined)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
