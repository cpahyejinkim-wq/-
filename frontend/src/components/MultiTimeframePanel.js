export function render(d) {
  const tf = d.timeframe_analysis;
  const frames = [
    { label: '월봉', state: tf.monthly_state },
    { label: '주봉', state: tf.weekly_state  },
    { label: '일봉', state: tf.daily_state   },
  ];

  const color = state =>
    state.includes('상승') || state.includes('베이스') || state.includes('양호') ? 'var(--green)'
    : state.includes('하락') || state.includes('역배열') || state.includes('부적합') ? 'var(--red)'
    : 'var(--gold)';

  const rows = frames.map(f => `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--border-soft)">
      <span style="color:var(--text-3);font-family:var(--mono);font-size:12px;width:36px">${f.label}</span>
      <span style="color:${color(f.state)};font-size:13px;flex:1;padding-left:12px">${f.state}</span>
    </div>`).join('');

  return `
  <div class="card">
    <div class="card-title">멀티 타임프레임
      <span class="tag mono">${tf.alignment_score.toFixed(1)} / 15</span>
    </div>
    <div>${rows}</div>
    <div class="note">${tf.comment}</div>
  </div>`;
}
