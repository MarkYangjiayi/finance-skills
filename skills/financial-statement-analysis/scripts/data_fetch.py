#!/usr/bin/env python3
"""
Data Fetching Helpers

Provides convenience functions for fetching data from FRED API and edgartools
that complement the EODHD MCP tools.

EODHD data is fetched via MCP tools directly (not through this script).
This script handles the non-MCP data sources.

Usage:
    # FRED API
    from data_fetch import fetch_fred_series, get_risk_free_rate, get_treasury_yields
    
    rfr = get_risk_free_rate(api_key="YOUR_FRED_KEY")
    yields = get_treasury_yields(api_key="YOUR_FRED_KEY")
    
    # edgartools
    from data_fetch import get_latest_10k, get_latest_10q, get_risk_factors, diff_risk_factors
"""

import json
import os
import urllib.request
import urllib.error
from typing import Optional
from datetime import datetime, timedelta


# =============================================================================
# FRED API Helpers
# =============================================================================

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

FRED_SERIES = {
    "DGS10": "10-Year Treasury Constant Maturity Rate",
    "DGS2": "2-Year Treasury Constant Maturity Rate",
    "DGS5": "5-Year Treasury Constant Maturity Rate",
    "DGS30": "30-Year Treasury Constant Maturity Rate",
    "DFF": "Federal Funds Effective Rate",
    "BAA": "Moody's BAA Corporate Bond Yield",
    "AAA": "Moody's AAA Corporate Bond Yield",
    "CPIAUCSL": "CPI All Urban Consumers (Seasonally Adjusted)",
    "GDP": "Nominal GDP",
    "GDPC1": "Real GDP",
    "UNRATE": "Unemployment Rate",
}

TREASURY_10Y_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "TextView?field_tdr_date_value={year}&type=daily_treasury_yield_curve"
)


def preflight_report(require_fred: bool = False, require_edgar: bool = False) -> dict:
    """Check local prerequisites before the skill starts substantive work.
    
    This is intentionally lightweight: it checks whether shell-side prerequisites
    are present and tells the caller what is required vs optional.
    """
    report = {
        "environment": {
            "FRED_API_KEY": bool(os.environ.get("FRED_API_KEY")),
            "EODHD_API_KEY": bool(os.environ.get("EODHD_API_KEY")),
            "API_TOKEN": bool(os.environ.get("API_TOKEN")),
        },
        "python_packages": {},
        "required_missing": [],
        "optional_missing": [],
        "notes": [],
    }
    
    try:
        import edgar  # noqa: F401
        report["python_packages"]["edgartools"] = True
    except ImportError:
        report["python_packages"]["edgartools"] = False
        if require_edgar:
            report["required_missing"].append("edgartools")
        else:
            report["optional_missing"].append("edgartools")
    
    if require_fred and not report["environment"]["FRED_API_KEY"]:
        report["required_missing"].append("FRED_API_KEY")
    elif not report["environment"]["FRED_API_KEY"]:
        report["optional_missing"].append("FRED_API_KEY")
        report["notes"].append("Use U.S. Treasury daily yield curve data as fallback for 10Y risk-free rate.")
    
    if not (report["environment"]["EODHD_API_KEY"] or report["environment"]["API_TOKEN"]):
        report["notes"].append(
            "Shell-side EODHD keys are not set. MCP-based EODHD tools may still work, "
            "but direct script access to EODHD is unavailable."
        )
    
    report["ok"] = len(report["required_missing"]) == 0
    return report


def fetch_fred_series(
    series_id: str,
    api_key: str,
    limit: int = 1,
    sort_order: str = "desc",
    observation_start: Optional[str] = None,
    observation_end: Optional[str] = None,
) -> dict:
    """Fetch observations from a FRED series.
    
    Args:
        series_id: FRED series ID (e.g., 'DGS10')
        api_key: FRED API key
        limit: number of observations (default 1 = most recent)
        sort_order: 'desc' for most recent first
        observation_start: YYYY-MM-DD
        observation_end: YYYY-MM-DD
    
    Returns:
        dict with 'value' (float), 'date', 'series_id', 'description'
    """
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": sort_order,
        "limit": str(limit),
    }
    if observation_start:
        params["observation_start"] = observation_start
    if observation_end:
        params["observation_end"] = observation_end
    
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{FRED_BASE}?{query}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        
        observations = data.get("observations", [])
        if not observations:
            return {"error": f"No observations found for {series_id}"}
        
        # Filter out missing values
        valid = [o for o in observations if o.get("value", ".") != "."]
        if not valid:
            return {"error": f"No valid observations for {series_id}"}
        
        obs = valid[0]
        return {
            "series_id": series_id,
            "description": FRED_SERIES.get(series_id, series_id),
            "date": obs["date"],
            "value": float(obs["value"]),
        }
    
    except urllib.error.URLError as e:
        return {"error": f"FRED API request failed: {str(e)}"}
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return {"error": f"Failed to parse FRED response: {str(e)}"}


def get_risk_free_rate(api_key: str) -> dict:
    """Get the current 10-Year Treasury yield (risk-free rate for WACC)."""
    return fetch_fred_series("DGS10", api_key)


def get_risk_free_rate_with_fallback(api_key: Optional[str] = None) -> dict:
    """Get the 10Y risk-free rate from FRED, falling back to the Treasury site.
    
    Returns a normalized dict with source metadata so the caller can cite it.
    """
    if api_key:
        fred = get_risk_free_rate(api_key)
        if "error" not in fred:
            fred["source"] = "FRED"
            return fred
    
    treasury = get_treasury_10y_from_website()
    treasury["source"] = "U.S. Treasury website"
    return treasury


def get_treasury_yields(api_key: str) -> dict:
    """Get current yield curve data points."""
    series_ids = ["DGS2", "DGS5", "DGS10", "DGS30", "DFF"]
    results = {}
    for sid in series_ids:
        r = fetch_fred_series(sid, api_key)
        if "error" not in r:
            results[sid] = {
                "description": r["description"],
                "value_pct": r["value"],
                "date": r["date"],
            }
    
    # Compute yield curve slope
    if "DGS10" in results and "DGS2" in results:
        spread = results["DGS10"]["value_pct"] - results["DGS2"]["value_pct"]
        results["yield_curve_slope"] = {
            "spread_10y_2y_pct": round(spread, 3),
            "interpretation": (
                "Normal (positive slope)" if spread > 0.5 else
                "Flat" if spread > -0.1 else
                "Inverted (recession signal)"
            )
        }
    
    return results


def get_credit_spreads(api_key: str) -> dict:
    """Get BAA and AAA corporate bond yields for cost of debt benchmarking."""
    baa = fetch_fred_series("BAA", api_key)
    aaa = fetch_fred_series("AAA", api_key)
    
    result = {}
    if "error" not in baa:
        result["BAA_yield_pct"] = baa["value"]
    if "error" not in aaa:
        result["AAA_yield_pct"] = aaa["value"]
    if "BAA_yield_pct" in result and "AAA_yield_pct" in result:
        result["credit_spread_pct"] = round(result["BAA_yield_pct"] - result["AAA_yield_pct"], 3)
    
    return result


def get_macro_context(api_key: str) -> dict:
    """Get broad macro indicators for context."""
    indicators = {}
    
    for sid in ["CPIAUCSL", "UNRATE", "DFF"]:
        r = fetch_fred_series(sid, api_key)
        if "error" not in r:
            indicators[sid] = {
                "description": r["description"],
                "value": r["value"],
                "date": r["date"],
            }
    
    # CPI YoY change (need 13 months of data)
    cpi_current = fetch_fred_series("CPIAUCSL", api_key, limit=1)
    one_year_ago = (datetime.now() - timedelta(days=380)).strftime("%Y-%m-%d")
    cpi_prior = fetch_fred_series(
        "CPIAUCSL", api_key, limit=1,
        observation_end=one_year_ago, sort_order="desc"
    )
    
    if "error" not in cpi_current and "error" not in cpi_prior:
        inflation_yoy = (cpi_current["value"] / cpi_prior["value"] - 1) * 100
        indicators["inflation_yoy_pct"] = round(inflation_yoy, 2)
    
    return indicators


def get_treasury_10y_from_website(year: Optional[int] = None) -> dict:
    """Fetch the most recent 10Y yield from the U.S. Treasury daily yield curve page.
    
    This is a fallback when FRED is unavailable. The parser is intentionally simple
    and designed for the Treasury table structure.
    """
    if year is None:
        year = datetime.now().year
    url = TREASURY_10Y_URL.format(year=year)
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "finance-skills/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.URLError as e:
        return {"error": f"Treasury yield page request failed: {str(e)}"}
    
    lines = [line.strip() for line in html.splitlines() if "/" in line and "N/A" in line]
    if not lines:
        return {"error": "Treasury yield page parse failed: no data rows found"}
    
    latest = lines[-1].split()
    if len(latest) < 10:
        return {"error": "Treasury yield page parse failed: malformed row"}
    
    # Table layout places the 10Y yield near the end. Current Treasury page order is:
    # Date ... 1 Mo 1.5 Mo 2 Mo 3 Mo 4 Mo 6 Mo 1 Yr 2 Yr 3 Yr 5 Yr 7 Yr 10 Yr 20 Yr 30 Yr
    try:
        date = latest[0]
        value = float(latest[-3])
    except (ValueError, IndexError):
        return {"error": "Treasury yield page parse failed: 10Y value not extractable"}
    
    return {
        "series_id": "UST10Y",
        "description": "10-Year Treasury yield from Treasury daily yield curve page",
        "date": date,
        "value": value,
    }


# =============================================================================
# edgartools Helpers
# =============================================================================

def get_latest_filing(ticker: str, form_type: str = "10-K"):
    """Get the latest SEC filing of a given type using edgartools.
    
    Args:
        ticker: Company ticker (e.g., 'AAPL')
        form_type: '10-K', '10-Q', '8-K', etc.
    
    Returns:
        Filing object or error dict
    
    Requires: pip install edgartools
    """
    try:
        from edgar import Company
        
        company = Company(ticker)
        filings = company.get_filings(form=form_type)
        latest = filings.latest(1)
        
        if latest and len(latest) > 0:
            return latest[0]
        else:
            return {"error": f"No {form_type} filings found for {ticker}"}
    
    except ImportError:
        return {"error": "edgartools not installed. Run: pip install edgartools"}
    except Exception as e:
        return {"error": f"Failed to fetch {form_type} for {ticker}: {str(e)}"}


def get_latest_10k(ticker: str):
    """Get the most recent 10-K filing."""
    return get_latest_filing(ticker, "10-K")


def get_latest_10q(ticker: str):
    """Get the most recent 10-Q filing."""
    return get_latest_filing(ticker, "10-Q")


def get_risk_factors(ticker: str, form_type: str = "10-K") -> dict:
    """Extract Item 1A Risk Factors from the latest filing.
    
    Returns:
        dict with 'text' (risk factors text) and 'filing_date'
    """
    try:
        from edgar import Company
        
        company = Company(ticker)
        filings = company.get_filings(form=form_type)
        latest = filings.latest(1)
        
        if not latest or len(latest) == 0:
            return {"error": f"No {form_type} found"}
        
        filing = latest[0]
        # Attempt to get the filing object with parsed sections
        filing_obj = filing.obj()
        
        # Try to extract Item 1A
        if hasattr(filing_obj, 'item_1a') or hasattr(filing_obj, 'risk_factors'):
            text = getattr(filing_obj, 'item_1a', None) or getattr(filing_obj, 'risk_factors', None)
            return {
                "filing_date": str(filing.filing_date),
                "text": str(text) if text else "Risk factors section not parseable",
            }
        else:
            return {
                "filing_date": str(filing.filing_date),
                "note": "Risk factors extraction not supported for this filing structure. Use filing.text() for full text.",
            }
    
    except ImportError:
        return {"error": "edgartools not installed"}
    except Exception as e:
        return {"error": f"Failed to extract risk factors: {str(e)}"}


def diff_risk_factors(ticker: str) -> dict:
    """Compare risk factors between the two most recent 10-K filings.
    
    This identifies NEW risks that appeared in the latest filing.
    New risk factors are one of the strongest signals of emerging problems.
    """
    try:
        from edgar import Company
        
        company = Company(ticker)
        filings = company.get_filings(form="10-K")
        recent = filings.latest(2)
        
        if not recent or len(recent) < 2:
            return {"error": "Need at least 2 annual filings for comparison"}
        
        return {
            "current_filing_date": str(recent[0].filing_date),
            "prior_filing_date": str(recent[1].filing_date),
            "note": (
                "To diff risk factors, load both filings with .obj() and compare "
                "Item 1A sections. Look for entirely new risk paragraphs, "
                "changed severity language (e.g., 'may' → 'will'), and "
                "new specific risk categories (regulatory, competitive, financial)."
            ),
            "instructions": (
                "1. current = recent[0].obj()\n"
                "2. prior = recent[1].obj()\n"
                "3. Compare text sections for additions/changes\n"
                "4. New risk factor language is a leading indicator"
            ),
        }
    
    except ImportError:
        return {"error": "edgartools not installed"}
    except Exception as e:
        return {"error": str(e)}


def get_xbrl_financials(ticker: str, form_type: str = "10-K") -> dict:
    """Extract structured XBRL financial data from the latest filing.
    
    This provides the authoritative financial data directly from SEC filings,
    useful for cross-checking EODHD data or getting line items EODHD doesn't cover.
    """
    try:
        from edgar import Company
        
        company = Company(ticker)
        filings = company.get_filings(form=form_type)
        latest = filings.latest(1)
        
        if not latest or len(latest) == 0:
            return {"error": f"No {form_type} found"}
        
        filing = latest[0]
        filing_obj = filing.obj()
        
        result = {
            "filing_date": str(filing.filing_date),
            "form_type": form_type,
        }
        
        # Try to extract financial statements
        for attr in ["balance_sheet", "income_statement", "cash_flow_statement"]:
            if hasattr(filing_obj, attr):
                stmt = getattr(filing_obj, attr)
                result[attr] = str(stmt) if stmt else None
        
        return result
    
    except ImportError:
        return {"error": "edgartools not installed"}
    except Exception as e:
        return {"error": f"XBRL extraction failed: {str(e)}"}


if __name__ == "__main__":
    print("Data Fetch Helpers")
    print("=" * 50)
    print("\nPreflight report:")
    print(json.dumps(preflight_report(), indent=2))
    print("\nFRED Series available:")
    for sid, desc in FRED_SERIES.items():
        print(f"  {sid}: {desc}")
    print("\nedgartools functions:")
    print("  get_latest_10k(ticker)")
    print("  get_latest_10q(ticker)")
    print("  get_risk_factors(ticker)")
    print("  diff_risk_factors(ticker)")
    print("  get_xbrl_financials(ticker)")
    print("\nUsage: Import this module and call functions with your API keys.")
