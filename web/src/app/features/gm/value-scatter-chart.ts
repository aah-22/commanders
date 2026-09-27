import { Component, computed, input } from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsCoreOption } from 'echarts/core';
import { AcquisitionCard } from '../../core/api.service';
import { fmtPctile } from '../../core/format';

const GRADE_COLOR: Record<string, string> = { A: '#c9a233', B: '#e0c069', C: '#888888', D: '#c46b6b', F: '#8b1a2b' };

/** Production percentile against cost percentile for every graded arrival; above the diagonal is value. */
@Component({
  selector: 'app-value-scatter-chart',
  imports: [NgxEchartsDirective],
  template: `
    <div class="panel">
      <h2>Production vs cost</h2>
      <p class="muted">Each arrival's production percentile at his position against his APY percentile. Above the line is more production than the money usually buys.</p>
      @if (points().length) {
        <div class="chart" echarts [options]="options()" theme="caabi" [autoResize]="true"></div>
      } @else {
        <p class="muted">No arrival has qualified for a percentile yet.</p>
      }
    </div>
  `,
  styles: `
    .chart { height: 320px; }
  `,
})
export class ValueScatterChart {
  readonly cards = input.required<AcquisitionCard[]>();

  readonly points = computed(() => this.cards().filter((c) => c.production_pct != null && c.cost_pct != null));

  readonly options = computed<EChartsCoreOption>(() => {
    const pts = this.points();
    return {
      grid: { left: 56, right: 16, top: 16, bottom: 44 },
      tooltip: {
        trigger: 'item',
        formatter: (p: { data: { card: AcquisitionCard } }) => {
          const c = p.data.card;
          return `${c.name} (${c.pos_group})<br/>production ${fmtPctile(c.production_pct)} · cost ${fmtPctile(c.cost_pct)}<br/>grade ${c.grade ?? '–'}`;
        },
      },
      xAxis: { type: 'value', min: 0, max: 1, name: 'cost percentile →', nameLocation: 'middle', nameGap: 28, axisLabel: { formatter: (v: number) => `${Math.round(100 * v)}` } },
      yAxis: { type: 'value', min: 0, max: 1, name: '↑ production percentile', nameLocation: 'middle', nameGap: 40, axisLabel: { formatter: (v: number) => `${Math.round(100 * v)}` } },
      series: [
        {
          type: 'scatter',
          data: pts.map((c) => ({
            value: [c.cost_pct, c.production_pct],
            card: c,
            itemStyle: { color: GRADE_COLOR[c.grade ?? ''] ?? '#888888', borderColor: '#111111', borderWidth: 2 },
          })),
          symbolSize: 12,
          label: { show: true, position: 'right', color: '#e0e0e0', fontSize: 10, formatter: (p: { data: { card: AcquisitionCard } }) => p.data.card.name?.split(' ').pop() ?? '' },
          markLine: { silent: true, symbol: 'none', lineStyle: { color: '#2a2a2a', type: 'dashed' }, label: { show: false }, data: [[{ coord: [0, 0] }, { coord: [1, 1] }]] },
        },
      ],
    };
  });
}
