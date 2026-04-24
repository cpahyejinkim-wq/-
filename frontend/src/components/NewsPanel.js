import { sentimentDot } from '../utils/uiMappers.js';

export function render(d) {
  const news = d.news || [];

  const items = news.length
    ? news.map(n => `
      <div class="news-item">
        ${sentimentDot(n.sentiment)}
        <div>
          <div class="news-title">${n.url ? `<a href="${n.url}" target="_blank">${n.title}</a>` : n.title}</div>
          <div class="news-meta">${[n.source, n.published_at].filter(Boolean).join(' · ')}</div>
        </div>
      </div>`).join('')
    : `<div style="color:var(--text-4);font-size:13px;padding:6px 0">최근 뉴스 없음</div>`;

  return `
  <div class="card">
    <div class="card-title">최근 뉴스 / 촉매</div>
    <div class="news-list">${items}</div>
  </div>`;
}
