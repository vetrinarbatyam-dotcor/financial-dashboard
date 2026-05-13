"""
agents/market.py — Analyzes market position and competitive dynamics.
Persona: Joel Greenblatt.
"""

from agents.base import call_claude

SYSTEM_PROMPT = """You are Joel Greenblatt, founder of Gotham Capital and author of
'The Little Book That Beats the Market', creator of the Magic Formula investing approach.

You evaluate companies based on market position, earnings power, and competitive dynamics
using the framework: Return on Capital × Earnings Yield = Magic Formula Score.

Greenblatt's key criteria:
1. Earnings yield (EBIT / Enterprise Value) — the "cheap" factor
2. Return on capital (EBIT / (Net Working Capital + Net Fixed Assets)) — the "good" factor
3. Industry dynamics — is this a structurally attractive industry?
4. Competitive positioning — does the company have pricing power in its market?
5. TAM (Total Addressable Market) — is the market big enough for continued growth?
6. Regulatory and macro risks — what external forces could impair earnings?
7. Cyclicality — is this a cyclical business temporarily at peak or trough earnings?
8. Moat sustainability — will high returns on capital attract destructive competition?

Be quantitative. If ROIC is high and EV/EBIT is low, that's a Magic Formula candidate.
Contextualize ratios within the sector — a 15% ROIC is great in manufacturing, mediocre in tech."""

USER_PROMPT = """Analyze this company's market position, competitive dynamics, and risk profile.
Use Greenblatt's Magic Formula framework — assess earnings yield AND return on capital.
Consider sector trends, TAM, macro risks, and competitive threats.
Score market position and risk-adjusted opportunity 0-100."""


async def analyze_market(stock_data: dict) -> dict:
    """Extract market/competitive fields and call Gemini."""
    financials = stock_data.get("financials", {})
    info = stock_data.get("info", {})

    # Compute earnings yield if possible
    earnings_yield = None
    try:
        ev = financials.get("enterprise_value")
        operating_income = None
        # Approximate EBIT from margins
        rev = financials.get("total_revenue")
        op_margin = financials.get("operating_margin")
        if rev and op_margin:
            operating_income = rev * op_margin / 100
        if operating_income and ev and ev != 0:
            earnings_yield = (operating_income / ev) * 100
    except Exception:
        earnings_yield = None

    relevant_data = {
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "exchange": info.get("exchange"),
        "longBusinessSummary_snippet": (info.get("longBusinessSummary") or "")[:500],
        # Greenblatt metrics
        "roic_pct": financials.get("roic"),
        "roe_pct": financials.get("roe"),
        "ev_ebitda": financials.get("ev_ebitda"),
        "earnings_yield_pct": earnings_yield,
        "enterprise_value": financials.get("enterprise_value"),
        "market_cap": financials.get("market_cap"),
        # Valuation context
        "pe_ratio": financials.get("pe_ratio"),
        "pb_ratio": financials.get("pb_ratio"),
        "operating_margin_pct": financials.get("operating_margin"),
        "gross_margin_pct": financials.get("gross_margin"),
        # Risk factors
        "beta": financials.get("beta"),
        "debt_equity_ratio": financials.get("debt_equity"),
        "total_debt": financials.get("total_debt"),
        "revenue_growth_pct": financials.get("revenue_growth"),
        "earnings_growth_pct": financials.get("earnings_growth"),
        "week_52_high": financials.get("week_52_high"),
        "week_52_low": financials.get("week_52_low"),
        "current_price": financials.get("current_price"),
        "fullTimeEmployees": info.get("fullTimeEmployees"),
    }

    return await call_claude(SYSTEM_PROMPT, USER_PROMPT, relevant_data)
