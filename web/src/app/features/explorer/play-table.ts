import { Component, input } from '@angular/core';
import { PlayRow } from '../../core/api.service';
import { clock, downDistance, fmtEpa, fmtPct, yardline } from '../../core/format';

/** Every play that passed the filters, in game order; scores, turnovers and big plays are flagged. */
@Component({
  selector: 'app-play-table',
  template: `
    <div class="panel">
      <h2>Plays <span class="muted count">{{ plays().length }}</span></h2>
      @if (plays().length) {
        <div class="scroll">
          <table>
            <thead>
              <tr><th>Clock</th><th>Off</th><th>Down</th><th>Ball on</th><th>Play</th><th>Yds</th><th>EPA</th><th>WP</th></tr>
            </thead>
            <tbody>
              @for (p of plays(); track p.play_id) {
                <tr [class.td]="p.touchdown === 1" [class.turnover]="p.interception === 1 || p.fumble_lost === 1">
                  <td>{{ clock(p.qtr, p.game_seconds_remaining) }}</td>
                  <td>{{ p.posteam ?? '' }}</td>
                  <td>{{ dd(p.down, p.ydstogo, p.goal_to_go) }}</td>
                  <td>{{ yl(p.yardline_100) }}</td>
                  <td class="desc">
                    {{ p.desc ?? p.play_type ?? '' }}
                    @if (p.touchdown === 1) { <span class="chip gold">TD</span> }
                    @if (p.interception === 1) { <span class="chip red">INT</span> }
                    @if (p.fumble_lost === 1) { <span class="chip red">FUM</span> }
                    @if (p.sack === 1) { <span class="chip">sack</span> }
                    @if (p.penalty === 1) { <span class="chip">flag</span> }
                    @if (p.first_down === 1 && p.touchdown !== 1) { <span class="chip">1st</span> }
                  </td>
                  <td>{{ p.yards_gained ?? '–' }}</td>
                  <td [class.pos]="(p.epa ?? 0) > 0.5" [class.neg]="(p.epa ?? 0) < -0.5">{{ epa(p.epa, 2) }}</td>
                  <td class="muted">{{ pct(p.wp) }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      } @else {
        <p class="muted">No plays match these filters.</p>
      }
    </div>
  `,
  styles: `
    .count { font-size: 0.9rem; font-weight: 400; margin-left: 0.4rem; }
    .scroll { overflow-x: auto; max-height: 640px; overflow-y: auto; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 0.9rem; }
    th, td { text-align: right; padding: 0.3rem 0.5rem; border-bottom: 1px solid var(--line); vertical-align: top; white-space: nowrap; }
    th { color: var(--muted); font-weight: 500; font-size: 0.8rem; position: sticky; top: 0; background: var(--panel); }
    th:nth-child(-n + 5), td:nth-child(-n + 5) { text-align: left; }
    td.desc { white-space: normal; min-width: 22rem; }
    tr.td td { background: rgba(201, 162, 51, 0.08); }
    tr.turnover td { background: rgba(139, 26, 43, 0.15); }
    td.pos { color: var(--good); }
    td.neg { color: var(--bad); }
    .chip { margin-left: 0.3rem; padding: 0 0.35rem; border: 1px solid var(--line-2); border-radius: 999px; color: var(--muted); font-size: 0.7rem; }
    .chip.gold { border-color: var(--gold); color: var(--gold); }
    .chip.red { border-color: var(--burgundy); color: #d9534f; }
  `,
})
export class PlayTable {
  readonly plays = input.required<PlayRow[]>();
  readonly clock = clock;
  readonly dd = downDistance;
  readonly yl = yardline;
  readonly epa = fmtEpa;
  readonly pct = fmtPct;
}
