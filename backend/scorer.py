"""
scorer.py — Combines 5 agent scores into 6 investor profile scores.
Each profile has custom weights + quantitative bonus checks on raw financial data.
All scores are capped at 100.
"""

from typing import Any


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert any value to float."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _agent_score(agent_results: dict, agent_name: str) -> float:
    result = agent_results.get(agent_name, {})
    if isinstance(result, dict):
        return _safe_float(result.get("score", 50))
    return 50.0


def score_profiles(agent_results: dict, stock_data: dict) -> dict:
    """
    Compute 6 investor profile scores + composite + recommendation.

    Parameters
    ----------
    agent_results : dict
        Keys: company, management, financial, growth, market
        Each value is the agent's result dict { score, summary, bullets, warnings }

    stock_data : dict
        Full stock data from data_fetcher — used for quantitative bonus checks.

    Returns
    -------
    dict with keys: buffett, munger, graham, lynch, greenblatt, fisher,
                    composite, recommendation
    """
    fin = stock_data.get("financials", {}) if stock_data else {}

    # Raw agent scores (0-100)
    c = _agent_score(agent_results, "company")     # moat / business
    m = _agent_score(agent_results, "management")  # management quality
    f = _agent_score(agent_results, "financial")   # financial health
    g = _agent_score(agent_results, "growth")      # growth trajectory
    k = _agent_score(agent_results, "market")      # market position / risk

    # Financial metrics for bonus checks
    roe = _safe_float(fin.get("roe"), None)
    fcf = fin.get("free_cash_flow")
    pe = _safe_float(fin.get("pe_ratio"), None)
    pb = _safe_float(fin.get("pb_ratio"), None)
    current_ratio = _safe_float(fin.get("current_ratio"), None)
    peg = _safe_float(fin.get("peg_ratio"), None)
    roic = _safe_float(fin.get("roic"), None)
    gross_margin = _safe_float(fin.get("gross_margin"), None)
    operating_margin = _safe_float(fin.get("operating_margin"), None)
    revenue_growth = _safe_float(fin.get("revenue_growth"), None)
    earnings_growth = _safe_float(fin.get("earnings_growth"), None)
    ev_ebitda = _safe_float(fin.get("ev_ebitda"), None)
    net_margin = _safe_float(fin.get("net_margin"), None)

    # -----------------------------------------------------------------------
    # 1. BUFFETT
    # Weights: company*0.30 + management*0.20 + financial*0.30 + growth*0.10 + market*0.10
    # Bonuses: ROE>15% (+5), FCF positive (+5), PE<20 (+5)
    # -----------------------------------------------------------------------
    buffett_base = c * 0.30 + m * 0.20 + f * 0.30 + g * 0.10 + k * 0.10
    buffett_bonus = 0.0
    if roe is not None and roe > 15:
        buffett_bonus += 5
    if fcf is not None:
        try:
            if float(fcf) > 0:
                buffett_bonus += 5
        except (TypeError, ValueError):
            pass
    if pe is not None and pe > 0 and pe < 20:
        buffett_bonus += 5
    buffett = _clamp(buffett_base + buffett_bonus)

    # -----------------------------------------------------------------------
    # 2. MUNGER
    # Weights: company*0.25 + management*0.35 + financial*0.20 + growth*0.10 + market*0.10
    # Bonuses: simple business (+5 if company score > 65), high margins (+5 if op_margin>20)
    # -----------------------------------------------------------------------
    munger_base = c * 0.25 + m * 0.35 + f * 0.20 + g * 0.10 + k * 0.10
    munger_bonus = 0.0
    if c > 65:  # proxy for "simple, understandable business"
        munger_bonus += 5
    if operating_margin is not None and operating_margin > 20:
        munger_bonus += 5
    munger = _clamp(munger_base + munger_bonus)

    # -----------------------------------------------------------------------
    # 3. GRAHAM
    # Weights: company*0.10 + management*0.10 + financial*0.50 + growth*0.10 + market*0.20
    # Bonuses: PB<1.5 (+10), PE<15 (+10), current_ratio>2 (+5)
    # -----------------------------------------------------------------------
    graham_base = c * 0.10 + m * 0.10 + f * 0.50 + g * 0.10 + k * 0.20
    graham_bonus = 0.0
    if pb is not None and pb > 0 and pb < 1.5:
        graham_bonus += 10
    if pe is not None and pe > 0 and pe < 15:
        graham_bonus += 10
    if current_ratio is not None and current_ratio > 2:
        graham_bonus += 5
    graham = _clamp(graham_base + graham_bonus)

    # -----------------------------------------------------------------------
    # 4. LYNCH
    # Weights: company*0.20 + management*0.15 + financial*0.25 + growth*0.30 + market*0.10
    # Bonuses: PEG<1 (+10), consistent growth (earnings_growth>10% AND rev_growth>10%) (+5)
    # -----------------------------------------------------------------------
    lynch_base = c * 0.20 + m * 0.15 + f * 0.25 + g * 0.30 + k * 0.10
    lynch_bonus = 0.0
    if peg is not None and peg > 0 and peg < 1.0:
        lynch_bonus += 10
    if (
        earnings_growth is not None and earnings_growth > 10
        and revenue_growth is not None and revenue_growth > 10
    ):
        lynch_bonus += 5
    lynch = _clamp(lynch_base + lynch_bonus)

    # -----------------------------------------------------------------------
    # 5. GREENBLATT
    # Weights: company*0.10 + management*0.10 + financial*0.40 + growth*0.20 + market*0.20
    # Bonuses: high ROIC (>15%) (+10), high earnings yield (EV/EBITDA<10 → yield>10%) (+5)
    # -----------------------------------------------------------------------
    greenblatt_base = c * 0.10 + m * 0.10 + f * 0.40 + g * 0.20 + k * 0.20
    greenblatt_bonus = 0.0
    if roic is not None and roic > 15:
        greenblatt_bonus += 10
    if ev_ebitda is not None and ev_ebitda > 0 and ev_ebitda < 10:
        greenblatt_bonus += 5
    greenblatt = _clamp(greenblatt_base + greenblatt_bonus)

    # -----------------------------------------------------------------------
    # 6. FISHER
    # Weights: company*0.30 + management*0.20 + financial*0.15 + growth*0.30 + market*0.05
    # Bonuses: expanding margins (gross>30% AND net>10%) (+5), R&D / innovation signal (+5 if tech/biotech)
    # -----------------------------------------------------------------------
    fisher_base = c * 0.30 + m * 0.20 + f * 0.15 + g * 0.30 + k * 0.05
    fisher_bonus = 0.0
    if (
        gross_margin is not None and gross_margin > 30
        and net_margin is not None and net_margin > 10
    ):
        fisher_bonus += 5
    sector = (stock_data.get("info", {}).get("sector") or "").lower()
    if any(kw in sector for kw in ["technology", "tech", "biotechnology", "health", "pharma", "software"]):
        fisher_bonus += 5  # R&D / innovation premium for quality growth sectors
    fisher = _clamp(fisher_base + fisher_bonus)

    # -----------------------------------------------------------------------
    # Composite & recommendation
    # -----------------------------------------------------------------------
    composite = (buffett + munger + graham + lynch + greenblatt + fisher) / 6.0
    composite = round(composite, 1)

    if composite >= 70:
        recommendation = "BUY"
    elif composite >= 50:
        recommendation = "HOLD"
    else:
        recommendation = "AVOID"

    return {
        "buffett": round(buffett, 1),
        "munger": round(munger, 1),
        "graham": round(graham, 1),
        "lynch": round(lynch, 1),
        "greenblatt": round(greenblatt, 1),
        "fisher": round(fisher, 1),
        "composite": composite,
        "recommendation": recommendation,
        # Breakdown for transparency
        "_agent_scores": {
            "company": round(c, 1),
            "management": round(m, 1),
            "financial": round(f, 1),
            "growth": round(g, 1),
            "market": round(k, 1),
        },
        "_bonuses": {
            "buffett": round(buffett_bonus, 1),
            "munger": round(munger_bonus, 1),
            "graham": round(graham_bonus, 1),
            "lynch": round(lynch_bonus, 1),
            "greenblatt": round(greenblatt_bonus, 1),
            "fisher": round(fisher_bonus, 1),
        },
    }
