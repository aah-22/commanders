import { Component, computed, input } from '@angular/core';
import { ImpactPlay, ImpactPlayer, TeamInsights } from '../../core/api.service';
import { cleanDesc, clock, downDistance, fmtEpa, fmtPct, yardline } from '../../core/format';
import { focusWp } from './takeaways';

const SHOW = 8;
const PLAYERS = 4;

export interface SwingRow {
  p: ImpactPlay;
  before: number | null;
  after: number | null;
  /** the focus team's change in win chance, in points */
  swing: number;
}

/** The biggest win-probability swings from the focus team's side, then the players who moved the game most. */
@Component({
  selector: 'app-impact-plays',
  template: `
    <div class="panel">
      <h2>Biggest swings</h2>
      <p class="muted">The plays that moved {{ focus() }}'s win chance most, either way. "Plays of this drive" filters the play list below.</p>
      @if (rows().length) {
        <ol class="swings">
          @for (r of rows(); track r.p.play_id) {
            <li>
              <div class="when">
                <span>{{ clock(r.p.qtr, r.p.game_seconds_remaining) }}</span>
                <span class="muted">{{ dd(r.p.down, r.p.ydstogo, r.p.goal_to_go) }} at {{ yl(r.p.yardline_100) }} · {{ r.p.posteam }} ball</span>
              </div>
              <div class="desc">
                {{ desc(r.p.desc) || r.p.play_type }}
                @if (r.p.touchdown === 1) { <span class="chip gold">TD</span> }
                @if (r.p.interception === 1) { <span class="chip red">INT</span> }
                @if (r.p.fumble_lost === 1) { <span class="chip red">FUM</span> }
                @if (r.p.sack === 1) { <span class="chip">sack</span> }
                @if (r.p.fourth_down) { <span class="chip">4th down</span> }
                @if (r.p.penalty === 1) { <span class="chip">flag</span> }
              </div>
              <div class="wp">
                <span class="pill" [class.good]="r.swing > 0" [class.bad]="r.swing < 0">{{ r.swing > 0 ? '+' : '' }}{{ r.swing }} pts</span>
                <span class="muted">{{ focus() }} {{ pct(r.before) }} → {{ pct(r.after) }} · EPA {{ epa(r.p.epa, 2) }}</span>
                @if (r.p.drive) { <button type="button" class="link" (click)="onDrive()?.(r.p.drive!)">plays of this drive</button> }
              </div>
            </li>
          }
        </ol>
      } @else {
        <p class="muted">No win-probability data for this game.</p>
      }
      <h2 class="who">Who moved the game</h2>
      <p class="muted">Each offense's most involved players: every pass thrown, carry and target, with the win probability and EPA those plays added up to.</p>
      <div class="grid cols-2">
        @for (t of teams(); track t.team) {
          <div>
            <h3>{{ t.team }}</h3>
            @if (t.players.length) {
              <ul class="players">
                @for (pl of t.players.slice(0, max); track pl.gsis_id) {
                  <li>
                    <div class="name">{{ pl.name ?? pl.gsis_id }} <span class="muted">{{ pl.position ?? '' }}</span></div>
                    <div class="muted small">{{ roles(pl) }}</div>
                    <div class="nums"><span [class.good]="(pl.wpa ?? 0) > 0.05" [class.bad]="(pl.wpa ?? 0) < -0.05">{{ wpPts(pl.wpa) }} WP</span> · {{ epa(pl.epa, 1) }} EPA · {{ pl.big_plays }} big play{{ pl.big_plays === 1 ? '' : 's' }}</div>
                  </li>
                }
              </ul>
            } @else {
              <p class="muted small">No plays credited yet.</p>
            }
          </div>
        }
      </div>
    </div>
  `,
  styles: `
    .swings { list-style: none; margin: 0 0 1rem; padding: 0; display: grid; gap: 0.6rem; }
    .swings li { display: grid; gap: 0.15rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--line); }
    .when { display: flex; gap: 0.6rem; flex-wrap: wrap; font-size: 0.85rem; font-variant-numeric: tabular-nums; }
    .desc { line-height: 1.4; }
    .wp { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; font-size: 0.85rem; }
    .pill { padding: 0 0.5rem; border-radius: 999px; border: 1px solid var(--line-2); font-variant-numeric: tabular-nums; font-weight: 600; }
    .pill.good { color: var(--good); border-color: var(--good); } .pill.bad { color: var(--bad); border-color: var(--bad); }
    .chip { margin-left: 0.3rem; padding: 0 0.35rem; border: 1px solid var(--line-2); border-radius: 999px; color: var(--muted); font-size: 0.7rem; }
    .chip.gold { border-color: var(--gold); color: var(--gold); } .chip.red { border-color: var(--burgundy); color: var(--bad); }
    .link { background: none; border: 0; padding: 0; min-height: 44px; color: var(--gold); font: inherit; font-size: 0.85rem; cursor: pointer; }
    .who { margin-top: 0.5rem; }
    h3 { font-size: 0.95rem; margin: 0.25rem 0 0.4rem; }
    .players { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.45rem; }
    .players li { padding: 0.4rem 0.6rem; background: var(--panel-2); border-radius: 8px; }
    .name { font-weight: 600; color: var(--heading); }
    .small { font-size: 0.8rem; }
    .nums { font-size: 0.85rem; font-variant-numeric: tabular-nums; }
    .good { color: var(--good); } .bad { color: var(--bad); }
  `,
})
export class ImpactPlays {
  readonly plays = input.required<ImpactPlay[]>();
  readonly teams = input.required<TeamInsights[]>();
  readonly focus = input.required<string>();
  readonly home = input.required<string>();
  readonly onDrive = input<(drive: number) => void>();
  readonly max = PLAYERS;
  readonly clock = clock;
  readonly dd = downDistance;
  readonly yl = yardline;
  readonly epa = fmtEpa;
  readonly pct = fmtPct;
  readonly desc = cleanDesc;

  readonly rows = computed<SwingRow[]>(() => {
    const focusIsHome = this.focus() === this.home();
    return this.plays().slice(0, SHOW).map((p) => {
      const { before, after } = focusWp(p, focusIsHome);
      return { p, before, after, swing: before != null && after != null ? Math.round(100 * (after - before)) : 0 };
    });
  });

  roles(p: ImpactPlayer): string {
    const parts = [];
    if (p.as_passer) parts.push(`${p.as_passer} pass${p.as_passer === 1 ? '' : 'es'}`);
    if (p.as_rusher) parts.push(`${p.as_rusher} carr${p.as_rusher === 1 ? 'y' : 'ies'}`);
    if (p.as_receiver) parts.push(`${p.as_receiver} target${p.as_receiver === 1 ? '' : 's'}`);
    return `${parts.join(' · ')} · ${p.yards} yds`;
  }

  wpPts(wpa: number | null): string {
    if (wpa == null) return '–';
    const pts = Math.round(100 * wpa);
    return `${pts > 0 ? '+' : ''}${pts}`;
  }
}
