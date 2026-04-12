#!/usr/bin/env python3
"""
Working Capital & Balance Sheet Analysis

Computes DSO, DIO, DPO, Cash Conversion Cycle, debt metrics, capital allocation
assessment, and SBC analysis from EODHD fundamentals JSON.

Usage:
    python working_capital_analysis.py <fundamentals_json_path>
    
    Or import:
    from working_capital_analysis import compute_all_working_capital
    results = compute_all_working_capital(fundamentals_dict)
"""

import json
import sys
from typing import Optional


def safe_div(n, d, default=0.0):
    try:
        n = float(n) if n is not None else None
        d = float(d) if d is not None else None
        if n is None or d is None or d == 0:
            return default
        return n / d
    except (TypeError, ValueError):
        return default


def get_field(stmt: dict, field: str, default=None):
    val = stmt.get(field, default)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def extract_quarterly_statements(fundamentals: dict, n_quarters: int = 12):
    """Extract the most recent n quarters of financial statements."""
    financials = fundamentals.get("Financials", {})
    
    is_q = financials.get("Income_Statement", {}).get("quarterly", {})
    bs_q = financials.get("Balance_Sheet", {}).get("quarterly", {})
    cf_q = financials.get("Cash_Flow", {}).get("quarterly", {})
    
    all_dates = sorted(
        set(is_q.keys()) & set(bs_q.keys()) & set(cf_q.keys()),
        reverse=True
    )
    
    quarters = []
    for date in all_dates[:n_quarters]:
        quarters.append({
            "date": date,
            "IS": is_q[date],
            "BS": bs_q[date],
            "CF": cf_q[date],
        })
    
    return quarters


def extract_annual_statements(fundamentals: dict, n_years: int = 5):
    """Extract the most recent n years of annual statements."""
    financials = fundamentals.get("Financials", {})
    
    is_y = financials.get("Income_Statement", {}).get("yearly", {})
    bs_y = financials.get("Balance_Sheet", {}).get("yearly", {})
    cf_y = financials.get("Cash_Flow", {}).get("yearly", {})
    
    all_dates = sorted(
        set(is_y.keys()) & set(bs_y.keys()) & set(cf_y.keys()),
        reverse=True
    )
    
    years = []
    for date in all_dates[:n_years]:
        years.append({
            "date": date,
            "IS": is_y[date],
            "BS": bs_y[date],
            "CF": cf_y[date],
        })
    
    return years


def compute_working_capital_metrics(periods: list, annualize_factor: float = 1.0) -> list:
    """Compute DSO, DIO, DPO, CCC for each period.
    
    Args:
        periods: list of statement dicts (quarterly or annual)
        annualize_factor: multiply revenue/COGS by this to annualize
            (4.0 for quarters, 1.0 for annual)
    """
    results = []
    
    for i, p in enumerate(periods):
        rev = get_field(p["IS"], "totalRevenue", 0) * annualize_factor
        cogs = get_field(p["IS"], "costOfRevenue", 0) * annualize_factor
        ar = get_field(p["BS"], "netReceivables", 0)
        inv = get_field(p["BS"], "inventory", 0)
        ap = get_field(p["BS"], "accountsPayable", 0)
        
        # Use average with prior period if available
        if i + 1 < len(periods):
            ar_prev = get_field(periods[i+1]["BS"], "netReceivables", 0)
            inv_prev = get_field(periods[i+1]["BS"], "inventory", 0)
            ap_prev = get_field(periods[i+1]["BS"], "accountsPayable", 0)
            avg_ar = (ar + ar_prev) / 2 if ar_prev else ar
            avg_inv = (inv + inv_prev) / 2 if inv_prev else inv
            avg_ap = (ap + ap_prev) / 2 if ap_prev else ap
        else:
            avg_ar, avg_inv, avg_ap = ar, inv, ap
        
        dso = safe_div(avg_ar, rev, 0) * 365 if rev else None
        dio = safe_div(avg_inv, cogs, 0) * 365 if cogs else None
        dpo = safe_div(avg_ap, cogs, 0) * 365 if cogs else None
        
        ccc = None
        if dso is not None and dio is not None and dpo is not None:
            ccc = dso + dio - dpo
        
        results.append({
            "date": p.get("date", "N/A"),
            "dso_days": round(dso, 1) if dso is not None else None,
            "dio_days": round(dio, 1) if dio is not None else None,
            "dpo_days": round(dpo, 1) if dpo is not None else None,
            "ccc_days": round(ccc, 1) if ccc is not None else None,
            "receivables": ar,
            "inventory": inv,
            "payables": ap,
            "revenue_annualized": rev,
            "cogs_annualized": cogs,
        })
    
    return results


def flag_working_capital_trends(wc_metrics: list) -> list:
    """Identify concerning trends in working capital metrics."""
    flags = []
    
    if len(wc_metrics) < 2:
        return flags
    
    latest = wc_metrics[0]
    prior = wc_metrics[1]
    
    # DSO trend
    if latest["dso_days"] and prior["dso_days"]:
        dso_change = latest["dso_days"] - prior["dso_days"]
        if dso_change > 5:
            flags.append({
                "metric": "DSO",
                "severity": "WARNING" if dso_change < 10 else "RED_FLAG",
                "message": f"DSO increased by {dso_change:.1f} days ({prior['date']} → {latest['date']})",
                "detail": "Rising DSO may indicate collection issues, aggressive revenue recognition, or channel stuffing"
            })
    
    # DIO trend
    if latest["dio_days"] and prior["dio_days"]:
        dio_change = latest["dio_days"] - prior["dio_days"]
        if dio_change > 5:
            flags.append({
                "metric": "DIO",
                "severity": "WARNING" if dio_change < 15 else "RED_FLAG",
                "message": f"DIO increased by {dio_change:.1f} days ({prior['date']} → {latest['date']})",
                "detail": "Rising DIO may signal demand weakness, product obsolescence, or supply chain issues"
            })
    
    # DPO trend (falling is concerning)
    if latest["dpo_days"] and prior["dpo_days"]:
        dpo_change = latest["dpo_days"] - prior["dpo_days"]
        if dpo_change < -5:
            flags.append({
                "metric": "DPO",
                "severity": "WARNING",
                "message": f"DPO decreased by {abs(dpo_change):.1f} days ({prior['date']} → {latest['date']})",
                "detail": "Falling DPO may indicate weakening supplier leverage or tighter payment terms"
            })
    
    # CCC trend
    if latest["ccc_days"] and prior["ccc_days"]:
        ccc_change = latest["ccc_days"] - prior["ccc_days"]
        if ccc_change > 10:
            flags.append({
                "metric": "CCC",
                "severity": "RED_FLAG",
                "message": f"Cash Conversion Cycle lengthened by {ccc_change:.1f} days",
                "detail": "A lengthening CCC often precedes cash flow problems by 1-2 quarters"
            })
    
    # Check for DSO growing faster than revenue
    if (latest["dso_days"] and prior["dso_days"] and 
        latest["revenue_annualized"] and prior["revenue_annualized"]):
        dso_growth = safe_div(latest["dso_days"] - prior["dso_days"], prior["dso_days"], 0) * 100
        rev_growth = safe_div(
            latest["revenue_annualized"] - prior["revenue_annualized"],
            prior["revenue_annualized"], 0
        ) * 100
        gap = dso_growth - rev_growth
        if gap > 5:
            flags.append({
                "metric": "DSO_vs_Revenue",
                "severity": "RED_FLAG",
                "message": f"DSO growth ({dso_growth:.1f}%) outpacing revenue growth ({rev_growth:.1f}%) by {gap:.1f}pp",
                "detail": "Classic channel stuffing signal — receivables growing disproportionately to sales"
            })
    
    return flags


def compute_debt_metrics(current: dict, highlights: dict) -> dict:
    """Compute leverage and debt health metrics."""
    bs = current["BS"]
    is_ = current["IS"]
    
    std = get_field(bs, "shortTermDebt", 0) or 0
    ltd = get_field(bs, "longTermDebt", 0) or 0
    total_debt = std + ltd
    cash = get_field(bs, "cash", 0) or get_field(bs, "cashAndShortTermInvestments", 0) or 0
    net_debt = total_debt - cash
    
    ebitda = get_field(highlights, "EBITDA", 0) or get_field(is_, "ebitda", 0) or 0
    ebit = get_field(is_, "operatingIncome", 0) or 0
    interest = get_field(is_, "interestExpense", 0) or 0
    # Interest expense is often reported as negative in EODHD
    interest = abs(interest) if interest else 0
    
    total_assets = get_field(bs, "totalAssets", 0) or 0
    equity = get_field(bs, "totalStockholderEquity", 0) or 0
    
    return {
        "total_debt": total_debt,
        "cash": cash,
        "net_debt": net_debt,
        "net_debt_to_ebitda": round(safe_div(net_debt, ebitda), 2) if ebitda else None,
        "debt_to_equity": round(safe_div(total_debt, equity), 2) if equity else None,
        "debt_to_assets": round(safe_div(total_debt, total_assets), 3) if total_assets else None,
        "interest_coverage": round(safe_div(ebit, interest), 2) if interest else None,
        "interpretation": {
            "leverage": (
                "Conservative" if safe_div(net_debt, ebitda, 99) < 1.5 else
                "Moderate" if safe_div(net_debt, ebitda, 99) < 3.0 else
                "Elevated" if safe_div(net_debt, ebitda, 99) < 5.0 else
                "High risk"
            ),
            "coverage": (
                "Strong" if safe_div(ebit, interest, 0) > 5 else
                "Adequate" if safe_div(ebit, interest, 0) > 3 else
                "Tight" if safe_div(ebit, interest, 0) > 1.5 else
                "Distressed"
            ) if interest > 0 else "No interest expense"
        }
    }


def compute_capital_allocation(years: list, highlights: dict) -> dict:
    """Assess capital allocation: FCF, capex split, buybacks, SBC."""
    if not years:
        return {}
    
    curr = years[0]
    cf = curr["CF"]
    is_ = curr["IS"]
    
    cfo = get_field(cf, "totalCashFromOperatingActivities", 0)
    capex = abs(get_field(cf, "capitalExpenditures", 0) or 0)
    depreciation = get_field(cf, "depreciation", 0) or 0
    sbc = get_field(cf, "stockBasedCompensation", 0) or 0
    dividends = abs(get_field(cf, "dividendsPaid", 0) or 0)
    buybacks = abs(get_field(cf, "salePurchaseOfStock", 0) or 0)
    revenue = get_field(is_, "totalRevenue", 0) or 0
    market_cap = get_field(highlights, "MarketCapitalization", 0) or 0
    
    fcf = cfo - capex
    maintenance_capex = depreciation  # proxy
    growth_capex = max(0, capex - maintenance_capex)
    
    result = {
        "date": curr.get("date", "N/A"),
        "cfo": cfo,
        "capex_total": capex,
        "maintenance_capex_estimate": round(maintenance_capex, 0),
        "growth_capex_estimate": round(growth_capex, 0),
        "fcf": fcf,
        "fcf_margin_pct": round(safe_div(fcf, revenue) * 100, 1) if revenue else None,
        "fcf_yield_pct": round(safe_div(fcf, market_cap) * 100, 2) if market_cap else None,
        "sbc": sbc,
        "sbc_pct_of_revenue": round(safe_div(sbc, revenue) * 100, 1) if revenue else None,
        "sbc_pct_of_fcf": round(safe_div(sbc, fcf) * 100, 1) if fcf and fcf > 0 else None,
        "dividends_paid": dividends,
        "buybacks": buybacks,
        "total_shareholder_return": dividends + buybacks,
        "payout_ratio_pct": round(safe_div(dividends + buybacks, fcf) * 100, 1) if fcf and fcf > 0 else None,
    }
    
    # SBC warning
    if result["sbc_pct_of_revenue"] and result["sbc_pct_of_revenue"] > 15:
        result["sbc_warning"] = "SBC exceeds 15% of revenue — significant real economic cost and dilution"
    elif result["sbc_pct_of_revenue"] and result["sbc_pct_of_revenue"] > 8:
        result["sbc_warning"] = "SBC between 8-15% of revenue — material cost that should not be excluded from earnings"
    
    # FCF quality
    if result["fcf_yield_pct"] and result["fcf_yield_pct"] > 6:
        result["fcf_assessment"] = "Strong FCF yield — potential value opportunity"
    elif result["fcf_yield_pct"] and result["fcf_yield_pct"] > 3:
        result["fcf_assessment"] = "Moderate FCF yield"
    elif result["fcf_yield_pct"] and result["fcf_yield_pct"] > 0:
        result["fcf_assessment"] = "Low FCF yield — priced for growth"
    elif result["fcf"] and result["fcf"] < 0:
        result["fcf_assessment"] = "Negative FCF — company is cash-burning"
    
    return result


def compute_margin_trends(years: list) -> list:
    """Compute margin trends over time."""
    results = []
    for yr in years:
        rev = get_field(yr["IS"], "totalRevenue", 0)
        gp = get_field(yr["IS"], "grossProfit", 0)
        op_inc = get_field(yr["IS"], "operatingIncome", 0)
        ni = get_field(yr["IS"], "netIncome", 0)
        ebitda = get_field(yr["IS"], "ebitda", 0)
        
        results.append({
            "date": yr.get("date", "N/A"),
            "revenue": rev,
            "gross_margin_pct": round(safe_div(gp, rev) * 100, 2) if rev else None,
            "operating_margin_pct": round(safe_div(op_inc, rev) * 100, 2) if rev else None,
            "net_margin_pct": round(safe_div(ni, rev) * 100, 2) if rev else None,
            "ebitda_margin_pct": round(safe_div(ebitda, rev) * 100, 2) if rev and ebitda else None,
        })
    
    # Add incremental margin if 2+ periods
    for i in range(len(results) - 1):
        curr_rev = get_field(years[i]["IS"], "totalRevenue", 0)
        prev_rev = get_field(years[i+1]["IS"], "totalRevenue", 0)
        curr_op = get_field(years[i]["IS"], "operatingIncome", 0)
        prev_op = get_field(years[i+1]["IS"], "operatingIncome", 0)
        
        delta_rev = curr_rev - prev_rev if curr_rev and prev_rev else 0
        delta_op = curr_op - prev_op if curr_op and prev_op else 0
        
        results[i]["incremental_operating_margin_pct"] = (
            round(safe_div(delta_op, delta_rev) * 100, 1) if delta_rev else None
        )
        results[i]["revenue_growth_yoy_pct"] = (
            round(safe_div(delta_rev, prev_rev) * 100, 1) if prev_rev else None
        )
    
    return results


def compute_all_working_capital(fundamentals: dict) -> dict:
    """Run all working capital and balance sheet analyses."""
    quarters = extract_quarterly_statements(fundamentals, n_quarters=12)
    years = extract_annual_statements(fundamentals, n_years=5)
    highlights = fundamentals.get("Highlights", {})
    
    result = {
        "company": fundamentals.get("General", {}).get("Name", "Unknown"),
        "ticker": fundamentals.get("General", {}).get("Code", "Unknown"),
    }
    
    # Working capital metrics (quarterly for trend detection)
    if quarters:
        result["working_capital_quarterly"] = compute_working_capital_metrics(quarters, annualize_factor=4.0)
        result["working_capital_flags"] = flag_working_capital_trends(result["working_capital_quarterly"])
    
    # Working capital metrics (annual for stability)
    if years:
        result["working_capital_annual"] = compute_working_capital_metrics(years, annualize_factor=1.0)
    
    # Debt metrics
    if years:
        result["debt_metrics"] = compute_debt_metrics(years[0], highlights)
    
    # Capital allocation
    if years:
        result["capital_allocation"] = compute_capital_allocation(years, highlights)
    
    # Margin trends
    if years:
        result["margin_trends"] = compute_margin_trends(years)
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python working_capital_analysis.py <fundamentals_json_path>")
        sys.exit(1)
    
    with open(sys.argv[1], "r") as f:
        data = json.load(f)
    
    results = compute_all_working_capital(data)
    print(json.dumps(results, indent=2))
