import { Component, computed, inject } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { catchError, map, of, switchMap } from 'rxjs';
import { ApiService, Need, Targets } from '../../core/api.service';
import { fmtMoney, fmtNum, fmtPctile } from '../../core/format';
import { NeedChart } from './need-chart';

const GROUPS = ['QB', 'RB', 'WR', 'TE', 'OL', 'IDL', 'ED', 'LB', 'CB', 'S', 'ST'];

/** Need by position group, then the target board: pending free agents and productive players on losing teams. */
@Component({
  selector: 'app-targets-page',
  imports: [NeedChart],
  template: `
    <p class="caabi-kicker">Front office</p>
    <h1>Target board</h1>
    @let n = need();
    @if (n === undefined) {
      <div class="panel"><p class="muted">Loading…</p></div>
    } @else if (n === null) {
      <div class="panel"><p>The need index is unavailable right now; try again in a minute.</p></div>
    } @else {
      <app-need-chart [groups]="n.groups" />
    }
    @let t = targets();
    <div class="panel top">
      <div class="head">
        <h2>Targets</h2>
        <label>Position
          <select [value]="position() ?? ''" (change)="setPosition(value($event))">
            <option value="">Top {{ perGroup }} per group</option>
            @for (g of groups; track g) { <option [value]="g">{{ g }}</option> }
          </select>
        </label>
        @if (t?.live) { <span class="chip" title="The nightly score job has not run for this season; the same formula was applied on request.">live</span> }
      </div>
      <p class="muted small">
        Who to go get: players not on {{ t?.team ?? 'the team' }} whose contract ends this season, or who are producing on a team at .350 or worse.
        Score = need at the position × projected production percentile (the production-next model where it has scored, else this season's) × 0.7 past the position's peak age.
      </p>
      @if (t === undefined) {
        <p class="muted">Loading…</p>
      } @else if (t === null) {
        <p>The target board is unavailable right now; try again in a minute.</p>
      } @else if (!t.targets.length) {
        <p class="muted">Nobody qualifies yet{{ position() ? ' at ' + position() : '' }}.</p>
      } @else {
        <div class="scroll">
          <table>
            <thead><tr><th>#</th><th>Player</th><th>Team</th><th>Why</th><th>Age</th><th>Now</th><th>Projected</th><th>APY</th><th>Left</th><th>Need</th><th>Score</th></tr></thead>
            <tbody>
              @for (x of t.targets; track x.gsis_id; let i = $index) {
                <tr>
                  <td>{{ i + 1 }}</td>
                  <td><b>{{ x.name }}</b> <span class="muted">{{ x.position ?? x.pos_group }}</span></td>
                  <td>{{ x.team }}</td>
                  <td>{{ x.reason }}</td>
                  <td>{{ num(x.age, 1) }}</td>
                  <td>{{ pctile(x.production_pct) }}</td>
                  <td [title]="x.projection_run_id ? 'MLflow run ' + x.projection_run_id : 'no projection yet'">{{ pctile(x.projected_pct) }}</td>
                  <td>{{ money(x.apy) }}</td>
                  <td>{{ x.years_left ?? '–' }}</td>
                  <td>{{ num(x.need_score, 0) }}</td>
                  <td class="score">{{ num(x.score, 3) }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
        <p class="muted small">{{ t.live ? 'Computed on request.' : 'Scored ' + t.scored_at + '.' }} Every row carries its MLflow run id in the API response.</p>
      }
    </div>
  `,
  styles: `
    .top { margin-top: 1rem; }
    .small { font-size: 0.85rem; }
    .head { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
    .head h2 { margin: 0; }
    .head label { display: flex; gap: 0.4rem; align-items: center; font-size: 0.8rem; color: var(--muted); }
    select { background: var(--panel-2); color: var(--text); border: 1px solid var(--line-2); border-radius: 6px; padding: 0.3rem 0.5rem; font: inherit; font-size: 0.9rem; }
    .chip { padding: 0 0.5rem; border: 1px solid var(--gold); border-radius: 999px; color: var(--gold); font-size: 0.75rem; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; white-space: nowrap; font-size: 0.9rem; }
    th, td { text-align: right; padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--line); }
    th { color: var(--muted); font-weight: 500; font-size: 0.8rem; }
    th:nth-child(-n + 4), td:nth-child(-n + 4) { text-align: left; }
    td.score { color: var(--gold); font-weight: 600; }
  `,
})
export class TargetsPage {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly groups = GROUPS;
  readonly perGroup = 8;
  readonly num = fmtNum;
  readonly pctile = fmtPctile;
  readonly money = fmtMoney;

  readonly position = toSignal(
    this.route.queryParamMap.pipe(map((q) => (GROUPS.includes(q.get('position') ?? '') ? q.get('position') : null))),
    { initialValue: null },
  );
  readonly need = toSignal<Need | null | undefined>(this.api.gmNeed().pipe(catchError(() => of(null))));
  readonly targets = toSignal<Targets | null | undefined>(
    toObservable(this.position).pipe(switchMap((p) => this.api.gmTargets(p).pipe(catchError(() => of(null))))),
  );
  readonly count = computed(() => this.targets()?.targets.length ?? 0);

  setPosition(p: string): void {
    void this.router.navigate([], { relativeTo: this.route, queryParams: { position: p || null }, replaceUrl: true });
  }

  value(e: Event): string {
    return (e.target as HTMLSelectElement).value;
  }
}
