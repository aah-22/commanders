import { Component, input, ChangeDetectionStrategy } from '@angular/core';
import { PlayRow } from '../../core/api.service';
import { cleanDesc, clock, downDistance, fmtEpa, fmtPct, yardline } from '../../core/format';

const ALIGN: Record<string, string> = { U: 'UC', S: 'SG', P: 'P' };

/** Every play that passed the filters, in game order, with the score, the charting chips and the win-probability swing. */
@Component({
  selector: 'app-play-table',
  template: `
    <div class="panel">
      <h2>Plays <span class="muted count">{{ plays().length }}</span></h2>
      @if (plays().length) {
        <div class="scroll">
          <table>
            <thead>
              <tr><th>Clock</th><th>Off</th><th>Score</th><th>Down</th><th class="wide">Ball on</th><th>Play</th><th>Yds</th><th>EPA</th><th class="wide">WP</th></tr>
            </thead>
            <tbody>
              @for (p of plays(); track p.play_id) {
                <tr [class.td]="p.touchdown === 1" [class.turnover]="p.interception === 1 || p.fumble_lost === 1">
                  <td>{{ clock(p.qtr, p.game_seconds_remaining) }}</td>
                  <td>{{ p.posteam ?? '' }}</td>
                  <td class="muted">{{ score(p) }}</td>
                  <td>{{ dd(p.down, p.ydstogo, p.goal_to_go) }}</td>
                  <td class="wide">{{ yl(p.yardline_100) }}</td>
                  <td class="desc">
                    @if (p.qb_location && align[p.qb_location]) { <span class="al muted" title="QB alignment: under center, shotgun or pistol">{{ align[p.qb_location] }}</span> }
                    {{ desc(p.desc) || p.play_type || '' }}
                    @if (p.touchdown === 1) { <span class="chip gold">TD</span> }
                    @if (p.interception === 1) { <span class="chip red">INT</span> }
                    @if (p.fumble_lost === 1) { <span class="chip red">FUM</span> }
                    @if (p.sack === 1) { <span class="chip">sack</span> }
                    @if (p.qb_hit === 1 && p.sack !== 1) { <span class="chip" title="the quarterback was hit">hit</span> }
                    @if (p.qb_scramble === 1) { <span class="chip">scramble</span> }
                    @if (p.penalty === 1) { <span class="chip">flag</span> }
                    @if (p.first_down === 1 && p.touchdown !== 1) { <span class="chip">1st</span> }
                    @if (p.is_play_action === 1) { <span class="chip blue" title="play action: a dropback that began with a run fake">PA</span> }
                    @if (p.is_screen_pass === 1) { <span class="chip blue" title="screen pass">screen</span> }
                    @if (p.is_rpo === 1) { <span class="chip blue" title="run-pass option">RPO</span> }
                    @if (p.is_motion === 1) { <span class="chip blue" title="pre-snap motion">motion</span> }
                    @if (p.no_huddle === 1) { <span class="chip blue">no huddle</span> }
                    @if ((p.n_blitzers ?? 0) >= 1) { <span class="chip green" title="blitzers counted by FTN">blitz {{ p.n_blitzers }}</span> }
                    @if (p.n_defense_box !== null && p.n_defense_box !== undefined && p.n_defense_box >= 3 && p.n_defense_box <= 6) { <span class="chip green" title="six or fewer defenders in the box">light box</span> }
                    @if ((p.n_defense_box ?? 0) >= 8) { <span class="chip green" title="eight or more in the box">stacked box</span> }
                  </td>
                  <td>{{ p.yards_gained ?? '–' }}</td>
                  <td [class.pos]="(p.epa ?? 0) > 0.5" [class.neg]="(p.epa ?? 0) < -0.5">{{ epa(p.epa, 2) }}</td>
                  <td class="muted wide" [title]="swing(p)">{{ pct(p.wp) }}</td>
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
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: `
    .count { font-size: 0.9rem; font-weight: 400; margin-left: 0.4rem; }
    .scroll { overflow-x: auto; max-height: 640px; overflow-y: auto; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 0.9rem; }
    th, td { text-align: right; padding: 0.3rem 0.5rem; border-bottom: 1px solid var(--line); vertical-align: top; white-space: nowrap; }
    th { color: var(--muted); font-weight: 500; font-size: 0.8rem; position: sticky; top: 0; background: var(--panel); }
    th:nth-child(-n + 6), td:nth-child(-n + 6) { text-align: left; }
    td.desc { white-space: normal; min-width: 18rem; }
    .al { font-size: 0.7rem; margin-right: 0.3rem; }
    tr.td td { background: rgba(201, 162, 51, 0.08); }
    tr.turnover td { background: rgba(139, 26, 43, 0.15); }
    td.pos { color: var(--good); }
    td.neg { color: var(--bad); }
    .chip { margin-left: 0.3rem; padding: 0 0.35rem; border: 1px solid var(--line-2); border-radius: 999px; color: var(--muted); font-size: 0.7rem; white-space: nowrap; }
    .chip.gold { border-color: var(--gold); color: var(--gold); }
    .chip.red { border-color: var(--burgundy); color: var(--bad); }
    .chip.blue { border-color: #3d5a99; color: #8fb0ff; }
    .chip.green { border-color: #2f6b45; color: #7fd6a2; }
    @media (max-width: 640px) { .wide { display: none; } td.desc { min-width: 14rem; } table { font-size: 0.85rem; } }
  `,
})
export class PlayTable {
  readonly plays = input.required<PlayRow[]>();
  readonly clock = clock;
  readonly dd = downDistance;
  readonly yl = yardline;
  readonly epa = fmtEpa;
  readonly pct = fmtPct;
  readonly desc = cleanDesc;
  readonly align = ALIGN;

  /** "3–20": the offense's score first, before the play. */
  score(p: PlayRow): string {
    return p.posteam_score == null || p.defteam_score == null ? '' : `${p.posteam_score}–${p.defteam_score}`;
  }

  swing(p: PlayRow): string {
    return p.wpa == null ? '' : `win probability moved ${p.wpa > 0 ? '+' : ''}${Math.round(100 * p.wpa)} points for the offense`;
  }
}
