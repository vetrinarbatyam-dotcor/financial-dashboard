"""
OR Finance — FastAPI backend entry point.
Port 3041 · SQLite cache · 5 parallel AI agents · 6 investor profiles
"""

import asyncio
import uuid
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from data_fetcher import fetch_stock_data
from agents.company import analyze_company
from agents.management import analyze_management
from agents.financial import analyze_financial
from agents.growth import analyze_growth
from agents.market import analyze_market
from scorer import score_profiles
from cache import save_analysis, get_history, get_stock_full_history
from screener import (
    run_screen_job,
    run_targeted_screen_job,
    create_screen_run,
    get_screen_run_status,
    get_screen_run_results,
    get_latest_screen_run_meta,
    get_latest_screen_results,
    init_screen_db,
)

try:
    from mailer import send_report as _send_report
    _MAILER_AVAILABLE = True
except ImportError:
    _MAILER_AVAILABLE = False
    _send_report = None

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="OR Finance API", version="1.0.0")


@app.on_event("startup")
async def on_startup():
    """Ensure SQLite schema is initialized on startup."""
    from cache import init_db
    await asyncio.to_thread(init_db)
    await asyncio.to_thread(init_screen_db)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store: { job_id: { status, progress, result, error } }
jobs: dict = {}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    ticker: str
    market: str = "US"  # "US" or "IL"


class JobStatus(BaseModel):
    job_id: str
    status: str          # pending | running | done | error
    progress: int        # 0-100
    result: Optional[dict] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Background analysis task
# ---------------------------------------------------------------------------

async def run_analysis(job_id: str, ticker: str, market: str) -> None:
    """Full pipeline: fetch → 5 agents (parallel) → score → cache."""
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["progress"] = 5

        # Step 1: Fetch stock data
        stock_data = await fetch_stock_data(ticker, market)
        jobs[job_id]["progress"] = 20

        if not stock_data:
            raise ValueError(f"No data found for ticker '{ticker}' in market '{market}'")

        # Step 2: Run all 5 agents in parallel
        jobs[job_id]["progress"] = 25
        (
            company_result,
            management_result,
            financial_result,
            growth_result,
            market_result,
        ) = await asyncio.gather(
            analyze_company(stock_data),
            analyze_management(stock_data),
            analyze_financial(stock_data),
            analyze_growth(stock_data),
            analyze_market(stock_data),
            return_exceptions=True,
        )

        jobs[job_id]["progress"] = 75

        # Unwrap exceptions from gather (replace with fallback dicts)
        def safe(res, name: str) -> dict:
            if isinstance(res, Exception):
                return {
                    "score": 50,
                    "summary": f"{name} analysis failed: {str(res)}",
                    "bullets": [],
                    "warnings": [str(res)],
                }
            return res

        agent_results = {
            "company": safe(company_result, "Company"),
            "management": safe(management_result, "Management"),
            "financial": safe(financial_result, "Financial"),
            "growth": safe(growth_result, "Growth"),
            "market": safe(market_result, "Market"),
        }

        # Step 3: Score investor profiles
        profiles = score_profiles(agent_results, stock_data)
        jobs[job_id]["progress"] = 90

        # Step 4: Build full result (frontend-compatible flat structure)
        fin = stock_data.get("financials", {})
        info = stock_data.get("info", {})
        ts = datetime.utcnow()

        # Format market cap for display
        mc = fin.get("market_cap")
        if mc:
            if mc >= 1e12:
                mc_str = f"${mc/1e12:.1f}T"
            elif mc >= 1e9:
                mc_str = f"${mc/1e9:.1f}B"
            else:
                mc_str = f"${mc/1e6:.0f}M"
        else:
            mc_str = None

        # Map recommendation to frontend keys
        rec_map = {"BUY": "buy", "HOLD": "wait", "AVOID": "avoid"}

        # FCF in millions
        fcf = fin.get("free_cash_flow")
        fcf_m = round(fcf / 1e6, 1) if fcf else None

        result = {
            # Identity
            "ticker": ticker.upper(),
            "market": market,
            "analysis_date": ts.strftime("%-d.%-m.%Y"),
            # Top-level scores (what Dashboard.jsx reads)
            "composite_score": round(profiles.get("composite", 0), 1),
            "recommendation": rec_map.get(profiles.get("recommendation", "HOLD"), "wait"),
            # Stock info
            "company_name": info.get("longName", ticker),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "current_price": fin.get("current_price"),
            "market_cap": mc_str,
            # Investor scores flat dict
            "investor_scores": {k: round(profiles.get(k, 0), 1) for k in ["buffett", "munger", "graham", "lynch", "greenblatt", "fisher"]},
            # Agent reports (Dashboard reads result.agent_reports.company etc.)
            "agent_reports": agent_results,
            # Metrics with frontend keys
            "metrics": {
                "pe":               fin.get("pe_ratio"),
                "pb":               fin.get("pb_ratio"),
                "roe":              fin.get("roe"),
                "roic":             fin.get("roic"),
                "fcf":              fcf_m,
                "debt_equity":      fin.get("debt_equity"),
                "current_ratio":    fin.get("current_ratio"),
                "peg":              fin.get("peg_ratio"),
                "ev_ebitda":        fin.get("ev_ebitda"),
                "gross_margin":     fin.get("gross_margin"),
                "operating_margin": fin.get("operating_margin"),
                "beta":             fin.get("beta"),
                "week52_high":      fin.get("week_52_high"),
                "week52_low":       fin.get("week_52_low"),
            },
            # Raw for cache / debug
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

        # Step 5: Persist to SQLite
        await asyncio.to_thread(save_analysis, ticker, market, result)

        jobs[job_id]["status"] = "done"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["result"] = result

    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["error"] = str(exc)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "OR Finance", "timestamp": datetime.utcnow().isoformat()}


@app.post("/analyze", response_model=dict, status_code=202)
async def start_analysis(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "result": None,
        "error": None,
        "ticker": req.ticker.upper(),
        "market": req.market.upper(),
    }
    background_tasks.add_task(run_analysis, job_id, req.ticker.upper(), req.market.upper())
    return {"job_id": job_id}


@app.get("/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        result=job.get("result"),
        error=job.get("error"),
    )


@app.get("/history")
async def history():
    rows = await asyncio.to_thread(get_history)
    return {"history": rows}


@app.get("/stock/{ticker}")
async def stock_history(ticker: str, limit: int = 20):
    """Return full analysis history for a specific ticker, newest first."""
    rows = await asyncio.to_thread(get_stock_full_history, ticker.upper(), limit)
    return {"ticker": ticker.upper(), "count": len(rows), "history": rows}


@app.post("/send-report")
async def send_email_report(req: dict):
    """
    Send an HTML analysis report by email for a completed job.
    Body: { "job_id": "<uuid>" }
    """
    if not _MAILER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Email feature not available (mailer import failed)")

    job_id = req.get("job_id")
    if not job_id:
        raise HTTPException(status_code=400, detail="Missing 'job_id' in request body")

    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if job.get("status") != "done":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not done yet (status: {job.get('status')})",
        )

    result = job.get("result")
    if not result:
        raise HTTPException(status_code=500, detail="Job is done but result is missing")

    try:
        await asyncio.to_thread(_send_report, result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(exc)}")

    return {"ok": True, "message": f"Report for {result.get('ticker')} sent successfully"}


# ---------------------------------------------------------------------------
# Screener (שטרסלר) routes
# ---------------------------------------------------------------------------

@app.post("/screen/start", status_code=202)
async def start_screen(background_tasks: BackgroundTasks):
    """Start a full TA-90 + S&P 500 screening run in the background."""
    job_id = str(uuid.uuid4())
    await asyncio.to_thread(create_screen_run, job_id)
    background_tasks.add_task(run_screen_job, job_id)
    return {"job_id": job_id}


@app.get("/screen/status/{job_id}")
async def screen_status(job_id: str):
    run = await asyncio.to_thread(get_screen_run_status, job_id)
    if not run:
        raise HTTPException(status_code=404, detail="Screen run not found")
    total = run["total"] or 1
    pct = round((run["done_count"] or 0) / total * 100)
    return {
        "job_id": job_id,
        "status": run["status"],
        "total": run["total"],
        "done": run["done_count"],
        "pct": pct,
        "started_at": run["started_at"],
        "completed_at": run.get("completed_at"),
    }


@app.get("/screen/results/{job_id}")
async def screen_results_by_id(job_id: str):
    run = await asyncio.to_thread(get_screen_run_status, job_id)
    if not run:
        raise HTTPException(status_code=404, detail="Screen run not found")
    if run["status"] != "done":
        raise HTTPException(status_code=409, detail=f"Run not done yet (status: {run['status']})")
    results = await asyncio.to_thread(get_screen_run_results, job_id)
    return {"job_id": job_id, "results": results or []}


@app.get("/screen/latest")
async def screen_latest():
    run = await asyncio.to_thread(get_latest_screen_run_meta)
    return {"run": run}


@app.get("/screen/stocks")
async def screen_stocks():
    """Return full results of the most recently completed screen run."""
    results = await asyncio.to_thread(get_latest_screen_results)
    return {"results": results or []}


class TargetedScreenRequest(BaseModel):
    tickers_us: list[str] = []
    tickers_il: list[str] = []


@app.post("/screen/targeted", status_code=202)
async def start_targeted_screen(req: TargetedScreenRequest, background_tasks: BackgroundTasks):
    """
    Run a focused screen on specific tickers (always fresh, no cache).
    Body: { tickers_us: ["AAPL", "MSFT", ...], tickers_il: ["NICE", "TEVA", ...] }
    """
    stocks = [(t.upper(), "US") for t in req.tickers_us] + [(t.upper(), "IL") for t in req.tickers_il]
    if not stocks:
        raise HTTPException(status_code=400, detail="Supply at least one ticker in tickers_us or tickers_il")
    job_id = str(uuid.uuid4())
    await asyncio.to_thread(create_screen_run, job_id)
    background_tasks.add_task(run_targeted_screen_job, job_id, stocks)
    return {"job_id": job_id, "total": len(stocks)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3041))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
