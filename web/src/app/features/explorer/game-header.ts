import { Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { GameDetail } from '../../core/api.service';

/** Score line for the game with the focus team's previous / next game as arrows. */
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
    </div>
  `,
  styles: `
    .head { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; row-gap: 0.25rem; }
    .nav.right { text-align: right; }
    .score { display: flex; align-items: baseline; gap: 0.75rem; font-size: 1.6rem; font-weight: 700; color: var(--heading); font-variant-numeric: tabular-nums; }
    .team.mine { color: var(--gold); }
    .at { color: var(--muted); font-size: 1rem; font-weight: 400; }
    .sub { grid-column: 1 / -1; text-align: center; margin: 0; }
    @media (max-width: 640px) { .score { font-size: 1.25rem; gap: 0.5rem; } }
  `,
})
export class GameHeader {
  readonly game = input.required<GameDetail>();

  readonly subtitle = computed(() => {
    const g = this.game();
    const kind = g.game_type === 'REG' ? `Week ${g.week}` : `${g.game_type} · week ${g.week}`;
    const when = [g.gameday, g.gametime].filter(Boolean).join(' ');
    return `${g.season} · ${kind}${when ? ` · ${when}` : ''}${g.played ? '' : ' · not played yet'}`;
  });
}
