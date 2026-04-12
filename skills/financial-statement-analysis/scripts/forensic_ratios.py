#!/usr/bin/env python3
"""
Forensic Accounting Ratios Calculator

Computes Beneish M-Score, Sloan Accruals Ratio, CFO/NI Quality Ratio,
and Altman Z-Score from EODHD fundamentals JSON data.

Usage:
    python forensic_ratios.py <fundamentals_json_path>
    
    Or import and call directly:
    from forensic_ratios import compute_all_forensic_ratios
    results = compute_all_forensic_ratios(fundamentals_dict)

Input: EODHD fundamentals JSON (full response from get_fundamentals_data)
Output: JSON with all forensic metrics, interpretations, and red flags
"""

import json
import sys
from typing import Optional


def safe_div(numerator, denominator, default=0.0):
    """Safe division that handles None, zero, and non-numeric values."""
    try:
        n = float(numerator) if numerator is not None else None
        d = float(denominator) if denominator is not None else None
        if n is None or d is None or d == 0:
            return default
        return n / d
    except (TypeError, ValueError):
        return default


def get_field(statement: dict, field: str, default=None):
    """Extract a numeric field from a financial statement entry."""
    val = statement.get(field, default)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def extract_annual_statements(fundamentals: dict, n_years: int = 5):
    """Extract the most recent n years of annual financial statements.
    
    Returns a list of dicts, each containing IS, BS, CF fields for one year,
    sorted from most recent to oldest.
    """
    financials = fundamentals.get("Financials", {})
    
    is_yearly = financials.get("Income_Statement", {}).get("yearly", {})
    bs_yearly = financials.get("Balance_Sheet", {}).get("yearly", {})
    cf_yearly = financials.get("Cash_Flow", {}).get("yearly", {})
    
    # Get all dates, sorted descending (most recent first)
    all_dates = sorted(set(is_yearly.keys()) & set(bs_yearly.keys()) & set(cf_yearly.keys()), reverse=True)
    
    years = []
    for date in all_dates[:n_years]:
        years.append({
            "date": date,
            "IS": is_yearly[date],
            "BS": bs_yearly[date],
            "CF": cf_yearly[date],
        })
    
    return years


def compute_beneish_mscore(current: dict, prior: dict) -> dict:
    """Compute the 8-variable Beneish M-Score.
    
    Args:
        current: dict with keys IS, BS, CF for current year
        prior: dict with keys IS, BS, CF for prior year
    
    Returns:
        dict with M-Score, all 8 sub-indices, interpretation, and flags
    """
    # --- Extract fields ---
    # Current year
    rev_c = get_field(current["IS"], "totalRevenue", 0)
    cogs_c = get_field(current["IS"], "costOfRevenue", 0)
    gp_c = rev_c - cogs_c
    ni_c = get_field(current["IS"], "netIncome", 0)
    sga_c = get_field(current["IS"], "sellingGeneralAdministrative", 0)
    dep_c = get_field(current["CF"], "depreciation", 0) or get_field(current["IS"], "depreciation", 0) or 0
    
    ar_c = get_field(current["BS"], "netReceivables", 0)
    ca_c = get_field(current["BS"], "totalCurrentAssets", 0)
    ta_c = get_field(current["BS"], "totalAssets", 0)
    ppe_c = get_field(current["BS"], "propertyPlantEquipment", 0)
    sec_c = get_field(current["BS"], "shortTermInvestments", 0)
    std_c = get_field(current["BS"], "shortTermDebt", 0) or 0
    ltd_c = get_field(current["BS"], "longTermDebt", 0) or 0
    
    cfo_c = get_field(current["CF"], "totalCashFromOperatingActivities", 0)
    
    # Prior year
    rev_p = get_field(prior["IS"], "totalRevenue", 0)
    cogs_p = get_field(prior["IS"], "costOfRevenue", 0)
    gp_p = rev_p - cogs_p
    sga_p = get_field(prior["IS"], "sellingGeneralAdministrative", 0)
    dep_p = get_field(prior["CF"], "depreciation", 0) or get_field(prior["IS"], "depreciation", 0) or 0
    
    ar_p = get_field(prior["BS"], "netReceivables", 0)
    ca_p = get_field(prior["BS"], "totalCurrentAssets", 0)
    ta_p = get_field(prior["BS"], "totalAssets", 0)
    ppe_p = get_field(prior["BS"], "propertyPlantEquipment", 0)
    sec_p = get_field(prior["BS"], "shortTermInvestments", 0)
    std_p = get_field(prior["BS"], "shortTermDebt", 0) or 0
    ltd_p = get_field(prior["BS"], "longTermDebt", 0) or 0
    
    # --- Compute 8 variables ---
    
    # 1. DSRI: Days Sales in Receivables Index
    dsri = safe_div(safe_div(ar_c, rev_c), safe_div(ar_p, rev_p), 1.0)
    
    # 2. GMI: Gross Margin Index
    gm_c = safe_div(gp_c, rev_c, 0)
    gm_p = safe_div(gp_p, rev_p, 0)
    gmi = safe_div(gm_p, gm_c, 1.0)
    
    # 3. AQI: Asset Quality Index
    hard_c = ca_c + ppe_c + sec_c
    hard_p = ca_p + ppe_p + sec_p
    aq_c = 1.0 - safe_div(hard_c, ta_c, 1.0) if ta_c else 0
    aq_p = 1.0 - safe_div(hard_p, ta_p, 1.0) if ta_p else 0
    aqi = safe_div(aq_c, aq_p, 1.0)
    
    # 4. SGI: Sales Growth Index
    sgi = safe_div(rev_c, rev_p, 1.0)
    
    # 5. DEPI: Depreciation Index
    dep_rate_c = safe_div(dep_c, dep_c + ppe_c, 0)
    dep_rate_p = safe_div(dep_p, dep_p + ppe_p, 0)
    depi = safe_div(dep_rate_p, dep_rate_c, 1.0)
    
    # 6. SGAI: SGA Expense Index
    sgai = safe_div(safe_div(sga_c, rev_c), safe_div(sga_p, rev_p), 1.0)
    
    # 7. TATA: Total Accruals to Total Assets
    tata = safe_div(ni_c - cfo_c, ta_c, 0.0)
    
    # 8. LVGI: Leverage Index
    lev_c = safe_div(std_c + ltd_c, ta_c, 0)
    lev_p = safe_div(std_p + ltd_p, ta_p, 0)
    lvgi = safe_div(lev_c, lev_p, 1.0)
    
    # --- Compute M-Score ---
    mscore = (
        -4.84
        + 0.920 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )
    
    # --- Interpret ---
    if mscore > -1.78:
        risk = "HIGH"
        interpretation = "M-Score above -1.78 indicates high probability of earnings manipulation."
    elif mscore > -2.22:
        risk = "MODERATE"
        interpretation = "M-Score in grey zone (-2.22 to -1.78). Warrants further investigation."
    else:
        risk = "LOW"
        interpretation = "M-Score below -2.22 indicates low manipulation risk."
    
    # Flag drivers
    flags = []
    if dsri > 1.1:
        flags.append(f"DSRI={dsri:.2f}: Receivables growing faster than revenue")
    if tata > 0.05:
        flags.append(f"TATA={tata:.3f}: Large gap between reported earnings and cash flow")
    if aqi > 1.1:
        flags.append(f"AQI={aqi:.2f}: Rising proportion of soft/intangible assets")
    if depi > 1.1:
        flags.append(f"DEPI={depi:.2f}: Depreciation rate slowing (useful life extensions?)")
    if gmi > 1.1:
        flags.append(f"GMI={gmi:.2f}: Gross margins deteriorating significantly")
    
    return {
        "mscore": round(mscore, 3),
        "risk_level": risk,
        "interpretation": interpretation,
        "variables": {
            "DSRI": round(dsri, 3),
            "GMI": round(gmi, 3),
            "AQI": round(aqi, 3),
            "SGI": round(sgi, 3),
            "DEPI": round(depi, 3),
            "SGAI": round(sgai, 3),
            "TATA": round(tata, 4),
            "LVGI": round(lvgi, 3),
        },
        "flags": flags,
        "periods": {
            "current": current.get("date", "N/A"),
            "prior": prior.get("date", "N/A"),
        }
    }


def compute_sloan_ratio(years: list) -> list:
    """Compute Sloan Accruals Ratio for each pair of consecutive years."""
    results = []
    for i in range(len(years) - 1):
        curr = years[i]
        prev = years[i + 1]
        
        ni = get_field(curr["IS"], "netIncome", 0)
        cfo = get_field(curr["CF"], "totalCashFromOperatingActivities", 0)
        ta_c = get_field(curr["BS"], "totalAssets", 0)
        ta_p = get_field(prev["BS"], "totalAssets", 0)
        avg_ta = (ta_c + ta_p) / 2 if (ta_c and ta_p) else ta_c or ta_p or 1
        
        ratio = (ni - cfo) / avg_ta if avg_ta else 0
        pct = ratio * 100
        
        if abs(pct) <= 10:
            risk = "LOW"
        elif pct <= 15:
            risk = "MODERATE"
        else:
            risk = "HIGH"
        
        results.append({
            "date": curr.get("date", "N/A"),
            "sloan_ratio_pct": round(pct, 2),
            "net_income": ni,
            "cfo": cfo,
            "risk_level": risk,
        })
    
    return results


def compute_cfo_ni_ratio(years: list) -> list:
    """Compute CFO/NI quality ratio for each year."""
    results = []
    for yr in years:
        ni = get_field(yr["IS"], "netIncome", 0)
        cfo = get_field(yr["CF"], "totalCashFromOperatingActivities", 0)
        
        if ni and ni != 0:
            ratio = cfo / ni
            if ratio > 1.2:
                quality = "HIGH"
            elif ratio > 1.0:
                quality = "GOOD"
            elif ratio > 0.7:
                quality = "MODERATE"
            elif ratio > 0.5:
                quality = "WEAK"
            else:
                quality = "POOR"
        else:
            ratio = None
            quality = "N/A (negative or zero NI)"
        
        results.append({
            "date": yr.get("date", "N/A"),
            "cfo": cfo,
            "net_income": ni,
            "cfo_ni_ratio": round(ratio, 3) if ratio is not None else None,
            "quality": quality,
        })
    
    return results


def compute_altman_zscore(current: dict, market_cap: float) -> dict:
    """Compute Altman Z-Score for manufacturing firms."""
    bs = current["BS"]
    is_ = current["IS"]
    
    ca = get_field(bs, "totalCurrentAssets", 0)
    cl = get_field(bs, "totalCurrentLiabilities", 0)
    ta = get_field(bs, "totalAssets", 0)
    re = get_field(bs, "retainedEarnings", 0)
    tl = get_field(bs, "totalLiab", 0)
    rev = get_field(is_, "totalRevenue", 0)
    ebit = get_field(is_, "operatingIncome", 0)
    
    if not ta or ta == 0:
        return {"zscore": None, "error": "Total assets is zero or missing"}
    
    wc_ta = (ca - cl) / ta
    re_ta = re / ta if re else 0
    ebit_ta = ebit / ta if ebit else 0
    mve_tl = market_cap / tl if tl and tl > 0 else 0
    sales_ta = rev / ta if rev else 0
    
    z = 1.2 * wc_ta + 1.4 * re_ta + 3.3 * ebit_ta + 0.6 * mve_tl + 1.0 * sales_ta
    
    if z > 2.99:
        zone = "SAFE"
        interpretation = "Low bankruptcy risk"
    elif z > 1.81:
        zone = "GREY"
        interpretation = "Moderate risk — warrants monitoring"
    else:
        zone = "DISTRESS"
        interpretation = "Elevated bankruptcy risk"
    
    return {
        "zscore": round(z, 3),
        "zone": zone,
        "interpretation": interpretation,
        "components": {
            "WC_TA": round(wc_ta, 4),
            "RE_TA": round(re_ta, 4),
            "EBIT_TA": round(ebit_ta, 4),
            "MVE_TL": round(mve_tl, 4),
            "Sales_TA": round(sales_ta, 4),
        }
    }


def compute_all_forensic_ratios(fundamentals: dict) -> dict:
    """Run all forensic analyses on EODHD fundamentals data.
    
    Args:
        fundamentals: Full EODHD fundamentals JSON response
    
    Returns:
        dict with all forensic metrics
    """
    years = extract_annual_statements(fundamentals, n_years=5)
    
    if len(years) < 2:
        return {"error": "Need at least 2 years of annual data for forensic analysis"}
    
    # Market cap for Z-Score
    highlights = fundamentals.get("Highlights", {})
    market_cap = get_field(highlights, "MarketCapitalization", 0)
    
    result = {
        "company": fundamentals.get("General", {}).get("Name", "Unknown"),
        "ticker": fundamentals.get("General", {}).get("Code", "Unknown"),
        "periods_available": [y["date"] for y in years],
    }
    
    # Beneish M-Score (most recent pair)
    result["beneish_mscore"] = compute_beneish_mscore(years[0], years[1])
    
    # M-Score for prior pair too if available (trend)
    if len(years) >= 3:
        result["beneish_mscore_prior"] = compute_beneish_mscore(years[1], years[2])
    
    # Sloan Accruals
    result["sloan_accruals"] = compute_sloan_ratio(years)
    
    # CFO/NI Quality
    result["cfo_ni_quality"] = compute_cfo_ni_ratio(years)
    
    # Altman Z-Score
    if market_cap and market_cap > 0:
        result["altman_zscore"] = compute_altman_zscore(years[0], market_cap)
    
    # Overall red flag summary
    red_flags = []
    if result["beneish_mscore"]["risk_level"] == "HIGH":
        red_flags.append("Beneish M-Score indicates high manipulation probability")
    
    for s in result["sloan_accruals"]:
        if s["risk_level"] == "HIGH":
            red_flags.append(f"Sloan accruals ratio is {s['sloan_ratio_pct']}% for {s['date']}")
            break
    
    consecutive_weak_cfo = 0
    for c in result["cfo_ni_quality"]:
        if c["cfo_ni_ratio"] is not None and c["cfo_ni_ratio"] < 0.7:
            consecutive_weak_cfo += 1
        else:
            consecutive_weak_cfo = 0
    if consecutive_weak_cfo >= 2:
        red_flags.append(f"CFO/NI ratio below 0.7 for {consecutive_weak_cfo} consecutive years")
    
    if result.get("altman_zscore", {}).get("zone") == "DISTRESS":
        red_flags.append("Altman Z-Score in distress zone")
    
    result["red_flag_summary"] = {
        "count": len(red_flags),
        "flags": red_flags,
        "overall_risk": "HIGH" if len(red_flags) >= 2 else "MODERATE" if len(red_flags) == 1 else "LOW"
    }
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python forensic_ratios.py <fundamentals_json_path>")
        print("  Reads EODHD fundamentals JSON and outputs forensic analysis.")
        sys.exit(1)
    
    with open(sys.argv[1], "r") as f:
        data = json.load(f)
    
    results = compute_all_forensic_ratios(data)
    print(json.dumps(results, indent=2))
