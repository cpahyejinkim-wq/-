/**
 * TradingView Lightweight Charts 기반 캔들차트
 * MA5(금), MA20(주황), MA60(보라) + 거래량 하단 패널
 */

let _chartInstance = null;
let _ro = null;

export function mount(container, data) {
  // 이전 차트 정리
  if (_ro) { _ro.disconnect(); _ro = null; }
  if (_chartInstance) { try { _chartInstance.remove(); } catch (_) {} _chartInstance = null; }
  container.innerHTML = '';

  const candles = data?.candles;
  if (!window.LightweightCharts || !candles || candles.length < 10) {
    container.innerHTML = '<div style="color:var(--text-4);padding:20px;text-align:center;font-size:12px">차트 라이브러리 로딩 중…</div>';
    return;
  }

  const chart = LightweightCharts.createChart(container, {
    layout: {
      background: { type: 'solid', color: '#0a0e14' },
      textColor: '#6e7681',
      fontSize: 11,
      fontFamily: 'JetBrains Mono, monospace',
    },
    grid: {
      vertLines: { color: '#161b22' },
      horzLines: { color: '#161b22' },
    },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: '#21262d' },
    timeScale: { borderColor: '#21262d', timeVisible: false },
    width: container.clientWidth,
    height: 360,
  });
  _chartInstance = chart;

  // ── 캔들 시리즈
  const candleSeries = chart.addCandlestickSeries({
    upColor:        '#00d395',
    downColor:      '#f04848',
    borderUpColor:  '#00d395',
    borderDownColor:'#f04848',
    wickUpColor:    '#00d395',
    wickDownColor:  '#f04848',
  });
  candleSeries.setData(candles.map(c => ({
    time: c.date, open: c.open, high: c.high, low: c.low, close: c.close,
  })));

  // ── 이동평균선 계산
  function calcMA(n) {
    const out = [];
    for (let i = n - 1; i < candles.length; i++) {
      let sum = 0;
      for (let j = i - n + 1; j <= i; j++) sum += candles[j].close;
      out.push({ time: candles[i].date, value: Math.round(sum / n * 100) / 100 });
    }
    return out;
  }

  chart.addLineSeries({ color: '#F4B942', lineWidth: 1, title: 'MA5',  lastValueVisible: false, priceLineVisible: false }).setData(calcMA(5));
  chart.addLineSeries({ color: '#FF8C42', lineWidth: 1, title: 'MA20', lastValueVisible: false, priceLineVisible: false }).setData(calcMA(20));
  chart.addLineSeries({ color: '#A78BFA', lineWidth: 1, title: 'MA60', lastValueVisible: false, priceLineVisible: false }).setData(calcMA(60));

  // ── 거래량 (하단 20%)
  const volSeries = chart.addHistogramSeries({
    priceFormat: { type: 'volume' },
    priceScaleId: 'vol',
  });
  chart.priceScale('vol').applyOptions({
    scaleMargins: { top: 0.82, bottom: 0 },
    drawTicks: false,
    borderVisible: false,
  });
  volSeries.setData(candles.map(c => ({
    time: c.date,
    value: c.volume,
    color: c.close >= c.open ? 'rgba(0,211,149,0.22)' : 'rgba(240,72,72,0.22)',
  })));

  chart.timeScale().fitContent();

  // ── 반응형 리사이즈
  _ro = new ResizeObserver(entries => {
    chart.applyOptions({ width: entries[0].contentRect.width });
  });
  _ro.observe(container);
}
