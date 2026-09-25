import * as echarts from 'echarts/core';
import { BarChart, HeatmapChart, LineChart, ScatterChart } from 'echarts/charts';
import {
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { CAABI_THEME } from './echarts-theme';

let registered = false;

/** Tree-shaken ECharts with the caabi theme; app.config.ts and every chart spec call this once. */
export function registerEcharts(): typeof echarts {
  if (!registered) {
    echarts.use([
      BarChart,
      LineChart,
      ScatterChart,
      HeatmapChart,
      GridComponent,
      TooltipComponent,
      LegendComponent,
      TitleComponent,
      VisualMapComponent,
      MarkLineComponent,
      CanvasRenderer,
    ]);
    echarts.registerTheme('caabi', CAABI_THEME);
    registered = true;
  }
  return echarts;
}
