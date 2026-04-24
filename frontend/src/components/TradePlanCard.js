import { fmt } from '../utils/formatters.js';

export function render(d) {
  const p = d.trade_plan;

  function cell(label, level, colorClass) {
    const hasPx = level.price != null;
    return `
    <div class="plan-cell ${hasPx ? '' : 'missing'}">
      <div class="label">${label}</div>
      <div class="price ${colorClass} mono">${hasPx ? fmt.price(level.price) : '—'}</div>
      <div class="rationale">${level.rationale}</div>
    </div>`;
  }

  const supports    = (p.support_levels    || []).slice(0, 5).map(fmt.price).join('  ');
  const resistances = (p.resistance_levels || []).slice(0, 5).map(fmt.price).join('  ');

  return `
  <div class="card">
    <div class="card-title">매매 전략 플랜
      <span class="tag">신뢰도 ${fmt.confidence(p.confidence_score)}</span>
    </div>
    <div class="one-line">${p.one_line_strategy}</div>
    <div class="plan-grid">
      ${cell('1차 매수구간', p.buy_zone_1, 'buy')}
      ${cell('2차 매수구간', p.buy_zone_2, 'buy')}
      ${cell('손절가',       p.stop_loss,  'stop')}
      ${cell('1차 목표가',  p.take_profit_1, 'tp')}
      ${cell('2차 목표가',  p.take_profit_2, 'tp')}
    </div>
    <div class="invalidation">⚠ 무효화 조건: ${p.invalidation_condition}</div>
    <div class="sizing">📐 포지션 사이징: ${p.position_sizing_note}</div>
    ${(supports || resistances) ? `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:4px">
      <div><div style="font-size:11px;color:var(--text-3);margin-bottom:4px">지지선</div>
        <div class="mono" style="font-size:12px;color:var(--down)">${supports || '—'}</div></div>
      <div><div style="font-size:11px;color:var(--text-3);margin-bottom:4px">저항선</div>
        <div class="mono" style="font-size:12px;color:var(--up)">${resistances || '—'}</div></div>
    </div>` : ''}
  </div>`;
}
