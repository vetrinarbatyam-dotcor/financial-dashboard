import React, { useState } from 'react';
import Dashboard from './pages/Dashboard.jsx';
import History from './pages/History.jsx';
import StockDetail from './pages/StockDetail.jsx';
import Screener from './pages/Screener.jsx';
import RetailAnalysis from './pages/RetailAnalysis.jsx';

export default function App() {
  const [page, setPage] = useState('dashboard'); // 'dashboard' | 'screener' | 'history' | 'stock-detail' | 'retail'
  const [selectedTicker, setSelectedTicker] = useState('');
  const [retailTicker, setRetailTicker] = useState('');
  const [retailMarket, setRetailMarket] = useState('us');

  const [disabledInvestors, setDisabledInvestors] = useState(() => {
    try {
      const saved = localStorage.getItem('or-finance-disabled-investors');
      return new Set(saved ? JSON.parse(saved) : []);
    } catch { return new Set(); }
  });

  function toggleInvestor(key) {
    setDisabledInvestors(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      localStorage.setItem('or-finance-disabled-investors', JSON.stringify([...next]));
      return next;
    });
  }

  function goToStockDetail(ticker) {
    setSelectedTicker(ticker);
    setPage('stock-detail');
  }

  function goToHistory() {
    setPage('history');
    setSelectedTicker('');
  }

  function goToRetail(ticker, market) {
    setRetailTicker(ticker || '');
    setRetailMarket(market || 'us');
    setPage('retail');
  }

  const navBtn = (active, onClick, label) => (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
        active
          ? 'bg-brand-600 text-white shadow-lg shadow-brand-500/25'
          : 'text-slate-400 hover:text-white hover:bg-slate-700'
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100" dir="rtl">
      {/* Navbar */}
      <nav className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg">
                <span className="text-white font-black text-sm">נח</span>
              </div>
              <div>
                <div className="font-bold text-white text-lg leading-tight">נחמיה</div>
                <div className="text-xs text-slate-400 leading-tight">מערכת ניתוח מניות ערך</div>
              </div>
            </div>

            {/* Nav links */}
            <div className="flex items-center gap-1">
              {navBtn(page === 'dashboard', () => setPage('dashboard'), '📊 ניתוח')}
              {navBtn(page === 'retail', () => goToRetail(), '📱 מהיר')}
              {navBtn(page === 'screener', () => setPage('screener'), '🔭 סורק')}
              {navBtn(
                page === 'history' || page === 'stock-detail',
                goToHistory,
                '🕐 היסטוריה'
              )}
            </div>

            {/* Status badge */}
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="w-2 h-2 rounded-full bg-emerald-400 pulse-dot inline-block"></span>
              מחובר
            </div>
          </div>
        </div>
      </nav>

      {/* Page content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {page === 'dashboard' && (
          <Dashboard
            disabledInvestors={disabledInvestors}
            toggleInvestor={toggleInvestor}
            onQuickAnalysis={goToRetail}
          />
        )}
        {page === 'retail' && (
          <RetailAnalysis
            initialTicker={retailTicker}
            initialMarket={retailMarket}
            onBack={() => setPage('dashboard')}
          />
        )}
        {page === 'screener' && (
          <Screener onSelectStock={goToStockDetail} />
        )}
        {page === 'history' && (
          <History
            onAnalyze={() => setPage('dashboard')}
            onSelectStock={goToStockDetail}
            disabledInvestors={disabledInvestors}
            toggleInvestor={toggleInvestor}
          />
        )}
        {page === 'stock-detail' && (
          <StockDetail
            ticker={selectedTicker}
            onBack={goToHistory}
            disabledInvestors={disabledInvestors}
            toggleInvestor={toggleInvestor}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 mt-16 py-6 text-center text-xs text-slate-600">
        נחמיה &copy; 2025 — מערכת ניתוח מניות בינה מלאכותית. אין לראות בניתוח המערכת המלצה פיננסית.
      </footer>
    </div>
  );
}
