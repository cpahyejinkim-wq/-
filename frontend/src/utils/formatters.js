/** Number/price formatting helpers used across all components. */

export const fmt = {
  price(v) {
    if (v == null) return '—';
    const n = Number(v);
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 10_000) return Math.round(n).toLocaleString('ko-KR') + '원';
    return Math.round(n).toLocaleString('ko-KR') + '원';
  },

  pct(v, { sign = true, decimals = 1 } = {}) {
    if (v == null) return '—';
    const n = Number(v);
    const s = sign && n > 0 ? '+' : '';
    return `${s}${n.toFixed(decimals)}%`;
  },

  score(v, max = 100) {
    if (v == null) return '—';
    return `${Number(v).toFixed(1)} / ${max}`;
  },

  volume(v) {
    if (v == null) return '—';
    const n = Number(v);
    if (n >= 100_000_000) return (n / 100_000_000).toFixed(1) + '억주';
    if (n >= 10_000) return Math.round(n / 10_000) + '만주';
    return n.toLocaleString() + '주';
  },

  confidence(v) {
    if (v == null) return '—';
    return `${Math.round(Number(v) * 100)}%`;
  },
};
