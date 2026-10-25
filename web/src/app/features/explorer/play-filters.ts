import { Component, input, output } from '@angular/core';
import { DistanceBucket, PlayFilters, PlayKind, PlayTag } from '../../core/api.service';

const KINDS: { value: PlayKind; label: string }[] = [
  { value: 'all', label: 'All plays' },
  { value: 'scrimmage', label: 'Pass + run' },
  { value: 'pass', label: 'Pass' },
  { value: 'run', label: 'Run' },
  { value: 'special', label: 'Special teams' },
];
const BUCKETS: { value: DistanceBucket; label: string }[] = [
  { value: 'short', label: '1–3' },
  { value: 'mid', label: '4–6' },
  { value: 'long', label: '7–10' },
  { value: 'xlong', label: '11+' },
];
const QUARTERS: { value: number; label: string }[] = [
  { value: 1, label: 'Q1' },
  { value: 2, label: 'Q2' },
  { value: 3, label: 'Q3' },
  { value: 4, label: 'Q4' },
  { value: 5, label: 'OT' },
];
export const TAGS: { value: PlayTag; label: string }[] = [
  { value: 'big_swing', label: 'Big WP swings' },
  { value: 'explosive', label: 'Explosive plays' },
  { value: 'play_action', label: 'Play action' },
  { value: 'screen', label: 'Screens' },
  { value: 'rpo', label: 'RPO' },
  { value: 'motion', label: 'Pre-snap motion' },
  { value: 'no_huddle', label: 'No huddle' },
  { value: 'scramble', label: 'Scrambles' },
  { value: 'pressure', label: 'Pressure (sack or hit)' },
  { value: 'blitz', label: 'Blitzed' },
  { value: 'light_box', label: 'Light box (6 or fewer)' },
  { value: 'penalty', label: 'Penalties' },
];

/** Offense / type / quarter / down / distance / red zone / drive / tag selects; each change emits the whole filter set. */
@Component({
  selector: 'app-play-filters',
  template: `
    <div class="filters">
      <label>Offense
        <select [value]="filters().posteam ?? ''" (change)="set('posteam', value($event))">
          <option value="">Both</option>
          @for (t of teams(); track t) { <option [value]="t">{{ t }}</option> }
        </select>
      </label>
      <label>Plays
        <select [value]="filters().type ?? 'all'" (change)="set('type', value($event))">
          @for (k of kinds; track k.value) { <option [value]="k.value">{{ k.label }}</option> }
        </select>
      </label>
      <label>Quarter
        <select [value]="filters().qtr ?? ''" (change)="set('qtr', value($event))">
          <option value="">Any</option>
          @for (q of quarters; track q.value) { <option [value]="q.value">{{ q.label }}</option> }
        </select>
      </label>
      <label>Down
        <select [value]="filters().down ?? ''" (change)="set('down', value($event))">
          <option value="">Any</option>
          @for (d of [1, 2, 3, 4]; track d) { <option [value]="d">{{ d }}</option> }
        </select>
      </label>
      <label>To go
        <select [value]="filters().distance ?? ''" (change)="set('distance', value($event))">
          <option value="">Any</option>
          @for (b of buckets; track b.value) { <option [value]="b.value">{{ b.label }}</option> }
        </select>
      </label>
      <label>Drive
        <select [value]="filters().drive ?? ''" (change)="set('drive', value($event))">
          <option value="">All</option>
          @for (d of drives(); track d) { <option [value]="d">{{ d }}</option> }
        </select>
      </label>
      <label>Show only
        <select [value]="filters().tag ?? ''" (change)="set('tag', value($event))">
          <option value="">Everything</option>
          @for (t of tags; track t.value) { <option [value]="t.value">{{ t.label }}</option> }
        </select>
      </label>
      <label class="check"><input type="checkbox" [checked]="filters().rz ?? false" (change)="set('rz', checked($event))" /> Red zone</label>
      @if (active()) {
        <button type="button" (click)="changed.emit({})">Clear</button>
      }
    </div>
  `,
  styles: `
    .filters { display: flex; flex-wrap: wrap; gap: 0.6rem 0.9rem; align-items: end; margin-bottom: 0.75rem; }
    label { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.8rem; color: var(--muted); }
    label.check { flex-direction: row; align-items: center; gap: 0.4rem; min-height: 44px; }
    select, button { min-height: 40px; background: var(--panel-2); color: var(--text); border: 1px solid var(--line-2); border-radius: 6px; padding: 0.3rem 0.5rem; font: inherit; font-size: 0.9rem; }
    button { color: var(--gold); cursor: pointer; }
    input[type='checkbox'] { accent-color: var(--gold); width: 1.1rem; height: 1.1rem; }
  `,
})
export class PlayFiltersBar {
  readonly filters = input.required<PlayFilters>();
  readonly teams = input.required<string[]>();
  readonly drives = input<number[]>([]);
  readonly changed = output<PlayFilters>();
  readonly kinds = KINDS;
  readonly buckets = BUCKETS;
  readonly quarters = QUARTERS;
  readonly tags = TAGS;

  active(): boolean {
    const f = this.filters();
    return Boolean(f.posteam || f.down || f.distance || f.rz || f.drive || f.qtr || f.tag || (f.type && f.type !== 'all'));
  }

  value(e: Event): string {
    return (e.target as HTMLSelectElement).value;
  }

  checked(e: Event): boolean {
    return (e.target as HTMLInputElement).checked;
  }

  set(key: keyof PlayFilters, raw: string | boolean): void {
    const next: PlayFilters = { ...this.filters() };
    if (raw === '' || raw === false) {
      delete next[key];
    } else if (key === 'down' || key === 'drive' || key === 'qtr') {
      next[key] = Number(raw);
    } else if (key === 'rz') {
      next.rz = true;
    } else if (key === 'type') {
      next.type = raw as PlayKind;
    } else if (key === 'distance') {
      next.distance = raw as DistanceBucket;
    } else if (key === 'tag') {
      next.tag = raw as PlayTag;
    } else {
      next.posteam = raw as string;
    }
    this.changed.emit(next);
  }
}
