import { api } from '../services/apiClient.js';

const QUICK_CHIPS = ['샘플반도체', '샘플바이오', '샘플2차전지', '샘플조선', '샘플AI'];

let _debounce = null;

export function mount(container, { onAnalyze, onLoading }) {
  container.innerHTML = `
    <div class="search-wrap">
      <div style="flex:1; display:flex; flex-direction:column; gap:8px;">
        <div style="display:flex; gap:12px;">
          <input id="q" class="search-input" type="text"
            placeholder="종목명 입력 (예: 삼성전자, 샘플반도체)"
            autocomplete="off" spellcheck="false" />
          <button id="go-btn" class="search-btn">분석 시작</button>
        </div>
        <div id="suggestions" class="suggestions"></div>
        <div class="quick-chips" id="chips"></div>
      </div>
    </div>`;

  const input   = container.querySelector('#q');
  const btn     = container.querySelector('#go-btn');
  const sugEl   = container.querySelector('#suggestions');
  const chipsEl = container.querySelector('#chips');

  // Quick chips
  chipsEl.innerHTML = QUICK_CHIPS.map(
    c => `<button class="quick-chip" data-q="${c}">${c}</button>`
  ).join('');
  chipsEl.addEventListener('click', e => {
    const q = e.target.dataset.q;
    if (q) { input.value = q; run(q); }
  });

  // Autocomplete
  input.addEventListener('input', () => {
    clearTimeout(_debounce);
    const q = input.value.trim();
    if (!q) { sugEl.innerHTML = ''; return; }
    _debounce = setTimeout(() => fetchSuggestions(q), 200);
  });

  // Dismiss suggestions on outside click
  document.addEventListener('click', e => {
    if (!container.contains(e.target)) sugEl.innerHTML = '';
  });

  // Submit
  btn.addEventListener('click', () => run(input.value.trim()));
  input.addEventListener('keydown', e => { if (e.key === 'Enter') run(input.value.trim()); });

  async function fetchSuggestions(q) {
    try {
      const data = await api.lookup(q);
      if (!data.candidates?.length) { sugEl.innerHTML = ''; return; }
      sugEl.innerHTML = `<div class="suggestions-list">${
        data.candidates.map(c => `
          <div class="suggestion-item" data-ticker="${c.ticker}" data-name="${c.name}">
            <span class="suggestion-name">${c.name}</span>
            <span class="suggestion-meta">${c.ticker} · ${c.market}</span>
          </div>`).join('')
      }</div>`;
      sugEl.querySelectorAll('.suggestion-item').forEach(el => {
        el.addEventListener('click', () => {
          input.value = el.dataset.name;
          sugEl.innerHTML = '';
          run(el.dataset.name);
        });
      });
    } catch (_) { sugEl.innerHTML = ''; }
  }

  async function run(q) {
    if (!q) return;
    sugEl.innerHTML = '';
    btn.disabled = true;
    btn.textContent = '분석 중…';
    onLoading(true);
    try {
      const data = await api.analyze(q);
      onAnalyze(data);
    } catch (err) {
      onAnalyze(null, err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = '분석 시작';
      onLoading(false);
    }
  }
}
