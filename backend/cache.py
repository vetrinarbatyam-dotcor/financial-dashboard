"""
cache.py — SQLite persistence layer for OR Finance.
DB path: /home/claude-user/Finance/finance.db
TTL: 24 hours (enforced at read time in main.py — cache stores everything).
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "/home/claude-user/Finance/finance.db")
# Fallback for local dev on Windows
if not os.path.isabs(DB_PATH) or (os.name == "nt" and not os.path.exists(os.path.dirname(DB_PATH))):
    _local_dir = os.path.join(os.path.dirname(__file__), "..")
    DB_PATH = os.path.abspath(os.path.join(_local_dir, "finance.db"))


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Called at startup."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker        TEXT    NOT NULL,
                market        TEXT    NOT NULL,
                timestamp     TEXT    NOT NULL,
                result_json   TEXT    NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ticker_market ON analyses (ticker, market)")
        conn.commit()


def save_analysis(ticker: str, market: str, result: dict) -> None:
    """Persist a completed analysis result."""
    ts = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO analyses (ticker, market, timestamp, result_json) VALUES (?, ?, ?, ?)",
            (ticker.upper(), market.upper(), ts, json.dumps(result, ensure_ascii=False)),
        )
        conn.commit()


def get_cached_analysis(ticker: str, market: str, ttl_hours: int = 24) -> Optional[dict]:
    """
    Return the most recent cached result for a ticker+market if within TTL,
    or None if not found / expired.
    """
    from datetime import timedelta

    cutoff = (datetime.utcnow() - timedelta(hours=ttl_hours)).isoformat()
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT result_json, timestamp FROM analyses
            WHERE ticker = ? AND market = ? AND timestamp >= ?
            ORDER BY timestamp DESC LIMIT 1
            """,
            (ticker.upper(), market.upper(), cutoff),
        ).fetchone()
    if row:
        return json.loads(row["result_json"])
    return None


def get_history(limit: int = 50) -> list[dict]:
    """
    Return list of recent analyses (metadata only, no full result_json).
    Ordered by most recent first.
    """
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT ticker, market, timestamp, result_json
            FROM analyses
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    history = []
    for row in rows:
        try:
            result = json.loads(row["result_json"])
            # Support both old nested format and new flat format
            composite = result.get("composite_score") or result.get("profiles", {}).get("composite")
            rec = result.get("recommendation") or result.get("profiles", {}).get("recommendation")
            name = result.get("company_name") or result.get("stock_info", {}).get("name")
            investor_scores = result.get("investor_scores") or {
                k: result.get("profiles", {}).get(k)
                for k in ["buffett", "munger", "graham", "lynch", "greenblatt", "fisher"]
            }
            metrics = result.get("metrics", {})
            history.append({
                "ticker": row["ticker"],
                "market": row["market"],
                "timestamp": row["timestamp"],
                "composite_score": composite,
                "recommendation": rec,
                "stock_name": name,
                "investor_scores": investor_scores,
                "metrics": {k: metrics.get(k) for k in ["pe", "pb", "roe", "roic", "peg", "ev_ebitda", "gross_margin", "beta"]},
            })
        except Exception:
            history.append({
                "ticker": row["ticker"],
                "market": row["market"],
                "timestamp": row["timestamp"],
                "composite_score": None,
                "recommendation": None,
                "stock_name": None,
                "investor_scores": {},
                "metrics": {},
            })
    return history


def get_stock_full_history(ticker: str, limit: int = 20) -> list[dict]:
    """
    Return all saved analyses for a specific ticker, ordered newest first.
    Each entry contains: ticker, market, timestamp, composite_score,
    recommendation, stock_name, investor_scores, metrics,
    agent_summaries (summary text only — no bullets/warnings).
    """
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT ticker, market, timestamp, result_json
            FROM analyses
            WHERE ticker = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (ticker.upper(), limit),
        ).fetchall()

    history = []
    for row in rows:
        try:
            result = json.loads(row["result_json"])
            composite = result.get("composite_score") or result.get("profiles", {}).get("composite")
            rec       = result.get("recommendation") or result.get("profiles", {}).get("recommendation")
            name      = result.get("company_name") or result.get("stock_info", {}).get("name")
            investor_scores = result.get("investor_scores") or {
                k: result.get("profiles", {}).get(k)
                for k in ["buffett", "munger", "graham", "lynch", "greenblatt", "fisher"]
            }
            metrics = result.get("metrics", {})

            # Extract only summary text from each agent report
            agent_reports = result.get("agent_reports", {})
            agent_summaries = {
                key: (agent_reports.get(key) or {}).get("summary")
                for key in ["company", "management", "financial", "growth", "market"]
            }

            history.append({
                "ticker":          row["ticker"],
                "market":          row["market"],
                "timestamp":       row["timestamp"],
                "composite_score": composite,
                "recommendation":  rec,
                "stock_name":      name,
                "investor_scores": investor_scores,
                "metrics": {
                    k: metrics.get(k)
                    for k in ["pe", "pb", "roe", "roic", "peg", "ev_ebitda", "gross_margin", "beta"]
                },
                "agent_summaries": agent_summaries,
            })
        except Exception:
            history.append({
                "ticker":          row["ticker"],
                "market":          row["market"],
                "timestamp":       row["timestamp"],
                "composite_score": None,
                "recommendation":  None,
                "stock_name":      None,
                "investor_scores": {},
                "metrics":         {},
                "agent_summaries": {},
            })
    return history


# Initialize DB on module import so the table is always ready.
try:
    init_db()
except Exception as _e:
    import warnings
    warnings.warn(f"OR Finance: SQLite init failed: {_e}")
