export function render(d) {
  const r = d.risk_analysis;
  const flags = r.warning_flags || [];

  const riskColor = r.score >= 7 ? 'var(--red)'
                  : r.score >= 4 ? 'var(--warn)'
                  : 'var(--green)';

  const riskLabel = r.score >= 7 ? '고위험' : r.score >= 4 ? '중위험' : '저위험';

  const rows = [
    ['변동성',       r.volatility_risk         ],
    ['이격 과대',    r.overextension_risk       ],
    ['이벤트/뉴스',  r.event_risk               ],
    ['유동성',       r.liquidity_risk           ],
    ['돌파실패 위험', r.breakout_failure_risk   ],
  ].map(([lbl, val]) => `
    <div style="display:flex;justify-content:space-between;font-size:12px;padding:6px 0;border-bottom:1px solid var(--border-soft)">
      <span style="color:var(--text-3)">${lbl}</span>
      <span style="color:var(--text-1);font-family:var(--mono);font-size:11px;text-align:right;max-width:70%">${val || '—'}</span>
    </div>`).join('');

  return `
  <div class="card">
    <div class="card-title">리스크 분석
      <span class="tag mono" style="color:${riskColor}">${riskLabel} ${r.score.toFixed(1)} / 10</span>
    </div>
    ${flags.length ? `<div class="flag-list">${flags.map(f => `<span class="flag">${f}</span>`).join('')}</div>` : ''}
    <div>${rows}</div>
    <div class="note">${r.comment}</div>
  </div>`;
}
