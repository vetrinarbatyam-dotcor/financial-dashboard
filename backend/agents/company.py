"""
agents/company.py — Analyzes competitive moat and business model.
Persona: Warren Buffett's research assistant.
"""

from agents.base import call_claude

SYSTEM_PROMPT = """You are Warren Buffett's senior research assistant at Berkshire Hathaway.
Your job is to evaluate a company's competitive moat and business model with the same rigor
that Warren Buffett would apply before making a long-term investment.

Focus exclusively on:
1. Brand strength and consumer loyalty (pricing power)
2. Switching costs — how hard is it for customers to leave?
3. Network effects — does value grow with user base?
4. Cost advantages (scale, proprietary processes, location)
5. Market position and share
6. Business simplicity — can a non-expert understand how the company makes money?
7. Durability — will this moat exist in 10-20 years?

Be analytical and skeptical. High scores (>75) require a CLEAR, durable moat.
Medium scores (50-75) mean some competitive advantages but not a fortress.
Low scores (<50) mean commoditized, easily disrupted, or unclear moat."""

USER_PROMPT = """Analyze the company's competitive moat and business model based on the stock data provided.
Pay special attention to the longBusinessSummary, sector, and industry fields.
Score the company 0-100 based on moat strength and business quality."""


async def analyze_company(stock_data: dict) -> dict:
    """Extract relevant fields and call Gemini for moat/business analysis."""
    info = stock_data.get("info", {})
    financials = stock_data.get("financials", {})

    relevant_data = {
        "longBusinessSummary": info.get("longBusinessSummary", ""),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "fullTimeEmployees": info.get("fullTimeEmployees"),
        "website": info.get("website"),
        "market_cap_usd": financials.get("market_cap"),
        "gross_margin_pct": financials.get("gross_margin"),
        "operating_margin_pct": financials.get("operating_margin"),
        "revenue_growth_pct": financials.get("revenue_growth"),
        "pe_ratio": financials.get("pe_ratio"),
        "ps_ratio": financials.get("ps_ratio"),
        "total_revenue": financials.get("total_revenue"),
    }

    return await call_claude(SYSTEM_PROMPT, USER_PROMPT, relevant_data)
