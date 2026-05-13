"""
screener.py — שטרסלר: batch screener for TA-90 + S&P 500.
Runs the full נחמיה pipeline (5 agents + 6 investor profiles) for each stock.
Results are persisted in screen_runs table in SQLite.
"""

import asyncio
import json
import sqlite3
import os
from datetime import datetime
from typing import Optional

from cache import get_cached_analysis, save_analysis, DB_PATH

from data_fetcher import fetch_stock_data
from agents.company import analyze_company
from agents.management import analyze_management
from agents.financial import analyze_financial
from agents.growth import analyze_growth
from agents.market import analyze_market
from scorer import score_profiles

BATCH_SIZE = 2          # for full scan: 2 stocks at a time = max 10 concurrent Claude calls
TARGETED_BATCH_SIZE = 1  # for targeted scan: 1 stock at a time = max 5 concurrent Claude calls

# ---------------------------------------------------------------------------
# Stock universes
# ---------------------------------------------------------------------------

# TA-35 + TA-90 = TA-125 Israeli stocks (base tickers, .TA appended by data_fetcher)
# Source: TASE index composition — update periodically
TASE_90 = [
    # TA-35 (top 35 by market cap)
    "NICE", "TEVA", "ICL", "ESLT", "NVMI", "BEZQ", "FIBI",
    "LUMI", "POLI", "AMOT", "ENLT", "CEL", "TSEM", "MGDL",
    "MKTG", "CPTP", "AURA", "RADI", "LEAO", "NETO",
    "SFET", "AMDL", "ORBI", "VALE", "KOST", "MISH",
    "INBR", "ORA", "IDBH", "FTAL", "SANO", "SPEK",
    "WAND", "BWAY", "BRMG",
    # TA-90 (stocks ranked 36-125 by market cap)
    "TASE", "MOMO", "TLRD", "SPEN", "ORIT", "ZION",
    "MGRT", "LHTV", "MXLG", "TACT", "TUYA", "PCBT",
    "ISRS", "SMTI", "KLIL", "SKBN", "SUPR", "UBNK",
    "VHCL", "SHVA", "STRS", "ENRG", "ALHE", "MNRV",
    "GISH", "GPRE", "IBIT", "ISNR", "LSCO", "MSBI",
    "MTDS", "NTGR", "ORCT", "PBSL", "PONT", "PRSK",
    "RMLI", "RPST", "RSHO", "RTAR", "RVIV", "SELA",
    "SNFL", "SPNT", "SPTR", "TBLT", "TDHA", "TLSY",
    "TNNR", "TPST", "TZUR", "VALS", "VTTR", "HTLR",
]

SP500_FALLBACK = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "BRK-B",
    "JPM", "JNJ", "V", "UNH", "PG", "HD", "MA", "XOM", "CVX", "MRK",
    "KO", "PEP", "ABBV", "AVGO", "LLY", "BAC", "WMT", "DIS", "COST",
    "TMO", "ACN", "DHR", "VZ", "CMCSA", "NFLX", "ADBE", "INTC", "CRM",
    "AMD", "QCOM", "TXN", "INTU", "IBM", "HON", "GE", "MMM", "CAT",
    "GS", "MS", "AXP", "SBUX", "MCD", "NKE", "BA", "RTX", "LMT", "NOC",
    "AMGN", "GILD", "BIIB", "REGN", "VRTX", "BMY", "PFE", "ABT", "MDT",
    "SYK", "ISRG", "BSX", "ZTS", "DXCM", "CI", "CVS", "UNP", "CSX",
    "NSC", "FDX", "UPS", "DE", "EMR", "ETN", "ITW", "PH", "ROP", "IEX",
    "AMT", "PLD", "SPG", "O", "DLR", "PSA", "EQR", "AVB", "WELL", "VTR",
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "XEL", "SRE", "WEC", "ES",
    "ORCL", "SAP", "NOW", "SNOW", "WDAY", "CDNS", "SNPS", "ANSS", "PTC",
    "F", "GM", "TM", "HMC", "STLA", "RIVN", "LCID", "NIO", "LI", "XPEV",
    "PYPL", "SQ", "AFRM", "UPST", "SOFI", "NU", "COIN", "HOOD", "MSTR",
    "WFC", "C", "USB", "TFC", "PNC", "KEY", "RF", "FITB", "HBAN", "CFG",
    "MU", "WDC", "STX", "AMAT", "LRCX", "KLAC", "MRVL", "ON", "SWKS",
    "CHTR", "TMUS", "T", "LUMN", "DISH", "WBD", "PARA", "FOX", "NYT",
    "AMCX", "AMC", "CNK", "RGC", "IMAX", "LGF-A",
    "PM", "MO", "BTI", "RAI", "VGR", "SWMAY",
    "BHP", "RIO", "VALE", "FCX", "NEM", "AEM", "WPM", "GOLD", "KGC",
    "HAL", "SLB", "BKR", "OXY", "DVN", "FANG", "EOG", "PXD", "COP",
    "ENPH", "SEDG", "RUN", "SPWR", "NOVA", "FSLR", "CSIQ",
    "SHOP", "MELI", "SE", "GRAB", "BABA", "JD", "PDD", "BIDU",
    "RBLX", "U", "EA", "TTWO", "ATVI", "NTDOY",
    "ZM", "DOCU", "DDOG", "NET", "CRWD", "S", "PANW", "FTNT", "OKTA",
    "TWLO", "MDB", "ESTC", "SUMO", "FROG", "GTLB",
    "UBER", "LYFT", "ABNB", "DASH", "EXPE", "BKNG", "TRIP",
    "SPOT", "NFLX", "ROKU", "FUBO", "SIRI",
    "W", "ETSY", "CHWY", "CHEWY", "CVNA", "CARVANA",
    "PTON", "LULU", "COLM", "PVH", "HBI", "UA", "SKX",
    "YUM", "QSR", "CMG", "WING", "SHAK", "TXRH",
    "WBA", "RAD", "COST", "TGT", "WMT", "DG", "DLTR",
    "CLX", "CHD", "ENR", "SJM", "MKC", "HRL", "TSN",
    "ADM", "BG", "INGR", "MOS", "CF", "NTR", "FMC",
    "IP", "PKG", "SON", "SEE", "ATR", "BERY",
    "ECL", "IFF", "RPM", "PPG", "SHW", "FUL", "H2O",
    "APD", "LIN", "PPL", "CF",
]


def get_sp500() -> list[str]:
    try:
        import pandas as pd
        df = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        tickers = df["Symbol"].tolist()
        return [str(t).replace(".", "-") for t in tickers]  # BRK.B → BRK-B for yfinance
    except Exception:
        return list(dict.fromkeys(SP500_FALLBACK))  # deduplicated fallback


# ---------------------------------------------------------------------------
# SQLite helpers for screen_runs table
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_screen_db() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screen_runs (
                id           TEXT PRIMARY KEY,
                started_at   TEXT,
                completed_at TEXT,
                status       TEXT DEFAULT 'running',
                total        INTEGER DEFAULT 0,
                done_count   INTEGER DEFAULT 0,
                results_json TEXT
            )
        """)
        conn.commit()


def create_screen_run(job_id: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO screen_runs (id, started_at, status) VALUES (?, ?, 'running')",
            (job_id, datetime.utcnow().isoformat()),
        )
        conn.commit()


def _update_screen_run(job_id: str, **kwargs) -> None:
    if not kwargs:
        return
    set_clauses = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [job_id]
    with _get_conn() as conn:
        conn.execute(f"UPDATE screen_runs SET {set_clauses} WHERE id = ?", values)
        conn.commit()


def get_screen_run_status(job_id: str) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, status, total, done_count, started_at, completed_at FROM screen_runs WHERE id = ?",
            (job_id,),
        ).fetchone()
    return dict(row) if row else None


def get_screen_run_results(job_id: str) -> Optional[list]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT results_json FROM screen_runs WHERE id = ?",
            (job_id,),
        ).fetchone()
    if row and row["results_json"]:
        return json.loads(row["results_json"])
    return None


def get_latest_screen_run_meta() -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, status, total, done_count, started_at, completed_at FROM screen_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def get_latest_screen_results() -> Optional[list]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT results_json FROM screen_runs WHERE status = 'done' ORDER BY completed_at DESC LIMIT 1"
        ).fetchone()
    if row and row["results_json"]:
        return json.loads(row["results_json"])
    return None


# ---------------------------------------------------------------------------
# Analysis pipeline helpers
# ---------------------------------------------------------------------------

def extract_screen_row(result: dict, ticker: str, market: str) -> dict:
    metrics = result.get("metrics", {})
    investor_scores = result.get("investor_scores", {})
    raw_ts = (result.get("_raw") or {}).get("timestamp") or datetime.utcnow().isoformat()
    return {
        "ticker": ticker.upper(),
        "market": market,
        "name": result.get("company_name", ticker),
        "sector": result.get("sector"),
        "composite": result.get("composite_score"),
        "buffett": investor_scores.get("buffett"),
        "munger": investor_scores.get("munger"),
        "graham": investor_scores.get("graham"),
        "lynch": investor_scores.get("lynch"),
        "greenblatt": investor_scores.get("greenblatt"),
        "fisher": investor_scores.get("fisher"),
        "pe": metrics.get("pe"),
        "pb": metrics.get("pb"),
        "roe": metrics.get("roe"),
        "roic": metrics.get("roic"),
        "fcf": metrics.get("fcf"),
        "debt_equity": metrics.get("debt_equity"),
        "peg": metrics.get("peg"),
        "ev_ebitda": metrics.get("ev_ebitda"),
        "gross_margin": metrics.get("gross_margin"),
        "beta": metrics.get("beta"),
        "rec": result.get("recommendation"),
        "current_price": result.get("current_price"),
        "market_cap": result.get("market_cap"),
        "analyzed_at": raw_ts,
    }


async def _analyze_one(ticker: str, market: str, force_refresh: bool = False) -> Optional[dict]:
    """Run full pipeline for one stock. Returns screen_row dict or None on failure."""
    try:
        # Cache check (skip on force_refresh)
        if not force_refresh:
            cached = get_cached_analysis(ticker, market, ttl_hours=24)
            if cached:
                return extract_screen_row(cached, ticker, market)

        # Fetch data
        stock_data = await fetch_stock_data(ticker, market)
        if not stock_data:
            return None

        # 5 agents in parallel
        (company_r, mgmt_r, fin_r, growth_r, market_r) = await asyncio.gather(
            analyze_company(stock_data),
            analyze_management(stock_data),
            analyze_financial(stock_data),
            analyze_growth(stock_data),
            analyze_market(stock_data),
            return_exceptions=True,
        )

        def safe(res, name: str) -> dict:
            if isinstance(res, Exception):
                return {"score": 50, "summary": f"{name} failed: {res}", "bullets": [], "warnings": [str(res)]}
            return res

        agent_results = {
            "company": safe(company_r, "Company"),
            "management": safe(mgmt_r, "Management"),
            "financial": safe(fin_r, "Financial"),
            "growth": safe(growth_r, "Growth"),
            "market": safe(market_r, "Market"),
        }

        profiles = score_profiles(agent_results, stock_data)

        fin = stock_data.get("financials", {})
        info = stock_data.get("info", {})
        ts = datetime.utcnow()

        mc = fin.get("market_cap")
        if mc:
            if mc >= 1e12:   mc_str = f"${mc/1e12:.1f}T"
            elif mc >= 1e9:  mc_str = f"${mc/1e9:.1f}B"
            else:             mc_str = f"${mc/1e6:.0f}M"
        else:
            mc_str = None

        fcf = fin.get("free_cash_flow")
        fcf_m = round(fcf / 1e6, 1) if fcf else None
        rec_map = {"BUY": "buy", "HOLD": "wait", "AVOID": "avoid"}

        result = {
            "ticker": ticker.upper(),
            "market": market,
            "analysis_date": ts.strftime("%-d.%-m.%Y"),
            "composite_score": round(profiles.get("composite", 0), 1),
            "recommendation": rec_map.get(profiles.get("recommendation", "HOLD"), "wait"),
            "company_name": info.get("longName", ticker),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "current_price": fin.get("current_price"),
            "market_cap": mc_str,
            "investor_scores": {k: round(profiles.get(k, 0), 1) for k in ["buffett", "munger", "graham", "lynch", "greenblatt", "fisher"]},
            "agent_reports": agent_results,
            "metrics": {
                "pe": fin.get("pe_ratio"),
                "pb": fin.get("pb_ratio"),
                "roe": fin.get("roe"),
                "roic": fin.get("roic"),
                "fcf": fcf_m,
                "debt_equity": fin.get("debt_equity"),
                "current_ratio": fin.get("current_ratio"),
                "peg": fin.get("peg_ratio"),
                "ev_ebitda": fin.get("ev_ebitda"),
                "gross_margin": fin.get("gross_margin"),
                "operating_margin": fin.get("operating_margin"),
                "beta": fin.get("beta"),
                "week52_high": fin.get("week_52_high"),
                "week52_low": fin.get("week_52_low"),
            },
            "_raw": {
                "stock_info": {
                    "website": info.get("website"),
                    "employees": info.get("fullTimeEmployees"),
                    "summary": info.get("longBusinessSummary", "")[:600],
                },
                "profiles_detail": profiles,
                "timestamp": ts.isoformat(),
            },
        }

        # Persist to analyses cache so /history and StockDetail can show it
        await asyncio.to_thread(save_analysis, ticker, market, result)

        return extract_screen_row(result, ticker, market)

    except Exception as exc:
        return None  # skip failed stocks silently


# ---------------------------------------------------------------------------
# Main screener job
# ---------------------------------------------------------------------------

async def run_screen_job(job_id: str) -> None:
    """Background coroutine: analyze all stocks in batches, update DB."""
    try:
        sp500 = await asyncio.to_thread(get_sp500)
        all_stocks = [(t, "IL") for t in TASE_90] + [(t, "US") for t in sp500]
        total = len(all_stocks)

        await asyncio.to_thread(_update_screen_run, job_id, status="running", total=total)

        results = []
        done_count = 0

        for i in range(0, total, BATCH_SIZE):
            batch = all_stocks[i : i + BATCH_SIZE]
            tasks = [_analyze_one(ticker, market) for ticker, market in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in batch_results:
                if r and not isinstance(r, Exception):
                    results.append(r)

            done_count = min(i + BATCH_SIZE, total)
            await asyncio.to_thread(_update_screen_run, job_id, done_count=done_count)

        await asyncio.to_thread(
            _update_screen_run,
            job_id,
            status="done",
            done_count=total,
            completed_at=datetime.utcnow().isoformat(),
            results_json=json.dumps(results, ensure_ascii=False),
        )

    except Exception as exc:
        await asyncio.to_thread(
            _update_screen_run,
            job_id,
            status="error",
            completed_at=datetime.utcnow().isoformat(),
            results_json=json.dumps([], ensure_ascii=False),
        )


async def run_targeted_screen_job(job_id: str, stocks: list[tuple[str, str]]) -> None:
    """
    Run analysis for a specific list of (ticker, market) pairs, one at a time.
    Always forces fresh analysis (bypasses cache).
    """
    total = len(stocks)
    await asyncio.to_thread(_update_screen_run, job_id, status="running", total=total)

    results = []
    for i, (ticker, market) in enumerate(stocks):
        row = await _analyze_one(ticker, market, force_refresh=True)
        if row:
            results.append(row)
        await asyncio.to_thread(_update_screen_run, job_id, done_count=i + 1)

    await asyncio.to_thread(
        _update_screen_run,
        job_id,
        status="done",
        done_count=total,
        completed_at=datetime.utcnow().isoformat(),
        results_json=json.dumps(results, ensure_ascii=False),
    )


# Initialize table on import
try:
    init_screen_db()
except Exception as _e:
    import warnings
    warnings.warn(f"שטרסלר: screen_runs table init failed: {_e}")
