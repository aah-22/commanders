import { Component, computed, input } from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsCoreOption } from 'echarts/core';
import { NeedGroup } from '../../core/api.service';
import { fmtMoney, fmtNum, fmtPct, fmtPctile } from '../../core/format';

/** Need score per position group as horizontal bars, worst first, with the starters behind each in the table twin. */
@Component({
  selector: 'app-need-chart',
  imports: [NgxEchartsDirective],
  template: `
    <div class="panel">
      <h2>Positional need</h2>
      <p class="muted">0 is elite, signed and young; 100 is poor, expiring and old. Half the score is the starters' production percentile, a quarter each expiring deals and age past the position's peak.</p>
      @if (groups().length) {
        <div class="chart" echarts [options]="options()" theme="caabi" [autoResize]="true"></div>
        <details open>
          <summary class="muted">Starters</summary>
          <div class="scroll">
            <table>
              <thead><tr><th>Group</th><th>Need</th><th>Starter</th><th>Age</th><th>Snaps</th><th>Pctile</th><th>APY</th><th>Left</th></tr></thead>
              <tbody>
                @for (g of groups(); track g.pos_group) {
                  @for (s of g.starter_list; track s.gsis_id; let first = $first) {
                    <tr [class.lead]="first">
                      <td>{{ first ? g.pos_group : '' }}</td>
                      <td>{{ first ? num(g.need_score, 0) : '' }}</td>
                      <td>{{ s.name }} <span class="muted">{{ s.position }}</span></td>
                      <td>{{ num(s.age, 1) }}</td>
                      <td>{{ pct(s.snap_share) }}</td>
                      <td>{{ pctile(s.production_pct) }}</td>
                      <td>{{ money(s.apy) }}</td>
                      <td [class.warn]="s.years_left === 0">{{ s.years_left ?? '–' }}</td>
                    </tr>
                  }
                }
              </tbody>
            </table>
          </div>
        </details>
      } @else {
        <p class="muted">No roster data for the season yet.</p>
      }
    </div>
  `,
  styles: `
    .chart { height: 340px; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; white-space: nowrap; font-size: 0.9rem; }
    th, td { text-align: right; padding: 0.25rem 0.5rem; border-bottom: 1px solid var(--line); }
    th:nth-child(-n + 3), td:nth-child(-n + 3) { text-align: left; }
    tr.lead td { border-top: 1px solid var(--line-2); }
    td.warn { color: var(--gold); }
  `,
})
export class NeedChart {
  readonly groups = input.required<NeedGroup[]>();
  readonly num = fmtNum;
  readonly pct = fmtPct;
  readonly pctile = fmtPctile;
  readonly money = fmtMoney;

  readonly options = computed<EChartsCoreOption>(() => {
    const gs = [...this.groups()].sort((a, b) => a.need_score - b.need_score);
    return {
      grid: { left: 44, right: 40, top: 8, bottom: 28 },
      tooltip: {
        trigger: 'item',
        formatter: (p: { dataIndex: number }) => {
          const g = gs[p.dataIndex];
          return `${g.pos_group}: need ${fmtNum(g.need_score, 0)}<br/>starters ${fmtPctile(g.starter_pct)} pctile · ${g.starters_expiring} expiring · ${g.starters_aging} past peak`;
        },
      },
      xAxis: { type: 'value', min: 0, max: 100 },
      yAxis: { type: 'category', data: gs.map((g) => g.pos_group) },
      series: [
        {
          type: 'bar',
          data: gs.map((g) => ({
            value: g.need_score,
            itemStyle: { color: g.need_score >= 50 ? '#8b1a2b' : g.need_score >= 25 ? '#c9a233' : '#888888', borderColor: '#111111', borderWidth: 1 },
          })),
          label: { show: true, position: 'right', color: '#e0e0e0', formatter: (p: { value: number }) => fmtNum(p.value, 0) },
        },
      ],
    };
  });
}
