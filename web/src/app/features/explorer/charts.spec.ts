import { TestBed } from '@angular/core/testing';
import { provideEchartsCore } from 'ngx-echarts';
import { registerEcharts } from '../../core/echarts-setup';
import { clock, downDistance, yardline } from '../../core/format';
import { DriveChart } from './drive-chart';
import { GAME } from './testing/fixtures';
import { WinProbChart } from './win-prob-chart';

interface BarSeries {
  data: { value: number; itemStyle: { color: string }; label: { formatter: string } }[];
}

describe('explorer charts', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ providers: [provideEchartsCore({ echarts: registerEcharts() })] }).compileComponents();
  });

  it('formats the clock, the ball spot and the down', () => {
    expect(clock(1, 3600)).toBe('Q1 15:00');
    expect(clock(2, 2252)).toBe('Q2 7:32');
    expect(clock(4, 5)).toBe('Q4 0:05');
    expect(clock(5, 300)).toBe('OT 5:00');
    expect(clock(null, 10)).toBe('–');
    expect([yardline(75), yardline(50), yardline(18), yardline(null)]).toEqual(['OWN 25', '50', 'OPP 18', '–']);
    expect([downDistance(3, 4), downDistance(1, 8, 1), downDistance(null, null)]).toEqual(['3rd & 4', '1st & Goal', '–']);
  });

  it('drive chart colours the focus team gold, labels results and reports clicks', () => {
    const fixture = TestBed.createComponent(DriveChart);
    fixture.componentRef.setInput('drives', GAME.drives);
    fixture.componentRef.setInput('team', 'WAS');
    const clicked: number[] = [];
    fixture.componentRef.setInput('onDrive', (d: number) => clicked.push(d));
    fixture.detectChanges();
    const data = (fixture.componentInstance.options()['series'] as BarSeries[])[0].data;
    expect(data.map((d) => d.value)).toEqual([2.4, -1.1, -0.4]);
    expect(data.map((d) => d.itemStyle.color)).toEqual(['#c9a233', '#888888', '#c9a233']);
    expect(data.map((d) => d.label.formatter)).toEqual(['TD', 'Punt', 'Punt']);
    fixture.componentInstance.onClick({ dataIndex: 1 });
    expect(clicked).toEqual([2]);
    expect(fixture.nativeElement.querySelectorAll('tbody tr').length).toBe(3);
  });

  it('win probability runs on elapsed time from the home side and tabulates each quarter', () => {
    const fixture = TestBed.createComponent(WinProbChart);
    fixture.componentRef.setInput('points', GAME.win_prob);
    fixture.componentRef.setInput('home', 'WAS');
    fixture.componentRef.setInput('away', 'NYG');
    fixture.detectChanges();
    expect(fixture.componentInstance.data().map((d) => d[0])).toEqual([0, 200, 300, 1000, 3600]);
    expect(fixture.componentInstance.rows()).toEqual([
      { label: 'Q1', wp: 0.72 },
      { label: 'Q2', wp: 0.66 },
      { label: 'Q4', wp: 1 },
    ]);
    expect(fixture.nativeElement.textContent).toContain("WAS's chance of winning");
  });
});
