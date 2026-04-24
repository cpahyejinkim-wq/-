import * as SearchBar        from './components/SearchBar.js';
import * as SummaryCard       from './components/SummaryCard.js';
import * as ScoreBreakdown    from './components/ScoreBreakdown.js';
import * as StageFlowCard     from './components/StageFlowCard.js';
import * as MultiTimeframe    from './components/MultiTimeframePanel.js';
import * as TradePlanCard     from './components/TradePlanCard.js';
import * as PatternPanel      from './components/PatternPanel.js';
import * as ThemeStrengthCard from './components/ThemeStrengthCard.js';
import * as RiskPanel         from './components/RiskPanel.js';
import * as NewsPanel         from './components/NewsPanel.js';

// ---- DOM refs (populated in mount) ----
let els = {};

export function mount() {
  els = {
    search:    document.getElementById('search-mount'),
    summary:   document.getElementById('summary-mount'),
    breakdown: document.getElementById('breakdown-mount'),
    stage:     document.getElementById('stage-mount'),
    tf:        document.getElementById('tf-mount'),
    trade:     document.getElementById('trade-mount'),
    pattern:   document.getElementById('pattern-mount'),
    theme:     document.getElementById('theme-mount'),
    risk:      document.getElementById('risk-mount'),
    news:      document.getElementById('news-mount'),
    results:   document.getElementById('results'),
    empty:     document.getElementById('empty'),
    loading:   document.getElementById('loading'),
    error:     document.getElementById('error'),
  };

  SearchBar.mount(els.search, {
    onLoading: setLoading,
    onAnalyze: handleAnalysis,
  });

  showEmpty();
}

function setLoading(on) {
  setVisible(els.loading, on);
  if (on) {
    setVisible(els.results, false);
    setVisible(els.empty,   false);
    setVisible(els.error,   false);
  }
}

function showEmpty() {
  setVisible(els.empty,   true);
  setVisible(els.results, false);
  setVisible(els.loading, false);
  setVisible(els.error,   false);
}

function handleAnalysis(data, errMsg) {
  setVisible(els.loading, false);

  if (!data || errMsg) {
    els.error.textContent = errMsg || '분석에 실패했습니다. 다시 시도해주세요.';
    setVisible(els.error,   true);
    setVisible(els.results, false);
    setVisible(els.empty,   false);
    return;
  }

  renderAll(data);
  setVisible(els.results, true);
  setVisible(els.empty,   false);
  setVisible(els.error,   false);
  els.results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderAll(data) {
  els.summary.innerHTML   = SummaryCard.render(data);
  els.breakdown.innerHTML = ScoreBreakdown.render(data);
  els.stage.innerHTML     = StageFlowCard.render(data);
  els.tf.innerHTML        = MultiTimeframe.render(data);
  els.trade.innerHTML     = TradePlanCard.render(data);
  els.pattern.innerHTML   = PatternPanel.render(data);
  els.theme.innerHTML     = ThemeStrengthCard.render(data);
  els.risk.innerHTML      = RiskPanel.render(data);
  els.news.innerHTML      = NewsPanel.render(data);
}

function setVisible(el, on) {
  if (!el) return;
  el.style.display = on ? '' : 'none';
}
