import { Component, computed, inject, input } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { GameDetail, GameRow, TeamInsights } from '../../core/api.service';

/** Score line with the focus team's previous / next arrows, the quarter line score and a jump to any played game. */
@Component({
  selector: 'app-game-header',
  imports: [RouterLink],
  template: `
    @let g = game();
    <div class="panel head">
      <div class="nav">
        @if (g.prev_game_id) {
          <a [routerLink]="['/explorer', g.prev_game_id]" title="Previous game">← prev</a>
        } @else {
          <span class="muted">← prev</span>
        }
      </div>
      <div class="score">
        <span class="team" [class.mine]="g.away_team === g.team">{{ g.away_team }}</span>
        <span class="pts">{{ g.away_score ?? '–' }}</span>
        <span class="at">&#64;</span>
        <span class="pts">{{ g.home_score ?? '–' }}</span>
        <span class="team" [class.mine]="g.home_team === g.team">{{ g.home_team }}</span>
      </div>
      <div class="nav right">
        @if (g.next_game_id) {
          <a [routerLink]="['/explorer', g.next_game_id]" title="Next game">next →</a>
        } @else {
          <span class="muted">next →</span>
        }
      </div>
      <p class="muted sub">{{ subtitle() }}</p>
      @if (line(); as l) {
        <table class="line" aria-label="Score by quarter">
          <thead><tr><th></th>@for (q of l.labels; track q) {<th>{{ q }}</th>}<th>T</th></tr></thead>
          <tbody>
            @for (r of l.rows; track r.team) {
              <tr [class.mine]="r.team === g.team"><td>{{ r.team }}</td>@for (p of r.points; track $index) {<td>{{ p ?? '–' }}</td>}<td>{{ r.total ?? '–' }}</td></tr>
            }
          </tbody>
        </table>
      }
      @if (games().length) {
        <label class="pick">
          <span class="muted">Jump to</span>
          <select id="game-pick" [value]="g.game_id" (change)="pick($event)">
            @for (r of games(); track r.game_id) {
              <option [value]="r.game_id">Week {{ r.week }} · {{ r.is_home ? 'vs' : '@' }} {{ r.opponent }} · {{ r.result }} {{ r.points_for }}–{{ r.points_against }}</option>
            }
          </select>
        </label>
      }
    </div>
  `,
  styles: `
    .head { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; row-gap: 0.3rem; }
    .nav a, .nav span { display: inline-block; min-height: 44px; line-height: 44px; }
    .nav.right { text-align: right; }
    .score { display: flex; align-items: baseline; gap: 0.75rem; font-size: 1.6rem; font-weight: 700; color: var(--heading); font-variant-numeric: tabular-nums; }
    .team.mine { color: var(--gold); }
    .at { color: var(--muted); font-size: 1rem; font-weight: 400; }
    .sub { grid-column: 1 / -1; text-align: center; margin: 0; }
    .line { grid-column: 1 / -1; justify-self: center; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 0.9rem; }
    .line th, .line td { padding: 0.1rem 0.6rem; text-align: right; }
    .line th { color: var(--muted); font-weight: 500; font-size: 0.75rem; }
    .line td:first-child { text-align: left; color: var(--muted); }
    .line td:last-child { font-weight: 600; color: var(--heading); }
    .line tr.mine td:first-child { color: var(--gold); }
    .pick { grid-column: 1 / -1; display: flex; gap: 0.5rem; align-items: center; justify-content: center; font-size: 0.8rem; }
    .pick select { min-height: 40px; max-width: 100%; background: var(--panel-2); color: var(--text); border: 1px solid var(--line-2); border-radius: 6px; padding: 0.3rem 0.5rem; font: inherit; font-size: 0.9rem; }
    @media (max-width: 640px) { .score { font-size: 1.25rem; gap: 0.5rem; } }
  `,
})
export class GameHeader {
  private readonly router = inject(Router);
  readonly game = input.required<GameDetail>();
  /** [focus, opponent] from the insights, for the quarter line score; absent while they load. */
  readonly teams = input<TeamInsights[] | null>(null);
  /** The focus team's played games, for the jump list. */
  readonly games = input<GameRow[]>([]);

  readonly subtitle = computed(() => {
    const g = this.game();
    const kind = g.game_type === 'REG' ? `Week ${g.week}` : `${g.game_type} · week ${g.week}`;
    const when = [g.gameday, g.gametime].filter(Boolean).join(' ');
    return `${g.season} · ${kind}${when ? ` · ${when}` : ''}${g.played ? '' : ' · not played yet'}`;
  });

  /** Away row first, like the score line; quarters the game reached, overtime included. */
  readonly line = computed(() => {
    const g = this.game();
    const ts = this.teams();
    if (!ts?.length || !ts.some((t) => t.quarters.length)) return null;
    const labels = [...new Set(ts.flatMap((t) => t.quarters.map((q) => q.label)))];
    const order = [g.away_team, g.home_team];
    const rows = order
      .map((team) => ts.find((t) => t.team === team))
      .filter((t): t is TeamInsights => !!t)
      .map((t) => ({ team: t.team, points: labels.map((l) => t.quarters.find((q) => q.label === l)?.points ?? null), total: t.points }));
    return { labels, rows };
  });

  pick(e: Event): void {
    const id = (e.target as HTMLSelectElement).value;
    if (id && id !== this.game().game_id) void this.router.navigate(['/explorer', id]);
  }
}
