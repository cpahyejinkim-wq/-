/** Thin wrapper around fetch so the base URL is one place. */

const BASE = (() => {
  // When served by FastAPI's StaticFiles the backend is on the same origin.
  // During local file:// development set BASE_URL in localStorage.
  const override = typeof localStorage !== 'undefined' && localStorage.getItem('BASE_URL');
  if (override) return override.replace(/\/$/, '');
  return '';
})();

async function request(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  health: () => request('/api/health'),

  lookup: (q) => request(`/api/lookup?q=${encodeURIComponent(q)}`),

  analyze: (query, mode = 'mock') =>
    request('/api/analyze', {
      method: 'POST',
      body: JSON.stringify({ query, market: 'KR', mode }),
    }),
};
