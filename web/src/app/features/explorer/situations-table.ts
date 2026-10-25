import { Component, computed, input } from '@angular/core';
import { Stat, TeamInsights } from '../../core/api.service';
import { fmtStat } from '../../core/format';
import { tone } from './matchup-compare';

/** Third down, fourth down, the red zone, late downs, sacks and turnovers for both teams beside the league. */
@Component({
  selector: 'app-situations-table',
  template: `
    @let f = focus();
    @let o = opp();
    <div class="panel">
      <h2>Situations</h2>
      <p class="muted">Each offense's money downs, with the plays behind every rate. Green and red compare with the NFL average.</p>
      <div class="scroll">
        <table>
          <thead><tr><th>Situation</th><th>{{ f.team }}</th><th>{{ o.team }}</th><th>NFL avg</th></tr></thead>
          <tbody>
            @for (r of rows(); track r.key) {
              <tr>
                <td>{{ r.label }}</td>
                <td [class.good]="tone(r.f) === 'good'" [class.bad]="tone(r.f) === 'bad'">{{ fmt(r.f) }} <span class="muted">{{ n(r.f) }}</span></td>
                <td [class.good]="tone(r.o) === 'good'" [class.bad]="tone(r.o) === 'bad'">{{ fmt(r.o) }} <span class="muted">{{ n(r.o) }}</span></td>
                <td class="muted">{{ r.f ? fmtS(r.f.league, r.f.kind) : '–' }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: `
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 0.9rem; }
    th, td { text-align: right; padding: 0.3rem 0.5rem; border-bottom: 1px solid var(--line); white-space: nowrap; }
    th { color: var(--muted); font-weight: 500; font-size: 0.8rem; }
    th:first-child, td:first-child { text-align: left; white-space: normal; }
    td .muted { font-size: 0.75rem; }
    td.good { color: var(--good); } td.bad { color: var(--bad); }
  `,
})
export class SituationsTable {
  readonly focus = input.required<TeamInsights>();
  readonly opp = input.required<TeamInsights>();
  readonly fmtS = fmtStat;
  readonly tone = tone;

  readonly rows = computed(() =>
    this.focus().situations.map((s) => ({ key: s.key, label: s.label, f: s, o: this.opp().situations.find((x) => x.key === s.key) ?? null })),
  );

  fmt(s: Stat | null): string {
    return s ? fmtStat(s.value, s.kind) : '–';
  }

  n(s: Stat | null): string {
    if (!s || s.value === null) return '';
    return s.kind === 'count' ? '' : `(${s.n})`;
  }
}
