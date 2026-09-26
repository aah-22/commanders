import { TestBed } from '@angular/core/testing';
import { provideEchartsCore } from 'ngx-echarts';
import { registerEcharts } from '../../core/echarts-setup';
import { fmtEpa, ordinal } from '../../core/format';
import { DownDistanceHeatmap } from './down-distance-heatmap';
import { EpaTrendChart } from './epa-trend-chart';
import { LeagueScatterChart } from './league-scatter-chart';
import { RecordStrip } from './record-strip';
import { LEAGUE, SUMMARY, WEEKS } from './testing/fixtures';

interface Series {
  name: string;
  data: unknown[];
  label?: { formatter: string };
}

describe('season charts', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideEchartsCore({ echarts: registerEcharts() })],
    }).compileComponents();
  });

  it('formats EPA with a sign and ranks with an ordinal suffix', () => {
    expect(fmtEpa(0.0812)).toBe('+0.081');
    expect(fmtEpa(-0.05)).toBe('-0.050');
    expect(fmtEpa(null)).toBe('–');
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22].map(ordinal)).toEqual(['1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd']);
  });

  it('record strip prints record, division rank and league ranks', () => {
    const fixture = TestBed.createComponent(RecordStrip);
    fixture.componentRef.setInput('summary', SUMMARY);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('0–2');
    expect(text).toContain('4th NFC East');
    expect(text).toContain('+0.081');
    expect(text).toContain('26th of 32');
    expect(text).toContain('.292');
  });

  it('trend chart leaves a bye week as a gap and carries the league band', () => {
    const fixture = TestBed.createComponent(EpaTrendChart);
    fixture.componentRef.setInput('weeks', [WEEKS[0], { ...WEEKS[1], week: 3 }]);
    fixture.componentRef.setInput('league', SUMMARY.league_weekly);
    fixture.componentRef.setInput('throughWeek', 3);
    fixture.detectChanges();
    const series = (fixture.componentInstance.options()['series'] as Series[]).map((s) => [s.name, s.data]);
    const offense = series.find(([n]) => n === 'offense')?.[1] as (number | null)[];
    expect(offense).toEqual([0.06, null, 0.103]);
    expect(series.map(([n]) => n)).toEqual(['band-lo', 'band', 'League median', 'offense', 'defense (allowed)']);
    expect(fixture.nativeElement.querySelectorAll('tbody tr').length).toBe(3);
  });

  it('scatter chart singles out the highlighted team', () => {
    const fixture = TestBed.createComponent(LeagueScatterChart);
    fixture.componentRef.setInput('teams', LEAGUE.teams);
    fixture.componentRef.setInput('highlight', 'WAS');
    fixture.detectChanges();
    const series = fixture.componentInstance.options()['series'] as Series[];
    expect(series[0].data.length).toBe(3);
    expect(series[1].data).toEqual([[0.081, 0.151, 'WAS']]);
    expect(series[1].label?.formatter).toBe('WAS');
    expect(fixture.nativeElement.querySelector('tr.mine').textContent).toContain('WAS');
  });

  it('heatmap dims thin cells and reports the gap to the league', () => {
    const fixture = TestBed.createComponent(DownDistanceHeatmap);
    fixture.componentRef.setInput('cells', SUMMARY.down_distance);
    fixture.detectChanges();
    const data = (fixture.componentInstance.options()['series'] as Series[])[0].data as { value: number[]; itemStyle?: { opacity: number } }[];
    expect(data.length).toBe(12);
    expect(data[0].value[2]).toBeCloseTo(0.08, 5);
    expect(data[0].itemStyle?.opacity).toBe(0.35); // n=2
    expect(data[1].itemStyle).toBeUndefined(); // n=53
  });
});
