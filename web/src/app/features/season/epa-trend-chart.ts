import { Component, computed, input } from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsCoreOption } from 'echarts/core';
import { LeagueWeek, TeamGameSummary } from '../../core/api.service';
import { fmtEpa } from '../../core/format';

/** offense and defense EPA/play by week against the league median and inter-quartile band; bye weeks stay gaps. */
@Component({
  selector: 'app-epa-trend-chart',
  imports: [NgxEchartsDirective],
  template: `
    <div class="panel">
      <h2>EPA per play by week</h2>
      <p class="muted">Gold: offense. Burgundy: defense (EPA allowed, lower is better). Grey band: league offense 25th–75th percentile.</p>
      @if (weeks().length) {
        <div class="chart" echarts [options]="options()" theme="caabi" [autoResize]="true"></div>
        <details>
          <summary class="muted">Table view</summary>
          <table>
            <thead><tr><th>Week</th><th>offense</th><th>defense</th><th>League median</th></tr></thead>
            <tbody>
              @for (r of rows(); track r.week) {
                <tr><td>{{ r.week }}</td><td>{{ fmt(r.off) }}</td><td>{{ fmt(r.def) }}</td><td>{{ fmt(r.median) }}</td></tr>
              }
            </tbody>
          </table>
        </details>
      } @else {
        <p class="muted">Not enough data yet.</p>
      }
    </div>
  `,
  styles: `
    .chart { height: 320px; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
    th, td { text-align: right; padding: 0.25rem 0.5rem; border-bottom: 1px solid var(--line); }
    th:first-child, td:first-child { text-align: left; }
  `,
})
export class EpaTrendChart {
  readonly weeks = input.required<TeamGameSummary[]>();
  readonly league = input.required<LeagueWeek[]>();
  readonly throughWeek = input<number | null>(null);
  readonly fmt = fmtEpa;

  readonly rows = computed(() => {
    const byWeek = new Map(this.weeks().map((w) => [w.week, w]));
    const leagueByWeek = new Map(this.league().map((l) => [l.week, l]));
    const last = Math.max(this.throughWeek() ?? 0, ...this.weeks().map((w) => w.week), ...this.league().map((l) => l.week));
    const rows = [];
    for (let wk = 1; wk <= last; wk++) {
      const w = byWeek.get(wk);
      const l = leagueByWeek.get(wk);
      rows.push({
        week: wk,
        off: w?.off_epa_per_play ?? null,
        def: w?.def_epa_per_play ?? null,
        median: l?.off_epa_median ?? null,
        p25: l?.off_epa_p25 ?? null,
        p75: l?.off_epa_p75 ?? null,
      });
    }
    return rows;
  });

  readonly options = computed<EChartsCoreOption>(() => {
    const rows = this.rows();
    const band = rows.map((r) => (r.p25 != null && r.p75 != null ? r.p75 - r.p25 : null));
    return {
      grid: { left: 52, right: 16, top: 36, bottom: 40 },
      tooltip: { trigger: 'axis', valueFormatter: (v: number | null) => fmtEpa(v) },
      legend: { top: 0, data: ['offense', 'defense (allowed)', 'League median'] },
      xAxis: { type: 'category', data: rows.map((r) => `Wk ${r.week}`) },
      yAxis: { type: 'value', name: 'EPA / play', axisLabel: { formatter: (v: number) => fmtEpa(v, 2) } },
      series: [
        { name: 'band-lo', type: 'line', stack: 'band', data: rows.map((r) => r.p25), lineStyle: { opacity: 0 }, symbol: 'none', silent: true, tooltip: { show: false } },
        { name: 'band', type: 'line', stack: 'band', data: band, lineStyle: { opacity: 0 }, areaStyle: { color: '#888888', opacity: 0.12 }, symbol: 'none', silent: true, tooltip: { show: false } },
        { name: 'League median', type: 'line', data: rows.map((r) => r.median), lineStyle: { color: '#888888', width: 2 }, itemStyle: { color: '#888888' }, symbol: 'none' },
        { name: 'offense', type: 'line', data: rows.map((r) => r.off), lineStyle: { color: '#c9a233', width: 2 }, itemStyle: { color: '#c9a233', borderColor: '#111111', borderWidth: 2 }, symbol: 'circle', symbolSize: 8, connectNulls: false },
        { name: 'defense (allowed)', type: 'line', data: rows.map((r) => r.def), lineStyle: { color: '#8b1a2b', width: 2 }, itemStyle: { color: '#8b1a2b', borderColor: '#111111', borderWidth: 2 }, symbol: 'circle', symbolSize: 8, connectNulls: false },
      ],
    };
  });
}
