import { fmt } from '../utils/formatters.js';
import { actionClass, actionKo, stageBadge } from '../utils/uiMappers.js';

export function render(d) {
  const { stock, market_data: md, final_decision: fd, stage_analysis: sa } = d;
  const changeDir = md.change_pct > 0 ? 'up' : md.change_pct < 0 ? 'down' : 'flat';
  const changeSign = md.change_pct > 0 ? '+' : '';

  return `
  <div class="summary">
    <div class="summary-head">
      <h2>${stock.name}</h2>
      <div class="tick">${stock.ticker} · ${stock.market}</div>
      <div class="meta">
        ${stock.sector ? `<span class="chip">${stock.sector}</span>` : ''}
        ${stock.theme  ? `<span class="chip">${stock.theme}</span>`  : ''}
        ${stageBadge(sa.stage)}
      </div>
    </div>
    <div class="price-block">
      <div class="price-now mono">${fmt.price(md.current_price)}</div>
      <div class="price-change ${changeDir} mono">
        ${changeSign}${fmt.pct(md.change_pct)} · ${fmt.volume(md.volume)}
        <span style="color:var(--text-4)"> as of ${md.as_of}</span>
      </div>
    </div>
    <div class="action-block">
      <div class="action-label">판정</div>
      <div class="action-value ${actionClass(fd.action)}">${actionKo(fd.action)}</div>
      <div class="total-score mono">${fd.total_score}</div>
      <div class="action-summary mono" style="font-size:11px">${fd.summary}</div>
    </div>
  </div>`;
}
