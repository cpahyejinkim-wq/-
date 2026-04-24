import { stageBadge } from '../utils/uiMappers.js';

const FLOW = ['관찰', 'T바닥', '포킹', '펌핑', '랠리', '역배열재매집', '재랠리', '과열'];

export function render(d) {
  const { stage_analysis: sa } = d;
  const currentIdx = FLOW.indexOf(sa.stage);

  const steps = FLOW.map((s, i) => {
    const isCurrent = s === sa.stage;
    const isPast    = i < currentIdx;
    const opacity   = isPast ? 0.35 : isCurrent ? 1 : 0.5;
    return `
    <div style="display:flex;flex-direction:column;align-items:center;gap:4px;opacity:${opacity}">
      ${isCurrent
        ? `<div style="width:10px;height:10px;border-radius:50%;background:var(--gold);box-shadow:0 0 8px var(--gold)"></div>`
        : `<div style="width:8px;height:8px;border-radius:50%;background:var(--border)"></div>`}
      <div style="font-size:10px;color:${isCurrent ? 'var(--gold)' : 'var(--text-3)'};white-space:nowrap;font-family:var(--mono)">${s}</div>
    </div>`;
  });

  // connector lines between dots
  const flow = steps.flatMap((s, i) =>
    i < steps.length - 1
      ? [s, `<div style="flex:1;height:1px;background:var(--border);margin-top:5px;min-width:10px"></div>`]
      : [s]
  );

  return `
  <div class="card">
    <div class="card-title">차트 흐름 단계
      <span class="tag">${stageBadge(sa.stage)}</span>
    </div>
    <div style="display:flex;align-items:flex-start;gap:0;overflow-x:auto;padding:4px 0">
      ${flow.join('')}
    </div>
    <dl class="kv" style="margin-top:4px">
      <dt>단계 점수</dt><dd>${sa.stage_score.toFixed(1)} / 8</dd>
      <dt>연속성 점수</dt><dd>${sa.continuity_score.toFixed(1)} / 6</dd>
    </dl>
    <div class="note">${sa.comment}</div>
  </div>`;
}
