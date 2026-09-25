import { Component, input } from '@angular/core';

/** One number with its label and an optional delta line, the building block of every dashboard row. */
@Component({
  selector: 'app-stat-tile',
  template: `
    <div class="panel tile">
      <div class="label">{{ label() }}</div>
      <div class="value">{{ value() }}</div>
      @if (delta()) {
        <div class="delta">{{ delta() }}</div>
      }
    </div>
  `,
  styles: `
    .tile { text-align: left; }
    .label { color: var(--muted); font-size: 0.8rem; }
    .value { font-size: 1.8rem; font-weight: 600; color: var(--primary); }
    .delta { color: var(--muted); font-size: 0.85rem; }
  `,
})
export class StatTile {
  readonly label = input.required<string>();
  readonly value = input.required<string>();
  readonly delta = input<string>();
}
