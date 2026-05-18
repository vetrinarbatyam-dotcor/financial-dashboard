import re
"""
data_fetcher.py — Pulls comprehensive stock data via yfinance.
Israeli stocks: appends .TA suffix automatically when market == "IL".
"""

import asyncio
import math
from typing import Optional
import yfinance as yf


def _safe_get(obj, *keys, default=None):
    """Safely traverse nested dicts/objects."""
    for key in keys:
        if obj is None:
            return default
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            obj = getattr(obj, key, None)
    return obj if obj is not None else default


def _sanitize_num(val):
    """Return float or None — strips inf/nan."""
    if val is None:
        return None
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def _fetch_sync(ticker_symbol: str) -> Optional[dict]:
    """Synchronous yfinance fetch — run via asyncio.to_thread."""
    try:
        tk = yf.Ticker(ticker_symbol)

        info: dict = tk.info or {}

        # ---- Income statement ----
        try:
            income = tk.financials  # annual, most recent = col 0
            latest_income = income.iloc[:, 0] if income is not None and not income.empty else None
        except Exception:
            latest_income = None

        # ---- Balance sheet ----
        try:
            balance = tk.balance_sheet
            latest_balance = balance.iloc[:, 0] if balance is not None and not balance.empty else None
        except Exception:
            latest_balance = None

        # ---- Cash flow ----
        try:
            cashflow = tk.cashflow
            latest_cf = cashflow.iloc[:, 0] if cashflow is not None and not cashflow.empty else None
        except Exception:
            latest_cf = None

        # ---- Revenue history (up to 5Y) ----
        revenue_history = []
        try:
            if tk.financials is not None and not tk.financials.empty:
                rev_row = tk.financials.loc["Total Revenue"] if "Total Revenue" in tk.financials.index else None
                if rev_row is not None:
                    revenue_history = [
                        {"year": str(col.year), "revenue": float(val)}
                        for col, val in rev_row.items()
                        if val is not None and not _is_nan(val)
                    ]
        except Exception:
            revenue_history = []

        # ---- EPS history ----
        eps_history = []
        try:
            earnings = tk.earnings_history
            if earnings is not None and not earnings.empty:
                eps_history = [
                    {"date": str(row["quarter"]) if "quarter" in earnings.columns else str(i),
                     "epsActual": float(row.get("epsActual", 0) or 0)}
                    for i, row in earnings.iterrows()
                ]
        except Exception:
            eps_history = []

        # ---- Computed helpers ----
        def _val(series, label):
            try:
                if series is not None and label in series.index:
                    v = series[label]
                    return float(v) if not _is_nan(v) else None
            except Exception:
                pass
            return None

        total_revenue = _val(latest_income, "Total Revenue")
        gross_profit = _val(latest_income, "Gross Profit")
        operating_income = _val(latest_income, "Operating Income")
        net_income = _val(latest_income, "Net Income")
        total_assets = _val(latest_balance, "Total Assets")
        total_equity = _val(latest_balance, "Stockholders Equity") or _val(latest_balance, "Total Stockholder Equity")
        total_debt = _val(latest_balance, "Total Debt") or _val(latest_balance, "Long Term Debt")
        current_assets = _val(latest_balance, "Current Assets")
        current_liabilities = _val(latest_balance, "Current Liabilities")
        inventory = _val(latest_balance, "Inventory")
        fcf = _val(latest_cf, "Free Cash Flow")
        capex = _val(latest_cf, "Capital Expenditure")
        operating_cf = _val(latest_cf, "Operating Cash Flow")

        # Derived ratios
        gross_margin = (gross_profit / total_revenue * 100) if gross_profit and total_revenue else info.get("grossMargins")
        if gross_margin and isinstance(gross_margin, float) and gross_margin < 1:
            gross_margin = gross_margin * 100  # yfinance sometimes returns 0-1

        operating_margin = (operating_income / total_revenue * 100) if operating_income and total_revenue else info.get("operatingMargins")
        if operating_margin and isinstance(operating_margin, float) and operating_margin < 1:
            operating_margin = operating_margin * 100

        roe = (net_income / total_equity * 100) if net_income and total_equity and total_equity != 0 else info.get("returnOnEquity")
        if roe and isinstance(roe, float) and abs(roe) < 2:
            roe = roe * 100

        debt_equity = (total_debt / total_equity) if total_debt and total_equity and total_equity != 0 else info.get("debtToEquity")

        current_ratio = (current_assets / current_liabilities) if current_assets and current_liabilities and current_liabilities != 0 else info.get("currentRatio")

        quick_ratio = ((current_assets - (inventory or 0)) / current_liabilities) if current_assets and current_liabilities and current_liabilities != 0 else info.get("quickRatio")

        # ROIC approximation: EBIT*(1-tax) / (debt + equity)
        roic = None
        try:
            ebit = operating_income
            if ebit and total_equity and total_debt:
                invested_capital = total_equity + total_debt
                if invested_capital != 0:
                    roic = (ebit * 0.75) / invested_capital * 100  # assume ~25% effective tax
        except Exception:
            roic = None

        financials = {
            # Valuation
            "pe_ratio": _sanitize_num(info.get("trailingPE") or info.get("forwardPE")),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "peg_ratio": info.get("pegRatio"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            # Profitability
            "gross_margin": gross_margin if gross_margin else (info.get("grossMargins", 0) or 0) * 100 if info.get("grossMargins") else None,
            "operating_margin": operating_margin if operating_margin else (info.get("operatingMargins", 0) or 0) * 100 if info.get("operatingMargins") else None,
            "net_margin": (info.get("profitMargins", 0) or 0) * 100 if info.get("profitMargins") else None,
            "roe": roe,
            "roa": (info.get("returnOnAssets", 0) or 0) * 100 if info.get("returnOnAssets") else None,
            "roic": roic,
            # Financial health
            "debt_equity": debt_equity,
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            "total_debt": total_debt,
            "total_equity": total_equity,
            "total_cash": info.get("totalCash"),
            # Cash flow
            "free_cash_flow": fcf if fcf else info.get("freeCashflow"),
            "operating_cash_flow": operating_cf,
            "capex": capex,
            # Growth
            "revenue_growth": (info.get("revenueGrowth", 0) or 0) * 100 if info.get("revenueGrowth") else None,
            "earnings_growth": (info.get("earningsGrowth", 0) or 0) * 100 if info.get("earningsGrowth") else None,
            "earnings_quarterly_growth": (info.get("earningsQuarterlyGrowth", 0) or 0) * 100 if info.get("earningsQuarterlyGrowth") else None,
            # Dividends
            "dividend_yield": (info.get("dividendYield", 0) or 0) * 100 if info.get("dividendYield") else None,
            "five_year_avg_dividend_yield": info.get("fiveYearAvgDividendYield"),
            "payout_ratio": (info.get("payoutRatio", 0) or 0) * 100 if info.get("payoutRatio") else None,
            # Price
            "beta": info.get("beta"),
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low": info.get("fiftyTwoWeekLow"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            # Share data
            "shares_outstanding": info.get("sharesOutstanding"),
            "float_shares": info.get("floatShares"),
            "insider_ownership": (info.get("heldPercentInsiders", 0) or 0) * 100 if info.get("heldPercentInsiders") else None,
            "institutional_ownership": (info.get("heldPercentInstitutions", 0) or 0) * 100 if info.get("heldPercentInstitutions") else None,
            # Totals for context
            "total_revenue": total_revenue,
            "gross_profit": gross_profit,
            "net_income": net_income,
        }

        officers = []
        try:
            raw_officers = info.get("companyOfficers", []) or []
            for o in raw_officers[:5]:
                officers.append({
                    "name": o.get("name"),
                    "title": o.get("title"),
                    "totalPay": o.get("totalPay"),
                    "exercisedValue": o.get("exercisedValue"),
                    "yearBorn": o.get("yearBorn"),
                })
        except Exception:
            officers = []

        return {
            "ticker": ticker_symbol,
            "info": {
                "longName": info.get("longName") or info.get("shortName"),
                "longBusinessSummary": info.get("longBusinessSummary", ""),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "fullTimeEmployees": info.get("fullTimeEmployees"),
                "companyOfficers": officers,
                "website": info.get("website"),
                "country": info.get("country"),
                "city": info.get("city"),
                "exchange": info.get("exchange"),
                "currency": info.get("currency"),
            },
            "financials": financials,
            "history": {
                "revenue": revenue_history,
                "eps": eps_history,
            },
        }

    except Exception as exc:
        raise RuntimeError(f"yfinance fetch failed for {ticker_symbol}: {exc}") from exc


def _is_nan(val) -> bool:
    try:
        return math.isnan(float(val))
    except Exception:
        return False


async def fetch_stock_data(ticker: str, market: str) -> dict:
    """
    Public async entry point.
    Appends .TA for Israeli stocks before calling yfinance.
    Raises ValueError for clearly invalid tickers before hitting the network.
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("ticker must be a non-empty string")
    symbol = ticker.strip().upper()
    if not re.match(r"^[A-Z0-9]{1,10}(\.TA)?$", symbol):
        raise ValueError(f"Invalid ticker format: {symbol!r}")
    if not re.match(r"^(US|IL)$", market.upper()):
        raise ValueError(f"market must be 'US' or 'IL', got {market!r}")
    if market.upper() == "IL" and not symbol.endswith(".TA"):
        symbol = f"{symbol}.TA"

    data = await asyncio.to_thread(_fetch_sync, symbol)
    return data
