"""
agents/management.py — Analyzes management quality and capital allocation.
Persona: Charlie Munger.
"""

from agents.base import call_claude

SYSTEM_PROMPT = """You are Charlie Munger, Vice Chairman of Berkshire Hathaway.
You are evaluating the quality of a company's management team and their capital allocation decisions.

Charlie Munger cares deeply about:
1. Integrity and honesty of management — do they shoot straight with shareholders?
2. Insider ownership — do management own enough skin in the game?
3. Capital allocation track record — do they buy back shares at good prices or dilute?
4. Executive compensation — is it aligned with long-term shareholder value?
5. CEO tenure and track record — experienced or revolving door?
6. Debt management — do they use leverage wisely?
7. Return on incremental capital — can they reinvest at high rates?

Apply Munger's inversion principle: first list everything that could go wrong with management.
Be skeptical of overpaid executives, excessive stock issuance, or poor capital allocation.
High scores require EXCEPTIONAL management with demonstrated long-term thinking."""

USER_PROMPT = """Analyze this company's management quality and capital allocation record.
Focus on the companyOfficers data, insider ownership percentage, and any available buyback/dilution signals.
Score management quality 0-100."""


async def analyze_management(stock_data: dict) -> dict:
    """Extract management-relevant fields and call Gemini."""
    info = stock_data.get("info", {})
    financials = stock_data.get("financials", {})

    relevant_data = {
        "companyOfficers": info.get("companyOfficers", []),
        "insider_ownership_pct": financials.get("insider_ownership"),
        "institutional_ownership_pct": financials.get("institutional_ownership"),
        "shares_outstanding": financials.get("shares_outstanding"),
        "float_shares": financials.get("float_shares"),
        "free_cash_flow": financials.get("free_cash_flow"),
        "operating_cash_flow": financials.get("operating_cash_flow"),
        "roe_pct": financials.get("roe"),
        "roic_pct": financials.get("roic"),
        "debt_equity_ratio": financials.get("debt_equity"),
        "total_debt": financials.get("total_debt"),
        "total_cash": financials.get("total_cash"),
        "capex": financials.get("capex"),
        "net_income": financials.get("net_income"),
        "sector": info.get("sector"),
        "longBusinessSummary_snippet": (info.get("longBusinessSummary") or "")[:400],
    }

    return await call_claude(SYSTEM_PROMPT, USER_PROMPT, relevant_data)
