import { Component, computed, input } from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsCoreOption } from 'echarts/core';
import { TeamSeasonAggregate } from '../../core/api.service';
import { fmtEpa } from '../../core/format';

/** Every team's season-to-date offense vs defense EPA/play; the highlighted team in gold, top-right is good-good. */
@Component({
  selector: 'app-league-scatter-chart',
  imports: [NgxEchartsDirective],
  template: `
    <div class="panel">
      <h2>offense vs defense, league</h2>
      <p class="muted">Season to date, plays-weighted. Right is a better offense, up is a better defense (less EPA allowed). Lines mark the league median.</p>
      @if (teams().length) {
        <div class="chart" echarts [options]="options()" theme="caabi" [autoResize]="true"></div>
        <details>
          <summary class="muted">Table view</summary>
          <table>
            <thead><tr><th>Team</th><th>Games</th><th>Off EPA/play</th><th>Def EPA/play</th></tr></thead>
            <tbody>
              @for (t of sorted(); track t.team) {
                <tr [class.mine]="t.team === highlight()"><td>{{ t.team }}</td><td>{{ t.games }}</td><td>{{ fmt(t.off_epa_per_play) }}</td><td>{{ fmt(t.def_epa_per_play) }}</td></tr>
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
    tr.mine td { color: var(--gold); font-weight: 600; }
  `,
})
export class LeagueScatterChart {
  readonly teams = input.required<TeamSeasonAggregate[]>();
  readonly highlight = input<string>('WAS');
  readonly fmt = fmtEpa;

  readonly sorted = computed(() =>
    [...this.teams()].sort((a, b) => (b.off_epa_per_play ?? -9) - (a.off_epa_per_play ?? -9)),
  );

  readonly options = computed<EChartsCoreOption>(() => {
    const pts = this.teams().filter((t) => t.off_epa_per_play != null && t.def_epa_per_play != null);
    const mine = pts.filter((t) => t.team === this.highlight());
    const rest = pts.filter((t) => t.team !== this.highlight());
    const median = (xs: number[]) => {
      const s = [...xs].sort((a, b) => a - b);
      return s.length ? (s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : 0;
    };
    const mx = median(pts.map((t) => t.off_epa_per_play as number));
    const my = median(pts.map((t) => t.def_epa_per_play as number));
    const point = (t: TeamSeasonAggregate) => [t.off_epa_per_play, t.def_epa_per_play, t.team];
    return {
      grid: { left: 64, right: 16, top: 24, bottom: 44 },
      tooltip: {
        trigger: 'item',
        formatter: (p: { data: [number, number, string] }) => `${p.data[2]}<br/>offense ${fmtEpa(p.data[0])}<br/>defense ${fmtEpa(p.data[1])}`,
      },
      xAxis: { type: 'value', name: 'offense EPA / play →', nameLocation: 'middle', nameGap: 28, axisLabel: { formatter: (v: number) => fmtEpa(v, 2) } },
      yAxis: { type: 'value', name: '↑ less EPA allowed', nameLocation: 'middle', nameGap: 46, inverse: true, axisLabel: { formatter: (v: number) => fmtEpa(v, 2) } },
      series: [
        {
          name: 'League',
          type: 'scatter',
          data: rest.map(point),
          symbolSize: 10,
          itemStyle: { color: '#888888', borderColor: '#111111', borderWidth: 2 },
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: '#2a2a2a', type: 'solid' },
            label: { show: false },
            data: [{ xAxis: mx }, { yAxis: my }],
          },
        },
        {
          name: this.highlight(),
          type: 'scatter',
          data: mine.map(point),
          symbolSize: 14,
          itemStyle: { color: '#c9a233', borderColor: '#111111', borderWidth: 2 },
          label: { show: true, formatter: this.highlight(), position: 'top', color: '#e0e0e0' },
        },
      ],
    };
  });
}
