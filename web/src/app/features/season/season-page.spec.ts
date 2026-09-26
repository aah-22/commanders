import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { provideEchartsCore } from 'ngx-echarts';
import { registerEcharts } from '../../core/echarts-setup';
import { SeasonDashboardPage } from './season-page';
import { EMPTY_SUMMARY, GAMES, LEAGUE, SUMMARY } from './testing/fixtures';

describe('SeasonDashboardPage', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SeasonDashboardPage],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), provideEchartsCore({ echarts: registerEcharts() })],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function render() {
    const fixture = TestBed.createComponent(SeasonDashboardPage);
    fixture.detectChanges();
    http.expectOne('/api/v1/meta/freshness').flush({ season: 2026, team: 'WAS', last_ingest: null, through_week: 2 });
    fixture.detectChanges();
    return fixture;
  }

  it('shows loading, then the record strip, charts and games for a season with data', () => {
    const fixture = render();
    expect(fixture.nativeElement.textContent).toContain('Loading');
    http.expectOne('/api/v1/season/2026/summary').flush(SUMMARY);
    http.expectOne('/api/v1/season/2026/league').flush(LEAGUE);
    http.expectOne('/api/v1/season/2026/games').flush(GAMES);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('0–2');
    expect(text).toContain('11th of 32');
    expect(text).toContain('through week 2');
    expect(text).toContain('Next: vs SEA');
    expect(fixture.nativeElement.querySelectorAll('app-game-results-table tbody tr').length).toBe(3);
    expect(fixture.nativeElement.querySelector('tr.next .chip').textContent).toContain('next');
    expect(fixture.nativeElement.querySelectorAll('[echarts]').length).toBe(3);
  });

  it('explains an empty season and still lists the schedule', () => {
    const fixture = render();
    http.expectOne('/api/v1/season/2026/summary').flush(EMPTY_SUMMARY);
    http.expectOne('/api/v1/season/2026/league').flush({ ...LEAGUE, teams: [] });
    http.expectOne('/api/v1/season/2026/games').flush({ ...GAMES, games: GAMES.games.map((g) => ({ ...g, result: null, summary: null })) });
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('No 2026 games ingested yet');
    expect(fixture.nativeElement.querySelectorAll('app-game-results-table tbody tr').length).toBe(3);
    expect(fixture.nativeElement.querySelector('app-record-strip')).toBeNull();
  });

  it('treats a 404 (season not ingested yet) as an empty season, not an outage', () => {
    const fixture = render();
    http.expectOne('/api/v1/season/2026/summary').flush({ detail: 'no games for season 2026' }, { status: 404, statusText: 'Not Found' });
    http.expectOne('/api/v1/season/2026/league').flush(null, { status: 404, statusText: 'Not Found' });
    http.expectOne('/api/v1/season/2026/games').flush(null, { status: 404, statusText: 'Not Found' });
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('No 2026 games ingested yet');
    expect(text).not.toContain('unavailable');
  });

  it('says so when the API fails', () => {
    const fixture = render();
    http.expectOne('/api/v1/season/2026/summary').flush(null, { status: 500, statusText: 'err' });
    http.expectOne('/api/v1/season/2026/league').flush(null, { status: 500, statusText: 'err' });
    http.expectOne('/api/v1/season/2026/games').flush(null, { status: 500, statusText: 'err' });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Season data is unavailable');
  });
});
