import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withXhr } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { provideEchartsCore } from 'ngx-echarts';
import { registerEcharts } from '../../core/echarts-setup';
import { GAMES } from '../season/testing/fixtures';
import { DriveExplorerPage } from './explorer-page';
import { GAME, GAME_ID, INSIGHTS, PLAYS } from './testing/fixtures';

const FRESH = { season: 2026, team: 'WAS', last_ingest: null, through_week: 2 };

describe('DriveExplorerPage', () => {
  let http: HttpTestingController;
  let harness: RouterTestingHarness;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withXhr()),
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

  /** The schedule read every page makes for the header's jump list. */
  function flushSchedule(): void {
    http.expectOne('/api/v1/meta/freshness').flush(FRESH);
    http.expectOne('/api/v1/season/2026/games').flush(GAMES);
  }

  it('renders the header, rail, story, matchup, charts, tendencies, swings and play table for a game', async () => {
    const page = await harness.navigateByUrl(`/explorer/${GAME_ID}`, DriveExplorerPage);
    http.expectOne(`/api/v1/games/${GAME_ID}`).flush(GAME);
    http.expectOne(`/api/v1/games/${GAME_ID}/insights`).flush(INSIGHTS);
    http.expectOne((r) => r.url === `/api/v1/games/${GAME_ID}/plays` && r.params.keys().length === 0).flush(PLAYS);
    flushSchedule();
    harness.detectChanges();
    const el = harness.routeNativeElement as HTMLElement;
    const text = el.textContent as string;
    expect(text).toContain('NYG @ WAS, week 1');
    expect(text).toContain('2026 · Week 1 · 2026-09-13 13:00');
    expect(el.querySelectorAll('app-section-rail a').length).toBe(8);
    expect([...el.querySelectorAll('section.sec')].map((s) => s.id)).toEqual(['story', 'matchup', 'drives', 'offense', 'defense', 'situations', 'big-plays', 'plays']);
    expect(text).toContain('WAS beat NYG 27–20 at home');
    expect(el.querySelectorAll('app-matchup-compare .row').length).toBe(11);
    expect(el.querySelectorAll('app-tendency-panel').length).toBe(2);
    expect(el.querySelectorAll('[echarts]').length).toBe(3);
    expect(el.querySelectorAll('table.line tbody tr').length).toBe(2);
    expect(el.querySelectorAll('app-play-table tbody tr').length).toBe(4);
    expect(el.querySelector('app-play-table tr.td')?.textContent).toContain('TOUCHDOWN');
    expect(el.querySelector('app-play-table .chip.blue')?.textContent).toContain('PA');
    expect(text).toContain('Q1 15:00');
    expect(text).toContain('3rd & 2');
    expect(el.querySelector('a[title="Next game"]')?.getAttribute('href')).toBe('/explorer/2026_02_WAS_DAL');
    expect(page.driveNumbers()).toEqual([1, 2, 3]);
  });

  it('still shows the drives and plays when the insights fail', async () => {
    await harness.navigateByUrl(`/explorer/${GAME_ID}`, DriveExplorerPage);
    http.expectOne(`/api/v1/games/${GAME_ID}`).flush(GAME);
    http.expectOne(`/api/v1/games/${GAME_ID}/insights`).flush(null, { status: 500, statusText: 'err' });
    http.expectOne(`/api/v1/games/${GAME_ID}/plays`).flush(PLAYS);
    flushSchedule();
    harness.detectChanges();
    const el = harness.routeNativeElement as HTMLElement;
    expect(el.textContent).toContain('Insights are unavailable right now');
    expect(el.querySelectorAll('[echarts]').length).toBe(3);
    expect(el.querySelectorAll('app-play-table tbody tr').length).toBe(4);
    expect(el.querySelector('app-matchup-compare')).toBeNull();
  });

  it('puts filter changes in the URL and refetches the plays with them', async () => {
    await harness.navigateByUrl(`/explorer/${GAME_ID}`, DriveExplorerPage);
    http.expectOne(`/api/v1/games/${GAME_ID}`).flush(GAME);
    http.expectOne(`/api/v1/games/${GAME_ID}/insights`).flush(INSIGHTS);
    http.expectOne(`/api/v1/games/${GAME_ID}/plays`).flush(PLAYS);
    flushSchedule();
    harness.detectChanges();
    const el = harness.routeNativeElement as HTMLElement;
    const selects = el.querySelectorAll('app-play-filters select');
    const down = selects[3] as HTMLSelectElement;
    down.value = '3';
    down.dispatchEvent(new Event('change'));
    await harness.fixture.whenStable();
    harness.detectChanges();
    expect(TestBed.inject(Router).url).toBe(`/explorer/${GAME_ID}?down=3`);
    http.expectOne((r) => r.url === `/api/v1/games/${GAME_ID}/plays` && r.params.get('down') === '3').flush({ ...PLAYS, plays: [PLAYS.plays[2]] });
    harness.detectChanges();
    expect(el.querySelectorAll('app-play-table tbody tr').length).toBe(1);
    expect(el.querySelector('app-play-filters button')?.textContent).toContain('Clear');
    const tag = el.querySelectorAll('app-play-filters select')[6] as HTMLSelectElement;
    tag.value = 'play_action';
    tag.dispatchEvent(new Event('change'));
    await harness.fixture.whenStable();
    harness.detectChanges();
    expect(TestBed.inject(Router).url).toBe(`/explorer/${GAME_ID}?down=3&tag=play_action`);
    http.expectOne((r) => r.url === `/api/v1/games/${GAME_ID}/plays` && r.params.get('tag') === 'play_action').flush(PLAYS);
  });

  it('reads filters from the URL on load and drops unknown values', async () => {
    const page = await harness.navigateByUrl(`/explorer/${GAME_ID}?posteam=NYG&type=run&down=9&distance=huge&rz=true&qtr=5&tag=nope`, DriveExplorerPage);
    expect(page.filters()).toEqual({ posteam: 'NYG', type: 'run', rz: true, qtr: 5 });
    http.expectOne(`/api/v1/games/${GAME_ID}`).flush(GAME);
    http.expectOne(`/api/v1/games/${GAME_ID}/insights`).flush(INSIGHTS);
    http
      .expectOne(
        (r) =>
          r.url === `/api/v1/games/${GAME_ID}/plays` &&
          r.params.get('posteam') === 'NYG' &&
          r.params.get('type') === 'run' &&
          r.params.get('rz') === 'true' &&
          r.params.get('qtr') === '5' &&
          !r.params.has('down') &&
          !r.params.has('tag'),
      )
      .flush(PLAYS);
    flushSchedule();
  });

  it('a drive picked from the swings filters the play list', async () => {
    const page = await harness.navigateByUrl(`/explorer/${GAME_ID}`, DriveExplorerPage);
    http.expectOne(`/api/v1/games/${GAME_ID}`).flush(GAME);
    http.expectOne(`/api/v1/games/${GAME_ID}/insights`).flush(INSIGHTS);
    http.expectOne(`/api/v1/games/${GAME_ID}/plays`).flush(PLAYS);
    flushSchedule();
    harness.detectChanges();
    page.selectDrive(2);
    await harness.fixture.whenStable();
    harness.detectChanges();
    expect(TestBed.inject(Router).url).toBe(`/explorer/${GAME_ID}?drive=2`);
    http.expectOne((r) => r.url === `/api/v1/games/${GAME_ID}/plays` && r.params.get('drive') === '2').flush(PLAYS);
  });

  it('says so when the game does not exist', async () => {
    await harness.navigateByUrl('/explorer/2026_09_WAS_PHI', DriveExplorerPage);
    http.expectOne('/api/v1/games/2026_09_WAS_PHI').flush({ detail: 'no game' }, { status: 404, statusText: 'Not Found' });
    http.expectOne('/api/v1/games/2026_09_WAS_PHI/insights').flush(null, { status: 404, statusText: 'Not Found' });
    http.expectOne('/api/v1/games/2026_09_WAS_PHI/plays').flush(null, { status: 404, statusText: 'Not Found' });
    flushSchedule();
    harness.detectChanges();
    expect((harness.routeNativeElement as HTMLElement).textContent).toContain('Game not found');
  });

  it('lists the played games with their result, latest first, when no game is chosen', async () => {
    await harness.navigateByUrl('/explorer', DriveExplorerPage);
    flushSchedule();
    harness.detectChanges();
    const links = [...(harness.routeNativeElement as HTMLElement).querySelectorAll('.picker a')];
    expect(links.map((a) => a.textContent?.replace(/\s+/g, ' ').trim())).toEqual(['L Week 2 · vs DAL · 20–37', 'L Week 1 · @ PHI · 22–24']);
    expect(links[0].getAttribute('href')).toBe('/explorer/2026_02_WAS_DAL');
    expect(links[0].querySelector('.chip')?.classList).toContain('l');
  });
});
