import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { provideEchartsCore } from 'ngx-echarts';
import { registerEcharts } from '../../core/echarts-setup';
import { GAMES } from '../season/testing/fixtures';
import { DriveExplorerPage } from './explorer-page';
import { GAME, GAME_ID, PLAYS } from './testing/fixtures';

describe('DriveExplorerPage', () => {
  let http: HttpTestingController;
  let harness: RouterTestingHarness;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([
          { path: 'explorer', component: DriveExplorerPage },
          { path: 'explorer/:gameId', component: DriveExplorerPage },
        ]),
        provideEchartsCore({ echarts: registerEcharts() }),
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    harness = await RouterTestingHarness.create();
  });

  afterEach(() => http.verify());

  it('renders the header, charts, heatmap and play table for a game', async () => {
    const page = await harness.navigateByUrl(`/explorer/${GAME_ID}`, DriveExplorerPage);
    http.expectOne(`/api/v1/games/${GAME_ID}`).flush(GAME);
    http.expectOne((r) => r.url === `/api/v1/games/${GAME_ID}/plays` && r.params.keys().length === 0).flush(PLAYS);
    harness.detectChanges();
    const el = harness.routeNativeElement as HTMLElement;
    const text = el.textContent as string;
    expect(text).toContain('NYG @ WAS, week 1');
    expect(text).toContain('2026 · Week 1 · 2026-09-13 13:00');
    expect(el.querySelectorAll('[echarts]').length).toBe(3);
    expect(el.querySelectorAll('app-play-table tbody tr').length).toBe(4);
    expect(el.querySelector('app-play-table tr.td')?.textContent).toContain('TOUCHDOWN');
    expect(text).toContain('Q1 15:00');
    expect(text).toContain('3rd & 2');
    expect(el.querySelector('a[title="Next game"]')?.getAttribute('href')).toBe('/explorer/2026_02_WAS_DAL');
    expect(page.driveNumbers()).toEqual([1, 2, 3]);
  });

  it('puts filter changes in the URL and refetches the plays with them', async () => {
    await harness.navigateByUrl(`/explorer/${GAME_ID}`, DriveExplorerPage);
    http.expectOne(`/api/v1/games/${GAME_ID}`).flush(GAME);
    http.expectOne(`/api/v1/games/${GAME_ID}/plays`).flush(PLAYS);
    harness.detectChanges();
    const el = harness.routeNativeElement as HTMLElement;
    const down = el.querySelectorAll('app-play-filters select')[2] as HTMLSelectElement;
    down.value = '3';
    down.dispatchEvent(new Event('change'));
    await harness.fixture.whenStable();
    harness.detectChanges();
    expect(TestBed.inject(Router).url).toBe(`/explorer/${GAME_ID}?down=3`);
    http.expectOne((r) => r.url === `/api/v1/games/${GAME_ID}/plays` && r.params.get('down') === '3').flush({ ...PLAYS, plays: [PLAYS.plays[2]] });
    harness.detectChanges();
    expect(el.querySelectorAll('app-play-table tbody tr').length).toBe(1);
    expect(el.querySelector('app-play-filters button')?.textContent).toContain('Clear');
  });

  it('reads filters from the URL on load and drops unknown values', async () => {
    const page = await harness.navigateByUrl(`/explorer/${GAME_ID}?posteam=NYG&type=run&down=9&distance=huge&rz=true`, DriveExplorerPage);
    expect(page.filters()).toEqual({ posteam: 'NYG', type: 'run', rz: true });
    http.expectOne(`/api/v1/games/${GAME_ID}`).flush(GAME);
    http
      .expectOne((r) => r.url === `/api/v1/games/${GAME_ID}/plays` && r.params.get('posteam') === 'NYG' && r.params.get('type') === 'run' && r.params.get('rz') === 'true' && !r.params.has('down'))
      .flush(PLAYS);
  });

  it('says so when the game does not exist', async () => {
    await harness.navigateByUrl('/explorer/2026_09_WAS_PHI', DriveExplorerPage);
    http.expectOne('/api/v1/games/2026_09_WAS_PHI').flush({ detail: 'no game' }, { status: 404, statusText: 'Not Found' });
    http.expectOne('/api/v1/games/2026_09_WAS_PHI/plays').flush(null, { status: 404, statusText: 'Not Found' });
    harness.detectChanges();
    expect((harness.routeNativeElement as HTMLElement).textContent).toContain('Game not found');
  });

  it('lists the played games, latest first, when no game is chosen', async () => {
    await harness.navigateByUrl('/explorer', DriveExplorerPage);
    http.expectOne('/api/v1/meta/freshness').flush({ season: 2026, team: 'WAS', last_ingest: null, through_week: 2 });
    http.expectOne('/api/v1/season/2026/games').flush(GAMES);
    harness.detectChanges();
    const links = [...(harness.routeNativeElement as HTMLElement).querySelectorAll('.picker a')];
    expect(links.map((a) => a.textContent?.trim())).toEqual(['Week 2 · vs DAL', 'Week 1 · @ PHI']);
    expect(links[0].getAttribute('href')).toBe('/explorer/2026_02_WAS_DAL');
  });
});
