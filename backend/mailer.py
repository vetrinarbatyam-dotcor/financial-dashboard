"""
mailer.py — HTML email report sender for OR Finance.
Sends a beautiful RTL Hebrew analysis report via Yahoo SMTP.
"""

import smtplib
import html as html_module
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ---------------------------------------------------------------------------
# SMTP credentials (hardcoded — move to env vars if needed)
# ---------------------------------------------------------------------------

SMTP_HOST = "smtp.mail.yahoo.com"
SMTP_PORT = 587
SMTP_USER = "vet_batyam@yahoo.com"
SMTP_PASS = "htqlobubdfdrwfic"
TO_ADDRESSES = ["vet_batyam@yahoo.com", "vetrinarbatyam@gmail.com"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_color(score: float) -> str:
    if score is None:
        return "#888888"
    if score >= 70:
        return "#27ae60"
    if score >= 50:
        return "#f39c12"
    return "#e74c3c"


def _score_bg(score: float) -> str:
    if score is None:
        return "#555555"
    if score >= 70:
        return "#1e8449"
    if score >= 50:
        return "#d68910"
    return "#c0392b"


def _rec_hebrew(rec: str) -> str:
    mapping = {"buy": "קנה", "wait": "המתן", "hold": "המתן", "avoid": "הימנע",
               "BUY": "קנה", "HOLD": "המתן", "AVOID": "הימנע"}
    return mapping.get(rec, rec or "—")


def _rec_color(rec: str) -> str:
    mapping = {"buy": "#27ae60", "wait": "#f39c12", "hold": "#f39c12", "avoid": "#e74c3c",
               "BUY": "#27ae60", "HOLD": "#f39c12", "AVOID": "#e74c3c"}
    return mapping.get(rec, "#888888")


def _investor_name(key: str) -> str:
    names = {
        "buffett": "Warren Buffett",
        "munger": "Charlie Munger",
        "graham": "Benjamin Graham",
        "lynch": "Peter Lynch",
        "greenblatt": "Joel Greenblatt",
        "fisher": "Philip Fisher",
    }
    return names.get(key, key.capitalize())


def _agent_name_he(key: str) -> str:
    names = {
        "company": "חברה",
        "management": "הנהלה",
        "financial": "פיננסים",
        "growth": "צמיחה",
        "market": "שוק",
    }
    return names.get(key, key)


def _fmt(val, suffix="", digits=2, prefix=""):
    if val is None:
        return "—"
    try:
        return f"{prefix}{val:,.{digits}f}{suffix}"
    except Exception:
        return str(val)


def _pct(val):
    if val is None:
        return "—"
    try:
        v = float(val)
        if abs(v) < 2:          # already a ratio like 0.25
            v *= 100
        return f"{v:.1f}%"
    except Exception:
        return str(val)


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def _build_html(result: dict) -> str:
    ticker         = result.get("ticker", "—")
    company_name   = result.get("company_name", ticker)
    composite      = result.get("composite_score")
    rec            = result.get("recommendation", "wait")
    rec_he         = _rec_hebrew(rec)
    rec_color      = _rec_color(rec)
    analysis_date  = result.get("analysis_date", datetime.utcnow().strftime("%-d.%-m.%Y"))
    sector         = result.get("sector") or "—"
    industry       = result.get("industry") or "—"
    price          = result.get("current_price")
    market_cap     = result.get("market_cap") or "—"

    investor_scores = result.get("investor_scores", {})
    agent_reports   = result.get("agent_reports", {})
    metrics         = result.get("metrics", {})

    score_color = _score_color(composite)
    score_bg    = _score_bg(composite)
    composite_str = f"{composite:.1f}" if composite is not None else "—"

    price_str = _fmt(price, prefix="$", digits=2) if price else "—"

    # --- Investor scores rows ---
    investor_rows = ""
    for key in ["buffett", "munger", "graham", "lynch", "greenblatt", "fisher"]:
        sc = investor_scores.get(key)
        sc_str = f"{sc:.1f}" if sc is not None else "—"
        sc_color = _score_color(sc)
        sc_bg    = _score_bg(sc)
        investor_rows += f"""
        <tr>
          <td style="padding:10px 14px; border-bottom:1px solid #2a2a2a; color:#ccc; text-align:right;">
            {_investor_name(key)}
          </td>
          <td style="padding:10px 14px; border-bottom:1px solid #2a2a2a; text-align:center;">
            <span style="display:inline-block; background:{sc_bg}; color:#fff;
                         padding:4px 14px; border-radius:20px; font-weight:bold; font-size:14px;">
              {sc_str}
            </span>
          </td>
        </tr>"""

    # --- Agent report sections ---
    agent_sections = ""
    for key in ["company", "management", "financial", "growth", "market"]:
        ar = agent_reports.get(key, {})
        if not ar:
            continue
        sc       = ar.get("score")
        summary  = html_module.escape(str(ar.get("summary", "—")))
        bullets  = ar.get("bullets", [])
        warnings = ar.get("warnings", [])
        sc_str   = f"{sc:.0f}" if sc is not None else "—"
        sc_color = _score_color(sc)
        sc_bg    = _score_bg(sc)

        bullets_html = ""
        for b in (bullets or []):
            bullets_html += f'<li style="margin:4px 0; color:#ccc;">{html_module.escape(str(b))}</li>'

        warnings_html = ""
        for w in (warnings or []):
            if w:
                warnings_html += (
                    f'<li style="margin:4px 0; color:#e74c3c;">'
                    f'&#9888; {html_module.escape(str(w))}</li>'
                )

        agent_sections += f"""
        <div style="background:#1e1e1e; border-radius:12px; padding:20px 24px;
                    margin-bottom:16px; border-right:4px solid {sc_color};">
          <div style="display:flex; justify-content:space-between; align-items:center;
                      margin-bottom:12px; flex-direction:row-reverse;">
            <div style="display:flex; align-items:center; gap:12px;">
              <span style="background:{sc_bg}; color:#fff; padding:4px 16px;
                           border-radius:20px; font-weight:bold; font-size:15px;">{sc_str}</span>
              <span style="color:#fff; font-size:17px; font-weight:bold;">
                סוכן {_agent_name_he(key)}
              </span>
            </div>
          </div>
          <p style="color:#bbb; line-height:1.7; margin:0 0 12px; text-align:right;">{summary}</p>
          {"<ul style='padding-right:20px; margin:8px 0; text-align:right;'>" + bullets_html + "</ul>" if bullets_html else ""}
          {"<ul style='padding-right:20px; margin:10px 0; text-align:right;'>" + warnings_html + "</ul>" if warnings_html else ""}
        </div>"""

    # --- Metrics table ---
    metric_labels = [
        ("pe",               "P/E",          lambda v: _fmt(v, digits=2)),
        ("pb",               "P/B",          lambda v: _fmt(v, digits=2)),
        ("roe",              "ROE",          _pct),
        ("roic",             "ROIC",         _pct),
        ("fcf",              "FCF ($M)",     lambda v: _fmt(v, digits=1)),
        ("peg",              "PEG",          lambda v: _fmt(v, digits=2)),
        ("ev_ebitda",        "EV/EBITDA",    lambda v: _fmt(v, digits=1)),
        ("gross_margin",     "Gross Margin", _pct),
        ("operating_margin", "Op. Margin",   _pct),
        ("debt_equity",      "Debt/Equity",  lambda v: _fmt(v, digits=2)),
        ("current_ratio",    "Current Ratio",lambda v: _fmt(v, digits=2)),
        ("beta",             "Beta",         lambda v: _fmt(v, digits=2)),
        ("week52_high",      "52W High",     lambda v: _fmt(v, prefix="$", digits=2)),
        ("week52_low",       "52W Low",      lambda v: _fmt(v, prefix="$", digits=2)),
    ]

    metric_rows = ""
    for i, (key, label, fmt_fn) in enumerate(metric_labels):
        bg = "#1a1a1a" if i % 2 == 0 else "#202020"
        val_str = fmt_fn(metrics.get(key))
        metric_rows += f"""
        <tr style="background:{bg};">
          <td style="padding:9px 14px; color:#27ae60; text-align:left; font-weight:bold;
                     font-size:14px;">{val_str}</td>
          <td style="padding:9px 14px; color:#bbb; text-align:right; font-size:14px;">{label}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>נחמיה — {ticker}</title>
</head>
<body style="margin:0; padding:0; background:#0f0f0f; font-family:'Segoe UI',Arial,sans-serif;
             direction:rtl; color:#fff;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#0f0f0f; padding:20px 0;">
    <tr><td align="center">
      <table width="640" cellpadding="0" cellspacing="0"
             style="max-width:640px; width:100%;">

        <!-- ── HEADER ── -->
        <tr>
          <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
                     border-radius:16px 16px 0 0; padding:36px 32px; text-align:center;">
            <div style="font-size:28px; font-weight:900; letter-spacing:3px;
                        color:#fff; margin-bottom:6px;">נחמיה</div>
            <div style="font-size:13px; color:#8892b0; letter-spacing:2px;">
              מערכת ניתוח מניות ערך
            </div>
          </td>
        </tr>

        <!-- ── SCORE HERO ── -->
        <tr>
          <td style="background:#141414; padding:32px 32px 24px; text-align:center;">

            <div style="font-size:15px; color:#888; margin-bottom:8px;">{company_name}</div>
            <div style="font-size:22px; font-weight:bold; color:#fff; margin-bottom:20px;">
              {ticker}
            </div>

            <!-- Composite score circle -->
            <div style="display:inline-block; background:{score_bg};
                        border-radius:50%; width:110px; height:110px; line-height:110px;
                        font-size:36px; font-weight:900; color:#fff;
                        margin-bottom:16px; text-align:center;">
              {composite_str}
            </div>

            <div style="font-size:12px; color:#aaa; margin-bottom:16px;">ציון כולל</div>

            <!-- Recommendation badge -->
            <div style="display:inline-block; background:{rec_color};
                        color:#fff; padding:10px 32px; border-radius:30px;
                        font-size:20px; font-weight:900; letter-spacing:1px;">
              {rec_he}
            </div>
          </td>
        </tr>

        <!-- ── STOCK INFO ── -->
        <tr>
          <td style="background:#181818; padding:24px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:6px 0; color:#888; font-size:13px; text-align:right;">תאריך ניתוח</td>
                <td style="padding:6px 0; color:#fff; font-size:13px; text-align:left;">{analysis_date}</td>
              </tr>
              <tr>
                <td style="padding:6px 0; color:#888; font-size:13px; text-align:right;">מחיר נוכחי</td>
                <td style="padding:6px 0; color:#27ae60; font-size:14px; font-weight:bold; text-align:left;">{price_str}</td>
              </tr>
              <tr>
                <td style="padding:6px 0; color:#888; font-size:13px; text-align:right;">שווי שוק</td>
                <td style="padding:6px 0; color:#fff; font-size:13px; text-align:left;">{html_module.escape(str(market_cap))}</td>
              </tr>
              <tr>
                <td style="padding:6px 0; color:#888; font-size:13px; text-align:right;">סקטור</td>
                <td style="padding:6px 0; color:#fff; font-size:13px; text-align:left;">{html_module.escape(str(sector))}</td>
              </tr>
              <tr>
                <td style="padding:6px 0; color:#888; font-size:13px; text-align:right;">תעשייה</td>
                <td style="padding:6px 0; color:#fff; font-size:13px; text-align:left;">{html_module.escape(str(industry))}</td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ── INVESTOR SCORES ── -->
        <tr>
          <td style="background:#141414; padding:24px 32px;">
            <div style="font-size:17px; font-weight:bold; color:#fff;
                        margin-bottom:14px; padding-bottom:10px;
                        border-bottom:1px solid #333; text-align:right;">
              ניקוד לפי משקיעים מובילים
            </div>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#1a1a1a; border-radius:10px; overflow:hidden;">
              {investor_rows}
            </table>
          </td>
        </tr>

        <!-- ── AGENT REPORTS ── -->
        <tr>
          <td style="background:#181818; padding:24px 32px;">
            <div style="font-size:17px; font-weight:bold; color:#fff;
                        margin-bottom:16px; padding-bottom:10px;
                        border-bottom:1px solid #333; text-align:right;">
              דוחות סוכני AI
            </div>
            {agent_sections}
          </td>
        </tr>

        <!-- ── METRICS TABLE ── -->
        <tr>
          <td style="background:#141414; padding:24px 32px;">
            <div style="font-size:17px; font-weight:bold; color:#fff;
                        margin-bottom:14px; padding-bottom:10px;
                        border-bottom:1px solid #333; text-align:right;">
              מדדים פיננסיים
            </div>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border-radius:10px; overflow:hidden;">
              {metric_rows}
            </table>
          </td>
        </tr>

        <!-- ── FOOTER ── -->
        <tr>
          <td style="background:#0f0f0f; border-radius:0 0 16px 16px;
                     padding:24px 32px; text-align:center;">
            <div style="color:#555; font-size:11px; line-height:1.6; text-align:center;">
              דוח זה נוצר אוטומטית על ידי מערכת OR Finance לצרכי מחקר בלבד.<br>
              אין לראות בדוח זה המלצת השקעה. כל השקעה כרוכה בסיכון.<br>
              הנתונים מבוססים על מידע ציבורי זמין ועשויים להכיל אי-דיוקים.<br>
              <strong style="color:#444;">נחמיה © {datetime.utcnow().year}</strong>
            </div>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_report(result: dict) -> None:
    """
    Send an HTML analysis report email for the given result dict.
    Raises on SMTP failure.
    """
    ticker       = result.get("ticker", "TICKER")
    composite    = result.get("composite_score")
    rec          = result.get("recommendation", "wait")
    rec_he       = _rec_hebrew(rec)
    composite_str = f"{composite:.1f}" if composite is not None else "—"

    subject = f"נחמיה — ניתוח {ticker}: ציון {composite_str} | {rec_he}"
    html_body = _build_html(result)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_USER
    msg["To"]      = ", ".join(TO_ADDRESSES)

    # Attach both plain-text fallback and HTML
    plain = (
        f"OR Finance — ניתוח {ticker}\n"
        f"ציון כולל: {composite_str}\n"
        f"המלצה: {rec_he}\n"
        f"תאריך: {result.get('analysis_date', '—')}\n"
    )
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, TO_ADDRESSES, msg.as_string())
