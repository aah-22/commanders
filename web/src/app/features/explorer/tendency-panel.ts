import { Component, computed, input, signal, ChangeDetectionStrategy } from '@angular/core';
import { Split, Stat, TeamInsights } from '../../core/api.service';
import { fmtDelta, fmtRate1, fmtStat } from '../../core/format';
import { tone } from './matchup-compare';

const THIN = 10;
/** Stats and splits that need FTN charting; they read "not charted yet" until the week's file lands. */
const CHARTED = new Set([
  'play_action_rate',
  'screen_rate',
  'rpo_rate',
  'motion_rate',
  'blitz_rate_faced',
  'pass_rushers_faced',
  'light_box_rate_faced',
  'blitz_rate',
  'pass_rushers',
  'light_box_rate',
  'qb_alignment',
  'box_faced',
  'box_shown',
  'pass_rushers_sent',
]);

/**
 * One side of the ball for either team: every split as a labelled bar list (never a stacked bar with labels inside the
 * segments), then the rates as cells with the plays behind them and the gap to the league in neutral words.
 */
@Component({
  selector: 'app-tendency-panel',
  template: `
    @let t = team();
    <div class="panel">
      <div class="head">
        <h2>{{ mode() === 'offense' ? 'Offense' : 'Defense' }}</h2>
        <div class="seg" role="group" aria-label="Which team">
          @for (x of teams(); track x.team; let i = $index) {
            <button type="button" [class.on]="which() === i" (click)="which.set(i)">{{ x.team }} {{ mode() }}</button>
          }
        </div>
      </div>
      <p class="muted">{{ caption() }}</p>
      @for (sp of splits(); track sp.key) {
        <h3>{{ sp.label }} <span class="muted n">{{ sp.n ? sp.n + ' plays' : '' }}</span></h3>
        @if (!sp.n) {
          <p class="muted small">{{ empty(sp.key) }}</p>
        } @else {
          <ul class="bars">
            @for (p of sp.parts; track p.key) {
              <li>
                <span class="lab">{{ p.label }}</span>
                <span class="track"><span class="fill" [style.width.%]="100 * (p.share ?? 0)"></span>@if (p.league_share !== null) {<span class="tick" [style.left.%]="100 * p.league_share"></span>}</span>
                <span class="val">{{ pct(p.share) }} <span class="muted">({{ p.count }})</span></span>
                <span class="lg muted">NFL {{ pct(p.league_share) }}</span>
              </li>
            }
          </ul>
        }
      }
      @if (mode() === 'offense' && t.by_down.length) {
        <h3>Dropback rate by down</h3>
        <ul class="bars">
          @for (s of t.by_down; track s.key) {
            <li [class.thin]="s.n < thin">
              <span class="lab">{{ s.label }}</span>
              <span class="track"><span class="fill" [style.width.%]="100 * (s.value ?? 0)"></span>@if (s.league !== null) {<span class="tick" [style.left.%]="100 * s.league"></span>}</span>
              <span class="val">{{ pct(s.value) }} <span class="muted">({{ s.n }})</span></span>
              <span class="lg muted">NFL {{ pct(s.league) }}</span>
            </li>
          }
        </ul>
      }
      <h3>Rates</h3>
      <div class="cells">
        @for (s of stats(); track s.key) {
          <div class="cell" [class.thin]="s.n < thin && s.value !== null" [title]="s.n < thin && s.value !== null ? 'small sample: ' + s.n + ' plays' : ''">
            <div class="k">{{ s.label }}</div>
            @if (s.value === null && !s.n && charted(s.key)) {
              <div class="v muted">not charted yet</div>
            } @else {
              <div class="v">{{ fmt(s.value, s.kind) }} <span class="muted">n={{ s.n }}</span></div>
              <div class="d" [class.good]="tone(s) === 'good'" [class.bad]="tone(s) === 'bad'">{{ delta(s) }}</div>
            }
          </div>
        }
      </div>
      <details>
        <summary class="muted">Table view</summary>
        <table>
          <thead><tr><th>Stat</th><th>{{ t.team }}</th><th>n</th><th>NFL avg</th><th>n</th></tr></thead>
          <tbody>
            @for (s of stats(); track s.key) {
              <tr><td>{{ s.label }}</td><td>{{ fmt(s.value, s.kind) }}</td><td class="muted">{{ s.n }}</td><td>{{ fmt(s.league, s.kind) }}</td><td class="muted">{{ s.league_n }}</td></tr>
            }
          </tbody>
        </table>
      </details>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: `
    .head { display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
    .seg { display: inline-flex; border: 1px solid var(--line-2); border-radius: 999px; overflow: hidden; }
    .seg button { min-height: 40px; padding: 0 0.9rem; background: transparent; color: var(--muted); border: 0; font: inherit; font-size: 0.85rem; cursor: pointer; }
    .seg button.on { background: var(--panel-2); color: var(--gold); }
    h3 { font-size: 0.95rem; margin: 0.9rem 0 0.35rem; }
    h3 .n { font-weight: 400; font-size: 0.8rem; }
    .bars { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.3rem; }
    .bars li { display: grid; grid-template-columns: 7.5rem 1fr 5.2rem 4.5rem; align-items: center; gap: 0.5rem; font-size: 0.85rem; }
    .lab { color: var(--text); }
    .track { position: relative; height: 10px; background: var(--panel-2); border-radius: 3px; }
    .fill { position: absolute; left: 0; top: 0; height: 100%; background: var(--gold); border-radius: 3px; }
    .tick { position: absolute; top: -2px; width: 2px; height: 14px; background: var(--burgundy); }
    .val { font-variant-numeric: tabular-nums; text-align: right; }
    .lg { font-size: 0.75rem; text-align: right; white-space: nowrap; }
    .cells { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.5rem; }
    .cell { background: var(--panel-2); border-radius: 8px; padding: 0.5rem 0.6rem; }
    .cell .k { color: var(--muted); font-size: 0.75rem; line-height: 1.2; }
    .cell .v { font-size: 1.05rem; font-weight: 600; color: var(--heading); }
    .cell .v .muted { font-size: 0.7rem; font-weight: 400; }
    .cell .d { font-size: 0.75rem; color: var(--muted); }
    .d.good { color: var(--good); } .d.bad { color: var(--bad); }
    .thin { opacity: 0.6; }
    .small { font-size: 0.85rem; margin: 0; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 0.85rem; margin-top: 0.4rem; }
    th, td { text-align: right; padding: 0.25rem 0.4rem; border-bottom: 1px solid var(--line); }
    th:first-child, td:first-child { text-align: left; }
    @media (max-width: 640px) { .bars li { grid-template-columns: 5.6rem 1fr 4.4rem; } .lg { display: none; } .cells { grid-template-columns: 1fr 1fr; } }
  `,
})
export class TendencyPanel {
  readonly teams = input.required<TeamInsights[]>();
  readonly mode = input.required<'offense' | 'defense'>();
  readonly isCharted = input(true);
  readonly throughWeek = input<number | null>(null);
  readonly which = signal(0);
  readonly thin = THIN;
  readonly pct = fmtRate1;
  readonly fmt = fmtStat;
  readonly tone = tone;

  readonly team = computed(() => this.teams()[Math.min(this.which(), this.teams().length - 1)]);
  readonly splits = computed<Split[]>(() => (this.mode() === 'offense' ? this.team().splits : this.team().defense_splits));
  readonly stats = computed<Stat[]>(() => (this.mode() === 'offense' ? this.team().tendencies : this.team().defense));
  readonly caption = computed(() => {
    const t = this.team();
    const n = this.mode() === 'offense' ? t.efficiency.find((s) => s.key === 'epa_per_play')?.n : t.defense.find((s) => s.key === 'def_epa_per_play')?.n;
    const who = this.mode() === 'offense' ? `${t.team}'s offense` : `${t.team}'s defense against ${t.opponent}'s offense`;
    return `${who}, ${n ?? 0} pass and run plays. Bars are shares of this game; the mark is the NFL share through week ${this.throughWeek() ?? '–'}. Neutral words for tendencies; green and red only where higher or lower is better.`;
  });

  charted(key: string): boolean {
    return CHARTED.has(key);
  }

  empty(key: string): string {
    return CHARTED.has(key) && !this.isCharted() ? 'Not charted yet: FTN publishes the week\'s charting a day or two after the game.' : 'No plays in this game.';
  }

  delta(s: Stat): string {
    return fmtDelta(s.value, s.league, s.kind);
  }
}
