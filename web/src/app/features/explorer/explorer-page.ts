import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, ChangeDetectionStrategy } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, ParamMap, Router, RouterLink } from '@angular/router';
import { catchError, map, of, switchMap } from 'rxjs';
import { ApiService, DistanceBucket, GameDetail, GameInsights, GamePlays, GameRow, PlayFilters, PlayKind, PlayTag } from '../../core/api.service';
import { fmtEpa } from '../../core/format';
import { DownDistanceHeatmap } from '../season/down-distance-heatmap';
import { DriveChart } from './drive-chart';
import { GameHeader } from './game-header';
import { GameStory } from './game-story';
import { ImpactPlays } from './impact-plays';
import { MatchupCompare } from './matchup-compare';
import { PlayFiltersBar, TAGS } from './play-filters';
import { PlayTable } from './play-table';
import { SectionRail } from './section-rail';
import { jumpTo } from './sections';
import { SituationsTable } from './situations-table';
import { TendencyPanel } from './tendency-panel';
import { WinProbChart } from './win-prob-chart';

const BUCKETS: DistanceBucket[] = ['short', 'mid', 'long', 'xlong'];
const KINDS: PlayKind[] = ['all', 'scrimmage', 'pass', 'run', 'special'];
const TAG_VALUES = new Set<string>(TAGS.map((t) => t.value));

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
  const qtr = Number(q.get('qtr'));
  if (qtr >= 1 && qtr <= 5) f.qtr = qtr;
  const tag = q.get('tag');
  if (tag && TAG_VALUES.has(tag)) f.tag = tag as PlayTag;
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
    qtr: f.qtr ? `${f.qtr}` : null,
    tag: f.tag ?? null,
  };
}

/**
 * /explorer lists the team's played games; /explorer/:gameId is the game page: the story, the matchup against the
 * league, drives and win probability, each side's tendencies, the situations, the biggest swings and the play list,
 * under a sticky rail of section chips.
 */
@Component({
  selector: 'app-explorer-page',
  imports: [
    RouterLink,
    GameHeader,
    SectionRail,
    GameStory,
    MatchupCompare,
    WinProbChart,
    DriveChart,
    TendencyPanel,
    DownDistanceHeatmap,
    SituationsTable,
    ImpactPlays,
    PlayFiltersBar,
    PlayTable,
  ],
  template: `
    <p class="caabi-kicker">Game insights</p>
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
          <p class="muted">Every played game, latest first, with the offense's EPA per play that day.</p>
          <ul class="picker">
            @for (g of gs; track g.game_id) {
              <li>
                <a [routerLink]="['/explorer', g.game_id]"><span class="chip" [class.w]="g.result === 'W'" [class.l]="g.result === 'L'">{{ g.result }}</span> Week {{ g.week }} · {{ g.is_home ? 'vs' : '@' }} {{ g.opponent }} · {{ g.points_for }}–{{ g.points_against }}</a>
                <span class="muted">{{ g.gameday }} · off EPA/play {{ epa(g.summary?.off_epa_per_play, 2) }}</span>
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
        @let ins = insights();
        <h1>{{ g.away_team }} &#64; {{ g.home_team }}, week {{ g.week }}</h1>
        <app-game-header [game]="g" [teams]="ins?.teams ?? null" [games]="games() ?? []" />
        @if (!g.played) {
          <div class="panel top"><p>Not played yet. Plays land the morning after the game.</p></div>
        } @else {
          <app-section-rail class="top" />
          <section id="story" class="sec">
            @if (ins === undefined) {
              <div class="panel"><p class="muted">Working out the story…</p></div>
            } @else if (ins === null) {
              <div class="panel"><p>Insights are unavailable right now; the drives and plays below still work.</p></div>
            } @else {
              <app-game-story [insights]="ins" />
            }
          </section>
          <section id="matchup" class="sec">
            @if (ins) {
              <app-matchup-compare [focus]="ins.teams[0]" [opp]="ins.teams[1]" [throughWeek]="ins.league_through_week" />
            } @else if (ins === null) {
              <div class="panel"><p class="muted">Matchup unavailable right now.</p></div>
            }
          </section>
          <section id="drives" class="sec grid cols-2">
            <app-win-prob-chart [points]="g.win_prob" [home]="g.home_team" [away]="g.away_team" />
            <app-drive-chart [drives]="g.drives" [team]="g.team" [onDrive]="selectDrive" />
          </section>
          <section id="offense" class="sec">
            @if (ins) {
              <app-tendency-panel [teams]="ins.teams" mode="offense" [isCharted]="ins.charted" [throughWeek]="ins.league_through_week" />
            } @else if (ins === null) {
              <div class="panel"><p class="muted">Tendencies unavailable right now.</p></div>
            }
          </section>
          <section id="defense" class="sec">
            @if (ins) {
              <app-tendency-panel [teams]="ins.teams" mode="defense" [isCharted]="ins.charted" [throughWeek]="ins.league_through_week" />
            }
          </section>
          <section id="situations" class="sec grid cols-2">
            <app-down-distance-heatmap [cells]="g.down_distance" [caption]="g.team + ' offense in this game against the league season rate.'" />
            @if (ins) {
              <app-situations-table [focus]="ins.teams[0]" [opp]="ins.teams[1]" />
            }
          </section>
          <section id="big-plays" class="sec">
            @if (ins) {
              <app-impact-plays [plays]="ins.impact_plays" [teams]="ins.teams" [focus]="ins.team" [home]="g.home_team" [onDrive]="selectDrive" />
            }
          </section>
          <section id="plays" class="sec">
            <app-play-filters [filters]="filters()" [teams]="[g.away_team, g.home_team]" [drives]="driveNumbers()" (changed)="setFilters($event)" />
            @let ps = plays();
            @if (ps === null) {
              <div class="panel"><p>The play list is unavailable right now; try again in a minute.</p></div>
            } @else {
              <app-play-table [plays]="ps?.plays ?? []" />
            }
          </section>
        }
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: `
    .top { margin-top: 1rem; }
    .sec { margin-top: 1rem; scroll-margin-top: 64px; }
    .picker { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.4rem; }
    .picker li { display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; border-bottom: 1px solid var(--line); padding: 0.35rem 0; }
    .picker a { display: inline-flex; align-items: center; min-height: 44px; gap: 0.5rem; }
    .chip { padding: 0 0.45rem; border: 1px solid var(--line-2); border-radius: 999px; color: var(--muted); font-size: 0.75rem; font-weight: 600; }
    .chip.w { border-color: var(--good); color: var(--good); }
    .chip.l { border-color: var(--bad); color: var(--bad); }
  `,
})
export class DriveExplorerPage {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly epa = fmtEpa;

  readonly gameId = toSignal(this.route.paramMap.pipe(map((p) => p.get('gameId'))), { initialValue: null });
  readonly filters = toSignal(this.route.queryParamMap.pipe(map(parseFilters)), { initialValue: {} as PlayFilters });

  /** undefined while loading, null when the request failed or the game does not exist. */
  readonly game = toSignal<GameDetail | null | undefined>(
    toObservable(this.gameId).pipe(
      switchMap((id) => (id ? this.api.game(id).pipe(catchError(() => of(null))) : of(undefined))),
    ),
  );

  /** undefined while loading, null when the request failed; the page still shows drives and plays without it. */
  readonly insights = toSignal<GameInsights | null | undefined>(
    toObservable(this.gameId).pipe(
      switchMap((id) => (id ? this.api.gameInsights(id).pipe(catchError(() => of(null))) : of(undefined))),
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

  /** The team's played games this season, most recent first: the picker's list and the header's jump list. */
  readonly games = toSignal<GameRow[] | null | undefined>(
    this.api.freshness().pipe(
      switchMap((f) => this.api.seasonGames(f.season)),
      map((sg) => sg.games.filter((g) => g.result).reverse()),
      catchError((e: HttpErrorResponse) => of(e.status === 404 ? [] : null)),
    ),
  );

  readonly selectDrive = (drive: number): void => {
    this.setFilters({ ...this.filters(), drive });
    jumpTo('plays');
  };

  setFilters(f: PlayFilters): void {
    void this.router.navigate([], { relativeTo: this.route, queryParams: toQuery(f), replaceUrl: true });
  }
}
