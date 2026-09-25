import { Component, computed, inject } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, map, of, switchMap } from 'rxjs';
import { ApiService, SeasonSummary } from '../../core/api.service';
import { DownDistanceHeatmap } from './down-distance-heatmap';
import { EpaTrendChart } from './epa-trend-chart';
import { GameResultsTable } from './game-results-table';
import { LeagueScatterChart } from './league-scatter-chart';
import { RecordStrip } from './record-strip';

/** The season dashboard: record strip, EPA trend, league scatter, down × distance heatmap, game table. */
@Component({
  selector: 'app-season-page',
  imports: [RecordStrip, EpaTrendChart, LeagueScatterChart, DownDistanceHeatmap, GameResultsTable],
  template: `
    @let s = summary();
    <p class="caabi-kicker">
      {{ season() }} season
      @if (s?.through_week) {
        · through week {{ s?.through_week }}
      }
    </p>
    <h1>Season dashboard</h1>
    @if (s === undefined) {
      <div class="panel"><p class="muted">Loading…</p></div>
    } @else if (s === null) {
      <div class="panel"><p>Season data is unavailable right now. The API did not answer; try again in a minute.</p></div>
    } @else if (!hasData()) {
      <div class="panel">
        <p>No {{ season() }} games ingested yet. The nightly job fills this in after the first week is played.</p>
      </div>
      <app-game-results-table [games]="games()?.games ?? []" [nextGameId]="s.next_game?.game_id ?? null" />
    } @else {
      <app-record-strip [summary]="s" />
      @if (s.next_game; as n) {
        <p class="muted next">Next: {{ n.is_home ? 'vs' : '@' }} {{ n.opponent }}, week {{ n.week }}, {{ n.gameday }} {{ n.gametime }}</p>
      }
      <div class="grid cols-2">
        <app-epa-trend-chart [weeks]="s.weeks" [league]="s.league_weekly" [throughWeek]="s.through_week" />
        <app-league-scatter-chart [teams]="league()?.teams ?? []" [highlight]="s.team" />
      </div>
      <div class="grid cols-2">
        <app-down-distance-heatmap [cells]="s.down_distance" />
        <app-game-results-table [games]="games()?.games ?? []" [nextGameId]="s.next_game?.game_id ?? null" />
      </div>
      <p class="muted small">
        EPA and success rate come from nflverse play-by-play over pass and run plays (kneels, spikes, aborted snaps and
        penalty no-plays excluded). Ranks are among teams through the last complete week. Division rank uses win % then
        point differential, not the full NFL tie-breakers.
      </p>
    }
  `,
  styles: `
    .grid { margin-top: 1rem; }
    .next { margin: 0.5rem 0 0; }
    .small { font-size: 0.8rem; margin-top: 1rem; }
  `,
})
export class SeasonDashboardPage {
  private readonly api = inject(ApiService);

  /** The season the API is configured for; the current year while freshness loads or if it fails. */
  readonly season = toSignal(
    this.api.freshness().pipe(
      map((f) => f.season),
      catchError(() => of(new Date().getFullYear())),
    ),
    { initialValue: new Date().getFullYear() },
  );
  private readonly season$ = toObservable(this.season);

  /** undefined while loading, null when the request failed. */
  readonly summary = toSignal<SeasonSummary | null>(
    this.season$.pipe(switchMap((s) => this.api.seasonSummary(s).pipe(catchError(() => of(null))))),
  );
  readonly league = toSignal(
    this.season$.pipe(switchMap((s) => this.api.seasonLeague(s).pipe(catchError(() => of(null))))),
    { initialValue: null },
  );
  readonly games = toSignal(
    this.season$.pipe(switchMap((s) => this.api.seasonGames(s).pipe(catchError(() => of(null))))),
    { initialValue: null },
  );
  readonly hasData = computed(() => (this.summary()?.weeks.length ?? 0) > 0);
}
