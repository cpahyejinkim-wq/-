export function render(d) {
  const { technical_analysis: ta } = d;
  const patterns = ta.patterns || [];
  const subs = ta.sub_scores || {};

  const subRows = [
    ['기저 반전',   subs.base_reversal,    8 ],
    ['캔들 품질',   subs.candle_quality,   5 ],
    ['이평 구조',   subs.ma_structure,     5 ],
    ['돌파 확인',   subs.breakout_confirm, 6 ],
    ['거래량 품질', subs.volume_quality,   4 ],
    ['과열 페널티', subs.overheat_penalty, 2, true],
  ].map(([lbl, v, max, isPenalty]) => {
    if (v == null) return '';
    const pct = Math.min(100, (v / max) * 100).toFixed(1);
    const color = isPenalty ? 'var(--red)' : 'var(--gold)';
    return `
    <div class="score-row" style="grid-template-columns:120px 1fr 60px">
      <span class="label" style="font-size:11px">${lbl}</span>
      <div class="bar-wrap">
        <div class="bar-fill" style="width:${pct}%;background:${color}"></div>
      </div>
      <span class="value mono" style="font-size:11px">${(v||0).toFixed(1)}/${max}</span>
    </div>`;
  }).join('');

  const patItems = patterns.length
    ? patterns.map(p => `
      <div class="pattern-row">
        <div class="pattern-head">
          <span class="pattern-name">${p.name}</span>
          <span class="pattern-conf mono">${Math.round(p.confidence * 100)}%</span>
        </div>
        <div class="pattern-ev mono">${(p.evidence || []).join(' · ')}</div>
      </div>`).join('')
    : `<div style="color:var(--text-4);font-size:13px;padding:8px 0">감지된 패턴 없음</div>`;

  return `
  <div class="card">
    <div class="card-title">기술적 패턴 분석
      <span class="tag mono">${ta.score.toFixed(1)} / 30</span>
    </div>
    <div class="pattern-list">${patItems}</div>
    <div class="score-rows" style="margin-top:8px">${subRows}</div>
    <div class="note">${ta.comment}</div>
  </div>`;
}
