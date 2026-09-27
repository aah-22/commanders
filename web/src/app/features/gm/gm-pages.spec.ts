import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { provideEchartsCore } from 'ngx-echarts';
import { registerEcharts } from '../../core/echarts-setup';
import { fmtMoney, fmtPctile } from '../../core/format';
import { AboutPage } from '../about/about-page';
import { AcquisitionsPage } from './acquisitions-page';
import { NeedChart } from './need-chart';
import { TargetsPage } from './targets-page';
import { ACQUISITIONS, MODELS, NEED, TARGETS } from './testing/fixtures';
import { ValueScatterChart } from './value-scatter-chart';

interface Series {
  data: { value: number[] | number; itemStyle: { color: string } }[];
}

describe('GM pages', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([
          { path: 'gm/targets', component: TargetsPage },
          { path: 'gm/acquisitions', component: AcquisitionsPage },
          { path: 'about', component: AboutPage },
        ]),
        provideEchartsCore({ echarts: registerEcharts() }),
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('formats money and percentiles', () => {
    expect([fmtMoney(12.65), fmtMoney(0.84), fmtMoney(null)]).toEqual(['$12.7M', '$840K', '–']);
    expect([fmtPctile(0.93), fmtPctile(0.004), fmtPctile(null)]).toEqual(['93rd', '1st', '–']);
  });

  it('acquisitions page renders cards sorted by gap and filters by how', () => {
    const fixture = TestBed.createComponent(AcquisitionsPage);
    fixture.detectChanges();
    http.expectOne('/api/v1/gm/acquisitions').flush(ACQUISITIONS);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const names = () => [...el.querySelectorAll('tbody tr td:first-child b')].map((b) => b.textContent);
    expect(names()).toEqual(['Odafe Oweh', 'Deebo Samuel', 'Antonio Williams']); // gap desc, unqualified last
    expect(el.textContent).toContain('1 free agent, 1 draft, 1 trade');
    expect(el.textContent).toContain('2 of 3 graded by the acquisition-value model');
    expect(el.querySelectorAll('app-grade-chip .g-A').length).toBe(1);
    expect(el.querySelectorAll('app-grade-chip .g-F').length).toBe(1);
    expect(el.textContent).toContain('R3 #71');
    expect(el.textContent).toContain('38th · 2025–26');  // Samuel's pooled grade and its seasons
    expect(el.textContent).toContain('not enough snaps yet');
    fixture.componentInstance.how.set('draft');
    fixture.detectChanges();
    expect(names()).toEqual(['Antonio Williams']);
    fixture.componentInstance.how.set('');
    fixture.componentInstance.sortBy('apy');
    fixture.detectChanges();
    expect(names()[0]).toBe('Deebo Samuel'); // $17.5M
  });

  it('value scatter colours points by grade and skips unqualified arrivals', () => {
    const fixture = TestBed.createComponent(ValueScatterChart);
    fixture.componentRef.setInput('cards', ACQUISITIONS.cards);
    fixture.detectChanges();
    const data = (fixture.componentInstance.options()['series'] as Series[])[0].data;
    expect(data.length).toBe(2);
    expect(data.map((d) => d.itemStyle.color)).toEqual(['#c9a233', '#8b1a2b']);
  });

  it('need chart orders groups and lists starters with expiring deals flagged', () => {
    const fixture = TestBed.createComponent(NeedChart);
    fixture.componentRef.setInput('groups', NEED.groups);
    fixture.detectChanges();
    const opts = fixture.componentInstance.options();
    expect((opts['yAxis'] as { data: string[] }).data).toEqual(['QB', 'WR', 'LB']); // ascending so the worst is on top
    const data = (opts['series'] as Series[])[0].data;
    expect(data.map((d) => d.itemStyle.color)).toEqual(['#888888', '#c9a233', '#8b1a2b']);
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelectorAll('tbody tr').length).toBe(5);
    expect(el.querySelectorAll('td.warn').length).toBe(2); // Wagner and Samuel at 0 years left
  });

  it('targets page loads need and targets, and puts the position filter in the URL', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/gm/targets', TargetsPage);
    http.expectOne('/api/v1/gm/need').flush(NEED);
    http.expectOne((r) => r.url === '/api/v1/gm/targets' && !r.params.has('position')).flush(TARGETS);
    harness.detectChanges();
    const el = harness.routeNativeElement as HTMLElement;
    expect(el.querySelectorAll('app-need-chart [echarts]').length).toBe(1);
    expect([...el.querySelectorAll('tbody tr td:nth-child(2) b')].map((b) => b.textContent)).toContain('A.J. Brown');
    expect(el.textContent).toContain('pending free agent');
    expect(el.querySelector('.chip')).toBeNull(); // not live
    const select = el.querySelector('select') as HTMLSelectElement;
    select.value = 'WR';
    select.dispatchEvent(new Event('change'));
    await harness.fixture.whenStable();
    harness.detectChanges();
    expect(TestBed.inject(Router).url).toBe('/gm/targets?position=WR');
    http.expectOne((r) => r.url === '/api/v1/gm/targets' && r.params.get('position') === 'WR').flush({ ...TARGETS, position: 'WR', live: true, targets: TARGETS.targets.slice(0, 2) });
    harness.detectChanges();
    expect(el.querySelectorAll('.panel.top tbody tr').length).toBe(2);
    expect(el.querySelector('.chip')?.textContent).toBe('live');
  });

  it('about page lists model outputs and jobs', () => {
    const fixture = TestBed.createComponent(AboutPage);
    fixture.detectChanges();
    http.expectOne('/api/v1/models').flush(MODELS);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent as string;
    expect(text).toContain('production-next');
    expect(text).toContain('run-value-1');
    expect(text).toContain('formula-1');
    expect((fixture.nativeElement as HTMLElement).querySelectorAll('tbody tr').length).toBe(5);
  });
});
