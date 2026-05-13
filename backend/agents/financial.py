"""
agents/financial.py — Analyzes financial health and valuation.
Persona: Benjamin Graham.
"""

from agents.base import call_claude

SYSTEM_PROMPT = """You are Benjamin Graham, the father of value investing and author of
'The Intelligent Investor' and 'Security Analysis'.

You evaluate stocks with extreme rigor on financial safety and valuation margin of safety.
Graham's core principles:
1. Margin of safety — only buy when price is significantly below intrinsic value
2. P/E ratio — ideally below 15 for value investments; above 25 is speculative
3. P/B ratio — below 1.5 is attractive; above 3 is expensive for most companies
4. Debt — current ratio above 2, debt/equity below 0.5 preferred
5. FCF — companies must generate real cash, not just accounting profits
6. Earnings stability — consistent earnings over 5-10 years, not just recent profits
7. ROE and ROIC — must demonstrate genuine economic returns
8. Dividend history — Graham valued consistent dividend payers

Apply strict quantitative discipline. Be harsh on overvalued or financially weak companies.
A score above 80 requires near-perfect financial metrics by Graham's standards.
A score below 40 means the company fails basic safety criteria."""

USER_PROMPT = """Perform a rigorous Graham-style financial analysis on this stock.
Evaluate all valuation multiples, balance sheet strength, profitability, and cash flow generation.
Apply margin-of-safety thinking. Score financial health and value 0-100."""


async def analyze_financial(stock_data: dict) -> dict:
    """Extract all financial ratios and call Gemini for Graham analysis."""
    financials = stock_data.get("financials", {})
    info = stock_data.get("info", {})

    relevant_data = {
        # Valuation
        "pe_ratio": financials.get("pe_ratio"),
        "forward_pe": financials.get("forward_pe"),
        "pb_ratio": financials.get("pb_ratio"),
        "ps_ratio": financials.get("ps_ratio"),
        "ev_ebitda": financials.get("ev_ebitda"),
        "peg_ratio": financials.get("peg_ratio"),
        "market_cap": financials.get("market_cap"),
        "enterprise_value": financials.get("enterprise_value"),
        # Profitability
        "gross_margin_pct": financials.get("gross_margin"),
        "operating_margin_pct": financials.get("operating_margin"),
        "net_margin_pct": financials.get("net_margin"),
        "roe_pct": financials.get("roe"),
        "roa_pct": financials.get("roa"),
        "roic_pct": financials.get("roic"),
        # Balance sheet
        "debt_equity_ratio": financials.get("debt_equity"),
        "current_ratio": financials.get("current_ratio"),
        "quick_ratio": financials.get("quick_ratio"),
        "total_debt": financials.get("total_debt"),
        "total_cash": financials.get("total_cash"),
        "total_equity": financials.get("total_equity"),
        # Cash flow
        "free_cash_flow": financials.get("free_cash_flow"),
        "operating_cash_flow": financials.get("operating_cash_flow"),
        "capex": financials.get("capex"),
        # Growth
        "revenue_growth_pct": financials.get("revenue_growth"),
        "earnings_growth_pct": financials.get("earnings_growth"),
        # Dividends
        "dividend_yield_pct": financials.get("dividend_yield"),
        "five_year_avg_dividend_yield": financials.get("five_year_avg_dividend_yield"),
        "payout_ratio_pct": financials.get("payout_ratio"),
        # Price data
        "beta": financials.get("beta"),
        "week_52_high": financials.get("week_52_high"),
        "week_52_low": financials.get("week_52_low"),
        "current_price": financials.get("current_price"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
    }

    return await call_claude(SYSTEM_PROMPT, USER_PROMPT, relevant_data)
