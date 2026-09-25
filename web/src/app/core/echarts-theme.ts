/** ECharts theme in the site palette; registered once in app.config.ts and used by every ChartHost. */
export const CAABI_THEME = {
  color: ['#c9a233', '#5a1414', '#4caf7d', '#6f8fd6', '#d9534f', '#9a978f'],
  backgroundColor: 'transparent',
  textStyle: { color: '#e8e6e1', fontFamily: 'Inter, system-ui, sans-serif' },
  title: { textStyle: { color: '#e8e6e1' }, subtextStyle: { color: '#9a978f' } },
  legend: { textStyle: { color: '#9a978f' } },
  tooltip: { backgroundColor: '#181818', borderColor: '#262626', textStyle: { color: '#e8e6e1' } },
  categoryAxis: { axisLine: { lineStyle: { color: '#262626' } }, axisLabel: { color: '#9a978f' }, splitLine: { show: false } },
  valueAxis: { axisLine: { show: false }, axisLabel: { color: '#9a978f' }, splitLine: { lineStyle: { color: '#1c1c1c' } } },
};
