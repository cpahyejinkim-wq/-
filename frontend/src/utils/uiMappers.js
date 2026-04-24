/** Map API values → CSS class names and Korean labels. */

export function actionClass(action) {
  const map = {
    'Strong Buy Setup': 'action-strong',
    'Buy on Pullback': 'action-buy',
    'Watch for Confirmation': 'action-watch',
    'Hold / No Immediate Entry': 'action-hold',
    'Avoid / Overheated / Weak Setup': 'action-avoid',
  };
  return map[action] ?? 'action-hold';
}

export function actionKo(action) {
  const map = {
    'Strong Buy Setup': '강력 매수 셋업',
    'Buy on Pullback': '눌림 매수',
    'Watch for Confirmation': '확인봉 대기',
    'Hold / No Immediate Entry': '관망',
    'Avoid / Overheated / Weak Setup': '진입 금지',
  };
  return map[action] ?? action;
}

export function stageBadge(stage) {
  const cls = `stage-badge stage-${encodeStageClass(stage)}`;
  return `<span class="${cls}">${stage}</span>`;
}

function encodeStageClass(stage) {
  // class names are defined in components.css
  return stage; // already Korean, CSS uses attribute selector workaround via exact match
}

export function sentimentDot(sentiment) {
  const cls = sentiment === 'positive' ? 'positive'
             : sentiment === 'negative' ? 'negative'
             : 'neutral';
  return `<span class="news-dot ${cls}"></span>`;
}

export function roleKo(role) {
  const map = { leader: '선도주', follower: '동반주', isolated: '독립상승', unknown: '미분류' };
  return map[role] ?? role;
}

export function scoreBarColor(key) {
  const map = { tech: 'tech', flow: 'flow', timeframe: 'tf', fundamental: 'fund', theme: 'theme', risk: 'risk' };
  return map[key] ?? '';
}
