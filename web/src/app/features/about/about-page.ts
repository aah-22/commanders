import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { catchError, of } from 'rxjs';
import { ApiService, Models } from '../../core/api.service';

/** Where the numbers come from: the data lineage, the models behind the GM pages and the last jobs that ran. */
@Component({
  selector: 'app-about-page',
  template: `
    <p class="caabi-kicker">Front office</p>
    <h1>About the numbers</h1>
    <div class="grid cols-2">
      <div class="panel">
        <h2>Data</h2>
        <p class="muted small">
          Everything starts as nflverse releases (play by play, player and team stats, snap counts, weekly rosters, depth charts,
          injuries, PFR advanced stats, Next Gen Stats, draft picks, trades and OverTheCap contracts), mirrored nightly into
          Postgres with the file digest of every asset recorded, then derived into team-game summaries, standings,
          per-player production with position percentiles, arrivals and positional need. No betting lines or odds are stored.
        </p>
        <h2>Models</h2>
        <p class="muted small">
          <b>production-next</b> projects next season's production percentile from this season's, the one before, age, snaps,
          experience and draft slot. <b>acquisition-value</b> learns the percentile a contract's APY percentile, age and pedigree
          usually buy at the position, so an arrival is graded on actual minus expected. <b>target-rank</b> is a tracked formula, not
          a learned model: need at the position × projected percentile × an age discount. Each is trained with a season held out
          and only replaces the champion when it beats both the champion and the naive forecast on that hold-out.
        </p>
      </div>
      <div class="panel">
        <h2>Lineage</h2>
        @let m = models();
        @if (m === undefined) {
          <p class="muted">Loading…</p>
        } @else if (m === null) {
          <p>The model inventory is unavailable right now.</p>
        } @else {
          <p class="muted small">MLflow experiment <code>{{ m.experiment }}</code> at <a [href]="m.tracking" target="_blank" rel="noopener">{{ m.tracking }}</a>. Every scored row on the GM pages carries the run id below.</p>
          @if (m.outputs.length) {
            <table>
              <thead><tr><th>Model</th><th>Season</th><th>Version</th><th>Rows</th><th>Run</th></tr></thead>
              <tbody>
                @for (o of m.outputs; track o.model + o.season + o.version) {
                  <tr><td>{{ o.model }}</td><td>{{ o.season }}</td><td>{{ o.version ?? '–' }}</td><td>{{ o.rows }}</td><td><code>{{ o.run_id ?? '–' }}</code></td></tr>
                }
              </tbody>
            </table>
          } @else {
            <p class="muted">No model has scored a season yet.</p>
          }
          @if (m.jobs.length) {
            <h3>Last jobs</h3>
            <table>
              <thead><tr><th>Job</th><th>Status</th><th>Season</th><th>Finished</th></tr></thead>
              <tbody>
                @for (j of m.jobs; track j.kind) {
                  <tr><td>{{ j.kind }}</td><td [class.bad]="j.status !== 'ok'">{{ j.status }}</td><td>{{ j.season ?? '–' }}</td><td class="muted">{{ j.finished_at }}</td></tr>
                }
              </tbody>
            </table>
          }
        }
      </div>
    </div>
  `,
  styles: `
    .small { font-size: 0.9rem; }
    h3 { margin-top: 1rem; font-size: 1rem; }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 0.85rem; }
    th, td { text-align: left; padding: 0.25rem 0.4rem; border-bottom: 1px solid var(--line); }
    code { font-size: 0.75rem; color: var(--muted); }
    td.bad { color: var(--bad); }
  `,
})
export class AboutPage {
  private readonly api = inject(ApiService);
  readonly models = toSignal<Models | null | undefined>(this.api.models().pipe(catchError(() => of(null))));
}
