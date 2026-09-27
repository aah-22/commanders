import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, ParamMap, Router, RouterLink } from '@angular/router';
import { catchError, map, of, switchMap } from 'rxjs';
import { ApiService, DistanceBucket, GameDetail, GamePlays, GameRow, PlayFilters, PlayKind } from '../../core/api.service';
import { DownDistanceHeatmap } from '../season/down-distance-heatmap';
import { DriveChart } from './drive-chart';
import { GameHeader } from './game-header';
import { PlayFiltersBar } from './play-filters';
import { PlayTable } from './play-table';
import { WinProbChart } from './win-prob-chart';

const BUCKETS: DistanceBucket[] = ['short', 'mid', 'long', 'xlong'];
const KINDS: PlayKind[] = ['all', 'scrimmage', 'pass', 'run', 'special'];

/** The filters live in the URL so a filtered view is a link; unknown values are dropped rather than sent. */
export function parseFilters(q: ParamMap): PlayFilters {
  const f: PlayFilters = {};
  const posteam = q.get('posteam');
  if (posteam && /^[A-Z]{2,3}$/.test(posteam)) f.posteam = posteam;
  const down = Number(q.get('down'));
  if (down >= 1 && down <= 4) f.down = down;
  const distance = q.get('distance') as DistanceBucket | null;
  if (distance && BUCKETS.includes(distance)) f.distance = distance;
  if (q.get('rz') === 'true') f.rz = true;
  const drive = Number(q.get('drive'));
  if (drive >= 1) f.drive = drive;
  const type = q.get('type') as PlayKind | null;
  if (type && KINDS.includes(type) && type !== 'all') f.type = type;
  return f;
}

export function toQuery(f: PlayFilters): Record<string, string | null> {
  return {
    posteam: f.posteam ?? null,
    down: f.down ? `${f.down}` : null,
    distance: f.distance ?? null,
    rz: f.rz ? 'true' : null,
    drive: f.drive ? `${f.drive}` : null,
    type: f.type && f.type !== 'all' ? f.type : null,
  };
}

/** /explorer picks a game from the schedule; /explorer/:gameId is the drive and play explorer for it. */
@Component({
  selector: 'app-explorer-page',
  imports: [RouterLink, GameHeader, WinProbChart, DriveChart, DownDistanceHeatmap, PlayFiltersBar, PlayTable],
  template: `
    <p class="caabi-kicker">Drive &amp; play explorer</p>
    @if (!gameId()) {
      <h1>Pick a game</h1>
      @let gs = games();
      @if (gs === undefined) {
        <div class="panel"><p class="muted">Loading…</p></div>
      } @else if (gs === null) {
        <div class="panel"><p>The schedule is unavailable right now; try again in a minute.</p></div>
      } @else if (!gs.length) {
        <div class="panel"><p>No games played yet this season.</p></div>
      } @else {
        <div class="panel">
          <ul class="picker">
            @for (g of gs; track g.game_id) {
              <li>
                <a [routerLink]="['/explorer', g.game_id]">Week {{ g.week }} · {{ g.is_home ? 'vs' : '@' }} {{ g.opponent }}</a>
                <span class="muted">{{ g.result }} {{ g.points_for }}–{{ g.points_against }} · {{ g.gameday }}</span>
              </li>
            }
          </ul>
        </div>
      }
    } @else {
      @let g = game();
      @if (g === undefined) {
        <h1>Loading…</h1>
      } @else if (g === null) {
        <h1>Game not found</h1>
        <div class="panel"><p>No game {{ gameId() }} in the database. <a routerLink="/explorer">Pick another game</a>.</p></div>
      } @else {
        <h1>{{ g.away_team }} &#64; {{ g.home_team }}, week {{ g.week }}</h1>
        <app-game-header [game]="g" />
        @if (!g.played) {
          <div class="panel top"><p>Not played yet. Plays land the morning after the game.</p></div>
        } @else {
          <div class="grid cols-2 top">
            <app-win-prob-chart [points]="g.win_prob" [home]="g.home_team" [away]="g.away_team" />
            <app-drive-chart [drives]="g.drives" [team]="g.team" [onDrive]="selectDrive" />
          </div>
          <div class="grid cols-2 top">
            <app-down-distance-heatmap [cells]="g.down_distance" [caption]="g.team + ' offense in this game against the league season rate.'" />
            <div class="panel">
              <h2>Reading the page</h2>
              <p class="muted small">
                EPA is nflverse's expected points added per play; a drive's EPA sums its pass and run plays. Win probability is
                the home team's before each play. Filters below narrow the play table and are part of the page address, so a
                filtered view can be shared. Click a drive bar to jump to its plays.
              </p>
            </div>
          </div>
          <div class="top">
            <app-play-filters [filters]="filters()" [teams]="[g.away_team, g.home_team]" [drives]="driveNumbers()" (changed)="setFilters($event)" />
            @let ps = plays();
            @if (ps === null) {
              <div class="panel"><p>The play list is unavailable right now; try again in a minute.</p></div>
            } @else {
              <app-play-table [plays]="ps?.plays ?? []" />
            }
          </div>
        }
      }
    }
  `,
  styles: `
    .top { margin-top: 1rem; }
    .picker { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.4rem; }
    .picker li { display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; border-bottom: 1px solid var(--line); padding: 0.35rem 0; }
    .small { font-size: 0.85rem; }
  `,
})
export class DriveExplorerPage {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly gameId = toSignal(this.route.paramMap.pipe(map((p) => p.get('gameId'))), { initialValue: null });
  readonly filters = toSignal(this.route.queryParamMap.pipe(map(parseFilters)), { initialValue: {} as PlayFilters });

  /** undefined while loading, null when the request failed or the game does not exist. */
  readonly game = toSignal<GameDetail | null | undefined>(
    toObservable(this.gameId).pipe(
      switchMap((id) => (id ? this.api.game(id).pipe(catchError(() => of(null))) : of(undefined))),
    ),
  );

  private readonly playsKey = computed(() => ({ id: this.gameId(), f: this.filters() }));
  /** undefined while loading, null when the request failed. */
  readonly plays = toSignal<GamePlays | null | undefined>(
    toObservable(this.playsKey).pipe(
      switchMap(({ id, f }) => (id ? this.api.gamePlays(id, f).pipe(catchError(() => of(null))) : of(undefined))),
    ),
  );

  readonly driveNumbers = computed(() => this.game()?.drives.map((d) => d.drive) ?? []);

  /** The picker's list: this season's played games for the configured team, most recent first. */
  readonly games = toSignal<GameRow[] | null | undefined>(
    toObservable(this.gameId).pipe(
      switchMap((id) => {
        if (id) return of(undefined);
        return this.api.freshness().pipe(
          switchMap((f) => this.api.seasonGames(f.season)),
          map((sg) => sg.games.filter((g) => g.result).reverse()),
          catchError((e: HttpErrorResponse) => of(e.status === 404 ? [] : null)),
        );
      }),
    ),
  );

  readonly selectDrive = (drive: number): void => this.setFilters({ ...this.filters(), drive });

  setFilters(f: PlayFilters): void {
    void this.router.navigate([], { relativeTo: this.route, queryParams: toQuery(f), replaceUrl: true });
  }
}
