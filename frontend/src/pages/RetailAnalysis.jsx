import React, { useState, useEffect } from 'react';

const REC_STYLES = {
  buy:     { bg: 'bg-emerald-500/20', border: 'border-emerald-500/50', text: 'text-emerald-300', label: 'קנה ✔' },
  consider:{ bg: 'bg-teal-500/20',   border: 'border-teal-500/50',    text: 'text-teal-300',    label: 'שקול לקנות' },
  wait:    { bg: 'bg-yellow-500/20', border: 'border-yellow-500/50',  text: 'text-yellow-300',  label: 'המתן ⏳' },
  avoid:   { bg: 'bg-red-500/20',    border: 'border-red-500/50',     text: 'text-red-300',     label: 'הימנע ✖' },
};

const HEALTH_COLOR = s => s >= 70 ? 'text-emerald-400' : s >= 45 ? 'text-yellow-400' : 'text-red-400';
const VAL_COLOR    = s => s >= 70 ? 'text-emerald-400' : s >= 45 ? 'text-yellow-400' : 'text-red-400';

function Stars({ count }) {
  return (
    <div className="flex gap-0.5">
      {[1,2,3,4,5].map(i => (
        <span key={i} className={`text-2xl ${i <= count ? 'text-yellow-400' : 'text-slate-700'}`}>★</span>
      ))}
    </div>
  );
}

function SectionCard({ title, icon, children, className }) {
  return (
    <div className={`bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5 ${className || ''}`}>
      <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
        <span>{icon}</span>{title}
      </h3>
      {children}
    </div>
  );
}

function Pill({ text, color }) {
  const colors = {
    green:  'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    yellow: 'bg-yellow-500/20  text-yellow-300  border-yellow-500/40',
    red:    'bg-red-500/20     text-red-300     border-red-500/40',
    slate:  'bg-slate-700/50   text-slate-300   border-slate-600/40',
    teal:   'bg-teal-500/20    text-teal-300    border-teal-500/40',
  };
  return (
    <span className={`inline-flex px-3 py-1 rounded-full text-sm font-semibold border ${colors[color||'slate']}`}>
      {text}
    </span>
  );
}

const STEPS = ['אוסף נתוני שוק', 'מנתח נתונים פיננסיים', 'מפיק המלצה למשקיע'];

export default function RetailAnalysis({ initialTicker, initialMarket, onBack }) {
  const [ticker, setTicker]     = useState(initialTicker || '');
  const [market, setMarket]     = useState(initialMarket || 'us');
  const [phase, setPhase]       = useState(initialTicker ? 'auto' : 'idle');
  const [jobId, setJobId]       = useState(null);
  const [progress, setProgress] = useState(0);
  const [stepIdx, setStepIdx]   = useState(0);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState('');

  useEffect(() => {
    if (phase === 'auto' && initialTicker) startAnalysis(initialTicker, initialMarket || 'us');
  }, []);

  useEffect(() => {
    if (!jobId || phase !== 'loading') return;
    const iv = setInterval(async () => {
      try {
        const r = await fetch('/retail-status/' + jobId);
        const d = await r.json();
        setProgress(d.progress || 0);
        setStepIdx(d.progress < 30 ? 0 : d.progress < 70 ? 1 : 2);
        if (d.status === 'done') {
          clearInterval(iv);
          setResult(d.result);
          setPhase('done');
        } else if (d.status === 'error') {
          clearInterval(iv);
          setError(d.error || 'שגיאה לא ידועה');
          setPhase('error');
        }
      } catch(e) { /* keep polling */ }
    }, 1200);
    return () => clearInterval(iv);
  }, [jobId, phase]);

  async function startAnalysis(t, m) {
    const tk = (t || ticker).trim().toUpperCase();
    const mk = (m || market).toUpperCase();
    if (!tk) return;
    setError(''); setResult(null); setProgress(0); setStepIdx(0);
    setPhase('loading');
    try {
      const r = await fetch('/retail-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: tk, market: mk }),
      });
      const d = await r.json();
      if (d.job_id) setJobId(d.job_id);
      else throw new Error('No job_id');
    } catch(e) {
      setError(e.message); setPhase('error');
    }
  }

  const rec = result?.verdict?.recommendation_en || 'wait';
  const recStyle = REC_STYLES[rec] || REC_STYLES.wait;
  const hs = result?.health?.health_score || 50;
  const vs = result?.valuation?.valuation_score || 50;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-black text-white flex items-center gap-2">
            <span>📱</span> ניתוח מהיר למשקיע
          </h1>
          <p className="text-slate-400 text-sm mt-1">ניתוח פשוט ואקציונבלי — כדאי לקנות?</p>
        </div>
        {onBack && (
          <button onClick={onBack} className="text-sm text-slate-400 hover:text-white px-4 py-2 rounded-xl hover:bg-slate-700 border border-transparent flex items-center gap-2 transition-colors">
            ← חזור לניתוח מלא
          </button>
        )}
      </div>

      <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[160px]">
            <label className="block text-xs text-slate-400 mb-1.5 font-medium">טיקר מנייה</label>
            <input
              value={ticker}
              onChange={e => setTicker(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === 'Enter' && startAnalysis()}
              placeholder="AAPL / TEVA / NICE"
              className="w-full bg-slate-900 border border-slate-600 rounded-xl px-4 py-2.5 text-white text-lg font-bold placeholder-slate-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/40"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1.5 font-medium">שוק</label>
            <div className="flex rounded-xl overflow-hidden border border-slate-600">
              {['us','il'].map(m => (
                <button key={m} onClick={() => setMarket(m)}
                  className={`px-5 py-2.5 text-sm font-bold transition-colors ${market===m ? 'bg-brand-600 text-white' : 'bg-slate-900 text-slate-400 hover:text-white'}`}>
                  {m === 'us' ? '🇺🇸 US' : '🇮🇱 IL'}
                </button>
              ))}
            </div>
          </div>
          <button onClick={() => startAnalysis()} disabled={!ticker.trim() || phase==='loading'}
            className="px-6 py-2.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white font-bold rounded-xl transition-colors flex items-center gap-2">
            {phase === 'loading' ? (
              <><svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>מנתח...</>
            ) : 'נתח ▶'}
          </button>
        </div>
      </div>

      {phase === 'loading' && (
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-8 text-center space-y-5">
          <div className="text-4xl animate-pulse">🔍</div>
          <p className="text-brand-400 font-semibold text-lg">{STEPS[stepIdx]}</p>
          <div className="max-w-sm mx-auto space-y-2">
            <div className="flex justify-between text-xs text-slate-500"><span>התקדמות</span><span>{progress}%</span></div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-brand-600 to-brand-400 rounded-full transition-all duration-700" style={{width:`${progress}%`}}/>
            </div>
          </div>
          <p className="text-slate-500 text-sm">עד 30 שניות...</p>
        </div>
      )}

      {phase === 'error' && (
        <div className="bg-red-900/20 border border-red-500/40 rounded-2xl p-6 text-center space-y-3">
          <div className="text-3xl">⚠️</div>
          <p className="text-red-300 font-semibold">לא ניתן לנתח את {ticker}</p>
          <p className="text-red-400/70 text-sm">{error}</p>
          <button onClick={() => setPhase('idle')} className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-xl text-sm">נסה שוב</button>
        </div>
      )}

      {phase === 'done' && result && (
        <div className="space-y-4">
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-black text-white">{result.company_name || result.ticker}</h2>
                <p className="text-slate-400 text-sm mt-1">{result.company_one_liner}</p>
                <div className="flex flex-wrap gap-2 mt-3">
                  {result.sector && <Pill text={result.sector}/>}
                  {result.market === 'IL' ? <Pill text='🇮🇱 ת"א'/> : <Pill text="🇺🇸 NASDAQ/NYSE"/>}
                  {result.current_price && <Pill text={`$${result.current_price}`} color="teal"/>}
                  {result.market_cap && <Pill text={result.market_cap}/>}
                </div>
              </div>
              <div className={`px-6 py-3 rounded-2xl border text-xl font-black ${recStyle.bg} ${recStyle.border} ${recStyle.text}`}>
                {recStyle.label}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SectionCard title="בריאות פיננסית" icon="💊">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 text-sm">ציון בריאות</span>
                  <span className={`text-2xl font-black ${HEALTH_COLOR(hs)}`}>{hs}<span className="text-sm font-normal">/100</span></span>
                </div>
                <div className="h-1.5 bg-slate-700 rounded-full">
                  <div className={`h-full rounded-full ${hs>=70?'bg-emerald-500':hs>=45?'bg-yellow-500':'bg-red-500'}`} style={{width:`${hs}%`}}/>
                </div>
                <div className="grid grid-cols-1 gap-2 mt-2">
                  {[['צמיחה', result.health?.revenue_growth_verdict],['רווחיות', result.health?.profitability_verdict],['חוב', result.health?.debt_verdict]].map(([label, val]) => (
                    <div key={label} className="flex items-center justify-between py-1.5 border-b border-slate-700/50 last:border-0">
                      <span className="text-slate-400 text-sm">{label}</span>
                      <span className="text-white text-sm font-semibold">{val || '—'}</span>
                    </div>
                  ))}
                </div>
                <p className="text-slate-300 text-sm leading-relaxed mt-2">{result.health?.health_summary}</p>
              </div>
            </SectionCard>

            <SectionCard title="תמחור" icon="💰">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 text-sm">ציון תמחור</span>
                  <span className={`text-2xl font-black ${VAL_COLOR(vs)}`}>{vs}<span className="text-sm font-normal">/100</span></span>
                </div>
                <div className="h-1.5 bg-slate-700 rounded-full">
                  <div className={`h-full rounded-full ${vs>=70?'bg-emerald-500':vs>=45?'bg-yellow-500':'bg-red-500'}`} style={{width:`${vs}%`}}/>
                </div>
                <div className="mt-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 text-sm">מסקנה:</span>
                    <span className={`font-bold text-sm ${result.valuation?.verdict?.includes('זול')?'text-emerald-400':result.valuation?.verdict?.includes('הוגן')?'text-yellow-400':'text-red-400'}`}>
                      {result.valuation?.verdict}
                    </span>
                  </div>
                  <p className="text-slate-400 text-sm">{result.valuation?.pe_context}</p>
                  <p className="text-slate-300 text-sm">{result.valuation?.dcf_note}</p>
                </div>
                {result.metrics && (
                  <div className="grid grid-cols-3 gap-2 mt-3">
                    {[['P/E', result.metrics.pe!=null?result.metrics.pe?.toFixed(1):null],['P/B', result.metrics.pb!=null?result.metrics.pb?.toFixed(2):null],['ROE', result.metrics.roe!=null?`${result.metrics.roe?.toFixed(1)}%`:null]].filter(([,v])=>v).map(([label,val])=>(
                      <div key={label} className="bg-slate-700/40 rounded-xl p-2 text-center">
                        <div className="text-xs text-slate-500 mb-0.5">{label}</div>
                        <div className="text-white font-bold text-sm">{val}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </SectionCard>

            <SectionCard title="תחושת שוק" icon="📡">
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <span className={`text-lg font-black ${result.analyst_view?.sentiment==='חיובי'?'text-emerald-400':result.analyst_view?.sentiment==='שלילי'?'text-red-400':'text-yellow-400'}`}>
                    {result.analyst_view?.sentiment==='חיובי'?'📈 חיובי':result.analyst_view?.sentiment==='שלילי'?'📉 שלילי':'📊 ניטרלי'}
                  </span>
                </div>
                <p className="text-slate-300 text-sm leading-relaxed">{result.analyst_view?.reasoning}</p>
                {result.metrics?.week52_high && result.metrics?.week52_low && (
                  <div className="mt-3 bg-slate-700/40 rounded-xl p-3">
                    <div className="text-xs text-slate-500 mb-2">טווח 52 שבועות</div>
                    <div className="flex justify-between text-sm">
                      <span className="text-red-400 font-semibold">נמוך: ${result.metrics.week52_low?.toFixed(2)}</span>
                      <span className="text-emerald-400 font-semibold">גבוה: ${result.metrics.week52_high?.toFixed(2)}</span>
                    </div>
                    {result.current_price && (
                      <div className="mt-2 h-1.5 bg-slate-600 rounded-full">
                        <div className="h-full bg-brand-500 rounded-full" style={{width:`${Math.min(100,Math.max(0,((result.current_price-result.metrics.week52_low)/(result.metrics.week52_high-result.metrics.week52_low))*100))}%`}}/>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </SectionCard>

            <SectionCard title="סיכונים עיקריים" icon="⚠️">
              <div className="space-y-2.5">
                {(result.risks || []).map((risk, i) => (
                  <div key={i} className="flex gap-2.5 items-start">
                    <span className="text-red-400 mt-0.5 text-sm font-bold shrink-0">{i+1}.</span>
                    <p className="text-slate-300 text-sm leading-relaxed">{risk}</p>
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>

          <div className={`border-2 rounded-2xl p-6 ${recStyle.border} ${recStyle.bg}`}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-2">
                <h3 className="text-slate-400 text-xs font-bold uppercase tracking-widest">פסיקה סופית</h3>
                <div className="flex items-center gap-3">
                  <Stars count={result.verdict?.stars || 3}/>
                  <span className={`text-2xl font-black ${recStyle.text}`}>{result.verdict?.recommendation}</span>
                </div>
                <p className="text-white font-semibold text-base mt-1">{result.verdict?.main_reason}</p>
              </div>
              <div className="space-y-2 text-sm min-w-[200px]">
                {[['אופק השקעה', result.verdict?.investment_horizon],['מתאים ל', result.verdict?.suitable_for]].map(([label, val]) => val ? (
                  <div key={label}><span className="text-slate-500">{label}: </span><span className="text-slate-200">{val}</span></div>
                ) : null)}
              </div>
            </div>
            {result.verdict?.caution && (
              <div className="mt-4 pt-4 border-t border-white/10 flex gap-2 items-start">
                <span className="text-yellow-400 shrink-0">⚡</span>
                <p className="text-slate-300 text-sm">{result.verdict.caution}</p>
              </div>
            )}
            <p className="text-slate-600 text-xs mt-4">* אין לראות בניתוח זה המלצה פיננסית. תמיד התייעץ עם יועץ מוסמך.</p>
          </div>

          <div className="flex justify-center">
            <button onClick={() => { setPhase('idle'); setResult(null); setTicker(''); }}
              className="px-6 py-2.5 text-sm text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 hover:bg-slate-700 rounded-xl transition-colors">
              ↩ ניתוח מנייה חדשה
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
