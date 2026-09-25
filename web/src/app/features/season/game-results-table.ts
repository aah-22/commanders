import { Component, input } from '@angular/core';
import { GameRow } from '../../core/api.service';
import { fmtEpa, fmtPct, fmtSignedPct } from '../../core/format';

/** The schedule with each played game's headline numbers; unplayed rows show the kickoff and the next game is marked. */
@Component({
  selector: 'app-game-results-table',
  template: `
    <div class="panel">
      <h2>Games</h2>
      @if (games().length) {
        <div class="scroll">
          <table>
            <thead>
              <tr><th>Wk</th><th>Date</th><th>Opponent</th><th>Result</th><th>Off EPA/play</th><th>Success</th><th>PROE</th><th>Def EPA/play</th></tr>
            </thead>
            <tbody>
              @for (g of games(); track g.game_id) {
                <tr [class.next]="g.game_id === nextGameId()">
                  <td>{{ g.week }}</td>
                  <td>{{ g.gameday ?? '' }}</td>
                  <td>{{ g.is_home ? 'vs' : '@' }} {{ g.opponent }}</td>
                  <td>
                    @if (g.result) {
                      {{ g.result }} {{ g.points_for }}–{{ g.points_against }}
                    } @else {
                      <span class="muted">{{ g.gametime ?? 'TBD' }}</span>
                      @if (g.game_id === nextGameId()) { <span class="chip">next</span> }
                    }
                  </td>
                  <td>{{ epa(g.summary?.off_epa_per_play) }}</td>
                  <td>{{ pct(g.summary?.off_success_rate) }}</td>
                  <td>{{ spct(g.summary?.off_proe) }}</td>
                  <td>{{ epa(g.summary?.def_epa_per_play) }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      } @else {
        <p class="muted">No schedule ingested yet.</p>
      }
    </div>
  `,
  styles: `
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; white-space: nowrap; }
    th, td { text-align: right; padding: 0.3rem 0.5rem; border-bottom: 1px solid var(--line); }
    th { color: var(--muted); font-weight: 500; font-size: 0.8rem; }
    th:nth-child(-n + 4), td:nth-child(-n + 4) { text-align: left; }
    tr.next td { background: var(--panel-2); }
    .chip { margin-left: 0.4rem; padding: 0 0.4rem; border: 1px solid var(--gold); border-radius: 999px; color: var(--gold); font-size: 0.7rem; }
  `,
})
export class GameResultsTable {
  readonly games = input.required<GameRow[]>();
  readonly nextGameId = input<string | null>(null);
  readonly epa = fmtEpa;
  readonly pct = fmtPct;
  readonly spct = fmtSignedPct;
}
