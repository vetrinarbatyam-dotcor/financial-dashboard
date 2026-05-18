import React, { useState, useEffect, useRef } from 'react';
import Gauge from '../components/Gauge.jsx';
import InvestorCard from '../components/InvestorCard.jsx';
import AgentPanel from '../components/AgentPanel.jsx';
import Tooltip from '../components/Tooltip.jsx';

// ─── Constants ───────────────────────────────────────────────────────────────

const METRICS_META = [
  { key: 'pe',             label: 'P/E',            tooltip: 'מכפיל רווח: כמה שנות רווח משלם השוק עבור המנייה', unit: 'x' },
  { key: 'pb',             label: 'P/B',            tooltip: 'מכפיל הון: מחיר המנייה ביחס לערך הספרים של החברה', unit: 'x' },
  { key: 'roe',            label: 'ROE',            tooltip: 'תשואה על ההון: כמה רווח מפיקה החברה מכל שקל של הון בעלים', unit: '%' },
  { key: 'roic',           label: 'ROIC',           tooltip: 'תשואה על ההשקעה: יעילות החברה בהפיכת הון לרווח', unit: '%' },
  { key: 'fcf',            label: 'FCF',            tooltip: 'תזרים מזומנים חופשי: כסף אמיתי שנשאר אחרי הוצאות הון', unit: 'M$' },
  { key: 'debt_equity',    label: 'Debt/Equity',    tooltip: 'יחס חוב להון: כמה חוב ביחס לבעלים', unit: '' },
  { key: 'current_ratio',  label: 'Current Ratio',  tooltip: 'יחס שוטף: כושר פירעון חובות קצרי טווח', unit: '' },
  { key: 'peg',            label: 'PEG',            tooltip: 'מכפיל צמיחה: P/E ביחס לצמיחת הרווח, <1 נחשב זול', unit: '' },
  { key: 'ev_ebitda',      label: 'EV/EBITDA',      tooltip: 'ערך חברה ביחס לרווח תפעולי לפני הוצאות. מדד תמחור עמוק', unit: 'x' },
  { key: 'gross_margin',   label: 'Gross Margin',   tooltip: 'מרווח גולמי: אחוז הרווח לפני הוצאות תפעוליות', unit: '%' },
  { key: 'operating_margin', label: 'Operating Margin', tooltip: 'מרווח תפעולי: רווחיות מהפעילות העסקית הליבתית', unit: '%' },
  { key: 'beta',           label: 'Beta',           tooltip: 'בטא: תנודתיות המנייה ביחס לשוק הכללי. >1 = תנודתי יותר', unit: '' },
  { key: 'week52_high',    label: '52W High',       tooltip: 'טווח 52 שבועות: המחיר הגבוה בשנה האחרונה', unit: '' },
  { key: 'week52_low',     label: '52W Low',        tooltip: 'טווח 52 שבועות: המחיר הנמוך בשנה האחרונה', unit: '' },
];

const INVESTOR_KEYS = ['buffett', 'munger', 'graham', 'lynch', 'greenblatt', 'fisher'];

const AGENT_KEYS = ['company', 'management', 'financial', 'growth', 'market'];

const STEPS_LABELS = [
  'אוסף נתוני שוק',
  'מנתח ביצועים פיננסיים',
  'בוחן מודל עסקי',
  'מעריך איכות ניהול',
  'בודק פוטנציאל צמיחה',
  'מחשב ציוני משקיעים',
  'מרכיב דוח סופי',
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function RecommendationBadge({ rec }) {
  const map = {
    buy:   { label: 'קנה ✔',   cls: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50 score-glow-green' },
    wait:  { label: 'המתן ⏳',  cls: 'bg-yellow-500/20  text-yellow-300  border-yellow-500/50  score-glow-yellow' },
    avoid: { label: 'הימנע ✖', cls: 'bg-red-500/20     text-red-300     border-red-500/50     score-glow-red' },
  };
  const r = map[rec] || { label: rec, cls: 'bg-slate-700 text-slate-200 border-slate-600' };
  return (
    <div className={`inline-flex px-5 py-2 rounded-2xl text-lg font-black border ${r.cls}`}>
      {r.label}
    </div>
  );
}

function MetricCell({ meta, value }) {
  const display = value == null ? '—' : `${value}${meta.unit}`;
  return (
    <div className="flex items-center justify-between py-2.5 px-3 rounded-xl hover:bg-slate-700/30 transition-colors duration-100 group">
      <span className="text-slate-300 font-semibold text-sm">{display}</span>
      <Tooltip text={meta.tooltip}>
        <span className="text-slate-500 group-hover:text-slate-300 transition-colors text-sm font-medium flex items-center gap-1">
          {meta.label}
          <span className="text-slate-600 text-xs">ⓘ</span>
        </span>
      </Tooltip>
    </div>
  );
}

function ProgressBar({ progress, stepName }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="text-brand-400 font-medium flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-brand-400 pulse-dot inline-block" />
          {stepName}
        </span>
        <span className="text-slate-400">{Math.round(progress)}%</span>
      </div>
      <div className="h-2.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-brand-600 to-brand-400 rounded-full transition-all duration-500 ease-out relative"
          style={{ width: `${progress}%` }}
        >
          <div className="absolute inset-0 bg-white/20 animate-pulse rounded-full" />
        </div>
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function Dashboard({ disabledInvestors = new Set(), toggleInvestor = () => {}, onQuickAnalysis }) {
  const [ticker, setTicker] = useState('');
  const [market, setMarket] = useState('us');
  const [phase, setPhase] = useState('idle'); // idle | loading | done | error
  const [jobId, setJobId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [stepIndex, setStepIndex] = useState(0);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const intervalRef = useRef(null);
  const [emailSending, setEmailSending] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [emailError, setEmailError] = useState('');

  // Cleanup polling on unmount
  useEffect(() => () => clearInterval(intervalRef.current), []);

  function stopPolling() {
    clearInterval(intervalRef.current);
    intervalRef.current = null;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!ticker.trim()) return;

    setPhase('loading');
    setProgress(0);
    setStepIndex(0);
    setResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: ticker.trim().toUpperCase(), market }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? err.message ?? `שגיאת שרת ${res.status}`);
      }
      const data = await res.json();
      const id = data.job_id;
      setJobId(id);
      startPolling(id);
    } catch (err) {
      setErrorMsg(err.message);
      setPhase('error');
    }
  }

  function startPolling(id) {
    intervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/status/${id}`);
        if (!res.ok) throw new Error(`שגיאת שרת ${res.status}`);
        const data = await res.json();

        const pct = data.progress ?? 0;
        const stepIdx = Math.min(Math.floor((pct / 100) * STEPS_LABELS.length), STEPS_LABELS.length - 1);
        setProgress(pct);
        setStepIndex(stepIdx);

        if (data.status === 'done') {
          stopPolling();
          setResult(data.result ?? data);
          setPhase('done');
        } else if (data.status === 'error') {
          stopPolling();
          setErrorMsg(data.error ?? 'אירעה שגיאה בניתוח');
          setPhase('error');
        }
      } catch (err) {
        stopPolling();
        setErrorMsg(err.message);
        setPhase('error');
      }
    }, 2000);
  }

  function resetForm() {
    setPhase('idle');
    setTicker('');
    setProgress(0);
    setStepIndex(0);
    setResult(null);
    setErrorMsg('');
    setJobId(null);
    setEmailSending(false);
    setEmailSent(false);
    setEmailError('');
  }

  async function handleSendEmail() {
    if (!jobId || emailSending) return;
    setEmailSending(true);
    setEmailSent(false);
    setEmailError('');
    try {
      const res = await fetch('/send-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? err.message ?? `שגיאת שרת ${res.status}`);
      }
      setEmailSent(true);
      setTimeout(() => setEmailSent(false), 3000);
    } catch (err) {
      setEmailError(err.message);
      setTimeout(() => setEmailError(''), 5000);
    } finally {
      setEmailSending(false);
    }
  }

  // ── Effective composite (recalculated based on enabled investors) ──────────
  const enabledVals = result
    ? INVESTOR_KEYS.filter(k => !disabledInvestors.has(k)).map(k => result.investor_scores?.[k]).filter(v => v != null)
    : [];
  const effectiveComposite = enabledVals.length > 0
    ? Math.round(enabledVals.reduce((a, b) => a + b, 0) / enabledVals.length * 10) / 10
    : null;
  const effectiveRec = effectiveComposite == null ? 'wait'
    : effectiveComposite >= 70 ? 'buy'
    : effectiveComposite >= 50 ? 'wait' : 'avoid';
  const activeCount = INVESTOR_KEYS.length - disabledInvestors.size;
  const isFiltered = disabledInvestors.size > 0;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-8">
      {/* ── Input Form ── */}
      <section>
        <div className="rounded-2xl border border-slate-700/50 bg-slate-800/50 backdrop-blur-sm p-6 shadow-xl">
          <div className="mb-5">
            <h1 className="text-2xl font-black text-white">ניתוח מנייה עם נחמיה</h1>
            <p className="text-slate-400 text-sm mt-1">
              הזן סימבול מנייה וקבל ניתוח ערך מעמיק על ידי 6 מודלי משקיעים
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
            {/* Ticker input */}
            <div className="flex-1 min-w-0">
              <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">
                סימבול מנייה
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="AAPL / TSLA / NICE.TA"
                disabled={phase === 'loading'}
                className="w-full bg-slate-900 border border-slate-600 text-white placeholder-slate-500
                           rounded-xl px-4 py-3 text-lg font-bold tracking-widest uppercase
                           focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
                           disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                dir="ltr"
              />
            </div>

            {/* Market toggle */}
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">
                שוק
              </label>
              <div className="flex rounded-xl border border-slate-600 overflow-hidden bg-slate-900">
                <button
                  type="button"
                  onClick={() => setMarket('us')}
                  disabled={phase === 'loading'}
                  className={`px-5 py-3 text-sm font-semibold transition-all duration-200 ${
                    market === 'us'
                      ? 'bg-brand-600 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-slate-700'
                  }`}
                >
                  🇺🇸 US
                </button>
                <button
                  type="button"
                  onClick={() => setMarket('israel')}
                  disabled={phase === 'loading'}
                  className={`px-5 py-3 text-sm font-semibold transition-all duration-200 ${
                    market === 'israel'
                      ? 'bg-brand-600 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-slate-700'
                  }`}
                >
                  🇮🇱 ישראל
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={phase === 'loading' || !ticker.trim()}
              className="px-7 py-3 bg-brand-600 hover:bg-brand-500 active:bg-brand-700 text-white rounded-xl
                         font-bold text-base transition-all duration-200 disabled:opacity-50
                         disabled:cursor-not-allowed shadow-lg shadow-brand-500/25 whitespace-nowrap
                         flex items-center gap-2 min-w-[140px] justify-center"
            >
              {phase === 'loading' ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  מנתח...
                </>
              ) : (
                <>📊 נתח מנייה</>
              )}
            </button>
          </form>
        </div>
      </section>

      {/* ── Error ── */}
      {phase === 'error' && (
        <div className="rounded-2xl bg-red-500/10 border border-red-500/30 p-5 flex items-start gap-4">
          <div className="text-3xl shrink-0">⚠</div>
          <div className="flex-1">
            <h3 className="font-bold text-red-300 mb-1">שגיאה בניתוח</h3>
            <p className="text-red-400/80 text-sm">{errorMsg}</p>
          </div>
          <button
            onClick={resetForm}
            className="text-xs text-slate-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-700 shrink-0"
          >
            נסה שוב
          </button>
        </div>
      )}

      {/* ── Loading / Progress ── */}
      {phase === 'loading' && (
        <div className="rounded-2xl border border-brand-500/30 bg-slate-800/60 p-8 shadow-xl shadow-brand-500/10">
          <div className="max-w-lg mx-auto space-y-6">
            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-brand-600/20 border border-brand-500/30 flex items-center justify-center text-4xl mx-auto mb-4 animate-pulse">
                🔍
              </div>
              <h2 className="text-xl font-bold text-white mb-1">נחמיה מנתח את {ticker}…</h2>
              <p className="text-slate-400 text-sm">6 מודלי משקיעים עובדים במקביל</p>
            </div>
            <ProgressBar progress={progress} stepName={STEPS_LABELS[stepIndex]} />
            <div className="grid grid-cols-3 gap-2">
              {INVESTOR_KEYS.map((k) => {
                const icons = { buffett: '🏦', munger: '🧠', graham: '📊', lynch: '🦁', greenblatt: '⚡', fisher: '🔬' };
                const isActive = stepIndex >= INVESTOR_KEYS.indexOf(k) + 1;
                return (
                  <div
                    key={k}
                    className={`rounded-xl p-2.5 text-center text-xs font-medium transition-all duration-500 border ${
                      isActive
                        ? 'bg-brand-600/20 border-brand-500/40 text-brand-300'
                        : 'bg-slate-700/20 border-slate-700/40 text-slate-500'
                    }`}
                  >
                    <div className="text-xl mb-1">{icons[k]}</div>
                    <div>{k.charAt(0).toUpperCase() + k.slice(1)}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Results ── */}
      {phase === 'done' && result && (
        <div className="space-y-8">
          {/* Reset button + Email button */}
          <div className="flex justify-between items-center flex-wrap gap-3">
            <h2 className="text-xl font-bold text-white">תוצאות ניתוח</h2>
            <div className="flex items-center gap-2">
              {/* Email send button */}
              <div className="relative">
                <button
                  onClick={handleSendEmail}
                  disabled={emailSending || emailSent}
                  className={`text-sm transition-colors px-4 py-2 rounded-xl flex items-center gap-2 border ${
                    emailSent
                      ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 cursor-default'
                      : emailError
                      ? 'bg-red-500/20 border-red-500/40 text-red-300'
                      : 'text-slate-400 hover:text-white border-slate-700 hover:border-slate-500 hover:bg-slate-700'
                  } disabled:cursor-not-allowed`}
                >
                  {emailSending ? (
                    <>
                      <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      שולח...
                    </>
                  ) : emailSent ? (
                    <>✓ נשלח!</>
                  ) : (
                    <>שלח במייל 📧</>
                  )}
                </button>
                {emailError && (
                  <div className="absolute top-full mt-1.5 left-0 bg-red-900/90 border border-red-500/50 text-red-200 text-xs rounded-lg px-3 py-2 whitespace-nowrap z-10 shadow-xl">
                    ⚠ {emailError}
                  </div>
                )}
              </div>
              {onQuickAnalysis && (
                <button
                  onClick={() => onQuickAnalysis(result?.ticker, result?.market?.toLowerCase() || 'us')}
                  className="text-sm text-teal-400 hover:text-white transition-colors px-4 py-2 rounded-xl hover:bg-teal-700/30 flex items-center gap-2 border border-teal-700/50 hover:border-teal-500"
                >
                  📱 ניתוח מהיר
                </button>
              )}
              <button
                onClick={resetForm}
                className="text-sm text-slate-400 hover:text-white transition-colors px-4 py-2 rounded-xl hover:bg-slate-700 flex items-center gap-2 border border-transparent"
              >
                ↩ ניתוח חדש
              </button>
            </div>
          </div>

          {/* Top section: Score + Info */}
          <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Gauge */}
            <div className="md:col-span-1 flex flex-col items-center justify-center rounded-2xl border border-slate-700/50 bg-slate-800/50 p-8 gap-4">
              <Gauge score={effectiveComposite ?? 0} size={180} label="ציון מורכב" thickness={14} />
              <RecommendationBadge rec={effectiveRec} />
              {isFiltered && (
                <div className="text-center">
                  {activeCount > 0 ? (
                    <span className="text-xs text-slate-500 bg-slate-700/50 border border-slate-600/50 rounded-full px-3 py-1">
                      מחושב מ-{activeCount}/6 משקיעים
                    </span>
                  ) : (
                    <span className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-full px-3 py-1">
                      נא לאפשר לפחות משקיע אחד
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Stock info */}
            <div className="md:col-span-2 rounded-2xl border border-slate-700/50 bg-slate-800/50 p-6 space-y-4">
              <div>
                <div className="text-slate-400 text-xs uppercase tracking-wide font-semibold mb-1">חברה</div>
                <h2 className="text-3xl font-black text-white">{result.company_name ?? result.ticker}</h2>
                <div className="flex flex-wrap items-center gap-3 mt-2">
                  <span className="px-3 py-1 rounded-lg bg-brand-600/20 border border-brand-500/30 text-brand-300 text-sm font-bold tracking-widest" dir="ltr">
                    {result.ticker}
                  </span>
                  <span className="text-slate-500 text-sm">
                    {result.market === 'IL' || result.market === 'israel' ? '🇮🇱 בורסת תל אביב' : '🇺🇸 NYSE / NASDAQ'}
                  </span>
                  {result.sector && (
                    <span className="text-slate-500 text-sm">· {result.sector}</span>
                  )}
                  {/* External links */}
                  {(() => {
                    const isIL = result.market === 'IL' || result.market === 'israel';
                    const yTicker = isIL ? `${result.ticker}.TA` : result.ticker;
                    const yahooUrl = `https://finance.yahoo.com/quote/${yTicker}/`;
                    const googleUrl = `https://www.google.com/finance/quote/${result.ticker}${isIL ? ':TLV' : ''}`;
                    return (
                      <span className="flex items-center gap-2 mr-auto">
                        <a href={yahooUrl} target="_blank" rel="noopener noreferrer"
                           className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-purple-600/20 border border-purple-500/30 text-purple-300 hover:bg-purple-600/30 transition-colors text-xs font-semibold">
                          📈 Yahoo Finance
                        </a>
                        <a href={googleUrl} target="_blank" rel="noopener noreferrer"
                           className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-300 hover:bg-blue-600/30 transition-colors text-xs font-semibold">
                          🔍 Google Finance
                        </a>
                      </span>
                    );
                  })()}
                </div>
              </div>

              {/* Quick stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                {[
                  { label: 'מחיר', value: result.current_price != null ? `$${result.current_price}` : '—' },
                  { label: 'שווי שוק', value: result.market_cap ?? '—' },
                  { label: 'ענף', value: result.industry ?? '—' },
                  { label: 'תאריך', value: result.analysis_date ?? new Date().toLocaleDateString('he-IL') },
                ].map(({ label, value }) => (
                  <div key={label} className="rounded-xl bg-slate-700/30 border border-slate-700/50 p-3">
                    <div className="text-slate-500 text-xs">{label}</div>
                    <div className="text-white font-semibold text-sm mt-0.5 truncate">{value}</div>
                  </div>
                ))}
              </div>

              {/* Investor score bar overview */}
              {result.investor_scores && (
                <div className="pt-2">
                  <div className="text-slate-400 text-xs uppercase tracking-wide font-semibold mb-2">ציוני משקיעים</div>
                  <div className="flex gap-2 flex-wrap">
                    {INVESTOR_KEYS.map((k) => {
                      const s = result.investor_scores[k] ?? 0;
                      const color = s >= 70 ? 'bg-emerald-500' : s >= 50 ? 'bg-yellow-500' : 'bg-red-500';
                      return (
                        <div key={k} className="flex items-center gap-1.5 bg-slate-700/30 rounded-lg px-2.5 py-1.5">
                          <div className={`w-2 h-2 rounded-full ${color}`} />
                          <span className="text-slate-400 text-xs capitalize">{k}</span>
                          <span className="text-white text-xs font-bold">{s}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Investor Profile Cards 3x2 */}
          {result.investor_scores && (
            <section>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <span>🎓</span>
                <span>פרופילי משקיעים</span>
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {INVESTOR_KEYS.map((k) => (
                  <InvestorCard
                    key={k}
                    investorKey={k}
                    score={result.investor_scores[k] ?? 0}
                    note={result.investor_notes?.[k]}
                    disabled={disabledInvestors.has(k)}
                    onToggle={() => toggleInvestor(k)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Agent Report Panels */}
          {result.agent_reports && (
            <section>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <span>🤖</span>
                <span>דוחות סוכנים</span>
              </h3>
              <div className="space-y-3">
                {AGENT_KEYS.map((k, i) => (
                  <AgentPanel
                    key={k}
                    agentKey={k}
                    data={result.agent_reports[k]}
                    defaultOpen={i === 0}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Financial Data Table */}
          {result.metrics && (
            <section>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <span>📋</span>
                <span>נתונים פיננסיים</span>
                <span className="text-xs text-slate-500 font-normal mr-auto">רחף על שם המדד לפרטים</span>
              </h3>
              <div className="rounded-2xl border border-slate-700/50 bg-slate-800/40 p-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-1 divide-y sm:divide-y-0 divide-slate-700/30">
                  {METRICS_META.map((meta) => (
                    <MetricCell key={meta.key} meta={meta} value={result.metrics[meta.key]} />
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* Summary / Thesis */}
          {result.investment_thesis && (
            <section>
              <div className="rounded-2xl border border-brand-500/30 bg-brand-600/10 p-6">
                <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
                  <span>💡</span>
                  <span>תזת ההשקעה</span>
                </h3>
                <p className="text-slate-300 leading-relaxed">{result.investment_thesis}</p>
              </div>
            </section>
          )}

          {/* Disclaimer */}
          <div className="rounded-xl bg-slate-800/30 border border-slate-700/30 px-5 py-3 text-xs text-slate-500 text-center">
            ⚠ נחמיה הוא כלי AI לצרכי מידע בלבד. אין לראות בניתוח המלצת השקעה. תמיד התייעץ עם יועץ פיננסי מוסמך.
          </div>
        </div>
      )}

      {/* ── Idle state ── */}
      {phase === 'idle' && (
        <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-800/20 p-12 text-center">
          <div className="text-5xl mb-4">📈</div>
          <h3 className="text-xl font-bold text-slate-300 mb-2">נחמיה מוכן לניתוח</h3>
          <p className="text-slate-500 text-sm max-w-md mx-auto">
            הזן סימבול מנייה למעלה וקבל ניתוח ערך מעמיק הכולל ציוני 6 משקיעים אגדיים, 5 דוחות סוכנים, ונתונים פיננסיים עם הסברים.
          </p>
          <div className="flex items-center justify-center gap-6 mt-8 flex-wrap">
            {['🏦 Buffett', '🧠 Munger', '📊 Graham', '🦁 Lynch', '⚡ Greenblatt', '🔬 Fisher'].map((label) => (
              <div key={label} className="text-sm text-slate-500 flex items-center gap-1">
                {label}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
