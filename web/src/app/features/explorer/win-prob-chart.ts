import { Component, computed, input } from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsCoreOption } from 'echarts/core';
import { WinProbPoint } from '../../core/api.service';
import { clock, fmtPct } from '../../core/format';

const REGULATION = 3600;

/** The home team's win probability through the game; quarter lines, the 50% line, and the table twin by quarter. */
@Component({
  selector: 'app-win-prob-chart',
  imports: [NgxEchartsDirective],
  template: `
    <div class="panel">
      <h2>Win probability</h2>
      <p class="muted">{{ home() }}'s chance of winning before each play (nflverse model). Above the line favours {{ home() }}, below favours {{ away() }}.</p>
      @if (points().length) {
        <div class="chart" echarts [options]="options()" theme="caabi" [autoResize]="true"></div>
        <details>
          <summary class="muted">Table view</summary>
          <table>
            <thead><tr><th>End of</th><th>{{ home() }} win %</th></tr></thead>
            <tbody>
              @for (r of rows(); track r.label) {
                <tr><td>{{ r.label }}</td><td>{{ pct(r.wp) }}</td></tr>
              }
            </tbody>
          </table>
        </details>
      } @else {
        <p class="muted">No win-probability data for this game.</p>
      }
    </div>
  `,
  styles: `
    .chart { height: 280px; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
    th, td { text-align: right; padding: 0.25rem 0.5rem; border-bottom: 1px solid var(--line); }
    th:first-child, td:first-child { text-align: left; }
  `,
})
export class WinProbChart {
  readonly points = input.required<WinProbPoint[]>();
  readonly home = input.required<string>();
  readonly away = input.required<string>();
  readonly pct = fmtPct;

  /** [seconds elapsed, home wp, qtr] — overtime keeps counting up past 3600. */
  readonly data = computed(() =>
    this.points().map((p) => {
      const qtr = p.qtr ?? 4;
      const elapsed = qtr <= 4 ? REGULATION - p.game_seconds_remaining : REGULATION + (600 - p.game_seconds_remaining);
      return [elapsed, p.home_wp, qtr] as [number, number, number];
    }),
  );

  /** The last point in each quarter, for the table twin. */
  readonly rows = computed(() => {
    const last = new Map<number, number>();
    for (const p of this.points()) last.set(p.qtr ?? 4, p.home_wp);
    return [...last.entries()].sort((a, b) => a[0] - b[0]).map(([q, wp]) => ({ label: q <= 4 ? `Q${q}` : 'OT', wp }));
  });

  readonly options = computed<EChartsCoreOption>(() => {
    const data = this.data();
    const max = Math.max(REGULATION, ...data.map((d) => d[0]));
    return {
      grid: { left: 48, right: 16, top: 16, bottom: 32 },
      tooltip: {
        trigger: 'axis',
        formatter: (ps: { data: [number, number, number] }[]) => {
          const [elapsed, wp, qtr] = ps[0].data;
          const remaining = qtr <= 4 ? REGULATION - elapsed : 600 - (elapsed - REGULATION);
          return `${clock(qtr, remaining)}<br/>${this.home()} ${fmtPct(wp)} · ${this.away()} ${fmtPct(1 - wp)}`;
        },
      },
      xAxis: {
        type: 'value',
        min: 0,
        max,
        interval: 900,
        axisLabel: { formatter: (v: number) => (v === 0 ? 'KO' : v > REGULATION ? 'OT' : `Q${v / 900}`) },
        splitLine: { show: true, lineStyle: { color: '#2a2a2a' } },
      },
      yAxis: { type: 'value', min: 0, max: 1, interval: 0.25, axisLabel: { formatter: (v: number) => fmtPct(v) } },
      series: [
        {
          name: this.home(),
          type: 'line',
          data,
          step: 'end',
          symbol: 'none',
          lineStyle: { color: '#c9a233', width: 2 },
          areaStyle: { color: '#c9a233', opacity: 0.12, origin: 0.5 },
          markLine: { silent: true, symbol: 'none', lineStyle: { color: '#888888', type: 'dashed' }, label: { show: false }, data: [{ yAxis: 0.5 }] },
        },
      ],
    };
  });
}
