"""
retail.py — Quick retail investor analysis (single Claude call, ~30s).
"""
import asyncio
import json
import re


async def analyze_retail(stock_data: dict) -> dict:
    fin = stock_data.get("financials", {})
    info = stock_data.get("info", {})
    ticker = stock_data.get("ticker", "").replace(".TA", "")

    mc = fin.get("market_cap")
    mc_str = None
    if mc:
        if mc >= 1e12:
            mc_str = f"${mc/1e12:.1f}T"
        elif mc >= 1e9:
            mc_str = f"${mc/1e9:.1f}B"
        else:
            mc_str = f"${mc/1e6:.0f}M"

    data_summary = {
        "ticker": ticker,
        "company_name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "current_price": fin.get("current_price"),
        "market_cap": mc_str,
        "currency": info.get("currency"),
        "pe_ratio": fin.get("pe_ratio"),
        "forward_pe": fin.get("forward_pe"),
        "pb_ratio": fin.get("pb_ratio"),
        "peg_ratio": fin.get("peg_ratio"),
        "ev_ebitda": fin.get("ev_ebitda"),
        "revenue_growth_pct": fin.get("revenue_growth"),
        "earnings_growth_pct": fin.get("earnings_growth"),
        "gross_margin_pct": fin.get("gross_margin"),
        "operating_margin_pct": fin.get("operating_margin"),
        "net_margin_pct": fin.get("net_margin"),
        "roe_pct": fin.get("roe"),
        "debt_equity": fin.get("debt_equity"),
        "current_ratio": fin.get("current_ratio"),
        "free_cash_flow_m": round(fin.get("free_cash_flow") / 1e6, 1) if fin.get("free_cash_flow") is not None else None,
        "beta": fin.get("beta"),
        "week52_high": fin.get("week_52_high"),
        "week52_low": fin.get("week_52_low"),
        "dividend_yield_pct": fin.get("dividend_yield"),
        "business_summary": (info.get("longBusinessSummary") or "")[:400],
    }

    prompt = f"""אתה יועץ השקעות מנוסה שמסביר למשקיע פרטי רגיל (לא מקצועי) האם כדאי לשקול לקנות מנייה זו.

נתוני המנייה:
{json.dumps(data_summary, ensure_ascii=False, indent=2, default=str)}

ענה בדיוק בפורמט JSON הבא (עברית בלבד בכל שדות הטקסט, אל תוסיף טקסט מחוץ ל-JSON):

{{
  "company_one_liner": "משפט אחד מה החברה עושה בשפה פשוטה",
  "health": {{
    "revenue_growth_verdict": "צומחת / יציבה / דועכת",
    "profitability_verdict": "רווחית מאוד / רווחית / סף רווחיות / הפסדית",
    "debt_verdict": "ללא חוב / חוב סביר / חוב גבוה / חוב מסוכן",
    "health_score": <0-100>,
    "health_summary": "2 משפטים על הבריאות הפיננסית"
  }},
  "valuation": {{
    "verdict": "זולה / מתומחרת הוגן / יקרה / יקרה מאוד",
    "pe_context": "משפט קצר על ה-P/E ביחס למגזר",
    "dcf_note": "האם המחיר הנוכחי מוצדק לפי הצמיחה הצפויה",
    "valuation_score": <0-100>
  }},
  "analyst_view": {{
    "sentiment": "חיובי / ניטרלי / שלילי",
    "reasoning": "2 משפטים על מה שמניע את הסנטימנט"
  }},
  "risks": [
    "סיכון ספציפי 1",
    "סיכון ספציפי 2",
    "סיכון ספציפי 3"
  ],
  "verdict": {{
    "stars": <1-5>,
    "recommendation": "קנה / שקול לקנות / המתן / הימנע",
    "recommendation_en": "buy / consider / wait / avoid",
    "main_reason": "הסיבה העיקרית להמלצה",
    "investment_horizon": "קצר (>1 שנה) / בינוני (1-3 שנים) / ארוך (3+ שנים)",
    "suitable_for": "למי מתאימה ההשקעה",
    "caution": "אזהרה חשובה אחת"
  }}
}}"""

    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "-p", prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
        response_text = stdout.decode().strip()
        if not response_text:
            raise RuntimeError("Empty Claude response")
        text = re.sub(r"```(?:json)?\s*", "", response_text).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON in response")
        result = json.loads(text[start:end + 1])
        # Ensure required top-level keys exist (defensive against partial Claude output)
        for _required_key in ("health", "valuation", "analyst_view", "risks", "verdict"):
            if _required_key not in result:
                raise ValueError(f"Claude response missing required key: {_required_key!r}")
        result["ticker"] = ticker
        result["company_name"] = data_summary.get("company_name", ticker)
        result["current_price"] = data_summary.get("current_price")
        result["market_cap"] = mc_str
        result["sector"] = data_summary.get("sector")
        result["metrics"] = {
            "pe": fin.get("pe_ratio"),
            "pb": fin.get("pb_ratio"),
            "roe": fin.get("roe"),
            "revenue_growth": fin.get("revenue_growth"),
            "operating_margin": fin.get("operating_margin"),
            "debt_equity": fin.get("debt_equity"),
            "week52_high": fin.get("week_52_high"),
            "week52_low": fin.get("week_52_low"),
            "dividend_yield": fin.get("dividend_yield"),
        }
        return result
    except asyncio.TimeoutError:
        return _fallback(ticker, "timeout")
    except Exception as exc:
        return _fallback(ticker, str(exc))


def _fallback(ticker: str, error: str = "") -> dict:
    return {
        "ticker": ticker, "company_name": ticker, "current_price": None,
        "market_cap": None, "sector": None, "metrics": {},
        "company_one_liner": f"לא ניתן לנתח את {ticker} כרגע",
        "health": {"revenue_growth_verdict": "לא זמין", "profitability_verdict": "לא זמין",
                    "debt_verdict": "לא זמין", "health_score": 50,
                    "health_summary": f"שגיאה: {error[:100]}"},
        "valuation": {"verdict": "לא זמין", "pe_context": "לא זמין",
                       "dcf_note": "לא זמין", "valuation_score": 50},
        "analyst_view": {"sentiment": "ניטרלי", "reasoning": "נתונים לא זמינים"},
        "risks": ["נתונים לא זמינים"],
        "verdict": {"stars": 3, "recommendation": "המתן", "recommendation_en": "wait",
                     "main_reason": "אין מספיק נתונים", "investment_horizon": "לא ידוע",
                     "suitable_for": "לא ידוע", "caution": "יש לאסוף נתונים נוספים"},
    }
