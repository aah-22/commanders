import { Component, computed, input } from '@angular/core';
import { Stat, TeamInsights } from '../../core/api.service';
import { fmtStat, ordinal } from '../../core/format';

type List = 'efficiency' | 'tendencies' | 'situations';
const ROWS: [List, string][] = [
  ['efficiency', 'epa_per_play'],
  ['efficiency', 'success_rate'],
  ['efficiency', 'explosive_rate'],
  ['efficiency', 'pass_epa_per_play'],
  ['efficiency', 'rush_epa_per_play'],
  ['efficiency', 'points_per_drive'],
  ['situations', 'third_down_conv'],
  ['situations', 'red_zone_td_rate'],
  ['tendencies', 'pass_rate'],
  ['tendencies', 'pressure_rate_taken'],
  ['situations', 'turnovers'],
];

export interface MatchupRow {
  key: string;
  label: string;
  f: Stat | null;
  o: Stat | null;
  /** bar widths in % of the row's widest value */
  fw: number;
  ow: number;
  lw: number | null;
  fNeg: boolean;
  oNeg: boolean;
  fTone: 'good' | 'bad' | '';
  oTone: 'good' | 'bad' | '';
}

/** Mirrored bars, the focus team on the left and the opponent on the right, with the league marked on each side. */
@Component({
  selector: 'app-matchup-compare',
  template: `
    @let f = focus();
    @let o = opp();
    <div class="panel">
      <h2>Matchup</h2>
      <p class="muted">
        <span class="sw f"></span> {{ f.team }} offense against <span class="sw o"></span> {{ o.team }}'s, this game. The thin mark is the NFL average through
        week {{ throughWeek() ?? '–' }}; a rank is the week's, among the teams that played.
      </p>
      <div class="rows">
        @for (r of rows(); track r.key) {
          <div class="row">
            <span class="v" [class.good]="r.fTone === 'good'" [class.bad]="r.fTone === 'bad'">{{ fmt(r.f) }}</span>
            <div class="mid">
              <div class="bars">
                <div class="half l"><span class="bar f" [class.neg]="r.fNeg" [style.width.%]="r.fw"></span>@if (r.lw !== null) {<span class="tick" [style.right.%]="r.lw"></span>}</div>
                <div class="half r"><span class="bar o" [class.neg]="r.oNeg" [style.width.%]="r.ow"></span>@if (r.lw !== null) {<span class="tick" [style.left.%]="r.lw"></span>}</div>
              </div>
              <div class="lab">
                {{ r.label }}
                @if (r.f?.rank) { <span class="rank" title="rank among the teams that played this week">{{ ord(r.f?.rank) }} of {{ r.f?.teams }}</span> }
              </div>
            </div>
            <span class="v" [class.good]="r.oTone === 'good'" [class.bad]="r.oTone === 'bad'">{{ fmt(r.o) }}</span>
          </div>
        }
      </div>
      <details>
        <summary class="muted">Table view</summary>
        <table>
          <thead><tr><th>Stat</th><th>{{ f.team }}</th><th>n</th><th>{{ o.team }}</th><th>n</th><th>NFL avg</th></tr></thead>
          <tbody>
            @for (r of rows(); track r.key) {
              <tr><td>{{ r.label }}</td><td>{{ fmt(r.f) }}</td><td class="muted">{{ r.f?.n ?? '' }}</td><td>{{ fmt(r.o) }}</td><td class="muted">{{ r.o?.n ?? '' }}</td><td>{{ r.f ? fmtS(r.f.league, r.f.kind) : '–' }}</td></tr>
            }
          </tbody>
        </table>
      </details>
    </div>
  `,
  styles: `
    .sw { display: inline-block; width: 0.7em; height: 0.7em; border-radius: 2px; vertical-align: -1px; }
    .sw.f { background: var(--gold); } .sw.o { background: var(--muted); }
    .rows { display: grid; gap: 0.55rem; margin: 0.5rem 0; }
    .row { display: grid; grid-template-columns: 4.2rem 1fr 4.2rem; align-items: center; gap: 0.5rem; }
    .v { font-variant-numeric: tabular-nums; font-weight: 600; color: var(--heading); text-align: right; }
    .v + .mid + .v { text-align: left; }
    .v.good { color: var(--good); } .v.bad { color: var(--bad); }
    .bars { display: grid; grid-template-columns: 1fr 1fr; gap: 2px; height: 10px; }
    .half { position: relative; background: var(--panel-2); border-radius: 3px; overflow: hidden; }
    .bar { position: absolute; top: 0; height: 100%; }
    .half.l .bar { right: 0; background: var(--gold); border-radius: 3px 0 0 3px; }
    .half.r .bar { left: 0; background: var(--muted); border-radius: 0 3px 3px 0; }
    .bar.neg { opacity: 0.45; }
    .tick { position: absolute; top: -2px; width: 2px; height: 14px; background: var(--burgundy); }
    .lab { display: flex; justify-content: space-between; gap: 0.5rem; font-size: 0.8rem; color: var(--muted); margin-top: 0.15rem; }
    .rank { color: var(--text); white-space: nowrap; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 0.9rem; margin-top: 0.4rem; }
    th, td { text-align: right; padding: 0.25rem 0.4rem; border-bottom: 1px solid var(--line); }
    th:first-child, td:first-child { text-align: left; }
    @media (max-width: 640px) { .row { grid-template-columns: 3.4rem 1fr 3.4rem; } .v { font-size: 0.9rem; } }
  `,
})
export class MatchupCompare {
  readonly focus = input.required<TeamInsights>();
  readonly opp = input.required<TeamInsights>();
  readonly throughWeek = input<number | null>(null);
  readonly ord = ordinal;
  readonly fmtS = fmtStat;

  readonly rows = computed<MatchupRow[]>(() =>
    ROWS.map(([list, key]) => {
      const f = this.focus()[list].find((s) => s.key === key) ?? null;
      const o = this.opp()[list].find((s) => s.key === key) ?? null;
      const league = f?.league ?? o?.league ?? null;
      const max = Math.max(Math.abs(f?.value ?? 0), Math.abs(o?.value ?? 0), Math.abs(league ?? 0)) || 1;
      const w = (v: number | null | undefined) => (v == null ? 0 : (100 * Math.abs(v)) / max);
      return {
        key,
        label: f?.label ?? o?.label ?? key,
        f,
        o,
        fw: w(f?.value),
        ow: w(o?.value),
        lw: league == null ? null : w(league),
        fNeg: (f?.value ?? 0) < 0,
        oNeg: (o?.value ?? 0) < 0,
        fTone: tone(f),
        oTone: tone(o),
      };
    }),
  );

  fmt(s: Stat | null): string {
    return s ? fmtStat(s.value, s.kind) : '–';
  }
}

/** good / bad only for a valenced stat, judged against the league and outside the noise. */
export function tone(s: Stat | null): 'good' | 'bad' | '' {
  if (!s || s.better === 'none' || s.value == null || s.league == null) return '';
  const noise = s.kind === 'rate' ? 0.02 : s.kind === 'epa' ? 0.02 : 0.1;
  const d = (s.value - s.league) * (s.better === 'high' ? 1 : -1);
  return d > noise ? 'good' : d < -noise ? 'bad' : '';
}
