import { roleKo } from '../utils/uiMappers.js';

export function render(d) {
  const { theme_analysis: t, fundamental_analysis: f } = d;

  const peerChips = (t.peer_names || []).map(
    n => `<span class="peer-chip">${n}</span>`
  ).join('');

  const fundRows = [
    ['매출 성장',       f.revenue_trend    ],
    ['영업이익 성장',   f.op_profit_trend  ],
    ['이익 레버리지',   f.earnings_leverage],
    ['마진 추세',       f.margin_trend     ],
    ['재무 건전성',     f.debt_health      ],
    f.estimate_revision ? ['추정치 변화', f.estimate_revision] : null,
  ].filter(Boolean);

  return `
  <div class="card">
    <div class="card-title">테마 · 펀더멘털
      <span class="tag">테마 ${t.score.toFixed(1)} · 펀드 ${f.score.toFixed(1)}</span>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
      <div>
        <div style="font-size:11px;color:var(--text-3);margin-bottom:6px;letter-spacing:.1em">테마/섹터</div>
        <dl class="kv">
          <dt>섹터</dt><dd>${t.sector_name || '—'}</dd>
          <dt>테마</dt><dd>${t.theme_name || '—'}</dd>
          <dt>섹터 강도</dt><dd>${t.sector_strength}</dd>
          <dt>테마 강도</dt><dd>${t.theme_strength}</dd>
          <dt>포지션</dt><dd>${roleKo(t.role_in_theme)}</dd>
          <dt>피어 확인</dt><dd>${t.peer_confirmation}</dd>
        </dl>
        ${peerChips ? `<div class="peer-chips" style="margin-top:8px">${peerChips}</div>` : ''}
      </div>
      <div>
        <div style="font-size:11px;color:var(--text-3);margin-bottom:6px;letter-spacing:.1em">펀더멘털</div>
        <dl class="kv">
          ${fundRows.map(([k,v]) => `<dt>${k}</dt><dd style="font-size:11px">${v}</dd>`).join('')}
        </dl>
      </div>
    </div>

    <div class="note">${t.comment}</div>
    <div class="note" style="margin-top:4px">${f.comment}</div>
  </div>`;
}
