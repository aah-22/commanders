import { Component, computed, input } from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsCoreOption } from 'echarts/core';
import { Drive } from '../../core/api.service';
import { clock, fmtEpa, yardline } from '../../core/format';

const RESULT_SHORT: Record<string, string> = {
  Touchdown: 'TD',
  'Field goal': 'FG',
  'Missed field goal': 'FG ✗',
  Punt: 'Punt',
  Interception: 'INT',
  Fumble: 'FUM',
  'Turnover on downs': 'Downs',
  Safety: 'SAF',
  'End of half': 'Half',
  'End of game': 'End',
  'Opp touchdown': 'Opp TD',
};

/** Total EPA per drive, gold for the focus team and grey for the opponent, labelled with the drive result. */
@Component({
  selector: 'app-drive-chart',
  imports: [NgxEchartsDirective],
  template: `
    <div class="panel">
      <h2>Drives</h2>
      <p class="muted">Total EPA of each possession's pass and run plays. Gold is {{ team() }}. Click a bar to filter the play table to that drive.</p>
      @if (drives().length) {
        <div class="chart" echarts [options]="options()" theme="caabi" [autoResize]="true" (chartClick)="onClick($event)"></div>
        <details>
          <summary class="muted">Table view</summary>
          <div class="scroll">
            <table>
              <thead><tr><th>#</th><th>Off</th><th>Start</th><th>Ball on</th><th>Plays</th><th>Yds</th><th>EPA</th><th>Result</th><th>Pts</th></tr></thead>
              <tbody>
                @for (d of drives(); track d.drive) {
                  <tr [class.mine]="d.posteam === team()">
                    <td>{{ d.drive }}</td><td>{{ d.posteam ?? '–' }}</td><td>{{ clock(d.qtr, d.start_seconds) }}</td><td>{{ yl(d.start_yardline_100) }}</td>
                    <td>{{ d.plays }}</td><td>{{ d.yards }}</td><td>{{ epa(d.epa) }}</td><td>{{ d.result ?? '–' }}</td><td>{{ d.points ?? '–' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </details>
      } @else {
        <p class="muted">No plays ingested for this game yet.</p>
      }
    </div>
  `,
  styles: `
    .chart { height: 300px; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; white-space: nowrap; }
    th, td { text-align: right; padding: 0.25rem 0.5rem; border-bottom: 1px solid var(--line); }
    th:nth-child(-n + 4), td:nth-child(-n + 4) { text-align: left; }
    tr.mine td:nth-child(2) { color: var(--gold); font-weight: 600; }
  `,
})
export class DriveChart {
  readonly drives = input.required<Drive[]>();
  readonly team = input.required<string>();
  readonly onDrive = input<(drive: number) => void>();
  readonly clock = clock;
  readonly yl = yardline;
  readonly epa = fmtEpa;

  readonly options = computed<EChartsCoreOption>(() => {
    const ds = this.drives();
    return {
      grid: { left: 48, right: 16, top: 28, bottom: 32 },
      tooltip: {
        trigger: 'item',
        formatter: (p: { dataIndex: number }) => {
          const d = ds[p.dataIndex];
          return `Drive ${d.drive} · ${d.posteam ?? '–'} · ${clock(d.qtr, d.start_seconds)} from ${yardline(d.start_yardline_100)}<br/>${d.plays} plays, ${d.yards} yds, EPA ${fmtEpa(d.epa)}<br/>${d.result ?? ''}${d.points ? ` (+${d.points})` : ''}`;
        },
      },
      xAxis: { type: 'category', data: ds.map((d) => `${d.drive}`), name: 'Drive', nameLocation: 'middle', nameGap: 22 },
      yAxis: { type: 'value', name: 'EPA', axisLabel: { formatter: (v: number) => fmtEpa(v, 1) } },
      series: [
        {
          type: 'bar',
          data: ds.map((d) => ({
            value: d.epa ?? 0,
            itemStyle: { color: d.posteam === this.team() ? '#c9a233' : '#888888', borderColor: '#111111', borderWidth: 1 },
            label: {
              show: true,
              position: (d.epa ?? 0) >= 0 ? 'top' : 'bottom',
              color: '#e0e0e0',
              fontSize: 10,
              formatter: RESULT_SHORT[d.result ?? ''] ?? d.result ?? '',
            },
          })),
        },
      ],
    };
  });

  onClick(e: { dataIndex?: number }): void {
    const d = e.dataIndex == null ? undefined : this.drives()[e.dataIndex];
    if (d) this.onDrive()?.(d.drive);
  }
}
