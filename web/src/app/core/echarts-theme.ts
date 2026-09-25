/** ECharts theme in the caabi.dev palette; registered once in app.config.ts and used by every chart. */
export const CAABI_THEME = {
  color: ['#c9a233', '#8b1a2b', '#4caf7d', '#6f8fd6', '#d9534f', '#888888'],
  backgroundColor: 'transparent',
  textStyle: { color: '#e0e0e0', fontFamily: '"Segoe UI", system-ui, -apple-system, sans-serif' },
  title: { textStyle: { color: '#ffffff' }, subtextStyle: { color: '#888888' } },
  legend: { textStyle: { color: '#888888' } },
  tooltip: { backgroundColor: '#161616', borderColor: '#2a2a2a', textStyle: { color: '#e0e0e0' } },
  categoryAxis: { axisLine: { lineStyle: { color: '#2a2a2a' } }, axisLabel: { color: '#888888' }, splitLine: { show: false } },
  valueAxis: { axisLine: { show: false }, axisLabel: { color: '#888888' }, splitLine: { lineStyle: { color: '#1a1a1a' } } },
};
