import { Component, computed, input } from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsCoreOption } from 'echarts/core';
import { DistanceBucket, DownDistanceCell } from '../../core/api.service';
import { fmtPct } from '../../core/format';

const BUCKETS: DistanceBucket[] = ['short', 'mid', 'long', 'xlong'];
const BUCKET_LABEL: Record<DistanceBucket, string> = { short: '1–3', mid: '4–6', long: '7–10', xlong: '11+' };
const DOWN_LABEL = ['1st', '2nd', '3rd'];
const THIN = 10; // cells with fewer team plays are dimmed and labelled with their n

/** Success rate by down × distance, coloured by the gap to the league; thin cells are dimmed. */
@Component({
  selector: 'app-down-distance-heatmap',
  imports: [NgxEchartsDirective],
  template: `
    <div class="panel">
      <h2>Success rate by down and distance</h2>
      <p class="muted">offense, season to date. Colour is the gap to the league rate; the label is the team's rate. Cells under {{ thin }} plays are dimmed.</p>
      @if (cells().length) {
        <div class="chart" echarts [options]="options()" theme="caabi" [autoResize]="true"></div>
        <details>
          <summary class="muted">Table view</summary>
          <table>
            <thead><tr><th>Down</th><th>Yards to go</th><th>Team</th><th>n</th><th>League</th><th>n</th></tr></thead>
            <tbody>
              @for (c of cells(); track c.down + c.bucket) {
                <tr><td>{{ downLabel(c.down) }}</td><td>{{ bucketLabel(c.bucket) }}</td><td>{{ pct(c.team_rate) }}</td><td>{{ c.team_n }}</td><td>{{ pct(c.league_rate) }}</td><td>{{ c.league_n }}</td></tr>
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
    th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) { text-align: left; }
  `,
})
export class DownDistanceHeatmap {
  readonly cells = input.required<DownDistanceCell[]>();
  readonly thin = THIN;
  readonly pct = fmtPct;
  downLabel = (d: number) => DOWN_LABEL[d - 1] ?? `${d}`;
  bucketLabel = (b: DistanceBucket) => BUCKET_LABEL[b];

  readonly options = computed<EChartsCoreOption>(() => {
    const cells = this.cells();
    const data = cells
      .filter((c) => c.team_rate != null && c.league_rate != null)
      .map((c) => ({
        value: [BUCKETS.indexOf(c.bucket), c.down - 1, (c.team_rate as number) - (c.league_rate as number)],
        cell: c,
        itemStyle: c.team_n < THIN ? { opacity: 0.35 } : undefined,
      }));
    return {
      grid: { left: 48, right: 16, top: 16, bottom: 72 },
      tooltip: {
        formatter: (p: { data: { cell: DownDistanceCell } }) => {
          const c = p.data.cell;
          return `${DOWN_LABEL[c.down - 1]} & ${BUCKET_LABEL[c.bucket]}<br/>Team ${fmtPct(c.team_rate)} (n=${c.team_n})<br/>League ${fmtPct(c.league_rate)} (n=${c.league_n})`;
        },
      },
      xAxis: { type: 'category', data: BUCKETS.map((b) => BUCKET_LABEL[b]), name: 'Yards to go', nameLocation: 'middle', nameGap: 28 },
      yAxis: { type: 'category', data: DOWN_LABEL, inverse: true },
      visualMap: {
        min: -0.25,
        max: 0.25,
        calculable: false,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        text: ['better than league', 'worse'],
        textStyle: { color: '#888888' },
        inRange: { color: ['#8b1a2b', '#3a3a3a', '#c9a233'] },
      },
      series: [
        {
          type: 'heatmap',
          data,
          label: {
            show: true,
            color: '#e0e0e0',
            formatter: (p: { data: { cell: DownDistanceCell } }) =>
              p.data.cell.team_n < THIN ? `n=${p.data.cell.team_n}` : fmtPct(p.data.cell.team_rate),
          },
          itemStyle: { borderColor: '#111111', borderWidth: 2 },
        },
      ],
    };
  });
}
