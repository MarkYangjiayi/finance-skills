#!/usr/bin/env python3
"""
Valuation Analysis Helpers

Computes DuPont decomposition, ROIC, simplified DCF, reverse DCF,
and comparable multiples analysis from EODHD fundamentals + FRED data.

Usage:
    python valuation_helpers.py <fundamentals_json_path> [--risk-free-rate 0.045]
    
    Or import:
    from valuation_helpers import compute_all_valuation
    results = compute_all_valuation(fundamentals_dict, risk_free_rate=0.045)
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


def extract_annual_statements(fundamentals: dict, n_years: int = 5):
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


def compute_dupont_3factor(years: list) -> list:
    """3-factor DuPont: ROE = Profit Margin × Asset Turnover × Equity Multiplier."""
    results = []
    
    for i, yr in enumerate(years):
        ni = get_field(yr["IS"], "netIncome", 0)
        rev = get_field(yr["IS"], "totalRevenue", 0)
        ta = get_field(yr["BS"], "totalAssets", 0)
        eq = get_field(yr["BS"], "totalStockholderEquity", 0)
        
        # Use average assets/equity with prior year if available
        if i + 1 < len(years):
            ta_prev = get_field(years[i+1]["BS"], "totalAssets", 0)
            eq_prev = get_field(years[i+1]["BS"], "totalStockholderEquity", 0)
            avg_ta = (ta + ta_prev) / 2 if ta_prev else ta
            avg_eq = (eq + eq_prev) / 2 if eq_prev else eq
        else:
            avg_ta, avg_eq = ta, eq
        
        npm = safe_div(ni, rev)
        at = safe_div(rev, avg_ta)
        em = safe_div(avg_ta, avg_eq)
        roe = npm * at * em
        
        # Identify primary driver
        drivers = [
            ("Profit Margin", abs(npm)),
            ("Asset Turnover", abs(at)),
            ("Equity Multiplier", abs(em)),
        ]
        
        results.append({
            "date": yr.get("date", "N/A"),
            "roe_pct": round(roe * 100, 2),
            "net_profit_margin_pct": round(npm * 100, 2),
            "asset_turnover": round(at, 3),
            "equity_multiplier": round(em, 3),
            "primary_roe_driver": (
                "Leverage" if em > 3 and npm < 0.1 else
                "Margin" if npm > at and npm > (em / 10) else
                "Turnover"
            ),
        })
    
    return results


def compute_dupont_5factor(years: list) -> list:
    """5-factor DuPont: Tax Burden × Interest Burden × Op Margin × Turnover × Leverage."""
    results = []
    
    for i, yr in enumerate(years):
        ni = get_field(yr["IS"], "netIncome", 0)
        pbt = get_field(yr["IS"], "incomeBeforeTax", 0)
        ebit = get_field(yr["IS"], "operatingIncome", 0)
        rev = get_field(yr["IS"], "totalRevenue", 0)
        ta = get_field(yr["BS"], "totalAssets", 0)
        eq = get_field(yr["BS"], "totalStockholderEquity", 0)
        
        if i + 1 < len(years):
            ta_prev = get_field(years[i+1]["BS"], "totalAssets", 0)
            eq_prev = get_field(years[i+1]["BS"], "totalStockholderEquity", 0)
            avg_ta = (ta + ta_prev) / 2 if ta_prev else ta
            avg_eq = (eq + eq_prev) / 2 if eq_prev else eq
        else:
            avg_ta, avg_eq = ta, eq
        
        tax_burden = safe_div(ni, pbt, 1.0)
        interest_burden = safe_div(pbt, ebit, 1.0)
        op_margin = safe_div(ebit, rev)
        turnover = safe_div(rev, avg_ta)
        leverage = safe_div(avg_ta, avg_eq)
        
        results.append({
            "date": yr.get("date", "N/A"),
            "tax_burden": round(tax_burden, 3),
            "interest_burden": round(interest_burden, 3),
            "operating_margin": round(op_margin, 4),
            "asset_turnover": round(turnover, 3),
            "equity_multiplier": round(leverage, 3),
            "roe_pct": round(tax_burden * interest_burden * op_margin * turnover * leverage * 100, 2),
        })
    
    return results


def compute_roic(years: list) -> list:
    """Compute ROIC and incremental ROIC."""
    results = []
    
    for i, yr in enumerate(years):
        ebit = get_field(yr["IS"], "operatingIncome", 0) or 0
        tax_expense = get_field(yr["IS"], "incomeTaxExpense", 0) or 0
        pbt = get_field(yr["IS"], "incomeBeforeTax", 0) or 0
        
        eff_tax = safe_div(tax_expense, pbt, 0.25) if pbt > 0 else 0.25
        nopat = ebit * (1 - eff_tax)
        
        eq = get_field(yr["BS"], "totalStockholderEquity", 0) or 0
        std = get_field(yr["BS"], "shortTermDebt", 0) or 0
        ltd = get_field(yr["BS"], "longTermDebt", 0) or 0
        cash = get_field(yr["BS"], "cash", 0) or get_field(yr["BS"], "cashAndShortTermInvestments", 0) or 0
        
        invested_capital = eq + std + ltd - cash
        
        if i + 1 < len(years):
            eq_p = get_field(years[i+1]["BS"], "totalStockholderEquity", 0) or 0
            std_p = get_field(years[i+1]["BS"], "shortTermDebt", 0) or 0
            ltd_p = get_field(years[i+1]["BS"], "longTermDebt", 0) or 0
            cash_p = get_field(years[i+1]["BS"], "cash", 0) or 0
            ic_prev = eq_p + std_p + ltd_p - cash_p
            avg_ic = (invested_capital + ic_prev) / 2 if ic_prev else invested_capital
        else:
            avg_ic = invested_capital
            ic_prev = None
        
        roic = safe_div(nopat, avg_ic) if avg_ic > 0 else 0
        
        entry = {
            "date": yr.get("date", "N/A"),
            "nopat": round(nopat, 0),
            "invested_capital": round(invested_capital, 0),
            "roic_pct": round(roic * 100, 2),
            "effective_tax_rate_pct": round(eff_tax * 100, 1),
        }
        
        # Incremental ROIC (requires prior period NOPAT)
        if i + 1 < len(years) and ic_prev:
            ebit_p = get_field(years[i+1]["IS"], "operatingIncome", 0) or 0
            nopat_p = ebit_p * (1 - eff_tax)
            delta_nopat = nopat - nopat_p
            delta_ic = invested_capital - ic_prev
            entry["incremental_roic_pct"] = (
                round(safe_div(delta_nopat, delta_ic) * 100, 2)
                if delta_ic != 0 else None
            )
        
        results.append(entry)
    
    return results


def compute_simplified_dcf(
    fundamentals: dict,
    risk_free_rate: float = 0.045,
    erp: float = 0.05,
    terminal_growth: float = 0.025,
    projection_years: int = 5,
) -> dict:
    """Simplified DCF valuation.
    
    Args:
        fundamentals: EODHD fundamentals
        risk_free_rate: from FRED DGS10
        erp: equity risk premium (default 5%)
        terminal_growth: long-term growth rate
        projection_years: explicit forecast period
    """
    highlights = fundamentals.get("Highlights", {})
    valuation = fundamentals.get("Valuation", {})
    shares_stats = fundamentals.get("SharesStats", {})
    
    years = extract_annual_statements(fundamentals, 5)
    if not years:
        return {"error": "No annual data available"}
    
    curr = years[0]
    
    # Compute base FCF
    cfo = get_field(curr["CF"], "totalCashFromOperatingActivities", 0)
    capex = abs(get_field(curr["CF"], "capitalExpenditures", 0) or 0)
    fcf = cfo - capex
    
    if fcf <= 0:
        return {
            "note": "Negative FCF — DCF not meaningful. Company is cash-burning.",
            "current_fcf": fcf,
        }
    
    # Get beta
    beta = get_field(highlights, "Beta", 1.0) or 1.0
    
    # Cost of equity
    ke = risk_free_rate + beta * erp
    
    # Debt data
    std = get_field(curr["BS"], "shortTermDebt", 0) or 0
    ltd = get_field(curr["BS"], "longTermDebt", 0) or 0
    total_debt = std + ltd
    cash = get_field(curr["BS"], "cash", 0) or get_field(curr["BS"], "cashAndShortTermInvestments", 0) or 0
    market_cap = get_field(highlights, "MarketCapitalization", 0) or 0
    
    interest = abs(get_field(curr["IS"], "interestExpense", 0) or 0)
    kd = safe_div(interest, total_debt, risk_free_rate + 0.02)
    
    pbt = get_field(curr["IS"], "incomeBeforeTax", 0) or 0
    tax_expense = get_field(curr["IS"], "incomeTaxExpense", 0) or 0
    tax_rate = safe_div(tax_expense, pbt, 0.25) if pbt > 0 else 0.25
    
    ev = market_cap + total_debt
    e_weight = safe_div(market_cap, ev, 0.8)
    d_weight = safe_div(total_debt, ev, 0.2)
    
    wacc = e_weight * ke + d_weight * kd * (1 - tax_rate)
    
    # Estimate FCF growth from historical
    if len(years) >= 3:
        fcf_prev = (
            get_field(years[2]["CF"], "totalCashFromOperatingActivities", 0)
            - abs(get_field(years[2]["CF"], "capitalExpenditures", 0) or 0)
        )
        if fcf_prev > 0:
            cagr = (fcf / fcf_prev) ** (1/2) - 1
            initial_growth = min(max(cagr, 0.02), 0.25)  # cap at 25%
        else:
            initial_growth = 0.08
    else:
        initial_growth = 0.08
    
    # Project FCF with growth decay
    projected_fcf = []
    cumulative_pv = 0
    for yr in range(1, projection_years + 1):
        growth = initial_growth - (initial_growth - terminal_growth) * (yr / projection_years)
        proj_fcf = fcf * (1 + growth) ** yr
        pv = proj_fcf / (1 + wacc) ** yr
        cumulative_pv += pv
        projected_fcf.append({
            "year": yr,
            "growth_rate_pct": round(growth * 100, 1),
            "fcf": round(proj_fcf, 0),
            "pv_fcf": round(pv, 0),
        })
    
    # Terminal value
    final_fcf = projected_fcf[-1]["fcf"]
    tv = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_tv = tv / (1 + wacc) ** projection_years
    
    # Enterprise value and equity value
    ev_dcf = cumulative_pv + pv_tv
    equity_value = ev_dcf - total_debt + cash
    shares = get_field(shares_stats, "SharesOutstanding", 0)
    per_share = safe_div(equity_value, shares) if shares else None
    
    # Current price for comparison
    current_price = safe_div(market_cap, shares) if shares else None
    
    # Sensitivity table
    sensitivity = []
    for wacc_adj in [-0.01, -0.005, 0, 0.005, 0.01]:
        for tg_adj in [-0.01, -0.005, 0, 0.005, 0.01]:
            w = wacc + wacc_adj
            g = terminal_growth + tg_adj
            if w > g and w > 0:
                tv_s = final_fcf * (1 + g) / (w - g)
                pv_tv_s = tv_s / (1 + w) ** projection_years
                ev_s = cumulative_pv + pv_tv_s  # simplified — should recompute stage 1 too
                eq_s = ev_s - total_debt + cash
                ps_s = safe_div(eq_s, shares)
                sensitivity.append({
                    "wacc_pct": round(w * 100, 1),
                    "terminal_growth_pct": round(g * 100, 1),
                    "implied_per_share": round(ps_s, 2) if ps_s else None,
                })
    
    return {
        "inputs": {
            "risk_free_rate_pct": round(risk_free_rate * 100, 2),
            "beta": round(beta, 2),
            "erp_pct": round(erp * 100, 1),
            "cost_of_equity_pct": round(ke * 100, 2),
            "cost_of_debt_pct": round(kd * 100, 2),
            "tax_rate_pct": round(tax_rate * 100, 1),
            "wacc_pct": round(wacc * 100, 2),
            "initial_fcf_growth_pct": round(initial_growth * 100, 1),
            "terminal_growth_pct": round(terminal_growth * 100, 1),
        },
        "base_fcf": round(fcf, 0),
        "projected_fcf": projected_fcf,
        "terminal_value": round(tv, 0),
        "pv_terminal_value": round(pv_tv, 0),
        "tv_pct_of_ev": round(safe_div(pv_tv, ev_dcf) * 100, 1),
        "enterprise_value": round(ev_dcf, 0),
        "equity_value": round(equity_value, 0),
        "implied_per_share": round(per_share, 2) if per_share else None,
        "current_price_approx": round(current_price, 2) if current_price else None,
        "upside_downside_pct": (
            round((per_share / current_price - 1) * 100, 1)
            if per_share and current_price and current_price > 0 else None
        ),
        "sensitivity": sensitivity,
    }


def compute_reverse_dcf(fundamentals: dict, wacc: float) -> dict:
    """Back-solve for the FCF growth rate implied by current market price."""
    highlights = fundamentals.get("Highlights", {})
    shares_stats = fundamentals.get("SharesStats", {})
    years = extract_annual_statements(fundamentals, 3)
    
    if not years:
        return {"error": "No data"}
    
    curr = years[0]
    cfo = get_field(curr["CF"], "totalCashFromOperatingActivities", 0)
    capex = abs(get_field(curr["CF"], "capitalExpenditures", 0) or 0)
    fcf = cfo - capex
    
    market_cap = get_field(highlights, "MarketCapitalization", 0) or 0
    std = get_field(curr["BS"], "shortTermDebt", 0) or 0
    ltd = get_field(curr["BS"], "longTermDebt", 0) or 0
    cash = get_field(curr["BS"], "cash", 0) or 0
    
    ev = market_cap + std + ltd - cash
    
    if fcf <= 0 or ev <= 0:
        return {"note": "Reverse DCF not meaningful with negative FCF or EV"}
    
    # Simple perpetuity approximation
    implied_growth = wacc - safe_div(fcf, ev)
    
    return {
        "current_fcf": round(fcf, 0),
        "enterprise_value": round(ev, 0),
        "wacc_pct": round(wacc * 100, 2),
        "implied_perpetuity_growth_pct": round(implied_growth * 100, 2),
        "interpretation": (
            "Market expects very high growth" if implied_growth > 0.10 else
            "Market expects strong growth" if implied_growth > 0.06 else
            "Market expects moderate growth" if implied_growth > 0.03 else
            "Market expects low growth" if implied_growth > 0 else
            "Market expects decline or FCF compression"
        ),
        "reality_check": (
            "Implied growth exceeds 10% perpetually — very aggressive pricing with limited margin of safety"
            if implied_growth > 0.10 else
            "Implied growth is reasonable for a growing company"
            if 0.02 < implied_growth < 0.08 else
            "Implied growth is conservative — potential value if fundamentals hold"
            if implied_growth < 0.02 else
            "Within normal range"
        )
    }


def compute_all_valuation(fundamentals: dict, risk_free_rate: float = 0.045) -> dict:
    """Run all valuation analyses."""
    years = extract_annual_statements(fundamentals, 5)
    highlights = fundamentals.get("Highlights", {})
    valuation_data = fundamentals.get("Valuation", {})
    
    result = {
        "company": fundamentals.get("General", {}).get("Name", "Unknown"),
        "ticker": fundamentals.get("General", {}).get("Code", "Unknown"),
    }
    
    if years:
        result["dupont_3factor"] = compute_dupont_3factor(years)
        result["dupont_5factor"] = compute_dupont_5factor(years)
        result["roic"] = compute_roic(years)
    
    # Current multiples from EODHD
    result["current_multiples"] = {
        "trailing_pe": get_field(valuation_data, "TrailingPE"),
        "forward_pe": get_field(valuation_data, "ForwardPE"),
        "price_to_sales": get_field(valuation_data, "PriceSalesTTM"),
        "price_to_book": get_field(valuation_data, "PriceBookMRQ"),
        "ev_to_revenue": get_field(valuation_data, "EnterpriseValueRevenue"),
        "ev_to_ebitda": get_field(valuation_data, "EnterpriseValueEbitda"),
    }
    
    # DCF
    result["dcf"] = compute_simplified_dcf(fundamentals, risk_free_rate=risk_free_rate)
    
    # Reverse DCF
    if result["dcf"].get("inputs", {}).get("wacc_pct"):
        wacc = result["dcf"]["inputs"]["wacc_pct"] / 100
        result["reverse_dcf"] = compute_reverse_dcf(fundamentals, wacc)
    
    return result


if __name__ == "__main__":
    rfr = 0.045
    path = None
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--risk-free-rate" and i + 1 < len(args):
            rfr = float(args[i + 1])
            i += 2
        else:
            path = args[i]
            i += 1
    
    if not path:
        print("Usage: python valuation_helpers.py <fundamentals_json_path> [--risk-free-rate 0.045]")
        sys.exit(1)
    
    with open(path, "r") as f:
        data = json.load(f)
    
    results = compute_all_valuation(data, risk_free_rate=rfr)
    print(json.dumps(results, indent=2))
