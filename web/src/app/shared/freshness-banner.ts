import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ApiService } from '../core/api.service';

/** Says which week the data runs through, or that the first ingest has not happened yet. */
@Component({
  selector: 'app-freshness-banner',
  template: `
    @let f = freshness();
    <p class="fresh">
      @if (f?.through_week) {
        {{ f?.season }} season, data through week {{ f?.through_week }} (ingested {{ f?.last_ingest }})
      } @else {
        No game data ingested yet — the nightly job fills this in.
      }
    </p>
  `,
  styles: `.fresh { color: var(--muted); font-size: 0.85rem; margin: 0.25rem 0 1rem; }`,
})
export class FreshnessBanner {
  private readonly api = inject(ApiService);
  readonly freshness = toSignal(this.api.freshness(), { initialValue: null });
}
