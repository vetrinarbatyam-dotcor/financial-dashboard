"""
agents/growth.py — Analyzes growth quality and sustainability.
Persona: Peter Lynch.
"""

from agents.base import call_claude

SYSTEM_PROMPT = """You are Peter Lynch, legendary fund manager of Fidelity Magellan Fund,
author of 'One Up on Wall Street' and 'Beating the Street'.

You evaluate growth stocks with a sharp eye for quality vs. hype.
Lynch's core growth investing principles:
1. PEG ratio — price/earnings-to-growth; below 1.0 is undervalued growth, below 0.5 is a gem
2. Revenue CAGR — consistent double-digit growth over 5 years is powerful
3. EPS growth consistency — erratic or declining EPS is a red flag
4. Growth story clarity — "invest in what you understand" — is the growth driver obvious?
5. Earnings guidance reliability — do management estimates prove accurate?
6. Category killers vs. stalwarts vs. slow growers — classify correctly
7. Balance sheet supporting growth — growth funded by FCF is far superior to debt-funded growth
8. Earnings yield vs. growth rate — identify "ten-baggers" hiding in plain sight

Lynch categories: Fast Growers (20%+ EPS growth), Stalwarts (10-20%), Slow Growers (<10%),
Cyclicals, Turnarounds, Asset Plays. Score accordingly.
A score above 80 requires genuinely exceptional, sustainable, undervalued growth."""

USER_PROMPT = """Analyze this company's growth trajectory and quality.
Evaluate revenue CAGR, EPS growth consistency, PEG ratio, and the sustainability of the growth story.
Classify the growth type (fast grower, stalwart, etc.) and score it 0-100."""


async def analyze_growth(stock_data: dict) -> dict:
    """Extract growth-relevant fields and call Gemini."""
    financials = stock_data.get("financials", {})
    history = stock_data.get("history", {})
    info = stock_data.get("info", {})

    relevant_data = {
        # Valuation + growth
        "peg_ratio": financials.get("peg_ratio"),
        "pe_ratio": financials.get("pe_ratio"),
        "forward_pe": financials.get("forward_pe"),
        "ps_ratio": financials.get("ps_ratio"),
        # Growth rates
        "revenue_growth_yoy_pct": financials.get("revenue_growth"),
        "earnings_growth_yoy_pct": financials.get("earnings_growth"),
        "earnings_quarterly_growth_pct": financials.get("earnings_quarterly_growth"),
        # Historical data
        "revenue_history_5y": history.get("revenue", []),
        "eps_history": history.get("eps", []),
        # Quality of growth
        "gross_margin_pct": financials.get("gross_margin"),
        "operating_margin_pct": financials.get("operating_margin"),
        "free_cash_flow": financials.get("free_cash_flow"),
        "total_debt": financials.get("total_debt"),
        "total_cash": financials.get("total_cash"),
        "beta": financials.get("beta"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "longBusinessSummary_snippet": (info.get("longBusinessSummary") or "")[:400],
        "total_revenue": financials.get("total_revenue"),
        "net_income": financials.get("net_income"),
    }

    return await call_claude(SYSTEM_PROMPT, USER_PROMPT, relevant_data)
