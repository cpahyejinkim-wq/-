import { scoreBarColor } from '../utils/uiMappers.js';

const BUCKETS = [
  { key: 'technical',   label: '기술적 구조',     max: 30  },
  { key: 'flow',        label: '차트 흐름 단계',   max: 20  },
  { key: 'timeframe',   label: '멀티 타임프레임',  max: 15  },
  { key: 'fundamental', label: '펀더멘털 방향성',  max: 15  },
  { key: 'theme',       label: '테마/섹터',         max: 10  },
  { key: 'risk',        label: '리스크',            max: 10, inverted: true },
];

export function render(d) {
  const { final_decision: fd } = d;
  // Reconstruct bucket totals from nested analysis objects
  const scores = {
    technical:   d.technical_analysis.score,
    flow:        d.stage_analysis.stage_score + d.stage_analysis.continuity_score,
    timeframe:   d.timeframe_analysis.alignment_score,
    fundamental: d.fundamental_analysis.score,
    theme:       d.theme_analysis.score,
    risk:        d.risk_analysis.score,
  };

  const rows = BUCKETS.map(b => {
    const v = scores[b.key] ?? 0;
    const pct = Math.min(100, (v / b.max) * 100).toFixed(1);
    const colorClass = `bar-fill ${scoreBarColor(b.key)}`;
    return `
    <div class="score-row">
      <span class="label">${b.label}</span>
      <div class="bar-wrap">
        <div class="${colorClass}" style="width:${pct}%"></div>
      </div>
      <span class="value mono">${v.toFixed(1)} / ${b.max}</span>
    </div>`;
  }).join('');

  return `
  <div class="card">
    <div class="card-title">점수 구성
      <span class="tag">총 ${fd.total_score} / 100</span>
    </div>
    <div class="score-rows">${rows}</div>
    <div class="note mono" style="font-size:11px">
      원점수 ${fd.raw_score} × 리스크게이트 ${fd.risk_multiplier}
      ${fd.overheat_penalty > 0 ? ` − 과열 ${fd.overheat_penalty}` : ''}
    </div>
  </div>`;
}
