import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { catchError, of } from 'rxjs';
import { AcquisitionCard, Acquisitions, ApiService } from '../../core/api.service';
import { fmtMoney, fmtNum, fmtPct, fmtPctile, fmtSignedPct } from '../../core/format';
import { GradeChip } from './grade-chip';
import { ValueScatterChart } from './value-scatter-chart';

type SortKey = 'name' | 'how' | 'apy' | 'production_pct' | 'value_gap' | 'age' | 'arrival_season';

const METRIC_LABEL: Record<string, string> = {
  epa_per_play: 'EPA / play',
  epa_per_touch: 'EPA / touch',
  epa_per_target: 'EPA / target',
  snap_share: 'snap share',
  pressure_rate: 'pressures / snap',
  play_rate: 'plays made / snap',
  passer_rating_allowed: 'rating allowed',
};

/** Report cards for every arrival since last season: how he came, what he costs, what he has produced. */
@Component({
  selector: 'app-acquisitions-page',
  imports: [GradeChip, ValueScatterChart],
  template: `
    <p class="caabi-kicker">Front office</p>
    <h1>Acquisition report cards</h1>
    @let a = data();
    @if (a === undefined) {
      <div class="panel"><p class="muted">Loading…</p></div>
    } @else if (a === null) {
      <div class="panel"><p>Report cards are unavailable right now; try again in a minute.</p></div>
    } @else if (!a.cards.length) {
      <div class="panel"><p>No arrivals on record for {{ a.since }}–{{ a.season }} yet. The nightly job fills this in from contracts, the draft and trades.</p></div>
    } @else {
      <p class="muted">
        Every {{ a.team }} arrival in {{ a.since }}–{{ a.season }}: {{ a.cards.length }} players ({{ counts() }}). Production is the
        {{ a.season }} percentile at the position among qualified players; the grade is production minus what the money
        usually buys ({{ modelShare() }} graded by the acquisition-value model, the rest against the APY percentile until it scores).
      </p>
      <div class="grid cols-2 top">
        <app-value-scatter-chart [cards]="a.cards" />
        <div class="panel">
          <h2>How to read a card</h2>
          <ul class="muted small">
            <li><b>Production</b>: the headline metric for the position group (EPA per target for receivers, pressures per snap for rushers, passer rating allowed for coverage, snap share for linemen) and its percentile, with the sample behind it.</li>
            <li><b>Expected</b>: the percentile the model expects for that contract, age and pedigree; before the model has scored a season it is the APY percentile itself.</li>
            <li><b>Grade</b>: A ≥ +20 points over expected, B ≥ +8, C within ±8, D ≥ −20, F below. No grade until the sample clears the position's floor.</li>
          </ul>
        </div>
      </div>
      <div class="panel top">
        <div class="bar">
          <label>Arrived
            <select [value]="season()" (change)="season.set(value($event))">
              <option value="">{{ a.since }}–{{ a.season }}</option>
              @for (s of seasons(); track s) { <option [value]="s">{{ s }}</option> }
            </select>
          </label>
          <label>How
            <select [value]="how()" (change)="how.set(value($event))">
              <option value="">All</option>
              @for (h of hows(); track h) { <option [value]="h">{{ h }}</option> }
            </select>
          </label>
          <span class="muted count">{{ rows().length }} shown</span>
        </div>
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th (click)="sortBy('name')" [class.on]="sort() === 'name'">Player</th>
                <th (click)="sortBy('how')" [class.on]="sort() === 'how'">How</th>
                <th (click)="sortBy('arrival_season')" [class.on]="sort() === 'arrival_season'">When</th>
                <th (click)="sortBy('age')" [class.on]="sort() === 'age'">Age</th>
                <th (click)="sortBy('apy')" [class.on]="sort() === 'apy'">APY</th>
                <th>Deal</th>
                <th>Production</th>
                <th (click)="sortBy('production_pct')" [class.on]="sort() === 'production_pct'">Pctile</th>
                <th>Expected</th>
                <th (click)="sortBy('value_gap')" [class.on]="sort() === 'value_gap'">Gap</th>
                <th>Grade</th>
              </tr>
            </thead>
            <tbody>
              @for (c of rows(); track c.gsis_id) {
                <tr>
                  <td><b>{{ c.name }}</b> <span class="muted">{{ c.position ?? c.pos_group }}</span></td>
                  <td>{{ c.how }}@if (c.from_team) { <span class="muted">from {{ c.from_team }}</span> }@if (c.draft_round) { <span class="muted">R{{ c.draft_round }} #{{ c.draft_pick }}</span> }</td>
                  <td>{{ c.arrival_season }}</td>
                  <td>{{ num(c.age, 1) }}</td>
                  <td>{{ money(c.apy) }}</td>
                  <td class="muted">{{ c.contract_years ?? '–' }} yr @if (c.years_left !== null) { · {{ c.years_left }} left }</td>
                  <td>
                    @if (c.metric) {
                      {{ metricValue(c) }} <span class="muted">{{ metricLabel(c.metric) }}, {{ c.games ?? 0 }} gm</span>
                    } @else { <span class="muted">–</span> }
                  </td>
                  <td>{{ c.qualified ? pctile(c.production_pct) : '–' }}@if (!c.qualified) { <span class="muted small">n/q</span> }</td>
                  <td>{{ pctile(c.expected_pct) }} <span class="muted small">{{ c.basis === 'model' ? 'model' : 'cost' }}</span></td>
                  <td [class.pos]="(c.value_gap ?? 0) > 0.08" [class.neg]="(c.value_gap ?? 0) < -0.08">{{ spct(c.value_gap) }}</td>
                  <td><app-grade-chip [grade]="c.grade" [title]="c.run_id ? 'MLflow run ' + c.run_id : 'graded against cost'" /></td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    }
  `,
  styles: `
    .top { margin-top: 1rem; }
    .small { font-size: 0.8rem; }
    ul.small { padding-left: 1.1rem; margin: 0; }
    ul.small li { margin-bottom: 0.4rem; }
    .bar { display: flex; flex-wrap: wrap; gap: 1rem; align-items: end; margin-bottom: 0.75rem; }
    .bar label { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.8rem; color: var(--muted); }
    .bar select { background: var(--panel-2); color: var(--text); border: 1px solid var(--line-2); border-radius: 6px; padding: 0.3rem 0.5rem; font: inherit; font-size: 0.9rem; }
    .count { align-self: center; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; white-space: nowrap; font-size: 0.9rem; }
    th, td { text-align: right; padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--line); }
    th { color: var(--muted); font-weight: 500; font-size: 0.8rem; cursor: pointer; user-select: none; }
    th.on { color: var(--gold); }
    th:nth-child(-n + 3), td:nth-child(-n + 3), th:nth-child(6), td:nth-child(6), th:nth-child(7), td:nth-child(7) { text-align: left; }
    td.pos { color: var(--good); }
    td.neg { color: var(--bad); }
  `,
})
export class AcquisitionsPage {
  private readonly api = inject(ApiService);
  readonly data = toSignal<Acquisitions | null | undefined>(this.api.gmAcquisitions().pipe(catchError(() => of(null))));
  readonly season = signal('');
  readonly how = signal('');
  readonly sort = signal<SortKey>('value_gap');
  readonly desc = signal(true);
  readonly money = fmtMoney;
  readonly pctile = fmtPctile;
  readonly spct = fmtSignedPct;
  readonly num = fmtNum;

  readonly seasons = computed(() => [...new Set((this.data()?.cards ?? []).map((c) => c.arrival_season))].sort((a, b) => b - a));
  readonly hows = computed(() => [...new Set((this.data()?.cards ?? []).map((c) => c.how))].sort((a, b) => a.localeCompare(b)));
  readonly counts = computed(() => {
    const by = new Map<string, number>();
    for (const c of this.data()?.cards ?? []) by.set(c.how, (by.get(c.how) ?? 0) + 1);
    return [...by.entries()].map(([h, n]) => `${n} ${h}`).join(', ');
  });
  readonly modelShare = computed(() => {
    const cards = this.data()?.cards ?? [];
    const n = cards.filter((c) => c.basis === 'model').length;
    return `${n} of ${cards.length}`;
  });

  readonly rows = computed(() => {
    const key = this.sort();
    const dir = this.desc() ? -1 : 1;
    return (this.data()?.cards ?? [])
      .filter((c) => (!this.season() || `${c.arrival_season}` === this.season()) && (!this.how() || c.how === this.how()))
      .sort((a, b) => {
        const x = a[key];
        const y = b[key];
        if (x == null && y == null) return 0;
        if (x == null) return 1;
        if (y == null) return -1;
        return (typeof x === 'string' ? x.localeCompare(y as string) : (x as number) - (y as number)) * dir;
      });
  });

  sortBy(key: SortKey): void {
    if (this.sort() === key) this.desc.update((d) => !d);
    else {
      this.sort.set(key);
      this.desc.set(key !== 'name' && key !== 'how');
    }
  }

  value(e: Event): string {
    return (e.target as HTMLSelectElement).value;
  }

  metricLabel(m: string): string {
    return METRIC_LABEL[m] ?? m;
  }

  metricValue(c: AcquisitionCard): string {
    if (c.production == null) return '–';
    if (c.metric === 'snap_share') return fmtPct(c.production);
    if (c.metric === 'passer_rating_allowed') return fmtNum(c.production, 1);
    return fmtNum(c.production, 3);
  }
}
